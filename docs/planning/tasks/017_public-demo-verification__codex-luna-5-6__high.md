# T-017 — live demo smoke, security, and rollback acceptance

**Status:** DRAFT — depends on approved public deploy (planning-only approval; NO implementation authorization). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
016 completed with actual resource receipts, owner accepted hosted exposure and available demo test identities. Independently verify active provider state and exact deployed SHAs; no auto-merge/public relaunch on red tests.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `docs/deployment/LOCAL_AND_RECOVERY.md`, live deployment config, app API contracts, UI parity matrix, approved owner demo Auth identities handled out-of-band and current deployed URLs.

## Observable result and scope
Test hosted public and invited-operator journeys in actual browsers through TLS against the separate `flowstead-demo` data, including all five fixed fictional public Plants, map tiles, history, forecast, exports and owner account restrictions. Verify free-tier cold start and paused DB messaging, signed-out/expired/revoked token, disjoint assigned Plants and no private-source leak. Validate backup/reseed procedure against disposable copy, rollback drill where safe/authorized, source/digest/version tracking and alert/log access without credentials exposed. Request owner acceptance of PDF sample, map and public presentation; do not assert uptime guarantees.



## Dependencies and allowed file closure
No new dependency expected. Additional live test tools must be explicitly named/approved before installation; no volume/load/24h soak default. Remote smoke uses minimum necessary requests.

Allowed create/edit paths: `docs/deployment/**`, `docs/design/UI_UX_PARITY_MATRIX.md`, `frontend/tests/e2e/**` targeted hosted checks, `backend/tests/` targeted auth tests, `README.md` for real live URL/status only, `justfile` only if adding existing safe smoke recipe. New dependency installation is authorized **only** when this task itself is approved, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `E2E-M17-PUBLIC`: anonymous sees exactly approved synthetic subset and no private IDs; list/map/history/chart/exports work.
- `E2E-M17-AUTH`: invite operator restricted to assigned Plants through direct crafted API/CSV/PDF requests; expired/revoked tokens fail.
- `UI-M17-LIVE`: actual 390px and desktop map/PDF/PNG/axis/keyboard parity; visible attribution and fail states.
- `OPS-M17-RECOVER`: documented reproducible seed and authorized backup/rollback drill with exact SHAs, no blind destructive DB reset.
- `OPS-M17-COST`: verified free tier/usage alerts and no unexpected paid service, with owner decision for any exception.

## Local verification, gates and stopping condition
Run bounded actual live browser tests, API smoke, provider logs/health and release-local unit regression; record exact deployment URL/time/SHA and distinguish local from remote evidence. No unattended status claim if owner/ChatGPT review unavailable.

If hosted privacy leak/security defect discovered, stop public traffic only through authorized host controls and escalate to owner; do not independently make destructive changes.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Normal-chat ChatGPT independently reviews; use `waiting_chat` if unavailable. After corrections, rerun checks on the exact final SHA on Mac. No 24-hour soak.
