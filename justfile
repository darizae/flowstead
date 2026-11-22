# Local PostgreSQL task entry points. Credentials come only from .env or the
# documented local defaults in compose.yml.
set dotenv-load := true

db-up:
    python3 scripts/db_lifecycle.py

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
    python3 scripts/db_lifecycle.py --require-database-url
    docker compose up -d --wait nats
    FLOWSTEAD_ISOLATED_NATS_TEST=1 uv run --project backend pytest -q backend/tests/integration/test_messaging.py

test-forecast-unit:
    uv run --project backend pytest -q backend/tests/unit/test_forecast.py

test-forecast-integration:
    python3 scripts/db_lifecycle.py --require-database-url
    uv run --project backend pytest -q backend/tests/integration/test_forecast.py

check-backend:
    python3 scripts/check_architecture.py
    uv run --project backend ruff check backend/src backend/importer.py backend/migrate.py backend/tests
    uv run --project backend ruff format --check backend/src backend/importer.py backend/migrate.py backend/tests
    uv run --project backend python -m compileall -q backend

format-backend:
    uv run --project backend ruff check --fix backend/src backend/importer.py backend/migrate.py backend/tests
    uv run --project backend ruff format backend/src backend/importer.py backend/migrate.py backend/tests

lint: check-backend
    npm --prefix frontend run lint
    npm --prefix frontend run format:check

format: format-backend
    npm --prefix frontend run format

test: test-backend-unit test-frontend-unit

coverage:
    uv run --project backend --with pytest-cov pytest --cov=flowstead_api.domain --cov-fail-under=60 --cov-report=term-missing backend/tests/unit
    npm --prefix frontend run test:coverage

check: lint typecheck-backend frontend-typecheck test docs-check

test-backend-unit:
    uv run --project backend pytest -q backend/tests/unit

test-db-integration:
    python3 scripts/db_lifecycle.py --require-database-url
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
    python3 scripts/db_lifecycle.py --require-database-url
    uv run --project backend pytest -q backend/tests/integration/test_api.py

test-auth:
    uv run --project backend pytest -q backend/tests/unit/test_auth.py
    python3 scripts/db_lifecycle.py --require-database-url
    uv run --project backend pytest -q backend/tests/integration/test_auth.py

# T-014 dev smoke: proves the local half of the Supabase integration without a
# hosted project — migration head + JWT verification (signature/issuer/audience)
# and SQL 401/404 Plant authorization against a disposable local PostgreSQL.
# Live Supabase operations require an owner-supplied admin connection string and
# invitation recipients; see docs/setup/DEV_SUPABASE.md.
dev-smoke:
    #!/usr/bin/env zsh
    set -euo pipefail
    export DATABASE_URL="${DATABASE_URL:-postgresql://flowstead:flowstead_local@127.0.0.1:${POSTGRES_PORT:-54329}/flowstead}"
    python3 scripts/db_lifecycle.py --require-database-url
    uv run --project backend pytest -q backend/tests/integration/test_migrations.py -k "head or stamp or reversible"
    uv run --project backend pytest -q backend/tests/unit/test_auth.py
    uv run --project backend pytest -q backend/tests/integration/test_auth.py

frontend-dev:
    npm --prefix frontend run dev -- --host 127.0.0.1

test-frontend-unit:
    npm --prefix frontend test -- --run

frontend-typecheck:
    npm --prefix frontend run typecheck

# Audit #45: strict static typing over the pure domain/application modules.
typecheck-backend:
    cd backend && uv run mypy

frontend-build:
    npm --prefix frontend run build

# Production backend+worker image from the committed uv.lock; non-root, no
# secrets baked in. Build context is backend/ (Dockerfile + .dockerignore there).
build-backend-image:
    docker build -f backend/Dockerfile -t flowstead-backend:local backend

# Production static frontend build configured for an explicit HTTPS API URL.
# Default is the proposed (NOT assigned) host-separated API; override with
# VITE_API_URL for a real target.
build:
    VITE_API_URL=$${VITE_API_URL:-https://api.flowstead.darizae.dev/api/v1} npm --prefix frontend run build

# Local staging-like container acceptance (OPS-M15-BUILD, IT-M15-START,
# SEC-M15-CONFIG, OPS-M15-RECOVER): real PostgreSQL + NATS/JetStream, Alembic
# upgrade-to-head, M1 import, API/health/bounds/CORS/auth, outbox replay through
# a worker restart, and backup/reseed/rollback on a disposable DB copy.
build-smoke: build-backend-image build
    uv run --project backend python scripts/test_deploy_local.py

test-deploy-local: build-smoke

# AMD64 backend image for the OCI existing micro VM (OPS-M16-ARM): explicit linux/amd64
# build + load, tagged for compose.hosted.yml. Same uv.lock-driven Dockerfile;
# no secrets baked in.
build-backend-image-host:
    docker build --platform linux/amd64 --load -f backend/Dockerfile -t flowstead-backend:amd64-hosted backend

# Verify linux/amd64 image arch + pinned NATS/Caddy amd64 manifests/digests.
verify-hosted-host:
    #!/usr/bin/env zsh
    set -euo pipefail
    echo "backend image: $(docker image inspect flowstead-backend:amd64-hosted | jq -r '.[0].Os + "/" + .[0].Architecture')"
    echo "nats amd64 manifest:"
    docker manifest inspect 'nats:2.12-alpine@sha256:b270f5e2428354c0335612694d7dd2fb588148e567a5757fdff325ef9c9332e6' | jq -r '.manifests[] | select(.platform.architecture=="amd64") | .digest'
    echo "caddy amd64 manifest:"
    docker manifest inspect 'caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d' | jq -r '.manifests[] | select(.platform.architecture=="amd64") | .digest'

# Static-validation of compose.hosted.yml (syntax, no local PostgreSQL, secret
# env-file path).
hosted-config-validate:
    #!/usr/bin/env bash
    set -euo pipefail
    HOSTED_ENV_FILE="${HOSTED_ENV_FILE:-/dev/null}" docker compose -f compose.hosted.yml config --quiet

# Hosted-config acceptance (OPS-M16-ARM, OPS-M16-QUEUE, SEC-M16-NET) against a
# disposable EXTERNAL PostgreSQL; compose.hosted.yml itself starts no db.
test-deploy-hosted: build-backend-image-host
    uv run --project backend python scripts/test_deploy_hosted.py

audit-frontend:
    npm --prefix frontend audit --audit-level=moderate

test-e2e-local:
    #!/usr/bin/env zsh
    set -euo pipefail
    export DATABASE_URL="${DATABASE_URL:-postgresql://flowstead:flowstead_local@127.0.0.1:${POSTGRES_PORT:-54329}/flowstead}"
    python3 scripts/db_lifecycle.py --require-database-url
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
    # importable (same contract as scripts/db_lifecycle.py consumers).
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

# Read-only diagnostics; safe to run repeatedly on the approved existing VM.
oci-diagnose:
    python3 scripts/recover_oci_demo.py

# Explicit bounded START/SOFTRESET; refuses transitional states and healthy guests.
oci-recover:
    python3 scripts/recover_oci_demo.py --recover
