# T-005 — Supabase Auth verifier with offline security tests

**Execution:** Start when explicitly assigned; no WAITING/READY/approval prerequisite. **Repository:** `darizae/flowstead`, local `main` checkout.

## Existing implementation and technical context
Existing FastAPI/SQL and the NATS implementation already committed to `main` are available for integration. Start offline JWT/JWKS auth tests now; no T-004b review/merge receipt is needed.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `backend` principal dependency, Plant assignments and API denial tests; official Supabase Auth JWT/JWKS docs (provider rules only), not private account notes.

## Observable result and scope
Implement invite-only Supabase-compatible identity verifier and typed `Principal(sub)` dependency for private endpoints; the authorization source remains the app's `operator_plant_access` table, never user-editable metadata or client-supplied Plant lists. Replace any local test-principal bypass with a test-only injected dependency that cannot be enabled in deployed configuration. Allow only configured Supabase issuer/audience and supported algorithms, validated exp/nbf/iat, kid, signature, JWKS rotation and bounded cache; redact tokens in logs. Return 401 on expired/forged issuer/audience/sig/unknown kid; 404 for unauthorised existing Plant IDs.

Prefer official JWKS asymmetric signing-key verification with an audited Python JOSE/JWT library (choose `PyJWT[crypto]>=2.9,<3` subject to current audit). Provide a **documented** server-to-Supabase token validation fallback only if live project still uses legacy symmetric tokens and verified official Auth endpoint supports it; never embed JWT signing secret or trust decoded unsigned claims. Fallback uses `httpx` bounded timeout, verified HTTPS and fail-closed errors; live behavior is UNVERIFIED until task 014. Health endpoint remains safe, no client ability to choose verification mode. Confirm open signup is disabled at live gate, not through unapproved cloud writes now.

## Dependencies and allowed file closure
Install required `PyJWT[crypto]`, `httpx` if absent, and tests in `backend/pyproject.toml`, `backend/uv.lock` via `uv add --project backend`. Existing dependencies from 002–004 must be verified, audited. Do not assume a Supabase service-role secret is required by the FastAPI read path.

Allowed create/edit paths: `backend/src/flowstead_api/**`, `backend/tests/**`, `backend/pyproject.toml`, `backend/uv.lock`, `justfile`, `.env.example`, `README.md`. Necessary package, manifest, lockfile, fixture, command and test updates in the named owning paths are in scope when this task is assigned. Choose supported compatible versions, generate lockfiles with the package manager, audit dependencies and verify locally. Do not request separate permission for predictable dependency setup; keep changes related to this task. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Reference-derived auth and integration boundaries

**Read-only local sources:** `/Users/danie/repos/repomix-static-reconstructor/reconstructed/toolkit/packages/fasterapi/src/fasterapi/dependencies/_current_user.py`, `/Users/danie/repos/repomix-static-reconstructor/reconstructed/toolkit/packages/fasterapi/src/fasterapi/errors.py`, `/Users/danie/repos/repomix-static-reconstructor/reconstructed/toolkit/packages/fasterapi/test/test_auth.py` (typed identity/errors); `/Users/danie/repos/repomix-static-reconstructor/reconstructed/integration_tests/test_authorization.py`, `/Users/danie/repos/repomix-static-reconstructor/reconstructed/integration_tests/conftest.py`, `/Users/danie/repos/repomix-static-reconstructor/reconstructed/integration_tests/harness/resources.py` (disjoint-owner real-resource test fixtures). Check actual local paths. Do not copy AuthStub, cookie middleware or unrelated architecture.

Use the **existing** `backend/src/flowstead_api/auth.py`, `database.py`, `models.py` and `main.py` as the migration baseline. Adapt the **typed principal dependency / structured unauthorized error** concept visible in the named FasterAPI examples and the **owned disjoint-client fixture** concept from the named read-only reference sources; do **not** port their external AuthStub service, cookies/session middleware or new package workspace. **Use the existing app-owned NATS transport from T-004b without inventing a separate auth service**; normal JWT/Plant access checks remain HTTP/SQL authority, never trusted to message payload alone. Keep FastAPI identity verification separate from PostgreSQL Plant assignment checks, with a single explicit config-dependent production/test mode boundary. The named read-only reference sources' code-structure patterns may inform structure but are not provider or security authority. Test failure paths first where practical and run genuine local PostgreSQL tests for A-vs-B access with signed JWT/JWKS fixtures. Do not infer hosted Supabase validation from an offline test.

Before test changes, read `docs/testing/INDEXED_TEST_PLAN.md` and `docs/testing/TEST_DATA_GUIDE.md`, repeat existing `UT-M5-*`/`IT-M5-*` case IDs in exact asserting test docstrings, use real PostgreSQL and deterministic JWKS fixtures, and report actual case coverage. No mock-only claim of hosted Auth.

## Test-first acceptance
- `UT-M5-JWT`: signed valid local JWKS passes; forged/wrong issuer/wrong audience/expired/unsigned/unknown `kid` rejected; rotations and cache expiry proven.
- `UT-M5-FAIL`: JWKS/unavailable Auth endpoint/timeout fails closed; no secret-bearing logs.
- `IT-M5-AUTHZ`: real SQL disjoint-Plant tests across list/latest/history/forecast; caller cannot assert Plant assignment.
- `UT-M5-MODE`: production config rejects test-principal bypass and missing Auth URL/issuer.

## Local verification and completion
Add `just test-auth` and execute `uv run --project backend pytest -q backend/tests/unit/test_auth.py` plus real SQL security tests. Audit patched crypto dependencies. No browser sign-in, invitation, session creation or cloud calls expected during offline fixture tests.

Hosted Supabase integration and invitation testing belong to T-014; this task implements the complete local verifier and test suite independently.



## Local completion

Implement immediately when this file is explicitly assigned. Run the stated targeted local tests and fix failures in task-owned source and tests; record observed checks and any environment limitations. Make a focused local task-branch commit and **merge into local `main`** after resolving code/test failures and Git conflicts. Record the resulting SHA and changes. **Do not push**. Independent ChatGPT review, PR receipts, predecessor acceptance, task index statuses and extra owner authorization are **not prerequisites** to starting, committing or locally merging this task. If a real external resource is absent, finish all feasible local work and report what could not be exercised without inventing hosted results.
