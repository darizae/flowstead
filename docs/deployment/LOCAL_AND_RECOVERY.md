# Local production build, deployment configuration and recovery (T-015)

This runbook documents the host-neutral, locally verified build and recovery
configuration for the Flowstead **FastAPI API**, the **bounded NATS/JetStream
forecast worker/dispatcher**, and the **static React frontend**. It is exercised
by `just test-deploy-local` against a disposable local staging stack with real
PostgreSQL, NATS/JetStream, Alembic and a restarted worker. No public host,
DNS or provider is required; the DNS names below are **proposals only and not
assigned**.

## Runtime topology and host separation

| Component | Runtime | Bound to | Purpose |
| --- | --- | --- | --- |
| `api` | `uvicorn flowstead_api.main:app` (port 8000) | Proposed `api.flowstead.darizae.dev` | FastAPI reads + forecast commands; server-only env |
| `worker` | `python -m flowstead_api.messaging run` | API host or its own host | dispatch outbox → JetStream publish; durable consumer → forecast |
| `db` | `postgres:16` | server-side only | authoritative store |
| `nats` | `nats:2.12` JetStream | server-side only | durable async jobs |
| `frontend` | static build (Vercel-style) | Proposed `flowstead.darizae.dev` | browser bundle, calls API host |

The frontend and API are **host-separated**: the frontend build embeds an
explicit HTTPS API URL (`VITE_API_URL`) and talks only to that origin. Secrets
never cross the boundary:

- **Server-only, host secret store:** `DATABASE_URL`,
  `SUPABASE_AUTH_URL`/`SUPABASE_JWT_ISSUER`/`SUPABASE_JWT_AUDIENCE`/
  `SUPABASE_JWT_ALGORITHMS`/`SUPABASE_AUTH_VERIFICATION_MODE`,
  `FLOWSTEAD_CORS_ORIGINS`, `FLOWSTEAD_TRUSTED_PROXIES`.
- **Browser-only (publishable):** Supabase project URL + anon/publishable key
  (`frontend/.env.example` `VITE_*`). Never place a service-role/admin key or
  SQL URI in the frontend bundle.
- The FastAPI verifier reads the Supabase **issuer → JWKS** URL
  (`<SUPABASE_JWT_ISSUER>/.well-known/jwks.json`) to verify asymmetric tokens;
  the browser only ever talks to FastAPI for data, never to a Supabase Data API.

The image itself (`just build-backend-image`) bakes in no secrets and runs as a
non-root user (uid 10001). Secret environment is injected at runtime only.

## Builds

```sh
just build-backend-image   # docker build backend/ -> flowstead-backend:local (from uv.lock)
just build                 # frontend/dist; VITE_API_URL defaults to the HTTPS API proposal
just test-deploy-local     # image + bundle + isolated container acceptance (below)
```

`build-backend-image` is a multi-stage image (uv → lock install under
`/opt/venv` → runtime) that serves both the API and the worker via the Compose
`command`. `just build` runs `pnpm run build` with `VITE_API_URL`
(`https://api.flowstead.darizae.dev/api/v1` by default; override for a real
target). Neither build embeds secrets.

## Compose staging profile

`compose.yml` adds a `staging` profile with `api` and `worker` built from
`flowstead-backend:local`:

```sh
COMPOSE_PROJECT_NAME=flowstead-deploy \
POSTGRES_PORT=54339 NATS_PORT=42239 API_PORT=18080 \
docker compose --profile staging up -d --wait db nats api worker
```

- `api` healthchecks are **liveness** (`/api/v1/health/live`, process up) and
  **readiness** (`/api/v1/health/ready`, `SELECT 1` succeeds → DB reachable);
  readiness fails closed with `503` when the database is unreachable.
- `worker` exposes no HTTP; its healthcheck is a process-alive probe in one
  process as PID 1. DB/JetStream reachability is asserted by the message
  pipeline in `just test-deploy-local`, not by HTTP health alone.
- `worker` uses `restart: unless-stopped`; the API is intentionally not
  auto-restarted.

## Default-deny HTTP and auth

- **CORS** accepts only the exact origins in `FLOWSTEAD_CORS_ORIGINS`; wildcard
  and non-loopback HTTP origins are rejected at startup (default is loopback
  only). Unreviewed origins are never echoed in `Access-Control-Allow-Origin`.
