# T-014 — private flowstead-dev Supabase migration and Auth smoke

**Execution:** Start immediately when assigned; planning-status and reviewer approvals are not prerequisites. **Repository:** `darizae/flowstead`, local `main`.

## Technical context
Implement the development Supabase integration when assigned. Before actual writes, verify the project ref, credentials, schema/recipient scope; missing live access does not prevent implementing and testing the local integration code.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: the actual app **Alembic** revision chain, immutable importer, NATS job schema and Auth verifier, owner-approved local smoke checks and `docs/setup/DEPLOYMENT_ARCHITECTURE.md`; current Supabase published Auth/database security docs. Never read private passwords from repo.

## Observable result and scope
Run reviewed **Alembic upgrade-to-head** migrations against the **existing** project after verifying the named project and non-destructive schema scope, confirm dedicated non-exposed `app` schema/limited roles/RLS on any exposed tables, import at most approved M1 synthetic records with exact digest, configure Auth for invite-only in reviewed settings and validate one or two owner-provided demo identities restricted to disjoint Plant IDs (when concrete invitation recipients are configured). Smoke JWT signature/issuer/audience/JWKS or verified fallback, login/expiry and SQL 401/404, public endpoint only if allowed. Use environment-specific connection choice (IPv6 direct vs IPv4 session pooler), server-side secret storage, connection caps/timeouts and cleanup/backup/reseed. No destructive reset of existing unrelated schemas or other data.



## Dependencies and allowed file closure
No new library by default; use existing app `uv.lock`, test harness and Supabase official auth provider. Any required SQL/role changes need explicit reviewed migration files in this task scope and actual execution record. Service-role/admin secret may be used only out of band for authorized one-time Auth invitations, never in app/frontend/Git.

Allowed create/edit paths: `backend/migrations/**`, `backend/src/flowstead_api/**` only for provider-specific fixes, `backend/tests/**`, `docs/setup/**`, `.env.example`, `justfile` only for explicit `dev-smoke` command, `README.md`. Any necessary new dependency installation inside the task's named owning paths is included in this assignment; install compatible versions using the package manager, update the lockfile and tests and report findings. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

Cloud DB test cases must confirm the real Alembic version/revisions match local source and preserve previously seeded data; local NATS operation is **not** permission to provision a hosted broker. Use indexed plan/data guide and exact Case IDs in asserting tests.

## Test-first acceptance
- `CLOUD-M14-SCOPE`: project ref verified and only authorized app schema objects/data touched; pre-change schema snapshot/backup recorded.
- `CLOUD-M14-IMPORT`: same M1 digest/row count as local; no real/DHI data.
- `SEC-M14-AUTH`: actual Supabase signed login token verified; user A/B disjoint Plant policies; public no private data.
- `SEC-M14-DATAAPI`: no unauthorized Supabase Data API access; grants and RLS or nonexposed schema verified.
- `OPS-M14-RESTORE`: bounded documented re-seed/rollback/backup procedure tested on disposable local clone, not destructive remote reset.

## Local verification and completion
Before writes: read-only `list_tables` (or SQL) and project-ref check; owner signs exact migration/input/version/role plan. Then execute only approved migration; capture redacted SQL diff/audit and scoped hosted integration proof. Local `just test-db-integration` must pass first. No all-account OAuth privilege assumption.

If cloud access or invitation recipients are unavailable, complete the task's code and local tests; report live operations as not performed.



## Local completion

Start coding when this task is explicitly assigned. Run focused local tests and repair real failures; never wait for reviewer certification, a READY table entry, earlier merge receipts or permission to install task dependencies. Commit a focused local task branch, **merge it into local `main`**, and report the commit/merge SHA and actual test results. **Do not push**. Real external writes require a concrete configured target and credentials, not planning-status approvals; complete all possible code/tests if a hosted environment is absent. Never invent secret values, paid service plans or successful deployment evidence.
