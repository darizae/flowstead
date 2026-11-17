# T-005 — Supabase Auth verifier with offline security tests

**Status:** WAITING — prerequisite preflight (bounded local scope approved; OMP handles ordinary execution setup). **Repository:** `darizae/flowstead`, private `main`. OMP resolves the current base commit at dispatch. No task may run solely because this file exists.

## Preconditions and order
003 local authorizer exists. This task needs no live project write and may proceed with configured local mock/JWKS fixtures; live validation is separately 014. Auth endpoint and public access must remain deny-by-default until configured.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `backend` principal dependency, Plant assignments and API denial tests; official Supabase Auth JWT/JWKS docs (provider rules only), not private account notes.

## Observable result and scope
Implement invite-only Supabase-compatible identity verifier and typed `Principal(sub)` dependency for private endpoints; the authorization source remains the app's `operator_plant_access` table, never user-editable metadata or client-supplied Plant lists. Replace any local test-principal bypass with a test-only injected dependency that cannot be enabled in deployed configuration. Allow only configured Supabase issuer/audience and supported algorithms, validated exp/nbf/iat, kid, signature, JWKS rotation and bounded cache; redact tokens in logs. Return 401 on expired/forged issuer/audience/sig/unknown kid; 404 for unauthorised existing Plant IDs.

Prefer official JWKS asymmetric signing-key verification with an audited Python JOSE/JWT library (choose `PyJWT[crypto]>=2.9,<3` subject to current audit). Provide a **documented** server-to-Supabase token validation fallback only if live project still uses legacy symmetric tokens and verified official Auth endpoint supports it; never embed JWT signing secret or trust decoded unsigned claims. Fallback uses `httpx` bounded timeout, verified HTTPS and fail-closed errors; live behavior is UNVERIFIED until task 014. Health endpoint remains safe, no client ability to choose verification mode. Confirm open signup is disabled at live gate, not through unapproved cloud writes now.

## Dependencies and allowed file closure
Approve required `PyJWT[crypto]`, `httpx` if absent, and tests in `backend/pyproject.toml`, `backend/uv.lock` via `uv add --project backend`. Existing dependencies from 002–004 must be verified, audited. Do not assume a Supabase service-role secret is required by the FastAPI read path.

Allowed create/edit paths: `backend/src/flowstead_api/**`, `backend/tests/**`, `backend/pyproject.toml`, `backend/uv.lock`, `justfile`, `.env.example`, `README.md`. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `UT-M5-JWT`: signed valid local JWKS passes; forged/wrong issuer/wrong audience/expired/unsigned/unknown `kid` rejected; rotations and cache expiry proven.
- `UT-M5-FAIL`: JWKS/unavailable Auth endpoint/timeout fails closed; no secret-bearing logs.
- `IT-M5-AUTHZ`: real SQL disjoint-Plant tests across list/latest/history/forecast; caller cannot assert Plant assignment.
- `UT-M5-MODE`: production config rejects test-principal bypass and missing Auth URL/issuer.

## Local verification, gates and stopping condition
Add `just test-auth` and execute `uv run --project backend pytest -q backend/tests/unit/test_auth.py` plus real SQL security tests. Audit patched crypto dependencies. No browser sign-in, invitation, session creation or cloud calls expected during offline fixture tests.

Live Supabase Auth configuration or project migration stays BLOCKED until separate owner-scoped write/invitation consent in 014.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. OMP owns independent PR review and acceptance synchronization as a control-plane follow-up; do not delay this task's implementation waiting for that upgrade. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