- **Auth fails closed:** with missing/unsafe `SUPABASE_*` configuration FastAPI
  installs an `UnavailableVerifier`, so every private route returns `401` while
  `/api/v1/health` and the public read routes remain available.
- There is **no open signup** and **no public SQL endpoint**: the route set is
  exactly the bounded approved list; the security middleware enforces request
  target/body bounds (oversized bodies → `413`) and a per-client sliding limit.

## Local container acceptance (`just test-deploy-local`)

The script `scripts/test_deploy_local.py` boots an isolated Compose project
(`flowstead-deploy`) with **fresh** PostgreSQL and NATS volumes and non-conflicting
loopback ports, then asserts:

1. **OPS-M15-BUILD** — `flowstead-backend:local` exists, runs as uid 10001, and
   exposes no secret env; `frontend/dist` contains the explicit HTTPS API URL and
   leaks no secret strings.
2. **IT-M15-START** — infra up → **real Alembic** upgrade-to-head on a fresh DB →
   real M1 import → API/worker boot on the migrated database; liveness/readiness
   pass; bounded requests (413 on oversized body; public list bounded to the five
   approved plants). The worker processes one **real** forecast command enqueued
   through the message store to `completed`, then a **second** command enqueued
   while the worker is stopped completes after the worker is restarted (durable
   JetStream consumer + outbox replay across restart). API and worker shut down
   gracefully (exit 0) on SIGTERM.
3. **SEC-M15-CONFIG** — private route `401` with no auth config; allowed origin
   echoed, unreviewed origin not echoed; no `/signup`, `/sql` or `/query` endpoint.
4. **OPS-M15-RECOVER** — a disposable DB copy is backed up (`pg_dump`) and
   restored, and the restored copy reproduces the **pre-backup** seed fingerprint
   exactly; reseeding a fresh database (Alembic → re-import) reproduces the exact
   **import** fingerprint (plants / hourly_readings / ingest_batches content +
   counts).

## Backup, reseed and rollback

### Backup
```sh
docker compose -p flowstead-deploy exec -T db pg_dump -U flowstead -d flowstead \
  > flowstead.sql
```

### Reseed (deterministic synthetic seed)
Reproduce the exact M1 seed on a fresh disposable database (create database →
Alembic upgrade-to-head → import with the canonical source and manifest):
```sh
uv run --project backend python -m backend.migrate upgrade
uv run --project backend python -m backend.importer \
  --manifest <manifest.json> --data <telemetry.csv> \
  --source-sha ad5c94d1f46e79312a99cb9721f38700f24fdf6b
```
The importer validates the pinned source/schema/seed and CSV checksum, size and
rows against the manifest. Independently confirm the manifest telemetry digest is
the canonical `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`.

### Rollback to a previous image / commit
Image rollback is a tag revert; rebuild tooling keeps the prior image as a named
target. With the current digest recorded (`docker image inspect --format
'{{index .RepoDigests 0}}' flowstead-backend:local`), revert by tagging the
previous image and restarting the API/worker with it:
```sh
docker tag flowstead-backend:<previous> flowstead-backend:local   # or compose image:
docker compose -p flowstead-deploy up -d --force-recreate api worker
```
Code rollback is the same as any commit: `git checkout <sha>` (or the shipped
commit), rebuild, redeploy. There is **no automatic deploy from a PR and no paid
upgrade**; deployments are manual and reviewed.

## Cold-start and unavailability messaging

- Postgres/JetStream are **infrastructure-first**: the API and worker are booted
  only after the database is migrated, so a cold worker never races the schema.
- If the API cannot reach the database, readiness returns `503` and private
  routes fail closed; `/api/v1/health` (liveness) stays up so the orchestrator
  can distinguish "process up" from "ready".
- If the worker cannot reach DB/store, outbox rows remain `pending` and are
  replayed on the next successful dispatch (idempotent, `Nats-Msg-Id`-deduped by
  JetStream). A worker restart recovers the durable consumer exactly.
- The frontend turns API/network failure into a friendly, actionable message
  (`Unable to reach Flowstead. Check your connection and try again.`) and
  terminates on session expiry; it never fabricates data or a completed job.