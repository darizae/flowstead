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

## Recovery verification (2026-11-21, ~22:47–22:52 CET)

Browser relay (evaluated first, per owner direction): the user's Chrome had **no
OCI Console tab and no authenticated OCI session**; opening
`https://cloud.oracle.com/` redirected to `oracle.com/cloud/sign-in.html`, so
console inspection would require MFA sign-in (forbidden). OCI CLI (configured,
working) was therefore the diagnostic path.

The stuck `STOPPING` resolved on its own: consecutive OCI lifecycle probes went
`STOPPING` (22:47:08→22:49:52) then **`RUNNING` at 22:50:04** — roughly 9 minutes
after the accepted `SOFTRESET`. No further power action was issued after the 409.
Public IPv4 re-read from the attached VNIC; SSH (owner `/32` ingress, unchanged)
re-established.

Post-recovery host health (SSH as `opc`, Oracle Linux 9.8, `x86_64`):
- `systemctl is-active sshd` = `active`; sshd listening on 0.0.0.0:22 and [::]:22.
- Memory: 498 MiB total, ~268 MiB used, 230 MiB available; 497 MiB swap, ~19 MiB used.
- Disk: root filesystem 30G, 5.4G used, 25G free (19%).
- `systemctl --failed`: only benign `mcelog.service` (Machine Check Exception
  Logging Daemon); no flowstead/nats/uvicorn/caddy processes or units present.
- No `dmesg` OOM/kill entries in this boot; only non-fatal `auditd` sendmail note.
- Listening sockets: 22, 111, and loopback-only control ports (44321, 4330);
  no public app/broker/database port exposed.

Status of key T-017 dependencies at this recovery: host **healthy and reachable**,
but the restricted Supabase runtime LOGIN/password, verified TLS DB connection,
real operator identities, and an authorized public TLS domain for the API remain
**outstanding**. The prepared `deploy/oci/native/` systemd units were **not**
uploaded/enabled in this recovery pass (memory-bounded install deferred until the
runtime DB credential and DNS/TLS are provisioned).

## Completion conditions

Restore healthy SSH access to the existing host, verify swap/memory and whether any package operation remains stuck. Securely provision/verify a restricted Supabase runtime login without leaking credentials, and arrange actual invited identities if private tests are required. Install/start and monitor native service components on the existing VM; prove NATS persistence and queued→completed forecasts; configure DNS/certificate/front-end API binding; then run direct public/private browser tests and provider cost checks. Do not call T-017 completed until those observations exist.

## NATS-only deployment on the existing host (2026-11-21, ~22:54–22:57 CET)

Installed and tested **only** the low-footprint NATS JetStream daemon as the non-root
`flowstead` system user on the existing Frankfurt micro. API/worker/proxy were **not**
installed or enabled (Supabase runtime LOGIN and authorized TLS domain still pending);
`install-unit-files.sh` was not run. No `dnf` install/upgrade was performed. No shell
`history`/logs received any secret.

| Item | Verified result |
| --- | --- |
| Host identity/state | `flowstead-demo-instance`, `VM.Standard.E2.1.Micro`, OCI **RUNNING**, Oracle Linux 9.8 x86_64 |
| NATS version | **v2.12.15** (latest 2.12.x), `git_commit 8460a42`, go1.25.12, from `nats-server` release assets |
| Publisher SHA-256 | tarball `nats-server-v2.12.15-linux-amd64.tar.gz` = `58ab8131f819263897e2fc38e503e1b755b63bcafeecc7d12582487df48ca15e` (verified against official release `SHA256SUMS`) |
| Installed binary SHA-256 | `/usr/local/bin/nats-server` = `214ca5fdf5adbda087e0167de530fa248ef5f80cea469e5ce0a905cd5be4b6d8`; `nats-server -v` = `v2.12.15` on host |
| Install path | `/usr/local/bin/nats-server` (root:root 0755); config `/etc/flowstead/nats.conf` (root:flowstead 0640); store `/var/lib/flowstead/nats` (flowstead 0700) |
| Service unit | `flowstead-nats.service` (root 0644), user/group `flowstead`, `Restart=on-failure`, `RestartSec=5`, `MemoryMax=80M`, `MemorySwapMax=160M`, `NoNewPrivileges`, `ProtectSystem=strict`, `ReadWritePaths=/var/lib/flowstead/nats`, **enabled** at boot, **active (running)** |
| Network | `listen 127.0.0.1:4222`, `http 127.0.0.1:8222`; `ss` shows both only on loopback. No public broker port. Only public listeners unchanged from baseline: `:22` ssh and `:111` rpc |
| JetStream bounds | `max_mem_store 16MB`, `max_file_store 256MB`, `store_dir /var/lib/flowstead/nats`; server reported Max Memory 16.00 MB / Max Storage 256.00 MB |
| Monitor health | `GET http://127.0.0.1:8222/healthz` → `{"status":"ok"}`; `/varz` host/port `127.0.0.1` |
| JetStream durability | Temporary file stream `FLOWSTEAD_TEST`: 100 msgs published (seq 1–100); after `systemctl restart flowstead-nats` the stream state still showed **Messages 100, First seq 1, Last seq 100**; message #50 retrieved intact by content. Stream was then deleted (store back to 0) |
| Memory | `MemoryCurrent` ≈ 3.4 MiB (peak 3.5 MiB) vs `MemoryMax 80M`; `MemorySwapMax 160M`; host free ≈ 233 MiB available, no OOM |
| SSH after install | `sshd active`, SSH session established after NATS install/restart |

