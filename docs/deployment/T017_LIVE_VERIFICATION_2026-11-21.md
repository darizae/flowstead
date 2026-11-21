# T-017 — verified existing-instance deployment checks (2026-11-21)

**Status: PARTIAL / NOT DEPLOYED.** This record separates directly executed operations and read-only provider evidence from remaining host/API/browser acceptance tests. The owner chose **only** the existing Oracle `flowstead-demo-instance` in Frankfurt (`VM.Standard.E2.1.Micro`, x86_64), with no replacement hardware or paid service.

## Verified actions and results

| Area | Status | Concrete evidence |
| --- | --- | --- |
| OCI existing instance identity | PASS | OCI read identified only `flowstead-demo-instance`, `VM.Standard.E2.1.Micro`, boot volume 47 GB |
| SSH network hardening | PASS | Existing subnet ingress TCP/22 changed from public `0.0.0.0/0` to owner's current IPv4 /32, re-read and verified; original ICMP rules retained |
| Initial host access | PASS, then DEGRADED | Instance START request accepted and `RUNNING` verified. Initial SSH to Oracle Linux 9.8 authenticated as `opc`, showed `x86_64`, roughly 500 MiB physical memory and 500 MiB swap, noninteractive sudo |
| Host lifecycle | BLOCKED | A later package-inspection command stalled; TCP/22 accepted connections without SSH banner. A graceful `SOFTRESET` was requested/accepted. The last OCI observation was `STOPPING`. **Do not interpret RUNNING from the initial test as present availability.** |
| Supabase demo schema | PASS | Only `flowstead-demo` was written. Source-defined migrations `001_initial`, `002_forecast_metadata`, `003_jetstream_messages` applied. Ten app tables, Alembic head `003_jetstream_messages`, 3 historical markers |
| M1 source provenance | PASS | Local importer validated manifest `m1.v1`, seed `20250101`, source revision `ad5c94d1f46e79312a99cb9721f38700f24fdf6b` and canonical CSV SHA-256 `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e` |
| M1 database import | PASS | 5 fictional Plants, 43,800 hourly reading rows (8,760 per Plant), 1 ingest batch; 5 synthetically correct ingest-completed events persisted as pending in the outbox |
| Data API boundary | PASS (SQL grants) | `anon` and `authenticated` have no `USAGE` on the private `app` schema; public migration markers are not granted to them |
| Runtime database authorization | PARTIAL | Created `flowstead_runtime` with app-only DML/sequence grants; no DDL or migration-table access. Role remains `NOLOGIN`; server-to-server secret provisioning and verified TLS database connection still unavailable. Never substitute the migration/admin credential |
| Operator identity and Plant grants | BLOCKED | Demo `auth.users`: 0; `app.operator_plant_access`: 0. No real invited operators to exercise private flows |
| Vercel frontend | PASS (build), PARTIAL (live) | Existing `flowstead` Vercel deployment READY and both default Vercel HTTPS hostnames return HTTP 200 to HEAD. Deployed app is not yet connected to an observed live backend. SSO/session flow not browser-verified |
| Backend API HTTPS | FAIL / NOT DEPLOYED | The proposed API hostname did not return a valid HTTPS health response. No FastAPI/NATS/worker/TLS proxy service has been started successfully on the Oracle host |
| Local backend regression | PASS | 59 backend unit tests passed, including existing-host and credential-isolation regressions |
| Local frontend build | PASS | TypeScript typecheck and Vite production build passed; bundler warned about a large JS chunk |
| Deployment documentation | PASS | Documentation check passed, and current runtime guides and Docker fallback target the existing x86_64 host exclusively |
| Npm production dependency audit | PASS (checked subset) | `npm --prefix frontend audit --omit=dev`: 0 advisories |
| Supabase security advisor | PASS (advisory result only) | Supabase `get_advisors` security returned 0 lints; **not** a penetration test |
| Python dependency advisories | PASS (installed distributions only) | Independent `pip-audit --path` check of 38 installed backend distributions found zero reported advisories. This is **not** an exhaustive locked transitive/environment audit |
| Tracked-file credential-pattern scan | PASS (limited) | 215 tracked files checked for key patterns; 0 matches. This is not a complete history/archive/PII audit |
| Cost and alerts | UNVERIFIED | No billing/usage hard-cap proof was obtained; no paid resource was created |

## Acceptance cases and incomplete work

- `CLOUD-M16-RESOURCES`: **PARTIAL** — existing host, shape, network/volume verified; last lifecycle state `STOPPING`, current usage cost unverified.
- `CLOUD-M16-DATA`: **PASS for schema/import** — head 003, 5 Plants/43,800 rows; no signed-in operator data setup.
- `SEC-M16-NET` and `SEC-M17-OCI-INGRESS`: **PARTIAL** — OCI SSH /32 verified, but no actual public TLS, HTTP port exposure or OS firewall host audit.
- `OPS-M16-ARM` and `OPS-M17-OCI-ARM` (historical IDs): **PARTIAL** — observed chosen host x86_64, service architecture/startup not verified.
- `OPS-M16-QUEUE`, `OPS-M17-OCI-RECOVERY`, `OPS-M17-RECOVER`: **BLOCKED** — 5 pending outbox events exist but no live JetStream/worker; no claim of durable replay after host restart.
- `E2E-M17-PUBLIC`, `E2E-M17-AUTH`, `UI-M17-LIVE`: **BLOCKED** — no verified HTTPS API or actual signed-in identities. A static Vercel HTTP 200 is not application E2E validation.
- `OPS-M17-OCI-COST` and `OPS-M17-COST`: **UNVERIFIED** — provider usage and billing alerts were not fully inspected.

## Implementation prepared but not installed

`deploy/oci/native/` includes low-footprint systemd units for the chosen host: non-root, memory-bounded NATS on loopback with persistent JetStream; FastAPI and worker configured to connect only over localhost; a loopback-only Caddy readiness route; and a separate example for a restricted runtime database credential. These artifacts were written/tested locally **without uploading or enabling them on the VM** because SSH was unresponsive. The optional Docker fallback was retargeted to `linux/amd64`, but Docker was not available on the host at initial inspection.

## OCI recovery escalation attempted

At approximately 22:41 Europe/Madrid (CET), after the existing host had remained
in `STOPPING` following the accepted graceful `SOFTRESET`, a single OCI
`RESET` attempt was made **on that same instance**. Oracle rejected the action
with **HTTP 409 Conflict**, and a fresh instance-status query still reported
`STOPPING`. No alternate or new instance was created. Do not repeatedly issue
power actions while Oracle holds the instance in this transition; wait for the
existing lifecycle operation to settle or use Oracle's supported instance
recovery/support workflow. The public application has **not** been launched.

## Completion conditions

Restore healthy SSH access to the existing host, verify swap/memory and whether any package operation remains stuck. Securely provision/verify a restricted Supabase runtime login without leaking credentials, and arrange actual invited identities if private tests are required. Install/start and monitor native service components on the existing VM; prove NATS persistence and queued→completed forecasts; configure DNS/certificate/front-end API binding; then run direct public/private browser tests and provider cost checks. Do not call T-017 completed until those observations exist.

No use of `flowstead-dev`, new VM, domain apex replacement, paid service, credential dump or destructive reset was performed.
