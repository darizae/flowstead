# Flowstead dev Supabase integration runbook (T-014)

Scope: the private `flowstead-dev` Supabase project, ref `jryvzjwsrxctjeawnkqo`,
region `eu-west-1`. This runbook is the reviewed, owner-signed plan for running the
existing Alembic chain to head and for all follow-up live smokes. It records what was
verifiably done read-only and what still requires an admin connection string and
concrete invitation recipients.

## Connectivity verification (done, read-only)

| Check | Result |
| --- | --- |
| Project ref | `jryvzjwsrxctjeawnkqo` (matching `docs/setup/DEPLOYMENT_ARCHITECTURE.md`) |
| Session role | `supabase_read_only_user`, database `postgres` |
| `public` tables | none |
| `app` tables | none |
| Alembic / Supabase migrations applied | none |
| Flowstead-created extensions | none (only Supabase defaults present) |

The project is a fresh, empty PostgreSQL instance: **pre-change snapshot** is a clean
database with no `app` schema, no migration history and no data, so there is nothing at
risk to back up. `pytest` and the local PostgreSQL integration suite confirm the reviewed
local chain reaches head `003_jetstream_messages` and passes (`just test-db-integration`).

## Approved migration plan (NOT executed — needs admin access)

1. Obtain the owner-supplied admin/owner connection string for `flowstead-dev` from the
   host secret store. Never place it in the repo, framework, `.env`, or Git.
2. Take a fresh snapshot before writing: `pg_dump` or Supabase "Database backup" of the
   project, recorded (redacted) in the task evidence. Because the project is empty this
   is cheap but still required by the acceptance record.
3. Run the exact reviewed local chain to head, in order, from the checked-out revision:
   `uv run --project backend python -m backend.migrate upgrade` with
   `FLOWSTEAD_ALEMBIC_DATABASE_URL` set to the direct (IPv6, port 5432) or IPv4 session
   pooler (port 6543) endpoint per the host environment. Confirm `just db-current`
   reports `003_jetstream_messages`. Confirm the cloud revision list matches the local
   source and that no pre-existing seeded data changed.
4. Confirm the dedicated non-exposed `app` schema exists with all owned tables, and that
   the Supabase limited `anon`/`authenticated` roles have **no** privileges on it.
   PostgREST `db-schemas` must remain `public` (the `app` schema is not exposed), so the
   Supabase Data API grants no access — this is the primary `SEC-M14-DATAAPI` control.
5. RLS is optional defense-in-depth because `app` is non-exposed and FastAPI enforces
   Plant-scoped reads over the owner connection (table owners bypass RLS). If enabled,
   add **deny-by-default** RLS (`ALTER TABLE … ENABLE ROW LEVEL SECURITY` with no granting
   policy) and never rely on a non-owner reader without adding permissive policies.
   Record the redacted SQL diff/audit in evidence.

## Approved import plan (NOT executed — needs admin access)

Import only the approved M1 synthetic payload with the exact pinned identity from
`backend/importer.py`:

- source SHA `ad5c94d1f46e79312a99cb9721f38700f24fdf6b`, schema `m1.v1`, seed `20250101`
- canonical telemetry SHA-256 `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`
  (caller independently confirms the manifest checksum equals this digest)
- row count and byte caps enforced by the importer (`≤ 43800` rows, `≤ 4247080` bytes)

Run `just import-m1-local <manifest> <source-sha> <data-csv>` against the dev database
and record `app.ingest_batches` digest/row count matching the local import. No real or
demo-plant data may be imported.

## Auth configuration plan (NOT executed — needs admin access + recipients)

- Enable **invite-only** in the Supabase Auth dashboard: disable public signups, allow
  only invited users.
- Configure the app's Auth verification from the host secret store (never in Git):
  `SUPABASE_AUTH_URL`, `SUPABASE_JWT_ISSUER`, `SUPABASE_JWT_AUDIENCE`, and
  `SUPABASE_JWT_ALGORITHMS` (JWKS mode defaults to `ES256,RS256`). The repository's
  JWKS verifier (`flowstead_api.auth.JWKSVerifier`) checks signature, `iss`, `aud`,
  `exp`, `nbf`, and `iat` and fails closed; the legacy `/user` endpoint fallback remains
  documented in case the live project still issues HS256 tokens.
- When one or two concrete demo identities are supplied by the owner, invite them and
  restrict them to **disjoint** Plant IDs via `app.operator_plant_access`
  (e.g. identity A → `plant-01`, identity B → `plant-02`). This reproduces
  `SEC-M14-AUTH`/`IT-M5-AUTHZ` locally and on the live project.

### JWT / Data API smoke (blocked on live access)

With a real signed Supabase token:
1. Signature/issuer/audience/JWKS: verify the token via `JWKSVerifier` and confirm
   `sub` is accepted and `Principal` carries no caller-supplied Plant access.
2. Login/expiry: confirm a valid token is accepted and an expired/invalid token is
   rejected with 401.
3. SQL 401/404: an unauthenticated request to `/api/v1/plants/**` returns 401;
   an authorized-but-unknown Plant returns 404; Public endpoints return only
   `public_demo` plants with no private fields.
4. Data API: the Supabase Data API over `public` exposes nothing from `app`; a direct
   table grant check confirms `anon`/`authenticated` have no grants on `app`.

The local equivalents of 1–3 run green (`just dev-smoke`).

## Rollback / backup / re-seed (OPS-M14-RESTORE)

- **Rollback:** Alembic downgrades are destructive and are refused for non-disposable
  targets by `backend.migrate`. For the dev database, restore from the pre-change
  `pg_dump`/Snapshot rather than downgrading in place; the migration script's
  `disposable` guard must never be bypassed for the shared project.
- **Backup:** rely on Supabase project backups plus a pre-change dump for the exact
  acceptance window. Record the dump location (redacted) in evidence.
- **Re-seed:** drop-and-recreate is out of scope for the shared project; re-seed is
  restore-of-backup followed by the approved migration + M1 import sequence above.
- The restore path is validated on a **disposable local clone** (throwaway database,
  `DB-M4A-*` / `IT-M2-MIGRATE` cases), never on the remote project.

## Live operations status

The following are **NOT performed** in this task because the attached access is read-only
and no admin connection string or invitation recipients were supplied:

- running the migration chain against the live project
- M1 import into the live project
- invite-only Auth configuration and demo-identity invitations
- real signed-token / Data API smoke

All local code, tests and the runbook above are complete and verified. Evidence should
include the redacted pre/post schema snapshot and the scoped hosted integration proof
once admin access is available.