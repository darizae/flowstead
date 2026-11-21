# Operator-safe OCI boot / SSH runbook (redacted, NOT EXECUTED)

- **Date:** 2026-11-21
- **Status:** **NOT EXECUTED.** Nothing here has been run. This runbook exists so the owner can boot/inspect the existing stopped VM **only under their own explicit decision**, and so Flowstead does not misrepresent that stopped instance as the target A1 host.
- **Verified fact:** the OCI VM `flowstead-demo-instance` (compartment root, `eu-frankfurt-1`) is **STOPPED** and is `VM.Standard.E2.1.Micro` — **1 GB RAM, 47 GB boot**, x86_64, **NOT** the Always-Free `VM.Standard.A1.Flex` (Arm64, 2 OCPU/12 GB) this project's hosting plan requires. A 1 GB x86 micro cannot run the NATS + API + worker + proxy stack the way the reviewed A1 arm64 layout expects, and it is not the shape this repo's deployment artifacts target.
- **OCI CLI commands are shown with placeholders only.** Never paste the tenancy/compartment OCID, instance OCID, public IP, SSH private-key path, or any secret into chat, Git, logs or screenshots. Redact all of them.

## Hard gates (no action without these, at least two of which the owner must confirm)

1. Owner explicitly authorizes **booting** `flowstead-demo-instance` / **replacing** it with an A1 host. Per T-019, do **not** start, resize, or re-provision it by default.
2. Actual zero-charge cost posture is confirmed in the live Console (Free Tier / Always-Free eligibility; A1 quota or explicit acceptance of the E2.1.Micro's usage/cost) — **or** the operator intentionally accepts the stopped-micro is only used for one-off inspection and is shut down again immediately.
3. The SSH **public** key fragment is known to the owner (private key stays on the owner machine). The exact bootstrap public key must match the owner's on-disk key before connecting.

## Prerequisite (owner-run, one-off)

```
# Preflight: confirm OCI CLI identity + region; do NOT print OCIDs.
oci iam region list
oci iam compartment list --compartment-id <REDACTED_COMPARTMENT> --all   # names only

# Confirm the instance state + shape WITHOUT starting it (read-only).
oci compute instance get --instance-id <REDACTED_INSTANCE_OCID> \
  --query "data.{state:\"lifecycle-state\",shape:shape,ocpu:shape-config.\"ocpus\",mem:\"memory-in-gbs\"}" \
  --output table

# Confirm the public IP is NOT exposed while STOPPED (it may vanish when stopped).
oci compute instance list-vnics --instance-id <REDACTED_INSTANCE_OCID> \
  --query "data[].{primary:is-primary,private:private-ip,public:\"public-ip\"}" --output table
```

## Boot (STOPPED → RUNNING), only after an explicit owner decision

```
oci compute instance action --instance-id <REDACTED_INSTANCE_OCID> --action START --wait-for-state RUNNING
```

**Verification after START (all read-only):**

```
oci compute instance get --instance-id <REDACTED_INSTANCE_OCID> \
  --query "data.\"lifecycle-state\"" --output table                 # expect Running
oci compute instance list-vnics --instance-id <REDACTED_INSTANCE_OCID> \
  --query "data[].\"public-ip\"" --output table                      # NEW public IP (rotate note)
```

Then confirm the **NSG/Security-List** allows only expected ingress before proceeding graded. If this micro is used only for one-off inspection: run the checks below, then **shut it down** to stop billing/uptime.

```
oci compute instance action --instance-id <REDACTED_INSTANCE_OCID> --action STOP --wait-for-state STOPPED
```

Do **not** `terminate` unless the owner separately authorizes deletion (destructive).

## SSH (only to an instance the owner authorized)

```
ssh -i <OWNER_PRIVATE_KEY_PATH> -o IdentitiesOnly=yes \
    opc@<REDACTED_PUBLIC_IP>                        # Oracle Linux default user is `opc`
```

- Keep the private key `chmod 600`, owned by the owner user, outside any repo.
- If the OS image uses a different default user (e.g. `ubuntu`), follow that image's convention.
- Restrict SSH to the owner's source CIDR in the NSG before/at first use; never wildcard `0.0.0.0/0`.

**First-contact verification after connect (redacted):**

```
sudo dnf --version >/dev/null && echo "os-ok"
uname -m                                   # expect the image arch you intended
free -m | awk '/Mem:/{print "mem_mb",$2}'
df -h / | awk 'NR==2{print "boot",$2,$4}'
# Only afterward: confirm ports are NOT bound publicly (8000/4222/8222/5432 def).
ss -ltn | grep -E ':8000|:4222|:8222|:5432' || echo "no-app-ports-public"
```

## Why the stopped E2.1.Micro is a blocker, not the target host

- 1 GB RAM is far below the reviewed stack's practical headroom and below the A1 12 GB target; NATS + API + worker + Caddy on 1 GB risks OOM with no swap and is not the layout `just test-deploy-hosted` proves.
- The repo's hosted artifacts target `linux/arm64` A1 (`build-backend-image-arm64`, pinned NATS/Caddy arm64 manifests). This micro is x86_64 with a different memory profile.
- Therefore: either (a) the owner later creates the reviewed Always-Free A1 VM (gated on confirmed free eligibility + quota), or (b) explicitly decides to repurpose the stopped micro — but then the documented "local hosted smoke passed" must not be presented as the A1/arm64 deployment. It is not.

## Outstanding environment blockers (carried forward, not resolved by this runbook)

- No Supabase `flowstead-demo` admin path for live Alembic/import/Auth/roles.
- No Vercel token/session for the frontend project + no DNS binding approval.
- No live OCI A1 host and no live cost/limits confirmation.