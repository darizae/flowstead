# Existing OCI micro — native, isolated services

This is the approved architecture for the **existing** Oracle Linux 9.8 x86_64
`flowstead-demo-instance`. No other VM is approved or required. See
[HOSTED_DEPLOYMENT.md](../../../docs/deployment/HOSTED_DEPLOYMENT.md) and
[T-017 live verification](../../../docs/deployment/T017_LIVE_VERIFICATION_2026-11-21.md)
for observed state rather than assuming a service is installed.

## Trust boundaries

- **NATS broker:** live and systemd-enabled; runs as `flowstead`. Listens
  ONLY on `127.0.0.1:4222` and monitor `127.0.0.1:8222`, stores JetStream
  at `/var/lib/flowstead/nats`. A host-generated, private NATS token is in
  `/etc/flowstead/nats-auth.conf` (root:flowstead, 0640). NATS config has
  `include ./nats-auth.conf`. No unauthenticated client may publish.
- **Worker:** NOT YET STARTED; must run as distinct OS user/group
  `flowstead-worker`, with only `/etc/flowstead/worker.env`
  (root:flowstead-worker, 0640) for PostgreSQL, and independent
  `/etc/flowstead/nats-worker.env` (same owner/group/mode) for the **separate**
  broker token. These are protected role-specific secrets. Worker DB
  `flowstead_worker` permits queue/forecast DML but cannot alter source data
  or operator assignments.
- **API:** NOT YET STARTED; must run as `flowstead-api` user/group, with only
  `/etc/flowstead/api.env` (root:flowstead-api, 0640). Database
  `flowstead_api` permits readonly Plant and source access and authorized
  forecast command enqueue; **cannot read broker tokens** or modify forecasts,
  source data, or operator assignments. No NATS_URL is configured for API.
- **TLS proxy:** NOT YET STARTED; will run as distinct `flowstead-proxy`
  with no database or broker secrets; when allowed, serves a verified, approved
  HTTPS API hostname only; default Caddyfile on 127.0.0.1:8080 is **local-only**.
  Keep 8000, 4222, 8222, 5432 and 6543 off all public interfaces.
- **Supabase:** existing `flowstead-demo` only. Role migration
  `deploy/supabase/005_least_privilege_runtime_roles.sql` has been **applied**.
  Legacy broad `flowstead_runtime` is NOLOGIN with DML revoked. Dedicated API
  and worker roles are **NOLOGIN until two unique credentials are securely
  provisioned**; never substitute the migration/admin password.

The host's `/etc/flowstead` directory is root:root 0711 (traversable, not
listable to other users); broker and per-service secret files are readable only
to the matching OS user/group. The installer creates four separate system users (broker, API, worker and
proxy). The proxy runs as `flowstead-proxy` and cannot read the NATS secret;
it never creates passwords, starts services or opens firewall ports.

## Deployment gates (complete in order)

1. **Host health:** SSH restricted to the owner's current IPv4 /32, host
   `uname -m` shows x86_64, and guest memory/swap and disk are safe.
   Avoid mass `dnf install/upgrade` on a 498 MiB guest; a previous package
   operation caused a guest hang that needed OCI SOFTRESET recovery.
2. **Broker:** Already live with NATS v2.12.15 on the existing host. Auth was
   generated **on the VM without transmitting a plaintext token through chat or
   Git**. Validate anonymous rejection, authenticated acceptance, persistent
   JetStream and systemd memory limits. Do not overwrite `nats-auth.conf`,
   `nats-worker.env`, or the durable store.
3. **DB roles:** On the user's OWN authorized Supabase `flowstead-demo`
   project in the SQL/connection UI, set unique API and worker passwords
   without pasting them into chat. For `psql` as an authorized admin,
   `\\password flowstead_api` and `\\password flowstead_worker` prompt
   privately, followed by `ALTER ROLE flowstead_api LOGIN;` and the
   corresponding `ALTER ROLE flowstead_worker LOGIN;`.
   Use the **session pooler** host copied from Supabase's Connect panel,
   `[ROLE].[PROJECT_REF]` username on port 5432. A guessed pooler host is
   NOT authoritative.
4. **Certificate:** Download Supabase's CA from its official Database Settings.
   On 2026-11-21, an independently distributed Supabase Root 2021 CA with
   SHA256 fingerprint
   `80:70:25:AD:50:D4:ED:21:9D:2C:9C:7D:29:9C:00:4F:82:4E:B0:0C:F7:F6:5A:FE:F6:07:D0:7B:72:E6:CA:FA`
   verified the session-pooler hostname and TLSv1.3 chain. Cross-check the
   certificate against the provider UI before distributing as a trust anchor.
   Place a verified public CA at `/etc/flowstead/supabase-root-2021.crt`
   (root:root 0644); use `sslmode=verify-full&sslrootcert=...` and confirm
   two real **restricted** connections, schema grants and timeouts.
5. **Secrets:** Use `api.env.example` and `worker.env.example` as checklists.
   Populate `/etc/flowstead/api.env` and `worker.env` securely with
   `sudoedit` or an approved local password manager without shell echo, Git,
   recorded CLI arguments, or token exposure. Never copy the database owner
   connection, frontend publishable keys or raw secrets into diagnostics.
   The NATS worker token remains in `nats-worker.env`, not in the API.
6. **Reviewed code/runtime:** Stage the checked Git commit at
   `/opt/flowstead/current`, install **pinned** Python 3.12 dependencies in
   `/opt/flowstead/venv` without running untrusted install scripts, and give
   each process read-only code access. Avoid unbounded concurrent builds.
7. **Services:** The installer `sudo bash install-unit-files.sh` only installs
   unit definitions; it fails closed if broker auth does not exist. Check
   systemd `User`, `Group`, `EnvironmentFile`, memory limits, and permissions.
   Start `flowstead-worker`, then `flowstead-api`, one at a time after
   DB connectivity and TLS trust verification; watch logs and RAM. No public
   proxy until DNS and real HTTPS certificate are verified.
8. **Public/identity:** Existing Vercel `flowstead` only. Public Supabase
   Auth URL and publishable key are configured for the NEXT build; no login
   users/Plant grants have been created. Invite owner-selected recipients using
   Supabase Auth, then insert their validated subject UUIDs into
   `app.operator_plant_access` through a reviewed private operator workflow.
   Test cross-Plant denies, JWT expiry/revocation, CSV/PDF exports and indexed
   caches. Publish only an explicitly approved Flowstead subdomain; never
   overwrite the full `darizae.dev` DNS zone.

## Local-on-host safe checks

```sh
systemctl is-active flowstead-nats
sudo systemctl status flowstead-nats --no-pager
curl --fail --max-time 5 http://127.0.0.1:8222/healthz
ss -ltn | grep -E ':(4222|8222|8000)'
# NATS and API ports must be 127.0.0.1 listeners.
```

For each uncompleted acceptance test record PASS, BLOCKED or UNVERIFIED.
Never claim T-017 as a hosted pass until a real TLS API, real restricted DB
connections, actual JetStream dispatcher+worker replay and browser/identity
tests have been observed. No paid resources or replacement compute.
