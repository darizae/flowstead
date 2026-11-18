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
    uv run --project backend python frontend/e2e/run_local.py

default:
    @just --list
