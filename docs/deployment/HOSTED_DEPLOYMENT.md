# Flowstead public-demo hosted deployment (T-016)

This runbook records the T-016 OCI read-only reconnaissance, the ARM64 hosted
deployment artifacts verified locally, and the exact external gates that could
not be executed during T-016 (each marked **UNVERIFIED**). It supplements the
Always Free preflight in [OCI_ALWAYS_FREE.md](OCI_ALWAYS_FREE.md) and the
host-neutral build/recovery runbook in [LOCAL_AND_RECOVERY.md](LOCAL_AND_RECOVERY.md).

## OCI reconnaissance (read-only, T-016 — recorded from the live Console)

Observed on the owner's authenticated Oracle Console via the browser relay
(2026-11-20); read-only inspection only, no resource created.

| Fact | Value | Source |
| --- | --- | --- |
| Home region | **eu-frankfurt-1** (Germany Central, Frankfurt) | Console region menu: "Germany Central (Frankfurt), home region, active" |
| Subscribed regions | 1 (Frankfurt only) | Region menu / Tenancy region picker |
| Tenancy | `danarech99` | Console home header |
| Account type | **Free Tier / Free Trial** | Console banner: "You are in a Free Trial. When your trial is over, your account is limited to Always Free resources." |
| Existing compute instances | **0** ("No items to display") | Compute → Instances, root compartment |
| A1 capacity | Ampere A1 available in any AD | Create Instance warning banner |
| Default image | Oracle Linux 9 (build 2026.10.30-0) | Create Instance → Image |
| Shape | `VM.Standard.A1.Flex`, marked **Always Free-eligible** | Create Instance → Shape |
| **Estimated cost** | **€1.85/month (boot volume)** | Create Instance → "View estimated cost" |

**Cost gate (BLOCKED, never provisioned).** Although `VM.Standard.A1.Flex` is
labelled "Always Free-eligible", the Create Instance estimate on this **Free
Trial** account reports a **€1.85/month** charge for the boot volume — **not
$0**. The Always Free $0 discount is therefore not confirmed for this account,
and the OCI preflight forbids provisioning anything whose estimated charge is
not $0. Post-trial, a Free Tria/Free Tier account may bill or drop free
resources; trial credits are **not** proof of permanent free eligibility.
**No VM, VCN, boot/block volume, budget or billing alert was created.**

Additional provisioning blockers recorded for the record:

- Owner-controlled **OpenSSH public key** not supplied → no authenticated
  VM access for deployment.
- `flowstead.darizae.dev` / `api.flowstead.darizae.dev` are **proposals only**;
  no DNS records approved or created (the apex `darizae.dev` personal site is
  untouched).
- Supabase **`flowstead-demo`** (`hkyobferqdfiicnsaupl`) has no verified app
  migrations/import; no admin connection string or invitation recipients were
  supplied → live Alembic/import/Auth are **UNVERIFIED**.
- No Vercel Flowstead project had been provisioned; Vercel deploy is separate
  and outside this task's verified execution.

## Hosted deployment artifacts (this repo)

| Artifact | Purpose |
| --- | --- |
| `compose.hosted.yml` | Hosted stack: `nats` (persistent JetStream), `api`, `worker`, `proxy`. **No local PostgreSQL**; only the proxy publishes 80/443; API 8000 and NATS 4222/8222 are never host-published. Secrets via `env_file` from a host secret-file (`HOSTED_ENV_FILE`). |
| `deploy/oci/Caddyfile` | Production HTTPS proxy config. Site host is the proposed `api.flowstead.darizae.dev` — **must stay disabled until that DNS record is approved** (Caddy ACME would fail on an unassigned hostname). |
| `deploy/oci/Caddyfile.test` | Local-only HTTP proxy config for the hosted smoke test (no DNS/TLS). |
| `deploy/oci/env.hosted.example` | Server-only env template (no secrets): hosted `DATABASE_URL`, Supabase verifier, CORS origin, trusted-proxy CIDR. |
| `deploy/oci/deploy.sh` | On-VM orchestrator: builds the arm64 image, validates/up starts the hosted stack, verifies only the proxy is public. |
| `just build-backend-image-arm64` / `verify-hosted-arm64` / `hosted-config-validate` / `test-deploy-hosted` | Local recipes. |

