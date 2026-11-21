# Existing E2 micro — native low-memory deployment (T-016/T-017)

These are **prepared, not yet deployed** native-service assets for the owner's
existing Oracle Linux 9.8 x86_64 `flowstead-demo-instance`, with limited
physical RAM and swap. No replacement compute host. See
[HOSTED_DEPLOYMENT.md](../../../docs/deployment/HOSTED_DEPLOYMENT.md) for currently verified facts.

## Preflight

1. Ensure the current instance is running, SSH is responsive through the
   owner's source-CIDR restriction, and `uname -m` shows `x86_64`.
2. Check `free -m`, `df -h`, `journalctl -b`, root filesystem capacity,
   and provider cost before any install. Do not start a bulk package upgrade
   if the tiny VM cannot finish it.
3. Provision **reviewed amd64** binaries for `nats-server` (pinned NATS 2
   compatible with checked-in lock/config) and `caddy`; verify SHA-256
   checksums and publisher provenance before `/usr/local/bin` installation.
   Install Python 3.12 and pinned `backend/uv.lock` dependencies under
   `/opt/flowstead/venv`, using the reviewed package installer; do not run as
   root. Avoid unpinned `curl | sh`.
4. Stage only the checked/reviewed Flowstead source at
   `/opt/flowstead/current`; keep `flowstead-sim` a data provenance source,
   not an extra hosted process. Ensure the unprivileged `flowstead` service
   user can read the code/venv but not write to it.
5. Create a **restricted** Supabase `flowstead_runtime` LOGIN with a unique
   password via a supported secure flow, not an administrator credential.
   Verify database TLS hostname/certificate and only app-table/sequence DML;
   store exclusively in `/etc/flowstead/runtime.env` (root:flowstead 0640).
   Use `runtime.env.example` as a checklist, never copy placeholders live.
   No secret values in command arguments, Git, journals or chat.
6. Install systemd units with `sudo bash install-unit-files.sh`. This
   operation does NOT start services. Start `flowstead-nats` first,
   verify persisted storage, then worker/API after the DB connection test.
7. The default `Caddyfile` binds a **loopback-only HTTP readiness proxy**
   to port 8080. Do not enable public 80/443 or modify DNS until a real
   approved domain resolves to the VM and TLS certificates work.
8. Confirm no public application, NATS, database or Docker socket ports.
   Measure RSS/swap and prove graceful worker restart/JetStream durability.
   Verify actual public/private tests, current provider costs, and security
   checks under `docs/planning/tasks/017_*.md`.

## Controlled local commands on the VM

```sh
sudo systemctl daemon-reload
sudo systemctl start flowstead-nats
sudo systemctl status flowstead-nats --no-pager
# Only once credentials are verified and host health is stable:
sudo systemctl start flowstead-worker flowstead-api
curl --fail --max-time 5 http://127.0.0.1:8000/api/v1/health/live
# TLS/DNS are separate steps.
```

Never enable all services automatically until recovery, security, and memory
checks have passed. Secrets stay in the OS-protected runtime env, not the repo.
