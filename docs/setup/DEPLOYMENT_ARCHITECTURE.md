# Flowstead — deployment architecture and environment responsibilities

**Scope:** Environment separation, hosting responsibility, access limits and deployment acceptance. Application behavior and data contracts are in [IMPLEMENTATION_SPEC.md](../planning/IMPLEMENTATION_SPEC.md); concrete executable work and sequencing context are in [HANDOFF_SEQUENCE.md](../planning/HANDOFF_SEQUENCE.md). An assigned task may start regardless of hosted-resource readiness. Real external operations require concrete target configuration and access; local code/configuration work does not wait for cloud setup.

## Runtime topology

| Component | Local development | Private development integration | Future public demo |
| --- | --- | --- | --- |
| React/Tailwind | Local dev server and Playwright | Local build/browser smoke; no required public frontend | New separately configured Vercel static frontend project |
| FastAPI | Local uv/FastAPI adapter | Local or configured hosted API test; never expose server secrets | Existing `VM.Standard.E2.1.Micro` x86_64 VM: small FastAPI process behind TLS; verify actual host memory and runtime |
| Async jobs | Local NATS 2 JetStream + dispatcher/forecast worker in Compose | Real broker/worker local tests; any remote broker is separately configured | Existing E2 micro: bounded persistent NATS/JetStream and restartable low-footprint worker; actual live startup still UNVERIFIED |
| PostgreSQL | Disposable Docker PostgreSQL, local Alembic/importer | Existing private Supabase flowstead-dev, project ref jryvzjwsrxctjeawnkqo, eu-west-1 | Existing flowstead-demo Supabase project hkyobferqdfiicnsaupl, eu-west-1, active; migrations to 003 and five-Plant 43,800-row M1 import completed 2026-11-21; restricted runtime connection still pending |
| Authentication | Deterministic test principals/JWKS; no public credential bypass | Invite-only Supabase Auth with real configured identities and project details | Invite-only Auth and protected operator routes; anonymous five-Plant synthetic read-only demo |
| Files/exports | Reproducible local generator output; on-demand authorized CSV/PNG/PDF | Local/on-demand, no persistent output archive | On-demand bounded server/client exports; no object storage dependency |

