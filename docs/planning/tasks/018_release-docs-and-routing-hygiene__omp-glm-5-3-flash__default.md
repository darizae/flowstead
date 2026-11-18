# T-018 — final Markdown/routing/release evidence hygiene

**Execution:** Start immediately when assigned; planning-status and reviewer approvals are not prerequisites. **Repository:** `darizae/flowstead`, local `main`.

## Technical context
Update release/docs references against actual source and available receipts; no predecessor approval is required to start.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: README, routes, app/spec/sequence, **real Alembic revisions and NATS/JetStream operations**, release/deploy notes, UI parity matrix, `docs/testing/INDEXED_TEST_PLAN.md`, `docs/testing/TEST_DATA_GUIDE.md`, case coverage reports, checked browser/SQL/broker receipts/real host URLs and exact generator source SHA.

## Observable result and scope
Update truthful README product/demo link (only if actually live), dev install/test quickstart, **actual Alembic upgrade and NATS stream/consumer/worker/restart recipes, IndexedDB cache rules, indexed case coverage/Playwright HTML report instructions**, API/UI routes, current host/rollback instructions, active task statuses and tested release refs. Delete stale AWS/S3 or provisional external-gate claims that are no longer accurate, but preserve historical decisions upstream privately. Verify no private planner/job/model comparison or DHI research data appeared in published output.



## Dependencies and allowed file closure
No new runtime deps; use `just docs-check` and existing low-cost local commands.

Allowed create/edit paths: `README.md`, `AGENTS.md`, `docs/planning/**` task-status and link changes, `AGENTS.md`, `docs/design/UI_UX_PARITY_MATRIX.md` evidence, `docs/deployment/**`, root `justfile` if stale reference only. Any necessary new dependency installation inside the task's named owning paths is included in this assignment; install compatible versions using the package manager, update the lockfile and tests and report findings. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `DOC-M18-RELEASE`: current remote URLs, CLI commands, tested SHA/version correct and all links resolve.
- `DOC-M18-NOCLAIM`: no unsupported test/deployment/security/compliance claims; README written for actual operator/developer.
- `DOC-M18-PRIVATE`: no secret/private planner DHI material in repo/docs/output.
- `DOC-M18-GATE`: documentation accurately reflects actual source and observed test outcomes.

## Local verification and completion
Run `just docs-check`, `just --list` and scoped link/recipe checks, record `PASS / NO CHANGES NEEDED / BLOCKED`, no code/architecture changes.

Document only actual finished releases; do not treat documentation review as a permission gate for assigned work.



## Local completion

Start coding when this task is explicitly assigned. Run focused local tests and repair real failures; never wait for reviewer certification, a READY table entry, earlier merge receipts or permission to install task dependencies. Commit a focused local task branch, **merge it into local `main`**, and report the commit/merge SHA and actual test results. **Do not push**. Real external writes require a concrete configured target and credentials, not planning-status approvals; complete all possible code/tests if a hosted environment is absent. Never invent secret values, paid service plans or successful deployment evidence.
