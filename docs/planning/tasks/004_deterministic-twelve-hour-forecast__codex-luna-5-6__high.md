# T-004 — twelve-hour deterministic influent-flow baseline

**Status:** OMP Issue #18 attempted after T-003 merge and reported **LOCAL FAST TEST FAILURE** at 2026-11-17 18:48 UTC (`omp:failed`); no task 004 PR was observed. **Reconcile the actual Mac log, test command, branch/worktree and source state before a safe retry**—do not replay an uncertain write or treat this as accepted forecasting. **Repository:** `darizae/flowstead`, private `main`; OMP must resolve the fresh base at deliberate dispatch.

## Preconditions and order
003 API and 002 readings are locally verified. Forecast evaluation uses only fixed synthetic data; it cannot demonstrate field accuracy. Do not wire a scheduled cloud job.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `backend/src/flowstead_api/`, forecast tables/migrations, existing SQL fixtures and API contract tests.

## Observable result and scope
For a requested issuance at the latest complete UTC observed bucket `t`, generate exactly 12 predictions at `t+1h … t+12h`, gal/h. Store `issued_at_utc`, `target_time_utc`, `predicted_flow_gal_h`, `model_version` and immutable input/source revision. Add `GET /api/v1/plants/{id}/forecast` with Plant authorization, plus `GET /api/v1/public/plants/{id}/forecast` only for owner-approved public Plants under the same strict allowlist/size and read-only policy (otherwise 404).

Algorithm: seasonal-naive uses the valid flow at `target_time - 24h` if observed by issuance; otherwise persistence of the latest valid hourly flow in `[t-5h,t]`; if neither exists, forecast unavailable (no fabricated zero). Clamp to nonnegative only when a valid physical bound is required and record that rule. Never use missing or invalid source values. Entire horizon uses only data at or before `issued_at`. Database transaction stores issuance plus exactly 12 unique future targets or nothing; repeated issuance with same plant/time/model is idempotent. Backtest by walking a strictly chronological holdout (e.g. final 30 days of a complete year), compute MAE (gal/h) and number of eligible predictions, exclude invalid/missing truth from metrics, compare a persistence reference. State clearly that synthetic backtests do not validate real-world performance; no invented accuracy claims. On-demand local forecast build command, not a public regeneration endpoint.

## Dependencies and allowed file closure
Use Python standard library + existing numeric/Python backend dependencies only unless an explicitly justified package needs authorization and owning `backend/pyproject.toml` + `backend/uv.lock` changes are included. Do not require NumPy, sklearn, task queue or GPU.

Allowed create/edit paths: `backend/src/flowstead_api/**`, `backend/tests/**`, `backend/migrations/**`, `backend/pyproject.toml`, `backend/uv.lock` only for justified install, `justfile`, `README.md`. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Reference-derived code structure and test-first responsibility

Extend the **existing** `backend/src/flowstead_api/` FastAPI modules instead of copying the multi-package `analysis_b.zip` compute/NATS architecture. Keep HTTP routes thin, strict typed forecast response models aligned to OpenAPI, a small deterministic forecast computation function with pure UTC/quality semantics, and parameterized `database.py` queries that enforce the same Plant authorization as current history/latest. Persist one issuance with twelve rows in an explicit transaction, no message broker, scheduler, queue or separate service. Apply the tested separation-of-concerns ideas from `toolkit.zip` and isolated real-SQL test fixtures from `integration_tests.zip` as summarized in `IMPLEMENTATION_SPEC.md` **without** importing reference code. Write `UT-M4-*` RED cases before forecast behavior when practical; verify `IT-M4-*` with disposable real PostgreSQL and report actual commands/outcomes. Do not assume a previously green API suite proves this forecast. The currently reported local fast-test failure must be diagnosed on the Mac; this planning edit does not repair or relaunch it.

## Test-first acceptance
- `UT-M4-HORIZON`: exactly 12 ordered hour-aligned UTC targets with no duplicate and correct units/version.
- `UT-M4-FALLBACK`: 24h valid seasonal input preferred; fallback to last six hours; invalid/missing source rejected; total unavailable is explicit.
- `IT-M4-ATOMIC`: partial insertion fails atomically; same-key rerun idempotent.
- `IT-M4-CROSSPLANT`: user assigned Plant A cannot see Plant B forecast; public absent by default.
- `UT-M4-BACKTEST`: feature inputs always ≤ issuance, held-out observations not accessed as features; metrics count correctly, and no fabricated empirical claim.

## Local verification, gates and stopping condition
Implement `just forecast-local`, `just test-forecast-unit`, `just test-forecast-integration` with existing scripts; focused `uv run --project backend pytest -q backend/tests/unit/test_forecast.py`, real DB forecast integration; later API regression. Record actual forecast unavailable behavior and held-out result, no accuracy marketing.

Stop on change to measurement semantics/forecast horizon. Owner only reviews user-facing display/thresholds later.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. OMP owns independent PR review and acceptance synchronization as a control-plane follow-up; do not delay this task's implementation waiting for that upgrade. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
