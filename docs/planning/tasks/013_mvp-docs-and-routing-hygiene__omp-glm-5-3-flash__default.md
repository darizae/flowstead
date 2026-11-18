# T-013 — MVP docs and routing hygiene

**Execution:** Start immediately when assigned; planning-status and reviewer approvals are not prerequisites. **Repository:** `darizae/flowstead`, local `main`.

## Technical context
Run documentation/routing checks against the checkout; correct stale docs now, regardless of predecessor task status.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: Root docs, `AGENTS.md`, `docs/design/UI_UX_PARITY_MATRIX.md`, task sequence, actual scripts/lockfiles/current README and local test receipts.

## Marisma frontend documentation (binding)

Flowstead consumes the published `@darizae/marisma` npm UI library as a mandatory frontend dependency beginning with T-007a. Keep install instructions, frontend package/lockfile references, theme setup and UI claims aligned with actual source and browser results. Do not describe Marisma as optional, prescribe replacement generic controls, or modify the separate Marisma repository.

## Observable result and scope
Correct stale routing, dead links, incorrect status/recipe/version claims and leftover AWS requirements. Keep README accurate for operator and developer: real running workflows first, present implementation status, actionable setup with real commands. Do not expose internal planner/job/model reasoning. Verify UI matrix evidence refers to actual screens and screenshots, and the current generator pinned SHA. Do not claim future live Supabase or public demo.



## Dependencies and allowed file closure
No new runtime deps. If a docs checker is needed, use existing Python stdlib or existing scripts.

Allowed create/edit paths: `README.md`, `AGENTS.md`, `docs/planning/**` status/routes only, `AGENTS.md`, `docs/design/**` evidence links only, `justfile`, `scripts/docs_check.py` if it exists or is needed. Necessary package/manifest/lockfile, test and command updates within the task's named owning paths are included in this assignment. Choose compatible maintained dependencies, use the real package manager to update locks, audit and test. Do not request separate approval for routine setup. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

Reconcile exact acceptance IDs from `docs/testing/INDEXED_TEST_PLAN.md` against asserting pytest/Vitest/Playwright tests, real NATS/PG/browser receipts, IndexedDB cache checks and the generated local Playwright HTML report. Mark absent cases UNVERIFIED, not PASS. Document genuine Alembic current/head, Compose NATS/JetStream and message recovery commands.

## Test-first acceptance
- `DOC-M13-ACTIVE`: relative links, skill read-set paths, current task links, no historical active instructions.
- `DOC-M13-CLAIMS`: README reports actual implemented stages and tested commands, no invented public deployment.
- `DOC-M13-VERSIONS`: exact pinned M1 source/manifest and runtime versions agree with actual lockfiles.
- `DOC-M13-PARITY`: matrix statuses supported by actual real-browser evidence.

## Local verification and completion
Run `just docs-check`, `just --list` and focused safe recipe checks; record PASS/NO CHANGES NEEDED/BLOCKED and no code changes.

Material source contract conflicts stop for ChatGPT; not quietly solved in a doc-cleanup PR.



## Local completion

Start coding when this task is explicitly assigned. Run focused local tests and repair real failures; never wait for reviewer certification, a READY table entry, earlier merge receipts or permission to install task dependencies. Commit a focused local task branch, **merge it into local `main`**, and report the commit/merge SHA and actual test results. **Do not push**. Real external writes require a concrete configured target and credentials, not planning-status approvals; complete all possible code/tests if a hosted environment is absent. Never invent secret values, paid service plans or successful deployment evidence.
