# Flowstead — existing OCI Always Free demo instance (operational preflight)

**Actual deployment target (owner decision, 2026-11-21):** reuse the **existing** `flowstead-demo-instance` in Oracle Cloud Frankfurt, shape `VM.Standard.E2.1.Micro` (x86_64), with a 47 GB boot volume. This is the **only** authorized compute host; do not propose or create a replacement VM. The instance was started on 2026-11-21 via the owner's configured OCI CLI and was verified **RUNNING**. After SSH became unresponsive, a graceful `SOFTRESET` was accepted and the **last observed state was STOPPING**; host recovery is pending. SSH ingress was narrowed from `0.0.0.0/0` to the owner's then-current public IPv4 `/32` before startup. The owner may have a changing public IP; update the narrow source range only after verifying the new address.

**Resource reality:** Oracle lists the E2 micro as an Always Free-eligible shape subject to the tenancy's Free Tier limits and capacity. The VM reports x86_64, Oracle Linux 9.8, roughly 500 MiB available to the guest in total and about 500 MiB swap; the OS root filesystem currently has ~25 GB free. Design the deployment to fit these limits; avoid concurrent Docker builds or unnecessary resident services. Do not claim that all containers have been deployed. **No new OCI resource, image, load balancer or attached volume is authorized.**

## Verified account and state

- Region/home: `eu-frankfurt-1` (the previously authenticated Console confirmed Frankfurt home region).
- Existing instance: `flowstead-demo-instance` in the root compartment, shape `VM.Standard.E2.1.Micro`, boot volume 47 GB; last observed lifecycle `STOPPING` during recovery.
- Network: existing `flowstead-demo-vcn` / `flowstead-demo-subnet`; SSH TCP/22 restricted to the owner's current IPv4 `/32`; application ports are not publicly open. Host firewall must be checked in addition to Oracle security lists.
- SSH: owner-controlled private key `~/.ssh/id_ed25519_flowstead_demo` stays on the Mac; default Oracle Linux username `opc`.
- Supabase: **only** `flowstead-demo` (`hkyobferqdfiicnsaupl`) is the backend database, not `flowstead-dev`. On 2026-11-21 it was migrated to Alembic head `003_jetstream_messages` and populated with 5 synthetic Plants and 43,800 M1 readings (8,760 per Plant); five ingest events await the broker. The runtime database credential still needs to be provisioned securely, separate from migration credentials.
- Vercel: `flowstead` project exists and has a READY production build; live API binding, public access and custom DNS are not yet verified.
- Billing: the existing instance is considered within the configured Free Tier target, but no live invoice or hard $0 spending cap was independently verified. A budget alert is not a hard cap.

## Safe operations

Use the actual installed OCI CLI without printing account or resource OCIDs. Discover the instance ID privately by name, then inspect before performing a change:

```sh
oci compute instance get --region eu-frankfurt-1 --instance-id "$INSTANCE_ID" --query 'data."lifecycle-state"'
oci compute instance action --region eu-frankfurt-1 --instance-id "$INSTANCE_ID" --action START --wait-for-state RUNNING
```

Do not start if already running, restart during active work, or automatically terminate/replace it. For the current approved setup, see [OCI_BOOT_SSH_RUNBOOK.md](OCI_BOOT_SSH_RUNBOOK.md). Only allow TCP 80/443 if a real HTTPS proxy and intended DNS are configured; keep FastAPI 8000, NATS 4222/8222 and database ports private. SSH must not be reopened to the world. Avoid installing infrastructure packages that cannot run within the instance's available memory.

## Delivery gates

1. Confirm the instance responds over the owner-restricted SSH path and measure CPU/memory/disk and network egress. If unavailable, diagnose rather than guessing.
2. Install or launch the smallest compatible **linux/amd64** FastAPI, persistent NATS and worker, and TLS proxy stack; validate memory under load and on restart. Native systemd services are acceptable on this existing host.
3. Configure only a **restricted runtime** Supabase database connection using TLS certificate/hostname verification. Keep owner/migration credentials offline and out of process environments, Docker Compose, logs and frontend bundles.
4. Validate TLS, public synthetic-only reads, deny-by-default authentication, queued forecast execution, persistence/restart, bounded requests, source and digest evidence.
5. Record *actual* billing/cost and ingress observations separately; mark untested claims UNVERIFIED.

Never modify `flowstead-dev`, create paid resources, expose a high-privilege secret, publish raw CLI logs or rely on a budget notification as a spending cap.
