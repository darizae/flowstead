# T-006 — backend contract and Markdown-routing hygiene

**Status:** WAITING — prerequisite preflight (bounded local task may run when ordered prerequisites and OMP readiness are verified; external operations remain separately gated). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
002–005 accepted and merged; no known unresolved material schema/API conflict. This is documentation-only and milestone-gated.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `AGENTS.md`, `docs/planning/IMPLEMENTATION_SPEC.md`, sequence and completed tasks; root `justfile`, README, generated API spec and actual backend source/tests only to verify command paths.

## Observable result and scope
Create/update concise `docs/agent/ROUTING.md` mapping actual backend migrations/importer/API/forecast/auth/tests to owning source. Correct dead relative links, stale cloud/AWS instructions, misnamed recipes, inaccurate README feature claims and completed statuses. Validate M1 immutable commit and actual API paths. No new product decision or feature.



## Dependencies and allowed file closure
No new runtime dependency required; link checker may use existing Python stdlib script inside `scripts/` only if needed, scoped and documented.

Allowed create/edit paths: `docs/agent/ROUTING.md`, `docs/planning/**` docs only, `AGENTS.md`, `README.md`, `justfile` only to fix stale recipe reference, `scripts/docs_check.py` if needed. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `DOC-M2-LINKS`: active Markdown links to files/skills/routes resolve; tracked docs do not point to missing files.
- `DOC-M2-COMMANDS`: every advertised `just` command exists and its referenced script exists; no fake pass claims.
- `DOC-M2-STATUS`: sequence status matches accepted PR/commit evidence; historical AWS is not an active requirement.
- `DOC-M2-DUP`: one current API spec/route per concern; no extra planner docs.

## Local verification, gates and stopping condition
Execute `just --list`, `just docs-check` if now implemented and scoped local link verification; verify recipes using their real low-cost selectors, but do not run the full DB suite just for a doc edit.

Record `PASS`, `NO CHANGES NEEDED` or `BLOCKED` with concrete files/links; no silent material conflict resolution.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Independent distinct-agent review at exact PR head is required; until OMP unattended-review acceptance passes, leave `review_ready` blocked. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
