# T-013 — MVP docs and routing hygiene

**Status:** WAITING — prerequisite preflight (bounded local scope approved; OMP handles ordinary execution setup). **Repository:** `darizae/flowstead`, private `main`. OMP resolves the current base commit at dispatch. No task may run solely because this file exists.

## Preconditions and order
012 local milestone completed with real receipts, task statuses reflect actual merges. No substantive code behavior changes here.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: Root docs, `AGENTS.md`, `docs/design/UI_UX_PARITY_MATRIX.md`, task sequence, actual scripts/lockfiles/current README and local test receipts.

## Observable result and scope
Correct stale routing, dead links, incorrect status/recipe/version claims and leftover AWS requirements. Keep README accurate for operator and developer: real running workflows first, present implementation status, actionable setup with real commands. Do not expose internal planner/job/model reasoning. Verify UI matrix evidence refers to actual screens and screenshots, and the current generator pinned SHA. Do not claim future live Supabase or public demo.



## Dependencies and allowed file closure
No new runtime deps. If a docs checker is needed, use existing Python stdlib or existing scripts.

Allowed create/edit paths: `README.md`, `AGENTS.md`, `docs/planning/**` status/routes only, `AGENTS.md`, `docs/design/**` evidence links only, `justfile`, `scripts/docs_check.py` if it exists or is needed. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

Reconcile exact acceptance IDs from `docs/testing/INDEXED_TEST_PLAN.md` against asserting pytest/Vitest/Playwright tests, real NATS/PG/browser receipts, IndexedDB cache checks and the generated local Playwright HTML report. Mark absent cases UNVERIFIED, not PASS. Document genuine Alembic current/head, Compose NATS/JetStream and message recovery commands.

## Test-first acceptance
- `DOC-M13-ACTIVE`: relative links, skill read-set paths, current task links, no historical active instructions.
- `DOC-M13-CLAIMS`: README reports actual implemented stages and tested commands, no invented public deployment.
- `DOC-M13-VERSIONS`: exact pinned M1 source/manifest and runtime versions agree with actual lockfiles.
- `DOC-M13-PARITY`: matrix statuses supported by actual real-browser evidence.

## Local verification, gates and stopping condition
Run `just docs-check`, `just --list` and focused safe recipe checks; record PASS/NO CHANGES NEEDED/BLOCKED and no code changes.

Material source contract conflicts stop for ChatGPT; not quietly solved in a doc-cleanup PR.



## Git / review receipt
Work on a short-lived local task branch from verified `main`; prepare focused commits and a reviewable local diff. A remote draft PR is not required for the owner-authorized no-push workflow. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push any branch or `main`, force-update history, tag, spend or alter cloud state without separate authorization; the local merge is permitted only after the task's acceptance gates. OMP must invoke ordinary Loop OMP **ChatGPT** independent review through the owner-approved Brave browser relay; OMP/SAIA review alone is not future acceptance. After any correction, rerun required checks on the exact final SHA on Mac. Never merge without verified independent review, required local tests and compliance with actual repository policy. No 24-hour soak.

**Local Git completion (owner authorization, 2026-11-18):** After this task becomes eligible, the scoped change passes its required independent ordinary ChatGPT review and exact-final-tree Mac verification, make a focused local task-branch commit and merge the reviewed branch into **local `main`** with a normal non-force Git merge. Verify and report the task SHA, resulting `main` SHA/tree and working-tree status; repeat relevant checks if the merged tree differs. **Do not push** the task branch or `main`. If verification/review is incomplete, the base changed without review, a merge conflicts, or repository policy requires a remote PR, stop and report the blocker rather than pushing or merging. This authorizes local Git completion only; external cloud, release, invite, spend and destructive-action gates remain unchanged.
