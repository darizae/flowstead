# Flowstead — deployment architecture and environment responsibilities

**Scope:** Environment separation, hosting responsibility, access limits and deployment acceptance. Application behavior and data contracts are in [IMPLEMENTATION_SPEC.md](../planning/IMPLEMENTATION_SPEC.md); concrete executable work and current gates are in [HANDOFF_SEQUENCE.md](../planning/HANDOFF_SEQUENCE.md). This document does not authorize provisioning or cloud writes.

## Runtime topology

| Component | Local development | Private development integration | Future public demo |
| --- | --- | --- | --- |
| React/Tailwind | Local dev server and Playwright | Local build/browser smoke; no required public frontend | New independently approved Vercel static frontend project |
| FastAPI | Local uv/FastAPI adapter | Local or specifically approved hosted API test; never expose server secrets | Compatible Python API host with bounded DB connections |
| Async jobs | Local NATS 2 JetStream + dispatcher/forecast worker in Compose | Real broker/worker local tests; any remote broker is separately authorized | Durable JetStream broker and independently restartable Python worker, with persistent storage/replay and safe secrets |
| PostgreSQL | Disposable Docker PostgreSQL, local Alembic/importer | Existing private Supabase flowstead-dev, project ref jryvzjwsrxctjeawnkqo, eu-west-1 | Separate flowstead-demo Supabase project (not yet created), synthetic-only |
| Authentication | Deterministic test principals/JWKS; no public credential bypass | Invite-only Supabase Auth after exact configuration/invitation approval | Invite-only Auth and protected operator routes; anonymous five-Plant synthetic read-only demo |
| Files/exports | Reproducible local generator output; on-demand authorized CSV/PNG/PDF | Local/on-demand, no persistent output archive | On-demand bounded server/client exports; no object storage dependency |

PostgreSQL is the authoritative application data store; NATS/JetStream transports durable jobs, not business records. Browser IndexedDB holds only bounded non-authoritative client state. The generator [flowstead-sim](https://github.com/darizae/flowstead-sim) is an independent source-only build dependency, not a hosted workload. API, worker, NATS and hosted PostgreSQL must use independently provisioned resources, not an operator's Mac. A static-host-only plan is insufficient for durable asynchronous work.

## Boundaries and credentials

- Server-only PostgreSQL connection string and Auth verification settings stay in approved host secret stores; frontend receives no service-role/admin keys or DB credentials. Validate Supabase Auth issuer/JWKS and enforce subject→Plant permission in FastAPI. Enforce minimal GRANT/RLS policies for any exposed Supabase tables.
- Local PostgreSQL migration, importer and forecast are tested against disposable data and exact pinned synthetic M1 manifest. Alembic must adopt existing populated local databases without rerunning destructive DDL. Hosted migrations use the same verified revision chain and a separate explicit approval.
- All five fictional M1 Plants are eligible for bounded public read-only synthetic views after manifest validation; operator-only assignments remain server-enforced. Public exposure, traffic limits and CORS/Auth/redirect decisions require a separate release gate.
- Authenticate local tools with owner-controlled project-scoped access. Never assume GitHub or ChatGPT OAuth credentials also authenticate a local OMP worker. Record results without tokens or personal identity data.
- Keep development and demo data, Auth users, URLs, secrets, migration history and backups independent. Never share a production DB connection with a disposable local test fixture.
- A Vercel team and darizae.dev domain already exist, but the root domain is used by a separate personal website. Do not repoint it. Potential frontend flowstead.darizae.dev and API api.flowstead.darizae.dev are proposals only; verify host/custom-domain compatibility and obtain explicit DNS approval first.

## Local-to-cloud delivery sequence

1. **Local implementation (tasks 004a–013):** establish real Alembic head, NATS/JetStream outbox/consumer recovery, JWT/Plant authorization and IndexedDB. Run fast tests, local real PostgreSQL and JetStream integration, Playwright desktop/mobile map/export/session acceptance and documentation hygiene. No cloud resources needed.
2. **Development database (task 014):** verify current flowstead-dev project and project-scoped read-only connectivity first (e.g. actual list_tables); current Mac OAuth is not proven by a config entry. Before any SQL migration/seed or Auth invitation, obtain exact owner consent for project ref, migration/revision, row scope, role privileges and recipients; validate local rollback and RLS. Record redacted before/after schema and real signed-token smoke. Remove temporary write grants.
3. **Host-neutral local production build (task 015):** verify React build, FastAPI and worker launch, real local JetStream durability/ack/replay, Alembic startup, health, restart/recovery and safe local shutdown. Can precede development cloud integration where independent.
4. **Public provisioning (task 016):** owner selects/approves Python API+worker and persistent JetStream hosting, new Vercel project, isolated Supabase flowstead-demo database/Auth, specific DNS records/subdomains, free-tier limits/charges, secrets, M1 seed/digest, controls and rollback. Never silently fall back to paid services or use an existing unrelated Vercel app.
5. **Host verification (task 017):** validate actual deployed SHAs, domain/TLS/CORS, anonymous public vs invited private authorization and leakage negatives, MapLibre tiles, download files, queue→forecast completion, dead-letter/restart behavior, DB backup/reseed and rollback. Preserve exact host receipts; mark unrun checks UNVERIFIED.
6. **Release documentation (task 018):** reconcile runbooks, tested deployment config, links, versions and commands; no publication based only on a green unit suite.

## Operational quality gates

A hosted broker must retain messages through worker restart and satisfy bounded retries and idempotent replay; provider sleep/cold starts and network partition must not produce fabricated completed forecasts. Verify actual backend host ability to maintain a durable worker, PostgreSQL pooler/direct connection constraints, supported Python runtime and provider quota/price/expiry just before task 016. Minimize remote CI; keep locally runnable integration and recovery tests primary. A successful local build, project existence or cloud OAuth setup alone is not hosted acceptance.