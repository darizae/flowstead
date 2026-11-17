# T-013 — MVP docs and routing hygiene

**Status:** WAITING — prerequisite preflight (bounded local task may run when ordered prerequisites and OMP readiness are verified; external operations remain separately gated). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
012 local milestone completed with real receipts, task statuses reflect actual merges. No substantive code behavior changes here.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: Root docs, `docs/agent/ROUTING.md`, `docs/design/UI_UX_PARITY_MATRIX.md`, task sequence, actual scripts/lockfiles/current README and local test receipts.

## Observable result and scope
Correct stale routing, dead links, incorrect status/recipe/version claims and leftover AWS requirements. Keep README accurate for operator and developer: real running workflows first, present implementation status, actionable setup with real commands. Do not expose internal planner/job/model reasoning. Verify UI matrix evidence refers to actual screens and screenshots, and the current generator pinned SHA. Do not claim future live Supabase or public demo.



## Dependencies and allowed file closure
No new runtime deps. If a docs checker is needed, use existing Python stdlib or existing scripts.

Allowed create/edit paths: `README.md`, `AGENTS.md`, `docs/planning/**` status/routes only, `docs/agent/ROUTING.md`, `docs/design/**` evidence links only, `justfile`, `scripts/docs_check.py` if it exists or is needed. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `DOC-M13-ACTIVE`: relative links, skill read-set paths, current task links, no historical active instructions.
- `DOC-M13-CLAIMS`: README reports actual implemented stages and tested commands, no invented public deployment.
- `DOC-M13-VERSIONS`: exact pinned M1 source/manifest and runtime versions agree with actual lockfiles.
- `DOC-M13-PARITY`: matrix statuses supported by actual real-browser evidence.

## Local verification, gates and stopping condition
Run `just docs-check`, `just --list` and focused safe recipe checks; record PASS/NO CHANGES NEEDED/BLOCKED and no code changes.

Material source contract conflicts stop for ChatGPT; not quietly solved in a doc-cleanup PR.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Independent distinct-agent review at exact PR head is required; until OMP unattended-review acceptance passes, leave `review_ready` blocked. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
