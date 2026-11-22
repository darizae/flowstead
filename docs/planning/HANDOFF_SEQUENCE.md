# Flowstead — task index

**This file is navigation, not an execution gate.** When the owner assigns a task specification, start it. Ignore legacy `WAITING`, `BLOCKED`, `DRAFT`, `READY`, predecessor-review and approval statuses found in historical files. Do not wait for receipts, an independent ChatGPT reviewer, status updates or owner re-approval. An actual absent API, test fixture or dependency is engineering work to investigate, not an administrative reason to stop.

## Task files

| Step | Specification | Context, not permission |
| --- | --- | --- |
| S-002 | [flowstead-sim M0](https://github.com/darizae/flowstead-sim/blob/main/docs/planning/HANDOFF_SEQUENCE.md) | Historical: MERGED PR #2 |
| S-003 | [flowstead-sim M1](https://github.com/darizae/flowstead-sim/blob/main/docs/planning/tasks/003_m1-annual-synthetic-generator__codex-luna-5-6__high.md) | Historical: MERGED PR #5; source ad5c94d, merge f06795b |
| 001 | [Repository initialization](tasks/001_repository-initialization__omp-glm-5-3-flash__default.md) | Historical: COMPLETE |
| 002 | [PostgreSQL/import](tasks/002_local-postgres-schema-import__codex-luna-5-6__high.md) | Historical: MERGED [PR #4](https://github.com/darizae/flowstead/pull/4) 0b8f3ec |
| 003 | [FastAPI read/Plant policy](tasks/003_fastapi-read-and-plant-policy__codex-luna-5-6__high.md) | Historical: MERGED [PR #5](https://github.com/darizae/flowstead/pull/5) 647b435 |
| 004 | [Deterministic 12h forecast](tasks/004_deterministic-twelve-hour-forecast__codex-luna-5-6__high.md) | Historical: MERGED [PR #6](https://github.com/darizae/flowstead/pull/6) 8af51c3 |
| 004a | [Alembic baseline](tasks/004a_alembic-baseline-adoption__codex-luna-5-6__high.md) | Historical: MERGED [PR #7](https://github.com/darizae/flowstead/pull/7), merge `78b109c`; acceptance receipt commit `3b40ce5` |
| 004b | [NATS/JetStream messaging](tasks/004b_nats-jetstream-message-flow__codex-luna-5-6__high.md) | NATS implementation committed to `main` at `388a5ad`; remaining test/review evidence is informational |
| 005 | [Local JWT/Auth verifier](tasks/005_supabase-auth-verifier-local__codex-luna-5-6__high.md) | Implemented on `main` at `e5482fdd3306dd83ed9c74b5b8d702bcdf2badf6`; tests were not rerun for this documentation update |
| 006 | [Backend docs hygiene](tasks/006_backend-contract-docs-hygiene__omp-glm-5-3-flash__default.md) | Execute immediately when assigned; consult previous implementations as technical context |
| 007 | [Frontend foundation and Plants](tasks/007_frontend-foundation-and-plants__codex-luna-5-6__high.md) | Owner reports completed locally; frontend not present on remote `main` as of 2026-11-18; preserve local work |
| 007a | [Integrate mandatory Marisma UI library](tasks/007a_marisma-ui-integration__codex-luna-5-6__high.md) | Start directly on the locally completed T-007 frontend; install and actually use `@darizae/marisma@0.2.0` before continuing frontend work |
| 008 | [Map and history](tasks/008_map-and-history-visualizations__codex-luna-5-6__high.md) | Execute immediately when assigned; consult previous implementations as technical context |
| 009 | [Forecast and session UX](tasks/009_forecast-and-session-ux__codex-luna-5-6__high.md) | Execute immediately when assigned; consult previous implementations as technical context |
| 010 | [CSV/PNG exports](tasks/010_bounded-csv-and-png-exports__codex-luna-5-6__high.md) | Merged locally at `b9e9ccf` and pushed; T-010 receipt and evidence recorded |
| 011 | [Plant PDF report](tasks/011_authorized-pdf-plant-report__codex-luna-5-6__high.md) | Merged locally at `e474c49`; T-011 receipt with real PostgreSQL, browser download and opened-PDF review recorded |
| 012 | [Local MVP security/parity](tasks/012_local-mvp-security-and-parity__codex-luna-5-6__high.md) | Execute immediately when assigned; consult previous implementations as technical context |
| 013 | [MVP docs hygiene](tasks/013_mvp-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md) | Completed locally on `main`; `just docs-check`, `just --list`, `just check-backend` and `just frontend-typecheck` pass; no stale links/claims/AWS requirements found; DOC-M13 verified |
| 014 | [Private development Supabase integration](tasks/014_dev-supabase-integration__codex-luna-5-6__high.md) | Local runbook/connection proof merged 73345a5; dev live migrations/import/Auth unperformed; keep dev unchanged for demo |
| 015 | [Local deployment and recovery](tasks/015_local-deployment-build-and-recovery__codex-luna-5-6__high.md) | Committed to remote main at 9c3ba5a; local staging build/recovery recorded, hosted state unverified |
| 016 | [Existing demo host deployment](tasks/016_public-demo-provision-and-deploy__codex-luna-5-6__high.md) | MERGED local `main`: existing Frankfurt E2.1.Micro used exclusively; demo Supabase migrated/imported (5 Plants, 43,800 rows); DNS/TLS/Caddy and frontend domain,API origin deployed; superseded by T-017 2026-11-22 cutover |
| 017 | [Hosted verification/rollback](tasks/017_public-demo-verification__codex-luna-5-6__high.md) | **PARTIAL** (see [live receipt](../deployment/T017_LIVE_VERIFICATION_2026-11-21.md)): 2026-11-22 live API/worker/PROXY/NATS cutover verified — HTTPS health/ready/public reads/PDF 200, two confirmed scoped test operators, five outbox events published, forecast jobs still 0. **Overall PARTIAL; no E2E pass yet.** Costs outstanding |
| 018 | [Release docs hygiene](tasks/018_release-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md) | EXECUTED in this pass: docs-check green, stale deployment claims refreshed, GitHub Actions CI added (see T-020 for next hosted work) |
| 019 | [Security exposure and cost-abuse audit](tasks/019_security-exposure-and-cost-abuse-audit.md) | PARTIAL remediation documented in [2026-11-21 sec19 report](../security/2026-11-21-sec19-report.md) and [end-to-end audit](../security/2026-11-21-end-to-end-security-audit.md); hosted verification remains OPEN |
| 020 | [Hosted operator login and validation](tasks/020_hosted-operator-login-and-validation.md) | **PARTIAL** ([session evidence](../deployment/T020_PROGRESS_2026-11-22.md)): real Supabase email/password login UI implemented, local backend/frontend tests passed, both test accounts authenticated directly to Supabase. OCI guest became unresponsive (one graceful SOFTRESET requested); hosted browser/Plant/forecast E2E, restart recovery and costs **NOT YET PASS** |

Current cloud note (2026-11-22): The owner selected only the existing Oracle `flowstead-demo-instance` in `eu-frankfurt-1` (`VM.Standard.E2.1.Micro`); SSH ingress is narrowed to the Mac public IPv4 /32, and `flowstead-demo` is migrated to 003 with five validated Plants and 43,800 readings. Verified 2026-11-22: `flowstead-api`, `flowstead-worker`, `flowstead-nats` and `flowstead-proxy` are active; live HTTPS health/ready and the public five-Plant reads/PDF return 200; two scoped test operators exist; five outbox events are published with zero failures; `app.forecast_jobs`/`forecast_issuances` are still 0. The deployed Vercel frontend serves the `flowstead` custom domain. No E2E pass is claimed and actual provider costs remain outstanding. Do not create a replacement machine. See [OCI runbook](../deployment/OCI_ALWAYS_FREE.md).

## Execution conventions

- **Frontend library:** `@darizae/marisma` is required in Flowstead, not optional. T-007a integrates it into the completed local T-007 frontend; T-008 onward reuse it for shared UI controls and app surfaces. No new approval/readiness checkpoint is needed to carry out the assigned work.
- Work on exactly the task the owner assigns. Earlier tasks explain source ownership and interfaces; examine current code instead of treating their documentation status as authoritative.
- T-005's local Supabase-compatible verifier is implemented at `e5482fd`; hosted Supabase behavior remains explicitly unverified until its owning cloud task. T-006 and later assigned tasks start without a review or status gate.
- Preserve the pinned M1 synthetic source commit `ad5c94d1f46e79312a99cb9721f38700f24fdf6b`, manifest `m1.v1`, seed `20250101` and telemetry digest `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`.
- Implement and verify behavior locally using targeted tests plus relevant real PostgreSQL, NATS/JetStream or browser interactions. Document failures honestly; tests are engineering checks, **not permission checks for starting work**.
- Complete the assigned task with a local commit and merge into local `main`, resolving actual Git conflicts and correcting failing checks. **Never push automatically.** Independent review may be done afterward and does not block the local workflow.
- Respect actual secrets/data boundaries. Local development must not create paid services, mutate unrelated cloud projects, expose credentials or publish a demo incidentally. For explicitly assigned cloud work, implement all feasible code/configuration and use only concrete authorized external resources; do not fabricate a host, recipient or cost.

Design reference: [UI/UX baseline](../design/UI_UX_BASELINE.md). Testing reference: [indexed tests](../testing/INDEXED_TEST_PLAN.md). Hosting setup: [deployment architecture](../setup/DEPLOYMENT_ARCHITECTURE.md).
