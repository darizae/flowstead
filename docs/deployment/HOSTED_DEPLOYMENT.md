# Flowstead — hosted deployment status and operator guide

**Status as inspected 2026-11-21:** The owner selected the existing `flowstead-demo-instance` (`VM.Standard.E2.1.Micro`, Oracle Linux 9.8, x86_64, Frankfurt) as the **sole deployment host**. OCI reported **RUNNING**, and Oracle SSH ingress was narrowed to the owner's current IPv4 `/32`. SSH and sudo were verified; the host recovered from a graceful `SOFTRESET` and is healthy. The **NATS JetStream daemon v2.12.15 is installed, enabled and active** as the non-root `flowstead` user on loopback with verified persistence. API/worker/TLS proxy remain **not deployed** until a restricted Supabase runtime LOGIN and an authorized TLS domain are provisioned. No additional VM is authorized.

## Verified completed items

- Existing Oracle instance is running; no new machine or volume was created.
- NATS server **v2.12.15** (`linux-amd64`, publisher SHA-256 `58ab8131…ca15e`, installed binary SHA-256 `214ca5fd…b6d8`) installed to `/usr/local/bin`, config `/etc/flowstead/nats.conf`, loopback only (`127.0.0.1:4222/8222`), bounded JetStream store, `flowstead-nats.service` enabled + active, memory-bounded (`MemoryMax 80M`). Verified JetStream durability across a graceful restart (100/100 messages preserved). Details in [T017_LIVE_VERIFICATION_2026-11-21.md](T017_LIVE_VERIFICATION_2026-11-21.md).
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
| `OPS-M16-ARM` (historical case ID) | x86_64 host; NATS `v2.12.15` amd64 binary installed, enabled, running; worker/API process startup still **UNVERIFIED** |
| `CLOUD-M16-DATA` | PASS migration 003 + five Plants + 43,800 validated rows |
| `SEC-M16-NET` | SSH source restricted to Mac /32; HTTPS/host-firewall and public ingress **UNVERIFIED** |
| `SEC-M16-AUTH` | Verified schema denies anonymous `app` access; live JWT identities **UNVERIFIED** |
| `OPS-M16-QUEUE` | 5 pending ingest events persisted; NATS JetStream daemon installed/durable probe passed; hosted worker dispatch of the 5 outbox events still **UNVERIFIED** |
| `OPS-M16-COST` | E2 micro is an Always Free-eligible target; actual billing **UNVERIFIED** |
| `OPS-M16-TLS` | Actual TLS endpoint/custom API domain **UNVERIFIED** |
| `OPS-M16-ROLLBACK` | No live app stack to roll back yet; preserve synthetic source and migration history |

The earlier local disposable Compose recovery tests are useful engineering evidence, not a deployed-service pass. T-017 owns browser, authorization, TLS, broker recovery and cost verification **only after actual services exist**.

Detailed start/access guide: [OCI_BOOT_SSH_RUNBOOK.md](OCI_BOOT_SSH_RUNBOOK.md). Provider and security restrictions: [OCI_ALWAYS_FREE.md](OCI_ALWAYS_FREE.md).

## Security-hardening update — 2026-11-21

The audit in [end-to-end security report](../security/2026-11-21-end-to-end-security-audit.md)
supersedes the initial shared-`flowstead_runtime` wording above. The live
`flowstead-demo` database now has **distinct NOLOGIN** roles
`flowstead_api` and `flowstead_worker`, with separately verified grants.
The old broad `flowstead_runtime` role has NOLOGIN and **all application
schema permissions revoked**; its old connection string must not be reused.
The worker cannot SELECT operator grants, and neither role can modify
synthetic telemetry or access-control data. The two public-schema migration
history tables have RLS enabled and no Data API read grants.

The existing OCI VM is **RUNNING**, NATS JetStream v2.12.15 is active, durable,
localhost-only, and NOW REQUIRES a protected host-generated authentication token;
unauthenticated NATS connections were denied on the live guest. The API and
worker OS users were created and are distinct from the broker user; their DB
credential files have NOT been provisioned, and API/worker services have NOT
been started. The proxy will use a fourth separate OS identity, but is not yet
installed.

The native templates are now `deploy/oci/native/api.env.example` and
`worker.env.example` plus the protected NATS token file. The optional Docker
fallback has **separate** API/worker env files and an explicit broker auth
secret; the older `deploy/oci/env.hosted.example` is intentionally
**deprecated**. Current Vercel project settings contain only the public
Supabase Auth URL and `sb_publishable_` key; new HTTP response headers and
non-HTML /api routing are in the local source, not deployed to production.
The actual public API/TLS/identity end-to-end status remains UNVERIFIED.

## Actual public domains and low-memory runtime staging (latest verified)

The custom frontend domain `https://flowstead.darizae.dev` is attached to the
existing Vercel `flowstead` project and serves its current GitHub deployment
with an SVG favicon. The API hostname `api.flowstead.darizae.dev` has a
dedicated Vercel-managed A record for the **existing** Oracle E2 micro, and
the VCN and guest firewall admit only public ACME/HTTPS 80/443 plus
owner-limited SSH. Caddy v2.10.2 was installed from a checksum-verified
linux/amd64 official release, runs as `flowstead-proxy`, and serves a valid
public HTTPS certificate. The API upstream currently returns **HTTP 502**
because FastAPI has not yet been started; this is NOT a deployment pass.

The existing VM also has a checksum-verified standalone CPython 3.12.16
and uv 0.9.13, committed backend source, and frozen production Python
dependencies in `/opt/flowstead/venv`. Imports of the FastAPI, PostgreSQL,
JWT, reporting, NATS and SQLAlchemy libraries passed. Caddy and
authenticated NATS JetStream are both systemd-active. API/worker systemd
units are installed but intentionally INACTIVE while their individual DB
logins are still NOLOGIN.

An authenticated Supabase Connect view confirmed the project session
pooler is **`aws-1-eu-west-1.pooler.supabase.com:5432`**. The VM verified
TLSv1.3, the hostname and the Supabase Root 2021 trust anchor. Templates
for API and worker are updated to use that host, the real project ref,
an ES256 Auth issuer, and the exact frontend CORS origin.

### Only required private credential action

In the owner's authenticated local Mac Terminal, use the read-only
`scripts/provision_demo_runtime.py` preflight and then the interactive
`--apply` mode. It prompts the owner **privately** for the existing
`flowstead-demo` PostgreSQL administrator password, never storing or
printing it. It creates or reuses two independent randomly generated
local role passwords, sends only standard SCRAM verifiers to Postgres over
certificate-validated TLS, verifies permission restrictions, installs
two separate protected host env files over SSH stdin, then starts and
smoke-tests worker/API. This is **prepared, not yet executed**. If the
admin password is unknown, the owner must reset it in the project's
Supabase Database Settings using their own authenticated session.
No admin credential should be pasted in chat or committed.

### Auth test-operator accounts

No Auth test identities were created. The authenticated provider dashboard
did reach Auth Users > Create new user, but the owner's Chrome password-manager
extension's autofill overlay blocked browser automation. Owner needs only
dismiss that overlay with Escape/click elsewhere in Chrome to retry.
The proposed synthetic non-deliverable identifiers are
`flowstead-test-operator-a@example.invalid` and
`flowstead-test-operator-b@example.invalid`. No real recipient invitations
may be sent; no direct SQL writes to managed `auth.users` are authorized.
