# Flowstead

Flowstead is a wastewater-plant operations demonstration for five fictional small Florida treatment Plants. It provides a bounded synthetic-data API and is being developed into an interactive Plants map, monitoring history, twelve-hour influent-flow forecasts, and authorized CSV/PNG/PDF exports. It does not connect to operational equipment.

**Current implementation:** local PostgreSQL Alembic migrations, the validated M1 importer, deterministic twelve-hour forecasting, Plant-scoped FastAPI reads and asynchronous forecast commands, a fail-closed Supabase-compatible JWT verifier, a PostgreSQL-outbox/NATS JetStream dispatcher and durable worker, and a React/Vite Plants overview/detail foundation with typed API handling, a 12-hour observed→predicted forecast chart, invite-only sign-in/expiry/logout states backed by a Supabase Auth client (identity only; data always from FastAPI), and a bounded versioned per-principal IndexedDB cache that is wiped on logout/expiry/switch/revocation. The existing OCI demo instance has been started, and `flowstead-demo` Supabase is migrated/populated with synthetic M1 data; the live FastAPI, broker/worker, TLS and signed-in hosted experience remain unverified.

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
just frontend-dev
just test-frontend-unit
just frontend-typecheck
just frontend-build
just audit-frontend
just test-e2e-local
just dev-smoke
just dev
just dev-down
just build-backend-image
just build
just test-deploy-local
~~~

`just build-backend-image`, `just build` and `just test-deploy-local` implement the
host-neutral production build and recovery acceptance from T-015: a non-root backend/worker
Docker image from the committed `uv.lock`, a static frontend build pointed at an explicit
HTTPS API URL, and an isolated local staging stack (real PostgreSQL + NATS/JetStream,
Alembic upgrade-to-head, M1 import, bounded requests, outbox replay across a worker restart,
graceful shutdown, and DB backup/reseed/rollback with known checksums). See
[docs/deployment/LOCAL_AND_RECOVERY.md](docs/deployment/LOCAL_AND_RECOVERY.md) for the
runbook. Public DNS aliases there are proposals only and not assigned.

`just dev` boots the whole local stack in one command and keeps it running until interrupted
(Ctrl-C): `message-up` (Docker PostgreSQL + NATS), `db-upgrade` (Alembic), `message-init`
(JetStream stream/consumer), then long-running FastAPI (`127.0.0.1:8000`), the JetStream
dispatch/forecast worker, and the Vite frontend (`127.0.0.1:5173`, proxying `/api` to the
API). It requires loopback `DATABASE_URL`/`NATS_URL` access and fails safely when either
`8000` or `5173` is already occupied. `just dev-down` stops the Docker Compose services.

The import recipe requires independent generator output at the pinned source revision; it never supplies a default manifest, source commit, or CSV. The importer validates the pinned source/schema/seed and verifies CSV checksum, size and rows against the supplied manifest. Before invoking it, independently confirm that manifest's telemetry checksum is the canonical `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`; the importer does not pin that digest. See [the implementation contract](docs/planning/IMPLEMENTATION_SPEC.md) for the complete immutable source contract.

`just test-e2e-local` is a real API/browser gate, not a mocked Playwright server. It starts the owned local PostgreSQL preflight and requires `FLOWSTEAD_M1_MANIFEST` and `FLOWSTEAD_M1_DATA` pointing to the adjacent verified M1 manifest/`telemetry.csv`. The runner verifies the pinned digests, creates and drops only a unique `flowstead_test_<uuid>` database, runs Alembic/import, builds the deterministic forecast, starts an isolated pinned NATS 2 JetStream container and durable worker, and starts a throwaway local Supabase-compatible JWKS authority with disjoint principals. Chromium then exercises public/private authorization, queued-to-completed forecast work, cache clearing, maps, exports, responsive views and 200% page scale through the real FastAPI and Vite proxy. The locally inspectable Playwright HTML report and generated indexed Markdown/JSON receipts live under `docs/design/evidence/`. Hosted Supabase identity remains UNVERIFIED.

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

## Local HTTP security policy

FastAPI applies `no-store`, `nosniff`, deny-framing, no-referrer, restrictive API CSP and
permissions headers to every response. CORS accepts only the exact origins in
`FLOWSTEAD_CORS_ORIGINS`; wildcard and non-loopback HTTP origins are rejected at startup.
Requests have bounded target/body sizes and a bounded single-process per-client sliding
rate limit configured by the `FLOWSTEAD_RATE_LIMIT_*` values in `.env.example`. A denied
request returns JSON `429` with `Retry-After`. `X-Forwarded-For` is ignored unless the
immediate peer matches `FLOWSTEAD_TRUSTED_PROXIES`; list only proxy CIDRs controlled by the
deployment. This limiter is intentionally for the initial single-instance demo. A shared
limiter is required before any multi-instance deployment.

Task 014 verified read-only connectivity to the private `flowstead-dev` Supabase project
(`jryvzjwsrxctjeawnkqo`): it is empty, so the pre-change snapshot is clean, and the reviewed
local chain reaches head `003_jetstream_messages` (`just dev-smoke` passes). Live migration
run, M1 import, invite-only Auth configuration, demo identities and signed-token/Data API
smoke are **NOT PERFORMED** — they require an owner-supplied admin connection string and
invitation recipients. If the live project then proves to still issue legacy HS256 tokens,
the documented temporary fallback is `SUPABASE_AUTH_VERIFICATION_MODE=legacy-auth-endpoint`
plus the project's publishable key. That mode validates the exact bearer token through the
configured HTTPS Supabase `/user` endpoint with a bounded timeout. It never stores or uses
the JWT signing secret or service-role secret. Hosted behavior, invite-only signup settings
and the fallback's need remain **UNVERIFIED** until live admin access is exercised. See
[docs/setup/DEV_SUPABASE.md](docs/setup/DEV_SUPABASE.md) for the approved runbook.
