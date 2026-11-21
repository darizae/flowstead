# Flowstead — end-to-end security review and live hardening, 2026-11-21

**Scope:** checked-out Flowstead API, frontend, auth, data export, simulation importer,
PostgreSQL/Alembic, NATS JetStream/worker, optional Docker deployment, existing
Oracle Linux E2 micro, Vercel static delivery, Supabase Auth and connection
pooler, TLS, DNS and operational cost controls.

**Verdict:** **PARTIALLY HARDENED; NOT APPROVED FOR PUBLIC BACKEND RELEASE.**
The documented changes have been implemented/tested where stated, but no live
FastAPI/worker/TLS endpoint or authenticated operator browser journey has been
verified. Do not describe the public site as a complete working application.
See [T-017 observed receipts](../deployment/T017_LIVE_VERIFICATION_2026-11-21.md)
and [historical SEC19 findings](2026-11-21-sec19-report.md).

## Trust-boundary model

```text
Internet anonymous browser ─HTTPS─> Vercel static React/MapLibre frontend
     │                               │
     │                     browser Supabase publishable Auth client
     │                               │ HTTPS identity only
     │                               ▼
     │                       flowstead-demo Supabase Auth/JWKS
     │
     └─ future HTTPS API hostname -> reverse proxy on existing OCI micro
                                      │ localhost FastAPI (flowstead-api Unix user)
                                      │ JWT issuer/JWKS + per-subject Plant grants
                                      │ DB: SELECT + command enqueue only
                                      ▼
                         Supabase app.forecast_jobs + message_outbox
                                      │ authenticated worker-only broker connection
                                      ▼
                            NATS JetStream durable file store
                                      │
                                      ▼
                         Forecast dispatcher/worker (flowstead-worker Unix user)
                                      │ restricted worker DB connection
                                      ▼
                       forecasts + inbox/outbox completion in Supabase
```

Offline **migration owner** performs reviewed schema/import operations only.
Neither frontend, API, broker, nor forecast worker may load its password.
The user-selected VM is exclusively `flowstead-demo-instance` in Frankfurt,
`VM.Standard.E2.1.Micro`, with no replacement compute.

## Implemented and verified fixes

