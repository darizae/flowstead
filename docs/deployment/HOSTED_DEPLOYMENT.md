# Flowstead — hosted deployment status and operator guide

**Status as inspected 2026-11-21:** The owner selected the existing `flowstead-demo-instance` (`VM.Standard.E2.1.Micro`, Oracle Linux 9.8, x86_64, Frankfurt) as the **sole deployment host**. OCI reported **RUNNING** following a verified CLI start, and Oracle SSH ingress was narrowed to the owner's current IPv4 `/32`. SSH and sudo were verified. A later remote package-inspection command hung, SSH subsequently timed out, and a graceful `SOFTRESET` was accepted; the last observed lifecycle state was **STOPPING**. Host recovery and application deployment remain incomplete. No additional VM is authorized.

## Verified completed items

- Existing Oracle instance is running; no new machine or volume was created.
- Existing Supabase project `flowstead-demo` was migrated using the checked-in 001/002/003 Alembic schema definitions; `app` contains 10 application tables. Five synthetic Plants and 43,800 immutable M1 hourly rows were imported and independently counted (8,760 each). Five ingest-completed events are queued in `app.message_outbox`.
- Migration history is `003_jetstream_messages`; the synthetic telemetry source checksum is `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`.
- A separate non-superuser `flowstead_runtime` role was created with app-schema DML privileges, not DDL or access to migration history; database-login provisioning and connection testing remain **UNVERIFIED**. Migration-owner credentials must never be injected into API/worker services.
- Existing Vercel `flowstead` project has a READY production deployment. API URL, anonymous public presentation, live TLS and identity flows are not yet verified.

## Deployment design on the existing host

The existing x86_64 host has limited RAM (roughly 500 MiB guest memory with swap). Prefer minimum-footprint native processes or a demonstrated low-memory configuration for **FastAPI**, **NATS JetStream with persistent storage**, **dispatcher/worker**, and **a TLS reverse proxy**. The repository's `compose.hosted.yml` and `deploy/oci/deploy.sh` are optional **linux/amd64** Docker assets; they are not proof that Docker is installed or the full stack fits this host. Do not run multi-architecture builds or substitute ephemeral messaging for durable NATS.

- PostgreSQL/Auth stay in the existing `flowstead-demo` Supabase project. Never deploy local Postgres to the VM.
- FastAPI binds to loopback or an isolated network; no public 8000. NATS 4222/8222 and database 5432/6543 must not be published on the host.
- Caddy or equivalent proxy terminates TLS only for a verified authorized hostname. No public proxy until the actual domain resolves, certificates work, and origin/auth checks pass.
- Use `deploy/oci/env.hosted.example` as a **non-secret** template. Place a restricted runtime connection in a host-protected secret file outside Git, not a migration/owner credential. `deploy/oci/env.migration.example` remains **offline-only** and must never enter the API/worker environment.
- Keep existing `darizae.dev` apex and unrelated projects untouched. Configure only specifically intended Flowstead subdomains.

## Acceptance matrix

| Case | Current evidence |
| --- | --- |
| `CLOUD-M16-RESOURCES` | PARTIAL existing VM identified and started, later graceful reset **STOPPING**; billing hard-cap/current invoice **UNVERIFIED** |
| `OPS-M16-ARM` (historical case ID) | Host observed x86_64; application process architecture/startup **UNVERIFIED** |
| `CLOUD-M16-DATA` | PASS migration 003 + five Plants + 43,800 validated rows |
| `SEC-M16-NET` | SSH source restricted to Mac /32; HTTPS/host-firewall and public ingress **UNVERIFIED** |
| `SEC-M16-AUTH` | Verified schema denies anonymous `app` access; live JWT identities **UNVERIFIED** |
| `OPS-M16-QUEUE` | 5 pending ingest events persisted; hosted NATS/worker dispatch **UNVERIFIED** |
| `OPS-M16-COST` | E2 micro is an Always Free-eligible target; actual billing **UNVERIFIED** |
| `OPS-M16-TLS` | Actual TLS endpoint/custom API domain **UNVERIFIED** |
| `OPS-M16-ROLLBACK` | No live app stack to roll back yet; preserve synthetic source and migration history |

The earlier local disposable Compose recovery tests are useful engineering evidence, not a deployed-service pass. T-017 owns browser, authorization, TLS, broker recovery and cost verification **only after actual services exist**.

Detailed start/access guide: [OCI_BOOT_SSH_RUNBOOK.md](OCI_BOOT_SSH_RUNBOOK.md). Provider and security restrictions: [OCI_ALWAYS_FREE.md](OCI_ALWAYS_FREE.md).
