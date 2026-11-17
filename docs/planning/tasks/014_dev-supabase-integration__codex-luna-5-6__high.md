# T-014 — private flowstead-dev Supabase migration and Auth smoke

**Status:** DRAFT — explicit cloud-write and invite gates (planning-only approval; NO implementation authorization). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
012+013 local tests pass; `flowstead-dev` is verified project ref `jryvzjwsrxctjeawnkqo`, `eu-west-1`, but its **current** health/schema/access must be read again. OWNER must authorize exact project-scoped migration/seed rows, Auth config, and any invitation recipients separately. Mac OAuth is user-reported only and requires actual scoped read-only preflight. Do not touch demo project. Local DB migration is single source of truth.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: the actual app **Alembic** revision chain, immutable importer, NATS job schema and Auth verifier, owner-approved local smoke checks and `docs/setup/SUPABASE_DEVELOPMENT_ACCESS.md`; current Supabase published Auth/database security docs. Never read private passwords from repo.

## Observable result and scope
Run reviewed **Alembic upgrade-to-head** migrations against the **existing** project only after owner grants write scope, confirm dedicated non-exposed `app` schema/limited roles/RLS on any exposed tables, import at most approved M1 synthetic records with exact digest, configure Auth for invite-only in reviewed settings and validate one or two owner-provided demo identities restricted to disjoint Plant IDs (if explicit invitation approval given). Smoke JWT signature/issuer/audience/JWKS or verified fallback, login/expiry and SQL 401/404, public endpoint only if allowed. Use environment-specific connection choice (IPv6 direct vs IPv4 session pooler), server-side secret storage, connection caps/timeouts and cleanup/backup/reseed. No destructive reset of existing unrelated schemas or other data.



## Dependencies and allowed file closure
No new library by default; use existing app `uv.lock`, test harness and Supabase official auth provider. Any required SQL/role changes need explicit reviewed migration files in this task scope and owner-approved write receipt. Service-role/admin secret may be used only out of band for authorized one-time Auth invitations, never in app/frontend/Git.

Allowed create/edit paths: `backend/migrations/**`, `backend/src/flowstead_api/**` only for provider-specific fixes, `backend/tests/**`, `docs/setup/**`, `.env.example`, `justfile` only for explicit `dev-smoke` command, `README.md`. New dependency installation is authorized **only** when this task itself is approved, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

Cloud DB test cases must confirm the real Alembic version/revisions match local source and preserve previously seeded data; local NATS operation is **not** permission to provision a hosted broker. Use indexed plan/data guide and exact Case IDs in asserting tests.

## Test-first acceptance
- `CLOUD-M14-SCOPE`: project ref verified and only authorized app schema objects/data touched; pre-change schema snapshot/backup recorded.
- `CLOUD-M14-IMPORT`: same M1 digest/row count as local; no real/DHI data.
- `SEC-M14-AUTH`: actual Supabase signed login token verified; user A/B disjoint Plant policies; public no private data.
- `SEC-M14-DATAAPI`: no unauthorized Supabase Data API access; grants and RLS or nonexposed schema verified.
- `OPS-M14-RESTORE`: bounded documented re-seed/rollback/backup procedure tested on disposable local clone, not destructive remote reset.

## Local verification, gates and stopping condition
Before writes: read-only `list_tables` (or SQL) and project-ref check; owner signs exact migration/input/version/role plan. Then execute only approved migration; capture redacted SQL diff/audit and scoped hosted integration proof. Local `just test-db-integration` must pass first. No all-account OAuth privilege assumption.

If owner has not authorized cloud writes/invitations, remain BLOCKED and do local-only tasks 015 instead; never improvise consent.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Normal-chat ChatGPT independently reviews; use `waiting_chat` if unavailable. After corrections, rerun checks on the exact final SHA on Mac. No 24-hour soak.