| Boundary | Severity before fix | Confirmed issue / attack | Remediation | Verification |
| --- | --- | --- | --- | --- |
| Database legacy role | **High** | Shared `flowstead_runtime` DML role could INSERT/UPDATE/DELETE immutable M1, Plants and operator assignment data | Applied `005_least_privilege_runtime_roles.sql`: revoke all grants, NOLOGIN old role, separate API and worker NOLOGIN roles with explicit table access | Live `has_table_privilege` per table |
| Database worker access | **Medium** | Worker role could read operator assignment table without using it | Applied `006_remove_worker_operator_grant.sql` | Live SQL: worker assignment SELECT false, API assignment SELECT true |
| Database Data API | Existing control, verified | `anon` and `authenticated` must not bypass the FastAPI authorization boundary | Keep private `app` schema inaccessible; add RLS on the two `public` migration marker tables | Live schema grants + RLS query; Supabase security advisor 0 lints |
| Native OS users | **High** | Proposed API/worker systemd processes used same `flowstead` user, so file-permission separation would not protect worker DB credentials | Distinct `flowstead-api`, `flowstead-worker` Linux accounts and group-owned 0640 secret files, broker on `flowstead`; native service files patched | OS accounts created on actual VM; source/config assertions. API and worker units not started |
| Native NATS broker | **Medium** | Broker loopback port was unauthenticated; any local process could publish to worker queue | Generated random broker token privately on OCI host, installed root:flowstead 0640 auth include, separately protected worker NATS_URL | Live anonymous connect rejected, authorized connect accepted, JetStream /healthz OK after restart; 127.0.0.1-only ports |
| Docker fallback service boundaries | **High** if deployed | Shared env, unauthed broker, insecure fallback path | Split API/worker env files; separate NATS token volume/secret, worker-only URL, broker config include, root-owned file checks and verified-CA mount | Static `docker compose config --quiet` and unit assertions pass; live Docker execution NOT verified |
| Supabase TLS transport | **Medium** | `sslmode=require` does not validate certificate hostname | Use `verify-full` + CA path in both runtime env templates; tested pooler TLSv1.3 and hostname with explicit CA | OpenSSL handshake TLSv1.3 / `Verification: OK`; role-authenticated SQL still pending |
| Frontend headers | **Medium** | Current Vercel HTTP response lacks HTTP CSP, X-Content-Type-Options, XFO and Referrer-Policy (HTML meta CSP alone cannot enforce `frame-ancestors`) | Added security response headers in `frontend/vercel.json` | Config and regex assertions; **new Vercel deployment required** |
| SPA fallback | **Medium** reliability / API confusion | Current Vercel `/api/v1/public/plants` returns HTTP 200 `text/html` index, not real JSON | Excluded `/api` paths from catchall SPA rewrite; no pretend API success | Tested current HTTP response; local rewrite pattern test only |
| JWT / BOLA | Existing control, tested | Forged/expired tokens and cross-Plant requests | Backend adversarial review and regression tests; SQL subject-based access predicate retained | Throwaway-DB crafted requests; live identities still missing |
| Backend parser and worker status | **Low–Medium** | Public datetime parser returned internal exception text; worker terminal job status could leak exception/DB details | Local backend audit patches sanitize both messages and add focused tests | 106 passed, 1 skipped in isolated backend audit; integration to main pending |
| Frontend CSV/export | Existing control reinforced | Spreadsheet formula injection in CSV from hostile leading `= + - @` | Added a matrix regression for formula escaping | Frontend audit 41 tests passed; integration to main pending |
| Frontend session/cache | Existing control, reviewed | Private Plant cache must not survive identity switch/401/403/404 | Existing per-principal IndexedDB partition and cleanup, same-origin fetch credentials, safe downloads | Code and test review; actual hosted expired/revoked-session journey pending |
| OCI ingress | Existing guard, verified | Public SSH wildcard and public API/queue ports | SSH ingress narrowed to the Mac's IPv4 /32. Existing NATS monitor and client bind localhost | Live OCI rule inspection, SSH, `ss` listeners; HTTPS firewall not configured |
| Vercel Supabase config | **Medium** configuration omission | Existing Vite app had no real Supabase URL or publishable key env vars | Set only `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (modern `sb_publishable_` key) for production and preview | Vercel confirmed variables created; **new build required**, no service-role key |

Note: the independently distributed Supabase Root 2021 CA
(SHA256 fingerprint
`80:70:25:AD:50:D4:ED:21:9D:2C:9C:7D:29:9C:00:4F:82:4E:B0:0C:F7:F6:5A:FE:F6:07:D0:7B:72:E6:CA:FA`)
successfully verified `*.pooler.supabase.com` with TLS 1.3. Its provenance
must additionally be cross-checked with the CA downloaded from Supabase's
official Database Settings before relying on it to authorize live credentials.
The **correct session-pooler hostname must be copied from the project's own
Connect panel** rather than inferred from its region.

## Required before hosted promotion (open and NOT assumed solved)

1. **P1 – distinct SQL logins and checked permissions.** Both
   `flowstead_api` and `flowstead_worker` are **NOLOGIN**. Attempts to pass
   generated credential material between connected tools were explicitly blocked
   by security checks, so no password was activated and no guess/shared/admin
   password may be used. Have the authorized owner provision each password
   through private Supabase/psql prompts, then enable LOGIN and populate two
   role-protected env files on the instance. Run actual `SELECT`, unauthorized
   `INSERT` and TLS verification probes as each role. Do NOT print passwords.
2. **P1 – real public API DNS/TLS routing.** `api.flowstead.darizae.dev`
   currently does NOT return a working TLS API response, and appears covered by
   existing Vercel DNS wildcard records. **Do not overwrite the entire
   `darizae.dev` DNS zone** with a replace-all API: this risks the personal site.
   Add only the explicitly approved subdomain record using safe DNS tools, and
   use a real ACME certificate before enabling 80/443/proxy. Vercel source
   security headers do NOT apply to the existing READY build until redeployment.
3. **P1 – operator identities and API authorization smoke.** There are
   currently **zero** `auth.users` and operator grants in `flowstead-demo`.
   No recipients have been selected and no access tokens fabricated. Invite
   owner-selected operators through Supabase Auth, then assign exact validated
   subject UUIDs to only their approved Plants. Verify denied other-Plant reads,
   reports, forecast command enqueue/status, expired JWT and revoked account.
4. **P1 – actual application delivery.** Only the NATS broker is installed.
   The worker, FastAPI and TLS proxy must be staged and tested **after** DB
   connection/identity/DNS checks. The five pending real outbox events are
   persisted but NOT yet published; do not mark replay or forecast completion
   passed until real worker processing, queue restart and signed-in browser
   tests have been recorded.
5. **P2 – retention / cost abuse.** Current per-principal forecast-request
   limiting is in-process and bounded, but rows in `forecast_jobs` and
   `message_outbox` do not have a proven age-based pruning lifecycle. Design
   a bounded, auditable terminal-only retention job with a safe rollback and
   reconciliation of NATS/JWKS to prevent permanent database growth; don't
   delete pending or unresolved jobs.
6. **P2 – dependencies / historic secrets.** Docker base images are currently
   tags rather than reviewed immutable digests; native host avoids this specific
   image risk. Re-run `pip-audit`, `npm audit` and a full Git history/ZIP/PDF/PNG
   secret and PII scan before a public launch; basic secret-pattern checks
   are not comprehensive.
7. **P2 – provider resource safety.** OCI billing/current spend and free
   quota have not been independently reconciled to a hard limit; alerts do
   not cap charges. No new VM, paid volume, load balancer, auth project or
   Vercel paid tier was created during this audit.

## Rollback and incident controls

- If a worker/API credential is ever suspected leaked: stop only that service,
  revoke LOGIN or rotate the corresponding restricted DB role, inspect
  `app.forecast_jobs`/outbox activity and restart with new OS-protected
  secret. Do not reset synthetic source data or repurpose an admin password.
- If NATS auth breaks, preserve `/var/lib/flowstead/nats`; verify config syntax,
  restart systemd under the `flowstead` user, and check localhost `/healthz`
  and protected JetStream state. Do not expose the monitor to the internet.
- If Vercel configuration is wrong, retain its prior known-good production
  deployment; release header/API-rewrite changes only after build tests.
- Keep OCI SSH source restricted and operate only on the existing E2 micro.
- In every receipt distinguish source review, local simulation, live provider
  control-plane evidence, and actual hosted application behavior.
