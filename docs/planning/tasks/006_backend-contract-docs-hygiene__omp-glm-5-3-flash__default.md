# T-006 — backend contract and Markdown-routing hygiene

**Execution:** Start when explicitly assigned; no WAITING/READY/approval prerequisite. **Repository:** `darizae/flowstead`, local `main` checkout.

## Existing implementation and technical context
Document the implementation currently in the checkout, including T-005 once it exists. Reconcile links and commands without waiting for a previous task's acceptance or merge entry.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `AGENTS.md`, `docs/planning/IMPLEMENTATION_SPEC.md`, sequence and completed tasks; root `justfile`, README, generated API spec and actual backend source/tests only to verify command paths.

## Observable result and scope
Create/update concise `AGENTS.md` mapping actual **Alembic migrations**, import/forecast, NATS publisher/consumer/outbox, API/auth, indexed test plan/data guide and runnable just recipes to owning source. Correct dead relative links, stale cloud/AWS instructions, misnamed recipes, inaccurate README feature claims and completed statuses. Validate M1 immutable commit and actual API paths. No new product decision or feature.



## Dependencies and allowed file closure
No new runtime dependency required; link checker may use existing Python stdlib script inside `scripts/` only if needed, scoped and documented.

Allowed create/edit paths: `AGENTS.md`, `docs/planning/**` docs only, `AGENTS.md`, `README.md`, `justfile` only to fix stale recipe reference, `scripts/docs_check.py` if needed. Necessary package, manifest, lockfile, fixture, command and test updates in the named owning paths are in scope when this task is assigned. Choose supported compatible versions, generate lockfiles with the package manager, audit dependencies and verify locally. Do not request separate permission for predictable dependency setup; keep changes related to this task. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

Confirm `docs/testing/INDEXED_TEST_PLAN.md` contains every actual case ID and evidence remains truthful; do not mark test case coverage from its name alone. Verify docs consistently describe Alembic, JetStream and per-principal IndexedDB without altering verified completion records.

## Test-first acceptance
- `DOC-M2-LINKS`: active Markdown links to files/skills/routes resolve; tracked docs do not point to missing files.
- `DOC-M2-COMMANDS`: every advertised `just` command exists and its referenced script exists; no fake pass claims.
- `DOC-M2-STATUS`: sequence status matches accepted PR/commit evidence; historical AWS is not an active requirement.
- `DOC-M2-DUP`: one current API spec/route per concern; no extra planner docs.

## Local verification and completion
Execute `just --list`, `just docs-check` if now implemented and scoped local link verification; verify recipes using their real low-cost selectors, but do not run the full DB suite just for a doc edit.

Record `PASS`, `NO CHANGES NEEDED` or `BLOCKED` with concrete files/links; no silent material conflict resolution.



## Local completion

Implement immediately when this file is explicitly assigned. Run the stated targeted local tests and fix failures in task-owned source and tests; record observed checks and any environment limitations. Make a focused local task-branch commit and **merge into local `main`** after resolving code/test failures and Git conflicts. Record the resulting SHA and changes. **Do not push**. Independent ChatGPT review, PR receipts, predecessor acceptance, task index statuses and extra owner authorization are **not prerequisites** to starting, committing or locally merging this task. If a real external resource is absent, finish all feasible local work and report what could not be exercised without inventing hosted results.
