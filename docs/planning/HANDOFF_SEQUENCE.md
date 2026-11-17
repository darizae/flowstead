# Flowstead — canonical implementation sequence

**Authority:** This is the single cross-repository task order and observed state. Product and engineering requirements: [IMPLEMENTATION_SPEC.md](IMPLEMENTATION_SPEC.md). Deployment responsibilities and external gates: [DEPLOYMENT_ARCHITECTURE.md](../setup/DEPLOYMENT_ARCHITECTURE.md). Execute **one** eligible task, never the complete sequence. The OMP worker was last reported **PAUSED BY OWNER** after task 004; no documentation edit resumes it. Do not repeat merged steps.

## Ordered execution

| Step | Executable file / ownership | Observed state | Gate |
| --- | --- | --- | --- |
| S-002 | [flowstead-sim M0](https://github.com/darizae/flowstead-sim/blob/main/docs/planning/HANDOFF_SEQUENCE.md) | MERGED PR #2 | Immutable generator contract |
| S-003 | [flowstead-sim M1](https://github.com/darizae/flowstead-sim/blob/main/docs/planning/tasks/003_m1-annual-synthetic-generator__codex-luna-5-6__high.md) | MERGED PR #5; source ad5c94d, merge f06795b | M1 manifest m1.v1, seed 20250101 and telemetry digest pinned; independent ChatGPT review not evidenced |
| 001 | [Repository initialization](tasks/001_repository-initialization__omp-glm-5-3-flash__default.md) | COMPLETE | Existing private main, never reinitialize |
| 002 | [PostgreSQL/import](tasks/002_local-postgres-schema-import__codex-luna-5-6__high.md) | MERGED [PR #4](https://github.com/darizae/flowstead/pull/4) 0b8f3ec | M1 pinned, audit and independent review not verified |
| 003 | [FastAPI read/Plant policy](tasks/003_fastapi-read-and-plant-policy__codex-luna-5-6__high.md) | MERGED [PR #5](https://github.com/darizae/flowstead/pull/5) 647b435 | 002, audit and independent review not verified |
| 004 | [Deterministic 12h forecast](tasks/004_deterministic-twelve-hour-forecast__codex-luna-5-6__high.md) | MERGED [PR #6](https://github.com/darizae/flowstead/pull/6) 8af51c3 | 003; recorded owner-specific review acceptance, audit not verified |
| 004a | [Alembic baseline](tasks/004a_alembic-baseline-adoption__codex-luna-5-6__high.md) | NEXT / NOT EXECUTED | 004; safe populated-database stamping and real local PostgreSQL tests; worker paused |
| 004b | [NATS/JetStream messaging](tasks/004b_nats-jetstream-message-flow__codex-luna-5-6__high.md) | WAITING | 004a merged; outbox/consumer + local PostgreSQL/JetStream tests |
| 005 | [Local JWT/Auth verifier](tasks/005_supabase-auth-verifier-local__codex-luna-5-6__high.md) | WAITING | 004b merged; local JWKS fixtures, no cloud writes |
| 006 | [Backend docs hygiene](tasks/006_backend-contract-docs-hygiene__omp-glm-5-3-flash__default.md) | WAITING | 005 accepted; verify contracts, links and commands |
| 007 | [Frontend foundation and Plants](tasks/007_frontend-foundation-and-plants__codex-luna-5-6__high.md) | WAITING | 006; local HTML reference, per-principal IndexedDB, real Playwright |
| 008 | [Map and history](tasks/008_map-and-history-visualizations__codex-luna-5-6__high.md) | WAITING | 007; real map/tiles, four channels, DST and UI parity |
| 009 | [Forecast and session UX](tasks/009_forecast-and-session-ux__codex-luna-5-6__high.md) | WAITING | 005+008; actual queue and account-switch/cache isolation |
| 010 | [CSV/PNG exports](tasks/010_bounded-csv-and-png-exports__codex-luna-5-6__high.md) | WAITING | 009; parsed files, real downloadable chart images |
| 011 | [Plant PDF report](tasks/011_authorized-pdf-plant-report__codex-luna-5-6__high.md) | WAITING | 010; authorize, parse and visually inspect actual PDF |
| 012 | [Local MVP security/parity](tasks/012_local-mvp-security-and-parity__codex-luna-5-6__high.md) | WAITING | 011; complete indexed real local/browser gates |
| 013 | [MVP docs hygiene](tasks/013_mvp-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md) | WAITING | 012 accepted; reconcile docs/paths/justfile/evidence |
| 014 | [Private development Supabase integration](tasks/014_dev-supabase-integration__codex-luna-5-6__high.md) | BLOCKED / CLOUD | 013 + explicit development DB migration/invite permission |
| 015 | [Local deployment and recovery](tasks/015_local-deployment-build-and-recovery__codex-luna-5-6__high.md) | WAITING | 013; local-only, independent of 014 cloud gate |
| 016 | [Public-demo provision/deploy](tasks/016_public-demo-provision-and-deploy__codex-luna-5-6__high.md) | BLOCKED / CLOUD | 014+015, chosen API/worker/broker host, Supabase/Vercel/DNS/cost/launch approval |
| 017 | [Hosted verification/rollback](tasks/017_public-demo-verification__codex-luna-5-6__high.md) | BLOCKED / CLOUD | 016 actual deployment receipts and approved validation |
| 018 | [Release docs hygiene](tasks/018_release-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md) | WAITING | 017 accepted; real links, deployment refs and release checks |

## Execution and acceptance gates

- **Source gate:** upstream synthetic M1 source ad5c94d1f46e79312a99cb9721f38700f24fdf6b, manifest m1.v1, seed 20250101, telemetry SHA-256 e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e. The imported output is source-at-SHA, not a claimed published package.
- **Review gate:** Future PRs require independent ordinary ChatGPT review via the designated browser handoff, real GitHub correction/review receipts and exact-final-SHA Mac tests before a policy-authorized merge. The current OMP worker instead invokes an OMP reviewer; that mismatch is a **blocking execution preflight**, not permission to substitute review. Do not claim it has been repaired or automatically resume the paused worker. Preserve recorded task 004 owner-specific exception without applying it to later tasks.
- **Local verification:** The existing PostgreSQL, API and forecast merges have reported Mac tests; local dependency-audit status and independent-review gaps remain UNVERIFIED where noted. Later tasks must produce exact test case IDs, observed results, logs and source SHA, including real PostgreSQL, JetStream and Playwright as applicable. A task file existing does not mark it executed.
- **Design gate:** [Reference HTML](../design/reference/flowstead-ui.html) and [UI baseline](../design/UI_UX_BASELINE.md) are approved design inputs. UI tasks 007–012 capture and review true desktop/mobile behavior and [parity matrix](../design/UI_UX_PARITY_MATRIX.md); unavailable map/PDF proof stays UNVERIFIED, not a pre-build blocker.
- **Hosted gate:** The [deployment architecture](../setup/DEPLOYMENT_ARCHITECTURE.md) separates local, existing development and future demo resources. No cloud project write, invitation, broker/worker host, provider account, DNS, production exposure or cost is inferred from local-task approval.
- **Documentation gate:** Tasks 006, 013 and 018 are required scoped Markdown/command/link hygiene reviews at their milestones. Preserve the app-owned task index as the only cross-repository execution queue.