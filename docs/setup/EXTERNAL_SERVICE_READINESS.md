# External service readiness — Flowstead (D-040/D-045 approved local architecture)

**Status:** Nonsecret prerequisites only. Architecture decision **D-040** removed AWS S3 from MVP; **D-045 added mandatory NATS/JetStream message transport, Alembic migrations and bounded browser IndexedDB**, already approved for **local** implementation. No broker or worker has been publicly provisioned. This document neither provisions cloud services nor authorizes hosting, public DNS edits, paid plans, migrations or user invitations. Backend/UI work should remain locally testable while external setup is gated.

## Verified or intended resources (2026-11-17)

| Resource | State and task boundary |
| --- | --- |
| GitHub app repo | Existing PRIVATE `darizae/flowstead`, `main`; do not recreate |
| Independent generator | Existing PRIVATE `darizae/flowstead-sim`, M0 completed; app pins immutable upstream before import |
| Development database | Supabase `flowstead-dev` (`jryvzjwsrxctjeawnkqo`, `eu-west-1`) verified `ACTIVE_HEALTHY`; OMP local project-scoped MCP still needs actual read-only verification |
| Local database | Docker PostgreSQL for real Alembic migration/integration work when configured by approved task; availability on owner's Mac must be checked |
| Local async transport | **NATS 2 + JetStream**, app-owned bounded outbox dispatcher/forecast worker, local Docker/Compose under approved D-045 T-004b; currently NOT IMPLEMENTED |
| Hosted message service | **Required for eventual message-driven hosted app**, but no provider/service selected or created; future choice must support durable broker state, worker restarts, scope and actual free/cost limits |
| Public demo database | Separate `flowstead-demo` Supabase project **planned, not created**; requires explicit external provisioning/cost authorization |
| Frontend hosting | Existing Vercel team `daniel-arizas-projects`; future separate Flowstead project only when approved |
| Domain | Existing `darizae.dev` on Vercel **serves unrelated `personal-website`**. MUST NOT repoint root, transfer domain, alter its records or remove its binding |
| Proposed app URLs | `flowstead.darizae.dev` and optional `api.flowstead.darizae.dev` only after explicit deployment/DNS authorization |
| Python API/worker hosting | Provider not yet chosen; select based on actual FastAPI + bounded NATS worker process, persistent JetStream broker availability, IPv4/IPv6, cold-start, cost and secret-store support |
| AWS/S3 | **Not required for MVP.** No account, IAM, bucket, S3 adapter, AWS CLI or paid AWS resources should be created |

## Safe agent preparation

1. Check actual local Git/gh/Docker/Compose/just/OMP availability before scheduling a task, preserving owner checkouts and authentication.
2. For private `flowstead-dev` reads, use the existing project-scoped OAuth/MCP connection and verify an actual `list_tables` result. Do not print secrets, copy ChatGPT OAuth or enable broad account-level access.
3. Any hosted schema migration needs an owner-approved **specific writable** project/role and exact expected **Alembic** revision, a local tested clean/existing baseline, security/RLS review and post-write checks. Turn off that grant after the task.
4. Future public deployment needs an approved FastAPI host **and durable NATS/JetStream/worker hosting topology**, separate `flowstead-demo`, cost and quota readback, Vercel project, scoped DNS change, invite-only Auth, reliable seed/backup/export/rebuild, bounded read/export/rate limits, **outbox/inbox recovery**, and a rollback plan. Local NATS authorization does not create a hosted broker. No automatic paid fallback or public-data uploads.
5. Secrets belong in owner-managed ignored local config/host secret manager. Frontend gets no DB password or Supabase administrative key. No privileged API keys, raw credentials, or private planner decisions in GitHub tasks.

## Provider boundary

The **app repo** owns one SQL migration/importer set and the backend/frontend/deployment contracts. `flowstead-sim` owns the deterministic local synthetic generator without any AWS, Supabase, Vercel or DNS dependency. Render/Supabase/Vercel provider details must be verified just before an approved deployment; no 24-hour soak.

References: [technical contract](../planning/IMPLEMENTATION_SPEC.md), [ordered work](../planning/HANDOFF_SEQUENCE.md), [Supabase access](SUPABASE_DEVELOPMENT_ACCESS.md), https://supabase.com/docs/guides/database/connecting-to-postgres, https://supabase.com/docs/guides/platform/billing-on-supabase
