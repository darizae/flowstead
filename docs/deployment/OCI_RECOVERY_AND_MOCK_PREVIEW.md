# OCI outage: reproducible diagnosis and bounded recovery

Target: **existing** `flowstead-demo-instance` in `eu-frankfurt-1`. Do **not** create a replacement, reset Supabase passwords, delete JetStream storage, change DNS, or open additional ports.

## One-command runbook (from your Mac)

Prerequisites: authenticated `oci` CLI (`~/.oci/config`) and the existing `~/.ssh/id_ed25519_flowstead_demo` SSH key.

```sh
cd ~/repos/flowstead
just oci-diagnose
```

Read-only check: fetch the **single exact-name** instance from the tenancy, inspect OCI state and public API readiness, resolve the existing VNIC's public IP without logging it, connect using the existing SSH key, and ask systemd whether the API, worker, NATS and proxy are active. Nonzero exit is intentional if anything is unhealthy, not permission to reset credentials.

If OCI reports `STOPPING`, `STARTING` or another transitional state, do **not** issue another action. Allow the existing provider operation to finish and rerun the diagnosis. If it reports `STOPPED`, or `RUNNING` with BOTH guest SSH/services and public API unresponsive, explicitly request safe recovery:

```sh
just oci-recover
```

The script permits only **START** of an existing stopped machine or **SOFTRESET** of an unreachable running machine. It refuses competing transitions, mixed healthy/unhealthy checks, unknown machine names and destructive/paid actions. Oracle may respond with HTTP 409 while an operation is in progress; this is a blocker, not a reason to force reset. Recovery returns only after the lifecycle request; API readiness may lag system boot. Re-run `just oci-diagnose` after recovery.

If SSH returns but the API fails, inspect the failed component before restarting anything:

```sh
ssh -i ~/.ssh/id_ed25519_flowstead_demo -o IdentitiesOnly=yes opc@<VM_PUBLIC_IP>
sudo systemctl --failed --no-pager
sudo systemctl status flowstead-api flowstead-worker flowstead-nats flowstead-proxy --no-pager
sudo journalctl -u flowstead-api -u flowstead-worker -u flowstead-nats -u flowstead-proxy -b --no-pager -n 100
free -m
df -h /
```

Once identified, restart only the failed unit (for example `sudo systemctl restart flowstead-api`) and check both `/api/v1/health/live` and `/api/v1/health/ready` over the existing public HTTPS API origin. Keep NATS durable data and protected PostgreSQL credentials intact. If SSH is blocked by an outdated owner-only `/32` Oracle network rule after a public IP change, **verify your actual current IP privately** before changing that single SSH rule; never widen it to `0.0.0.0/0`.

## Observed outage on 2026-11-22

- Vercel `https://flowstead.darizae.dev/plants` returned HTTP 200, so static frontend hosting was online.
- Existing OCI machine initially reported `RUNNING`, but SSH could not complete its banner exchange and HTTPS API readiness, liveness and Plants reads timed out.
- A bounded SOFTRESET request returned OCI **409 Conflict**, reporting an existing modification. Subsequent Oracle state queries reported `STOPPING`. **No successful reset or restored API has been verified**. The runbook refuses to overlap that transition.
- Oracle console username recognition is separate from the OCI CLI API-key identity; the CLI was authenticated successfully and could read the instance. Console login failure by itself does not establish a VM fault.

## Deployed demonstration when Oracle is unavailable

On a **production** frontend build, anonymous visitors can click **Load Mock Data** on the Plants page. It switches to a clearly labeled **MOCK PREVIEW** rather than silently replacing real API results. **Return to Live Data** discards the in-memory preview and retries the real backend.

The preview contains five fictional Florida sites; latest readings, at most **168 hourly readings** per requested chart and **12 future forecast points** are generated *on demand* from a fixed clock and short deterministic arithmetic formulas. No JSON data dump, local database, new services or API requests are required to load the mock plants, readings or forecast. The preview displays an explicitly schematic, clickable Florida location panel **without map tiles or mapping libraries**; the normal live map is lazy-loaded separately. Forecast refresh and PDF requests remain live-only; the UI identifies forecasts as synthetic browser-computed values. Authenticated sessions cannot enable mock mode, and mock forecasts are never persisted to IndexedDB. This mode is intentionally for demo presentation, **not** offline authorization or evidence of backend readiness.

Verify locally:

```sh
npm --prefix frontend run typecheck
npm --prefix frontend test -- --run
npm --prefix frontend run build
python3 -m py_compile scripts/recover_oci_demo.py
```

Deploy the pushed frontend commit through the existing Vercel Git integration (or verify the release in the existing project); a Git push alone is not proof that production has updated.
