# Flowstead

Flowstead is a wastewater-plant operations demonstration for five fictional small Florida treatment Plants. It provides a bounded synthetic-data API and is being developed into an interactive Plants map, monitoring history, twelve-hour influent-flow forecasts, and authorized CSV/PNG/PDF exports. It does not connect to operational equipment.

**Current implementation:** local PostgreSQL Alembic migrations, the validated M1 importer, deterministic twelve-hour forecasting, Plant-scoped FastAPI reads and asynchronous forecast commands, a fail-closed Supabase-compatible JWT verifier, and a PostgreSQL-outbox/NATS JetStream dispatcher and durable worker exist. The React frontend and hosted deployment remain planned; do not treat the planned UI or hosted demo as available.

## Start with the active contracts

- [Implementation contract](docs/planning/IMPLEMENTATION_SPEC.md) — product, API, data, authorization and runtime module ownership.
- [Ordered task sequence](docs/planning/HANDOFF_SEQUENCE.md) — task navigation and source-backed implementation history, not a start gate.
- [Design and UI parity](docs/design/UI_UX_BASELINE.md) — screens/states and [local visual reference](docs/design/reference/flowstead-ui.html).
- [Test cases](docs/testing/INDEXED_TEST_PLAN.md) — stable case IDs and actual required evidence.
- [Deployment architecture](docs/setup/DEPLOYMENT_ARCHITECTURE.md) — local/development/demo environments and external approvals.

## Existing local backend workflow

Prerequisites: Python 3.11–3.13, uv, Docker Compose and [just](https://just.systems/). Run from repository root. Existing commands use loopback-only local PostgreSQL and NATS/JetStream services.

~~~sh
just --list
just db-up
just db-upgrade
just db-current
just migrate-local
just db-down
just import-m1-local <manifest-path> <source-commit-sha> <data-csv-path>
just api-dev
just forecast-local
just message-up
just message-init
just message-dispatch-once
just message-worker-once
just message-worker
just check-backend
just test-backend-unit
just test-db-integration
just test-api-unit
just test-api-integration
just test-auth
just test-forecast-unit
just test-forecast-integration
just test-message-unit
just test-message-integration
just audit-backend
just docs-check
~~~

The import recipe requires independent generator output at the pinned source revision; it never supplies a default manifest, source commit, or CSV. The importer validates the pinned source/schema/seed and verifies CSV checksum, size and rows against the supplied manifest. Before invoking it, independently confirm that manifest's telemetry checksum is the canonical `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`; the importer does not pin that digest. See [the implementation contract](docs/planning/IMPLEMENTATION_SPEC.md) for the complete immutable source contract.

The integration recipes first run `backend/tests/db_lifecycle.py --require-database-url`, a bounded, owner-aware Docker PostgreSQL preflight. It checks the configured `127.0.0.1:${POSTGRES_PORT:-54329}` binding and local `DATABASE_URL`, reuses a healthy database only when its configured Compose project/service and canonical checkout/Compose-file identity match (set `COMPOSE_PROJECT_NAME` for an explicitly named controller project), starts that owned stopped instance, restarts that owned unhealthy instance once, and waits for Docker health plus TCP readiness. If a foreign container/process owns the port or ownership is ambiguous, it fails without stopping or replacing that service. The standalone `just db-up` uses the same preflight without requiring `DATABASE_URL`. `just message-up` additionally starts the pinned NATS 2 service with JetStream storage and monitoring bound only to loopback; `message-init`, dispatcher, and worker commands use `NATS_URL`. Migration and messaging tests use isolated, uniquely named local `flowstead_test_<uuid>` databases; destructive rollback is refused elsewhere. The integration commands require a working local Docker daemon and appropriate local environment. No hosted project, invitation, deployment or secret is provisioned by these commands. `just audit-backend` runs pinned `pip-audit` against a strict, hash-verified export of all runtime and development packages in `backend/uv.lock`.

The canonical [current backend HTTP route list](docs/planning/IMPLEMENTATION_SPEC.md#current-backend-http-routes) is derived from `backend/src/flowstead_api/main.py`. FastAPI serves its generated OpenAPI schema at `/openapi.json`; do not infer implemented routes from future task specifications.

## Supabase Auth verification

Private API routes accept only `Authorization: Bearer <JWT>` and resolve a typed verified
principal. Plant authorization is still read from `app.operator_plant_access`; JWT metadata,
custom headers and client-supplied Plant IDs are ignored. Configure the server-only
`SUPABASE_AUTH_URL`, `SUPABASE_JWT_ISSUER`, `SUPABASE_JWT_AUDIENCE` and asymmetric
`SUPABASE_JWT_ALGORITHMS` values shown in `.env.example`. The default `jwks` mode accepts
only ES256/RS256 keys from the configured issuer's JWKS endpoint, uses a bounded ten-minute
cache, and refreshes safely for key rotation. Missing or unsafe configuration fails private
requests closed while `/api/v1/health` remains available.

If task 014 confirms that the live project still uses legacy HS256 tokens, the documented
temporary fallback is `SUPABASE_AUTH_VERIFICATION_MODE=legacy-auth-endpoint` plus the
project's publishable key. That mode validates the exact bearer token through the configured
HTTPS Supabase `/user` endpoint with a bounded timeout. It never stores or uses the JWT
signing secret or service-role secret. Hosted behavior, invite-only signup settings and the
fallback's need remain **UNVERIFIED** until task 014; this task makes no cloud changes.
