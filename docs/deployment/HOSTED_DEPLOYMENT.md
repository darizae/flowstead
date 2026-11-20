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
| **Create Instance estimate** | **Boot volume €1.85/month (no compute charge shown)** | Create Instance → "View estimated cost" |
| **Cost Estimator (public, Oracle)** | A1 `VM.Standard.A1.Flex` 2 OCPU/12 GB + 50 GB boot with **"Apply 200 GB Free Tier Discount"** checked → **storage €0.00** | oracle.com/cloud/costestimator.html; toggle zeroes the boot volume |
| **Live tenancy cost confirmation** | **UNVERIFIED** — in-console Cost Estimator/Limits unreachable (OCI session lapsed, owner re-auth required) | — |

**Cost reconciliation (BLOCKED on live confirmation — nothing provisioned).**
The Create Instance "€1.85/month boot volume" is the **rate-card list price**;
that estimate does **not** subtract the Always Free 200 GB combined block+boot
storage allowance, and it shows **no compute charge** at all (A1 2 OCPU/12 GB is
Always Free). Oracle's official Always Free docs ([Always Free Resources,
resourceref](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm)) confirm "All tenancies receive a total of 200 GB of
Block Volume storage … apply to both boot volumes and block volumes combined",
and A1 Ampere 2 OCPU/12 GB is Always Free; this allowance applies to eligible
**Free Trial** accounts. Oracle's **Cost Estimator offers an explicit "Apply
200 GB Free Tier Discount"** control, which changed the boot volume estimate from
≈€8.50 to **€0.00** (EUR: storage `€0.00`). Net: the €1.85 figure is **not proof
of a billable charge**, and the target configuration (A1 + 50 GB boot in
`eu-frankfurt-1`) is **supported as €0** by official docs + the estimator.

**However**, that is estimator + documentation evidence, **not** a live-tenancy
billing confirmation, and the OCI preflight forbids provisioning without
confirmed zero-charge eligibility in the actual tenancy. Provisioning
was **not** performed and remains gated on the live checks below. Post-trial a
Free Tier account may bill or reclaim idle resources; trial credits are **not**
proof of permanent free eligibility. **No VM, VCN, boot/block volume, budget or
billing alert was created.**

Remaining prerequisites to provision at confirmed €0 (each blocked):

1. **Owner re-signs in to OCI** (session lapsed; a password-manager autofill
   overlay also blocks the browser relay — must be dismissed in Chrome). Then
   confirm in the **in-console Cost Estimator** with "Apply 200 GB Free Tier
   discount" and read **Limits/Usage** to prove remaining quota
   (0/2 OCPU, 0/12 GB, 0/200 GB) in `eu-frankfurt-1`.
2. **Owner SSH public OpenSSH key** supplied → authenticated VM access for
   deployment.
3. **DNS approval** for `flowstead.darizae.dev` / `api.flowstead.darizae.dev`
   (proposals only; apex `darizae.dev` personal site untouched).
4. **Supabase `flowstead-demo`** admin connection string + invitation recipients
   → live Alembic/import/Auth (else marked UNVERIFIED).
5. Vercel static-frontend project provisioning (separate).

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
| `CLOUD-M16-RESOURCES` | PARTIAL/UNVERIFIED: home region/tenancy/shape recorded; zero-cost **supported** (docs + Cost Estimator "Apply 200 GB Free Tier discount" → storage €0.00) but **not confirmed live** (OCI session lapsed) → **NOT DEPLOYED** |
| `OPS-M16-ARM` | **PASS (local)**: linux/arm64 backend image + nats/caddy arm64 manifests |
| `SEC-M16-NET` | **PASS (config/local)**: compose hosts only proxy; live local containers expose no app/NATS ports |
| `CLOUD-M16-DATA` | UNVERIFIED (no Supabase admin connection/DNS) |
| `SEC-M16-AUTH` | UNVERIFIED (no real recipients / live Auth) |
| `OPS-M16-QUEUE` | **PASS (local)**: durable queue survives worker restart (disposable external DB) |
| `OPS-M16-COST` | BLOCKED on live confirmation: €1.85 shown is rate-card list price (no compute charge; storage €0.00 with the 200 GB Free Tier discount). No VM/budget created; in-console Cost/Limits confirmation pending owner re-auth |
| `OPS-M16-ROLLBACK` | Local: image digest recorded; no live deployment to roll back |
| `OPS-M16-TLS` | UNVERIFIED (no approved DNS / no deployed proxy) |

T-017 owns the extended hosted browser/recovery/live-cost verification once a
$0-eligible path and approved DNS/recipients/SSH key exist.