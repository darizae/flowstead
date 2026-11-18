# T-006 — backend contract and Markdown-routing hygiene

**Status:** WAITING — prerequisite preflight (bounded local scope approved; OMP handles ordinary execution setup). **Repository:** `darizae/flowstead`, private `main`. OMP resolves the current base commit at dispatch. No task may run solely because this file exists.

## Preconditions and order
002–005 accepted and merged; no known unresolved material schema/API conflict. This is documentation-only and milestone-gated.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `AGENTS.md`, `docs/planning/IMPLEMENTATION_SPEC.md`, sequence and completed tasks; root `justfile`, README, generated API spec and actual backend source/tests only to verify command paths.

## Observable result and scope
Create/update concise `AGENTS.md` mapping actual **Alembic migrations**, import/forecast, NATS publisher/consumer/outbox, API/auth, indexed test plan/data guide and runnable just recipes to owning source. Correct dead relative links, stale cloud/AWS instructions, misnamed recipes, inaccurate README feature claims and completed statuses. Validate M1 immutable commit and actual API paths. No new product decision or feature.



## Dependencies and allowed file closure
No new runtime dependency required; link checker may use existing Python stdlib script inside `scripts/` only if needed, scoped and documented.

Allowed create/edit paths: `AGENTS.md`, `docs/planning/**` docs only, `AGENTS.md`, `README.md`, `justfile` only to fix stale recipe reference, `scripts/docs_check.py` if needed. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

Confirm `docs/testing/INDEXED_TEST_PLAN.md` contains every actual case ID and evidence remains truthful; do not mark test case coverage from its name alone. Verify docs consistently describe Alembic, JetStream and per-principal IndexedDB without altering verified completion records.

## Test-first acceptance
- `DOC-M2-LINKS`: active Markdown links to files/skills/routes resolve; tracked docs do not point to missing files.
- `DOC-M2-COMMANDS`: every advertised `just` command exists and its referenced script exists; no fake pass claims.
- `DOC-M2-STATUS`: sequence status matches accepted PR/commit evidence; historical AWS is not an active requirement.
- `DOC-M2-DUP`: one current API spec/route per concern; no extra planner docs.

## Local verification, gates and stopping condition
Execute `just --list`, `just docs-check` if now implemented and scoped local link verification; verify recipes using their real low-cost selectors, but do not run the full DB suite just for a doc edit.

Record `PASS`, `NO CHANGES NEEDED` or `BLOCKED` with concrete files/links; no silent material conflict resolution.



## Git / review receipt
Work on a short-lived local task branch from verified `main`; prepare focused commits and a reviewable local diff. A remote draft PR is not required for the owner-authorized no-push workflow. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push any branch or `main`, force-update history, tag, spend or alter cloud state without separate authorization; the local merge is permitted only after the task's acceptance gates. OMP routes **ordinary ChatGPT normal-chat** independent PR review through the owner-approved Brave browser relay; current worker implementation remains misaligned, so never claim ChatGPT review from an OMP/SAIA model PASS. After any correction, rerun required checks on the exact final SHA on Mac. Never merge without verified independent review, required local tests and compliance with actual repository policy. No 24-hour soak.

**Local Git completion (owner authorization, 2026-11-18):** After this task becomes eligible, the scoped change passes its required independent ordinary ChatGPT review and exact-final-tree Mac verification, make a focused local task-branch commit and merge the reviewed branch into **local `main`** with a normal non-force Git merge. Verify and report the task SHA, resulting `main` SHA/tree and working-tree status; repeat relevant checks if the merged tree differs. **Do not push** the task branch or `main`. If verification/review is incomplete, the base changed without review, a merge conflicts, or repository policy requires a remote PR, stop and report the blocker rather than pushing or merging. This authorizes local Git completion only; external cloud, release, invite, spend and destructive-action gates remain unchanged.
