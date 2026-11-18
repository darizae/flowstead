# Flowstead

Flowstead is a wastewater-plant operations demonstration for five fictional small Florida treatment Plants. It provides a bounded synthetic-data API and is being developed into an interactive Plants map, monitoring history, twelve-hour influent-flow forecasts, and authorized CSV/PNG/PDF exports. It does not connect to operational equipment.

**Current implementation:** local PostgreSQL Alembic migrations, schema/importer, FastAPI read endpoints and deterministic forecast baseline exist. NATS/JetStream asynchronous processing, React frontend and hosted deployment remain planned; do not treat the planned UI or hosted demo as available.

## Start with the active contracts

- [Implementation contract](docs/planning/IMPLEMENTATION_SPEC.md) — product, API, data, authorization and runtime module ownership.
- [Ordered task sequence](docs/planning/HANDOFF_SEQUENCE.md) — exact tasks, prerequisites and current implementation gates.
- [Design and UI parity](docs/design/UI_UX_BASELINE.md) — screens/states and [local visual reference](docs/design/reference/flowstead-ui.html).
- [Test cases](docs/testing/INDEXED_TEST_PLAN.md) — stable case IDs and actual required evidence.
- [Deployment architecture](docs/setup/DEPLOYMENT_ARCHITECTURE.md) — local/development/demo environments and external approvals.

## Existing local backend workflow

Prerequisites: Python 3.11–3.13, uv, Docker Compose and [just](https://just.systems/). Run from repository root. Existing commands use local PostgreSQL only.

~~~sh
just --list
just db-up
just db-upgrade
just db-current
just test-backend-unit
just test-db-integration
just test-api-integration
just test-forecast-unit
just test-forecast-integration
just docs-check
~~~

To import the accepted M1 synthetic fixture, obtain the independent generator's output at the pinned source revision and run:

~~~sh
just import-m1-local <manifest-path> <source-commit-sha> <data-csv-path>
~~~

See [the implementation contract](docs/planning/IMPLEMENTATION_SPEC.md) for the pinned source and checksum. The integration recipes first run `backend/tests/db_lifecycle.py --require-database-url`, a bounded, owner-aware Docker PostgreSQL preflight. It checks the configured `127.0.0.1:${POSTGRES_PORT:-54329}` binding and local `DATABASE_URL`, reuses a healthy database only when its configured Compose project/service and canonical checkout/Compose-file identity match (set `COMPOSE_PROJECT_NAME` for an explicitly named controller project), starts that owned stopped instance, restarts that owned unhealthy instance once, and waits for Docker health plus TCP readiness. If a foreign container/process owns the port or ownership is ambiguous, it fails without stopping or replacing that service. The standalone `just db-up` uses the same preflight without requiring `DATABASE_URL`. Migration tests use isolated, uniquely named local `flowstead_test_<uuid>` databases; destructive rollback is refused elsewhere. The integration commands require a working local Docker daemon and appropriate local environment. No hosted project, invitation, deployment or secret is provisioned by these commands. Dependency audits should use just audit-backend; when no supported audit executable is installed the recipe reports UNVERIFIED.