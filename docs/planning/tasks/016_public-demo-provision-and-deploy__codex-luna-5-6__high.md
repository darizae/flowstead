# T-016 — deploy the synthetic demo to the existing OCI host

**Owner decision (2026-11-21):** Use only the **existing** `flowstead-demo-instance` in Frankfurt (`VM.Standard.E2.1.Micro`, Oracle Linux 9.8, x86_64). The owner explicitly rejected creating a different machine; this instruction supersedes historical assumptions in older receipts and Git history. Begin work without another readiness interview. **Never create, resize, or replace the instance.** No paid upgrade, unapproved DNS/domain/apex change, unrelated project writes, or dangerous data reset.

## Fixed infrastructure and current evidence

- **OCI:** The original instance was **STARTED** using the configured OCI CLI on 2026-11-21. OCI showed RUNNING; ingress TCP/22 was narrowed to the owner's current Mac public IPv4 /32. SSH and sudo worked once. Subsequent SSH probes intermittently timed out after a lengthy package check; troubleshoot resource use and SSH before installing a service. Existing public VCN/subnet and 47 GB boot volume are the sole authorized resources.
- **Supabase:** Use only `flowstead-demo` (`hkyobferqdfiicnsaupl`, `eu-west-1`). On 2026-11-21 the app schema was migrated from source to Alembic `003_jetstream_messages`, five approved fictional Plants and 43,800 immutable synthetic M1 rows were imported, and five ingest-completed events were queued. A separate restricted role `flowstead_runtime` exists with app-only DML grants; secure runtime LOGIN/password and connection verification remain outstanding. **Never expose the owner/migration DB credential to the API/worker or frontend.** The `flowstead-dev` project is out of scope.
- **Vercel:** Existing `flowstead` project already has a READY production frontend build. Do not create a duplicate. SSO/deployment protection remains enabled and live API binding/custom DNS have not been proven.
- **Actual memory:** OCI guest reports roughly 500 MiB physical memory with a similar amount of swap. Minimize process footprint and bounded resource use; do not claim a local Docker stack will fit without measuring it.

## Objective

Serve the same five synthetic Plants and their observations with real FastAPI and a persistent NATS JetStream broker/worker running under the existing Oracle Linux host, a valid HTTPS endpoint, a connected Supabase demo DB, and an existing Vercel frontend. Private actions require real JWT identities with verified Plant grants. No public signup, real facility data, public forecast submission, or hidden provider charges.

## Steps

1. **Observe host safely:** Revalidate OCI RUNNING and approved public IPv4/SSH source /32, guest `uname -m`, memory/swap, disk, SSH health and active systemd services. Diagnose any hangs/OOM. Do not reset running services as a troubleshooting shortcut. No new compute/network/storage resource.
2. **Choose a verified low-footprint runtime:** Prefer native Python 3.12 service and separately supervised NATS/worker/HTTPS proxy if more feasible than Docker. If Docker is actually installable and sustainable, use `linux/amd64` backend and pinned NATS/proxy images. Set systemd resource limits, restart policies and durable NATS storage; ensure owner `opc` is not given unnecessary root permissions.
3. **Protect ingress:** restrict SSH to a current owner CIDR; do not expose API 8000, NATS 4222/8222, PostgreSQL 5432/6543, or Docker socket. HTTPS proxy only after real domain and TLS verification. Do not redirect `darizae.dev` apex or unrelated Vercel projects.
4. **Bind database correctly:** use the existing demo project; verify Alembic/row counts first. Create a safe restricted runtime login credential via a supported secret-management flow, store it protected outside Git, verify TLS certificates and hostname (e.g. `sslmode=verify-full` with a trusted CA), deny runtime DDL, and keep migration-owner privileges offline. No `flowstead-dev` use.
5. **Start one bounded instance of each service:** FastAPI, NATS JetStream with persistence, forecast/outbox worker, and TLS proxy; measure RSS/swap, failures and restart behavior on the **real** VM. Never replace persistent JetStream with an ephemeral web process.
6. **Join existing frontend:** inspect Vercel's actual frontend/deployment settings, point only `flowstead` at the verified HTTPS API, retain publishable-only Supabase client keys, enforce exact CORS origins and safe authentication.
7. **Financial and security review:** inspect current actual provider spend and free eligibility; an alert is NOT a hard spending cap. Test public/private boundaries, per-principal forecast throttling, queue retention, TLS, paths and provider IAM roles before public promotion. Do not create billable services.

## Source/data invariants

Synthetic source `flowstead-sim` pinned commit `ad5c94d1f46e79312a99cb9721f38700f24fdf6b`, manifest `m1.v1`, seed `20250101`, SHA-256 `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`. Existing records have been counted; never re-import without digest/transaction checks or mutate another Supabase project. Retain `@darizae/marisma@0.2.0` UI library.

## Verification and delivery

- `CLOUD-M16-RESOURCES`: existing running E2 micro, guest resources, ingress, actual cost/inventory; no additional resources.
- `OPS-M16-ARM`: **historical test-case ID only** — check running `linux/amd64` image/process compatibility and RSS on the actual chosen host; do not demand an unrelated architecture.
- `SEC-M16-NET`: only verified 443/80 if needed and owner-CIDR SSH; app/broker/DB not directly exposed.
- `CLOUD-M16-DATA`: 10 tables, schema at 003, five Plants and 43,800 readings; runtime credential tested without disclosure.
- `SEC-M16-AUTH`: real issuer/JWKS, Plant-scoped private routes and no anonymous writes or cross-Plant data.
- `OPS-M16-QUEUE`: durable ingest/replay and requested→completed forecast job with worker restart.
- `OPS-M16-COST`: observed provider billing/free plan; no invented $0 guarantee.
- `OPS-M16-TLS`: real frontend→backend HTTPS, certificate and CORS checks.
- `OPS-M16-ROLLBACK`: safe reversible release without DB wipe; log exact deployed SHA.

Root `AGENTS.md` applies: implement, run local regressions, document **PASSED / BLOCKED / UNVERIFIED** honestly, commit and merge into **local** `main`, and **do not push** automatically. See `docs/deployment/OCI_ALWAYS_FREE.md`, `HOSTED_DEPLOYMENT.md`, `OCI_BOOT_SSH_RUNBOOK.md`, `docs/testing/INDEXED_TEST_PLAN.md` and `docs/planning/IMPLEMENTATION_SPEC.md`.
