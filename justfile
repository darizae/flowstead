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
    if uv help | grep -qE '(^|[[:space:]])audit([[:space:]]|$)'; then uv audit --project backend; elif command -v pip-audit >/dev/null 2>&1; then pip-audit; else echo "UNVERIFIED: neither uv audit nor pip-audit is available"; fi

docs-check:
    uv run --project backend python -m backend.docs_check

api-dev:
    uv run --project backend uvicorn flowstead_api.main:app --app-dir backend/src --host 127.0.0.1 --port 8000

test-api-unit:
    uv run --project backend pytest -q backend/tests/unit/test_api_contract.py

test-api-integration:
    python3 backend/tests/db_lifecycle.py --require-database-url
    uv run --project backend pytest -q backend/tests/integration/test_api.py

default:
    @just --list
