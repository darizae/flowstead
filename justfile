# Local PostgreSQL task entry points. Credentials come only from .env or the
# documented local defaults in compose.yml.
set dotenv-load := true

db-up:
    python3 backend/tests/db_lifecycle.py

db-down:
    docker compose down

db-upgrade:
    uv run --project backend python -m backend.migrate upgrade

db-current:
    uv run --project backend python -m backend.migrate current

migrate-local: db-upgrade
import-m1-local manifest source_sha data:
    uv run --project backend python -m backend.importer --manifest "{{manifest}}" --data "{{data}}" --source-sha "{{source_sha}}"


forecast-local:
    uv run --project backend python -m flowstead_api.forecast

message-up:
    docker compose up -d --wait db nats

message-init:
    uv run --project backend python -m flowstead_api.messaging init

message-dispatch-once:
    uv run --project backend python -m flowstead_api.messaging dispatch

message-worker-once:
    uv run --project backend python -m flowstead_api.messaging worker

message-worker:
    uv run --project backend python -m flowstead_api.messaging run

test-message-unit:
    uv run --project backend pytest -q backend/tests/unit/test_messages.py

test-message-integration:
    python3 backend/tests/db_lifecycle.py --require-database-url
    docker compose up -d --wait nats
    FLOWSTEAD_ISOLATED_NATS_TEST=1 uv run --project backend pytest -q backend/tests/integration/test_messaging.py

test-forecast-unit:
    uv run --project backend pytest -q backend/tests/unit/test_forecast.py

test-forecast-integration:
    python3 backend/tests/db_lifecycle.py --require-database-url
    uv run --project backend pytest -q backend/tests/integration/test_forecast.py

check-backend:
    uv run --project backend python -m compileall -q backend

test-backend-unit:
    uv run --project backend pytest -q backend/tests/unit

test-db-integration:
    python3 backend/tests/db_lifecycle.py --require-database-url
    uv run --project backend pytest -q backend/tests/integration

audit-backend:
    #!/usr/bin/env zsh
    set -euo pipefail
    uv tool run --from 'pip-audit==2.10.1' pip-audit --requirement <(uv export --quiet --project backend --locked --no-emit-project --format requirements.txt) --require-hashes --disable-pip --strict --progress-spinner off

docs-check:
    python3 scripts/docs_check.py

api-dev:
    uv run --project backend uvicorn flowstead_api.main:app --app-dir backend/src --host 127.0.0.1 --port 8000

test-api-unit:
    uv run --project backend pytest -q backend/tests/unit/test_api_contract.py
test-report:
    uv run --project backend pytest -q backend/tests/unit/test_report.py backend/tests/integration/test_api.py -k report


test-api-integration:
    python3 backend/tests/db_lifecycle.py --require-database-url
    uv run --project backend pytest -q backend/tests/integration/test_api.py

test-auth:
    uv run --project backend pytest -q backend/tests/unit/test_auth.py
    python3 backend/tests/db_lifecycle.py --require-database-url
    uv run --project backend pytest -q backend/tests/integration/test_auth.py

frontend-dev:
    npm --prefix frontend run dev -- --host 127.0.0.1

test-frontend-unit:
    npm --prefix frontend test -- --run

frontend-typecheck:
    npm --prefix frontend run typecheck

frontend-build:
    npm --prefix frontend run build

audit-frontend:
    npm --prefix frontend audit --audit-level=moderate

test-e2e-local:
    #!/usr/bin/env zsh
    set -euo pipefail
    export DATABASE_URL="${DATABASE_URL:-postgresql://flowstead:flowstead_local@127.0.0.1:${POSTGRES_PORT:-54329}/flowstead}"
    python3 backend/tests/db_lifecycle.py --require-database-url
    uv run --project backend python frontend/e2e/run_local.py

# One-command local stack: Docker PostgreSQL + NATS, Alembic upgrade, JetStream
# topology, FastAPI API, durable forecast worker and the Vite frontend.
dev:
    #!/usr/bin/env zsh
    set -euo pipefail
    cd {{ justfile_directory() }}

    export DATABASE_URL="${DATABASE_URL:-postgresql://flowstead:flowstead_local@127.0.0.1:${POSTGRES_PORT:-54329}/flowstead}"
    export NATS_URL="${NATS_URL:-nats://127.0.0.1:${NATS_PORT:-42229}}"
    # flowstead_api.database imports backend.importer; the repo root must be
    # importable (same contract as backend/tests/db_lifecycle.py consumers).
    export PYTHONPATH="{{ justfile_directory() }}${PYTHONPATH:+:$PYTHONPATH}"

    for port in 8000 5173; do
        if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
            echo "just dev: 127.0.0.1:$port is already in use; free it first" >&2
            exit 1
        fi
    done

    echo "== Frontend dependencies =="
    if [ ! -d frontend/node_modules ]; then
        npm --prefix frontend install
    else
        echo "frontend/node_modules present, skipping npm install"
    fi

    echo "== Docker PostgreSQL + NATS =="
    just message-up

    echo "== Alembic schema upgrade =="
    just db-upgrade

    echo "== JetStream stream/consumer topology =="
    just message-init

    plant_count=$(docker compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD:-flowstead_local}" db psql -U "${POSTGRES_USER:-flowstead}" -d "${POSTGRES_DB:-flowstead}" -tAc "select count(*) from app.plants" || echo 0)
    if [ "$plant_count" = "0" ]; then
        echo "NOTE: app.plants is empty; the API serves /api/v1/health only."
        echo "      Import M1 data first, e.g.: just import-m1-local <manifest> ad5c94d1f46e79312a99cb9721f38700f24fdf6b <telemetry.csv>"
    else
        echo "app.plants rows: $plant_count"
    fi

    cleanup() {
        [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null
        [ -n "${WORKER_PID:-}" ] && kill "$WORKER_PID" 2>/dev/null
        [ -n "${FE_PID:-}" ] && kill "$FE_PID" 2>/dev/null
        wait 2>/dev/null
    }
    trap cleanup EXIT INT TERM

    echo "== FastAPI on http://127.0.0.1:8000 (frontend proxies /api) =="
    uv run --project backend uvicorn flowstead_api.main:app --app-dir backend/src --host 127.0.0.1 --port 8000 &
    API_PID=$!

    echo "== JetStream dispatch/forecast worker =="
    uv run --project backend python -m flowstead_api.messaging run &
    WORKER_PID=$!

    echo "== Vite frontend on http://127.0.0.1:5173 =="
    (cd frontend && exec ./node_modules/.bin/vite --host 127.0.0.1 --port 5173) &
    FE_PID=$!

    echo "Flowstead dev stack is up: frontend http://127.0.0.1:5173, API http://127.0.0.1:8000/api/v1/health"
    wait

dev-down:
    docker compose down

default:
    @just --list