### Pinned images

| Image | Reference | arm64? |
| --- | --- | --- |
| NATS JetStream | `nats:2.12-alpine@sha256:b270f5e2428354c0335612694d7dd2fb588148e567a5757fdff325ef9c9332e6` | yes (manifest `a1f26b77…`) |
| Caddy proxy | `caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d` | yes (manifest `8dbca352…`) |
| FastAPI/worker | `flowstead-backend:arm64-hosted` (built `--platform linux/arm64` from `backend/Dockerfile` + `uv.lock`) | yes (image `os=linux arch=arm64`) |

## Networking (host-side + NSG; intended only)

Only the proxy terminates client traffic. Intended public ingress:

| Port | Purpose | Rule |
| --- | --- | --- |
| 443 | HTTPS (prod) | public, TLS via approved DNS |
| 80 | HTTP (cert issuance / redirect) | public, bounded |
| 22 | SSH | **only** from the owner-approved source CIDR |

Deny public ingress for FastAPI `8000`, NATS `4222`/`8222`, PostgreSQL
`5432`/`6543`, Docker socket. In the hosted stack nothing but the proxy has a
host port mapping, so a mis-set NSG cannot expose the app ports; `just
test-deploy-hosted` asserts `5443/4222/8222/8000` are never published.

## Local verification executed in T-016

```sh
just hosted-config-validate     # compose.hosted.yml parses; no local PostgreSQL
just build-backend-image-arm64  # docker build --platform linux/arm64 --load
just verify-hosted-arm64        # image linux/arm64; nats+caddy arm64 manifests
just test-deploy-hosted         # queue/worker restart + proxy path + no-db hosted stack
```

`scripts/test_deploy_hosted.py` boots `compose.hosted.yml` with a disposable
**external** PostgreSQL (standing in for Supabase), runs real Alembic to head,
imports the exact M1 source, then proves: OPS-M16-ARM image arch; SEC-M16-NET
(no host-published API/NATS ports); public reads + CORS + fail-closed auth
through the proxy; OPS-M16-QUEUE — a forecast command completes, a second
command enqueued while the worker is stopped survives, and the restarted worker
replays it (durable JetStream + outbox recovery); and graceful SIGTERM exit 0.

## Hosted acceptance status (T-016)

| Gate | Status |
| --- | --- |
| `CLOUD-M16-RESOURCES` | FAIL (cost): home region/tenancy/shape recorded, but A1 estimate is **€1.85/month**, not $0 → **NOT DEPLOYED** |
| `OPS-M16-ARM` | **PASS (local)**: linux/arm64 backend image + nats/caddy arm64 manifests |
| `SEC-M16-NET` | **PASS (config/local)**: compose hosts only proxy; live local containers expose no app/NATS ports |
| `CLOUD-M16-DATA` | UNVERIFIED (no Supabase admin connection/DNS) |
| `SEC-M16-AUTH` | UNVERIFIED (no real recipients / live Auth) |
| `OPS-M16-QUEUE` | **PASS (local)**: durable queue survives worker restart (disposable external DB) |
| `OPS-M16-COST` | BLOCKED: no VM created (non-zero estimate); no budget configured |
| `OPS-M16-ROLLBACK` | Local: image digest recorded; no live deployment to roll back |
| `OPS-M16-TLS` | UNVERIFIED (no approved DNS / no deployed proxy) |

T-017 owns the extended hosted browser/recovery/live-cost verification once a
$0-eligible path and approved DNS/recipients/SSH key exist.