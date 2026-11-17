# T-018 — final Markdown/routing/release evidence hygiene

**Status:** DRAFT — gated by 017 (planning-only approval; NO implementation authorization). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
017 hosted acceptance and owner public approval recorded. No unresolved material security or docs defect. Documentation-only task.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: README, routes, app/spec/sequence, **real Alembic revisions and NATS/JetStream operations**, release/deploy notes, UI parity matrix, `docs/testing/INDEXED_TEST_PLAN.md`, `docs/testing/TEST_DATA_GUIDE.md`, case coverage reports, checked browser/SQL/broker receipts/real host URLs and exact generator source SHA.

## Observable result and scope
Update truthful README product/demo link (only if actually live), dev install/test quickstart, **actual Alembic upgrade and NATS stream/consumer/worker/restart recipes, IndexedDB cache rules, indexed case coverage/Playwright HTML report instructions**, API/UI routes, current host/rollback instructions, active task statuses and tested release refs. Delete stale AWS/S3 or provisional external-gate claims that are no longer accurate, but preserve historical decisions upstream privately. Verify no private planner/job/model comparison or DHI research data appeared in published output.



## Dependencies and allowed file closure
No new runtime deps; use `just docs-check` and existing low-cost local commands.

Allowed create/edit paths: `README.md`, `AGENTS.md`, `docs/planning/**` task-status and link changes, `docs/agent/ROUTING.md`, `docs/design/UI_UX_PARITY_MATRIX.md` evidence, `docs/deployment/**`, root `justfile` if stale reference only. New dependency installation is authorized **only** when this task itself is approved, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `DOC-M18-RELEASE`: current remote URLs, CLI commands, tested SHA/version correct and all links resolve.
- `DOC-M18-NOCLAIM`: no unsupported test/deployment/security/compliance claims; README written for actual operator/developer.
- `DOC-M18-PRIVATE`: no secret/private planner DHI material in repo/docs/output.
- `DOC-M18-GATE`: active milestone statuses match independent approvals and receipts.

## Local verification, gates and stopping condition
Run `just docs-check`, `just --list` and scoped link/recipe checks, record `PASS / NO CHANGES NEEDED / BLOCKED`, no code/architecture changes.

No final release marked complete until this gate closes.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Normal-chat ChatGPT independently reviews; use `waiting_chat` if unavailable. After corrections, rerun checks on the exact final SHA on Mac. No 24-hour soak.