The five original `app.message_outbox` ingest events still await a real worker dispatch;
T-017 messaging durability beyond the isolated probe stream remains a scheduled
acceptance test once API/worker are provisioned.

No use of `flowstead-dev`, new VM, domain apex replacement, paid service, credential dump or destructive reset was performed.

## End-to-end hardening follow-up — same day

This section **supersedes older STOPPING and pre-NATS entries above** where
they described a temporarily unreachable host. The existing OCI micro is
RUNNING and NATS is deployed; neither the API nor worker is deployed yet.

- **Verified live OCI NATS auth:** Broker has a host-generated random token
  stored at `/etc/flowstead/nats-auth.conf`, owned root:flowstead 0640.
  `nats.conf` includes this protected file. An unauthenticated NATS protocol
  client received no successful PONG, while a client with the protected worker
  token authenticated successfully. `flowstead-nats` remains active, with
  file-backed JetStream, localhost-only 4222/8222, healthy `/healthz`, no
  additional volume, package upgrade or public port.
- **Separate operating-system identity:** On the existing VM, Linux accounts
  `flowstead-api` and `flowstead-worker` were created for future services;
  the `flowstead-proxy` identity is defined in the local service config but
  has NOT been installed on the host (the proxy is not deployed),
  separate from the already-running `flowstead` broker user. The worker-only
  broker connection exists in root:flowstead-worker 0640
  `/etc/flowstead/nats-worker.env`. API service code does not load that file
  or a NATS_URL. Future API and worker DB environment files are distinct and
  have not yet been populated with DB secrets.
- **Verified live Supabase permission fix:** The initial
  `flowstead_runtime` DML role was excessively broad; the revised SQL
  migrations `005_least_privilege_runtime_roles` and
  `006_remove_worker_operator_grant` were applied on **flowstead-demo only**.
  `flowstead_runtime` retains no app DML and NOLOGIN; dedicated
  `flowstead_api` and `flowstead_worker` are also currently NOLOGIN pending
  separate secure passwords. API cannot mutate source/Plant/operator grants,
  worker cannot mutate source/Plant data **or even SELECT operator assignments**,
  and API cannot read broker/worker credentials. Public-schema historical
  migration tables gained RLS; Data API anon/auth still have no app-schema use.
- **Database TLS (Mac, not credential-authenticated host):** An OpenSSL
  Postgres STARTTLS connection to an observed Supabase session pooler completed
  with TLSv1.3 and `Verification: OK` using a pinned Supabase Root 2021 CA.
  The CA came from an independent public repository and should be cross-checked
  against the CA served by Supabase Database Settings before first credential
  delivery. The **correct** project-specific pooler host must come from the
  Supabase Connect panel; no database LOGIN connection yet passed.
- **Vercel:** Existing production host served HTTP 200 HTML for
  `/api/v1/public/plants`, **not JSON**. Local Vercel rewrite now excludes
  `/api` and adds HTTP-level CSP/anti-framing/MIME/referrer headers; this
  has **not been redeployed**. Live Vercel project was configured with only
  the `flowstead-demo` public Auth URL and `sb_publishable_` key for
  production and preview. No database or service-role credential was sent
  to Vercel. A new build is required.
- **Operator identities:** Supabase `auth.users=0` and
  `app.operator_plant_access=0`; no owner-selected invitee, grant or
  token exists. Real signed-in private E2E remains **BLOCKED**.
- **Optional Docker fallback:** Local config has independent API/worker DB
  files, a protected NATS token secret and separate worker-only broker URL.
  Static Docker Compose configuration passes. The Docker daemon is not running
  in the available local environment, so no container runtime test is claimed.
- **Provider billing and public HTTPS:** Still **UNVERIFIED**, no new paid
  resource/VM made, and no DNS zone-wide replacement performed.

See the [end-to-end security report](../security/2026-11-21-end-to-end-security-audit.md)
for remaining P1/P2 checks. **T-017 remains PARTIAL** until a real configured
FastAPI/worker, invited-operator JWT authorization, NATS outbox delivery and
HTTPS browser smoke have all been observed. The five initial outbox events
remain awaiting a worker.