PostgreSQL is the authoritative application data store; NATS/JetStream transports durable jobs, not business records. Browser IndexedDB holds only bounded non-authoritative client state. The generator [flowstead-sim](https://github.com/darizae/flowstead-sim) is an independent source-only build dependency, not a hosted workload. API, worker, NATS and hosted PostgreSQL must use independently provisioned resources, not an operator's Mac. A static-host-only plan is insufficient for durable asynchronous work.

## Boundaries and credentials

- Server-only PostgreSQL connection string and Auth verification settings stay in host secret stores; frontend receives no service-role/admin keys or DB credentials. Validate Supabase Auth issuer/JWKS and enforce subject→Plant permission in FastAPI. Enforce minimal GRANT/RLS policies for any exposed Supabase tables. Runtime API/worker connect as a **least-privilege DML role** (`sslmode=verify-full`); schema migrations + M1 import are a separate one-shot step against an owner role (`MIGRATION_DATABASE_URL`) held in an **offline-only** secret file (see `deploy/oci/env.migration.example`). Never place that variable in `HOSTED_ENV_FILE`: Compose injects every entry into both API and worker (SEC19-01/SEC19-04).
- Local PostgreSQL migration, importer and forecast are tested against disposable data and exact pinned synthetic M1 manifest. Alembic must adopt existing populated local databases without rerunning destructive DDL. Hosted migrations use the same verified revision chain and a verified target database and migration plan.
- All five fictional M1 Plants are eligible for bounded public read-only synthetic views after manifest validation; operator-only assignments remain server-enforced. Public exposure, traffic limits and CORS/Auth/redirect decisions require real hosted verification.
- Authenticate local tools with owner-controlled project-scoped access. Never assume GitHub or ChatGPT OAuth credentials also authenticate a local OMP worker. Record results without tokens or personal identity data.
- Keep development and demo data, Auth users, URLs, secrets, migration history and backups independent. Never share a production DB connection with a disposable local test fixture.
- A Vercel team and darizae.dev domain already exist, but the root domain is used by a separate personal website. Do not repoint it. Potential frontend flowstead.darizae.dev and API api.flowstead.darizae.dev are proposals only; verify host/custom-domain compatibility and use only exact DNS records explicitly supplied by the owner.

## Local-to-cloud delivery sequence

1. **Local implementation (tasks 004a–013):** establish real Alembic head, NATS/JetStream outbox/consumer recovery, JWT/Plant authorization and IndexedDB. Run fast tests, local real PostgreSQL and JetStream integration, Playwright desktop/mobile map/export/session acceptance and documentation hygiene. No cloud resources needed.
2. **Development database (task 014):** verify current flowstead-dev project and project-scoped read-only connectivity first (e.g. actual list_tables); current Mac OAuth is not proven by a config entry. Use only a concrete owner-provided project ref, migration/revision, row scope, role privileges and invitation recipients; validate local rollback and RLS. Missing details do not block preparing local code, but do not guess targets for external writes. Record redacted before/after schema and real signed-token smoke. Remove temporary write grants.

   T-014 verified read-only connectivity to `flowstead-dev` (`jryvzjwsrxctjeawnkqo`): the
   project is empty (`public` and `app` have no tables, no migrations applied), so the
   pre-change snapshot is clean. The local chain reaches head `003_jetstream_messages`,
   `just test-db-integration` and `just dev-smoke` pass. Live writes (migration run, M1
   import, invite-only Auth, demo identities, signed-token/Data API smoke) remain **not
   performed** pending an owner-supplied admin connection string and invitation
   recipients. See [the T-014 runbook](DEV_SUPABASE.md) for the approved, documented
   plan.
3. **Host-neutral local production build (task 015):** verify React build, FastAPI and worker launch, real local JetStream durability/ack/replay, Alembic startup, health, restart/recovery and safe local shutdown. Can precede development cloud integration where independent.
4. **Existing-host deployment (task 016):** use the current `flowstead-demo-instance` only (Frankfurt E2 micro, RUNNING), keep FastAPI/NATS/worker inside its measured resources and restrict SSH/ports. The demo Supabase schema is at 003 with 5 Plants and 43,800 M1 readings, and the Vercel Flowstead frontend project already exists. Securely provision a restricted database login, actual TLS hostname, and invited identities before public promotion. No new compute/paid resources or personal-site changes.
5. **Host verification (task 017):** validate actual deployed SHAs, domain/TLS/CORS, anonymous public vs invited private authorization and leakage negatives, MapLibre tiles, download files, queue→forecast completion, dead-letter/restart behavior, DB backup/reseed and rollback. Preserve exact host receipts; mark unrun checks UNVERIFIED.
6. **Release documentation (task 018):** reconcile runbooks, tested deployment config, links, versions and commands; no publication based only on a green unit suite.

## Existing OCI instance and cost

The owner has selected the **already provisioned** Frankfurt `flowstead-demo-instance` (`VM.Standard.E2.1.Micro`, x86_64). It is RUNNING and SSH ingress has been restricted to the owner's then-current public IPv4 /32. No additional VM, VCN, volume, paid tier, load balancer or replacement machine is authorized. The guest has limited memory and swap; size the live service to the **actual** measured resources. Existing Free Tier eligibility is not a hard spending cap; verify any billed usage and remaining quota in the live Console. Supabase `flowstead-demo` is migrated/imported; the Vercel project exists with a READY build. Backend, TLS and login remain unverified. Follow [the current OCI runbook](../deployment/OCI_ALWAYS_FREE.md) for operations.

## Operational verification

A hosted broker must retain messages through worker restart and satisfy bounded retries and idempotent replay; provider sleep/cold starts and network partition must not produce fabricated completed forecasts. Verify actual backend host ability to maintain a durable worker, PostgreSQL pooler/direct connection constraints, supported Python runtime and provider quota/price/expiry just before task 016. Minimize remote CI; keep locally runnable integration and recovery tests primary. A successful local build, project existence or cloud OAuth setup alone is not hosted acceptance.

## Superseding security isolation decision (2026-11-21)

The shared `flowstead_runtime` model described in earlier planning is
**retired**. In live `flowstead-demo` migrations 005/006, `flowstead_api`
and `flowstead_worker` were created as distinct, NOLOGIN database roles
with mutually restricted grants. They require separate verified session-pooler
credentials and root-protected environment files before services can start.
The approved OCI host has a live authenticated NATS broker, a separate
`flowstead` OS account, distinct proposed `flowstead-api`/`flowstead-worker`
accounts and a fourth future proxy account; these must not share a Linux group
capable of reading each other's secrets. Read the current
[end-to-end security report](../security/2026-11-21-end-to-end-security-audit.md)
rather than treating any proposed public hostname or earlier shared
`DATABASE_URL` as verified deployment state.