## Additional external ingress verification

A bounded single-connect external TCP probe from the owner's Mac against
the existing OCI VM on 2026-11-21 showed port **22 reachable** (restricted by
Oracle ingress to the owner's current public IPv4 /32), and ports
**80, 443, 8000, 4222, 8222, 5432 not connectable** (TCP timeouts).
This verifies the current no-public-API/queue exposure from this vantage
only, not arbitrary remote source restrictions or complete host firewall
correctness. Remote SSH confirmed `flowstead-nats active`, `enabled`, and
localhost `/healthz` returned `{"status":"ok"}`; the API/worker Unix
accounts exist, and broker auth and worker-token files have restrictive
0640 permissions. A separate operator TLS API hostname still does not work.

The new Vercel public Auth URL/publishable key settings were re-listed by
provider API. Local source tests show the revised Vercel config excludes
`/api` from SPA rewrites and adds HTTP CSP/anti-framing headers, but the
deployed frontend is still an earlier commit, so these changes are
**NOT live**. A source-controlled release is required; no GitHub push or
Vercel production promotion was performed.

## Flowstead custom-domain and backend staging follow-up (November 2026)

**Public frontend — PASS:** The existing Vercel project now owns the verified
`flowstead.darizae.dev` custom domain, with a dedicated Vercel DNS CNAME.
Production deployment `0554a10` serves HTTPS status 200 and a checked-in SVG
favicon at `/favicon.svg` (image/svg+xml). SPA fallback correctly returns 404
for missing `/api` paths. Vercel public build environment has exactly the
expected public Supabase Auth URL/publishable key and
`VITE_API_URL=https://api.flowstead.darizae.dev/api/v1`.

**API DNS and TLS — PASS for transport, NOT the application:** Added explicit
`api.flowstead` A record for the *existing* OCI micro. Existing OCI VCN and
host firewall permit only SSH from the owner's /32 plus required ACME/HTTPS
80/443; the NATS and database ports remain private. Official published
Caddy v2.10.2 linux/amd64 release was checksum-verified and installed as the
unprivileged `flowstead-proxy` systemd service. Caddy and NATS stay active.
An external `curl` request to the live HTTPS health endpoint completed
certificate verification but returned **502**, correctly indicating that the
FastAPI upstream was not running. Do not mark T-017 API PASS on this basis.

**Backend runtime staging — PASS for software, not service startup:** Installed
an official digest-verified, standalone CPython 3.12.16 distribution and
checksum-verified uv 0.9.13 on the existing x86_64 micro. Staged reviewed
Flowstead backend source in `/opt/flowstead/current/backend`, installed
committed `uv.lock` requirements in `/opt/flowstead/venv` using
`uv sync --frozen --no-dev` with bounded concurrency, and successfully
imported FastAPI, psycopg, NATS client, JWT, SQLAlchemy and report libraries.
The broker and proxy remained active after installation; the host had >200 MiB
memory available. API and worker systemd units are installed but remain
**INACTIVE** pending delivery of already-activated restricted role credentials to the VM.

**Verified Supabase connection target — PASS (TLS, not DB login):** The
authenticated project-specific Connect dialog identified session pooler
`aws-1-eu-west-1.pooler.supabase.com:5432`, with username
`postgres.hkyobferqdfiicnsaupl` for the owner. The server verified the
pooler TLS 1.3 certificate, hostname and Supabase Root 2021 CA with
`Verification: OK` and correct pinned fingerprint. The earlier guessed
`aws-0` endpoint was **not** the confirmed host.

**Updated database status (2026-11-22) — activated and verified:** The owner ran
`scripts/provision_demo_runtime.py --apply` in their private Mac Terminal.
Both `flowstead_api` and `flowstead_worker` database roles now have LOGIN,
and their individually generated high-entropy credentials succeeded against
the Supabase session pooler over verified TLS. Postgres owner credentials
were not stored. The script exited with a generic RuntimeError **after** those
checks, before it reported VM credential installation; the later VM SSH
preflight timed out without a server SSH banner. Existing app role passwords
are still in the owner-only, local `runtime-roles.json` file and MUST NOT be
regenerated or shared. The updated script supports `--resume` to recheck both
existing logins and continue secure VM secret-file installation and service
startup without asking for the database administrator password. The VM was
placed through one graceful SOFTRESET for an unresponsive SSH daemon; its
stop/restart and any resumed run must be verified, not assumed complete.

**Test identities — CREATED, CONFIRMED, SCOPED (2026-11-22):** The
owner used the actual Supabase Auth Admin Create New User dialog with unique
private passwords and Auto confirm. Read-only SQL verified that the two
non-deliverable test accounts now exist and are confirmed:
`flowstead-test-operator-a@example.invalid` and
`flowstead-test-operator-b@example.invalid`. Scoped idempotent database
grants were applied after verifying real `auth.users.id` subjects. Operator
A has precisely `plant-01` and `plant-02`; operator B has precisely
`plant-03`, `plant-04`, and `plant-05`. SQL verification confirmed five
disjoint operator access rows and no additional test grants. **Real JWT
authorization via hosted FastAPI is still unverified** because the existing
VM is in a graceful SOFTRESET transition and worker/API are not yet running.
No test passwords or tokens were copied into Git or chat.

**Current release conclusion:** Frontend DOMAIN/TLS/FAVICON passed. Backend
origin DOMAIN/TLS passed, but application HTTPS 200, outbox dispatch,
auth journeys, forecasting, provider billing and full T-017 remain incomplete.
No extra VM, load balancer, paid hosting or unrelated Supabase project was
created or changed.

## 2026-11-22 live API and worker cutover — verified, supersedes earlier blockers

- **Root-cause and repair:** The first successful role-login `--resume` run
  installed both environment files but failed its OS-file-access check:
  it used Postgres role names with underscores (`flowstead_api`,
  `flowstead_worker`) as Unix groups. The actual Linux groups have hyphens
  (`flowstead-api`, `flowstead-worker`). Files were `0640 root:root`,
  preventing each service from reading its own DB credential. The installer
  now maps role names to Linux groups and uses `set -eu` to fail on an
  unsuccessful `chown`. A focused regression test verifies both behaviors.
- **Startup handling:** A second attempt passed all file checks and started
  both systemd services, but an immediate HTTPS smoke encountered a
  **transient 502** while Uvicorn bound its socket. Added a bounded
  readiness retry limited to HTTPS 502/503/504 and transport errors; actual
  401 and other unexpected status codes fail immediately. Regression
  tests cover a transient 502 and a non-retryable 401.
- **Full bootstrap acceptance:** Running
  `backend/.venv/bin/python scripts/provision_demo_runtime.py --resume`
  with the existing private local credential file completed with **exit 0**,
  without reentering the admin password: both restricted DB logins and
  certificate-validated TLS PASS; protected VM file ACLs PASS; worker/API
  systemd startup PASS; live HTTPS health and five public Plants PASS;
  PostgreSQL pending outbox rows **0**.
- **Live systemd and resource evidence:** Existing Oracle E2 micro RUNNING.
  `flowstead-api`, `flowstead-worker`, `flowstead-nats` and
  `flowstead-proxy` are all **active** with zero recorded restarts.
  `api.env` is `0640 root:flowstead-api`; `worker.env` and
  `nats-worker.env` are `0640 root:flowstead-worker`.
  The API listens only on `127.0.0.1:8000`, NATS on
  `127.0.0.1:4222` and `127.0.0.1:8222`; Caddy exposes 80/443.
  Host reported approximately **945 MiB RAM**, **369 MiB available**,
  **0 MiB of 497 MiB swap in use**. Worker and API used approximately
  85 MiB and 93 MiB of memory, respectively.
- **Real external HTTPS checks:** Both `/api/v1/health/live` and
  `/api/v1/health/ready` returned **200 JSON**; `/api/v1/public/plants`
  returned **200 JSON** with all five synthetic Plants;
  `/api/v1/public/plants/plant-01/latest` returned **200 JSON**;
  `/api/v1/public/plants/plant-01/report.pdf` returned **200**
  `application/pdf` with a valid PDF header; unknown-Plant latest
  returned **404**.
- **Authentication/CORS negative checks:** Protected `/api/v1/plants`
  denied anonymous and obviously forged-token requests with **401**.
  CORS preflight from `https://flowstead.darizae.dev` returned **200**
  with the matching allow-origin; untrusted origin was rejected with
  **400** and no allow-origin.
- **Message bridge:** Five original `app.message_outbox` rows moved from
  `pending` to **`published`**, zero remain pending, and the NATS
  JetStream monitoring endpoint reported one stream/one consumer/five
  stored messages. `app.message_failures` was **0**. These observations
  prove actual publishing, **not** a full authenticated forecast job
  and processing path. `app.forecast_jobs` and
  `app.forecast_issuances` still had zero rows.
- **Remaining T-017 scope:** Authenticated browser sessions using both
  confirmed test operators, real JWT cross-Plant authorization (positive
  and negative), forecast request -> worker -> stored 12-hour forecast,
  report/export access isolation, Caddy/NATS restart recovery, actual
  OCI charges and retention controls remain to be independently tested.
  This is a **LIVE API/WORKER deployment PASS, overall T-017 PARTIAL**.
  No new VM or paid cloud resource was created in this cutover.
