# T-004 — twelve-hour deterministic influent-flow baseline

**Status: IMPLEMENTED AND MERGED** — [Flowstead PR #6](https://github.com/darizae/flowstead/pull/6), merge `8af51c38b13b2c3260781df5ccd176fa1feb27a1` (2026-11-17 18:57 UTC); OMP Issue #18 is closed `omp:done` after an earlier failed fast-test attempt. Reported gates: 5 forecast unit, 3 forecast PostgreSQL integration and backend regressions; dependency audit UNVERIFIED. **Owner explicitly accepted the OMP/SAIA reviewer for this T-004 only; do not request a second reviewer for this historical task or claim it was ChatGPT-reviewed.** The owner then paused before T-005 dispatch. Do not reimplement T-004; successors T-004a/T-004b migrate the schema and wrap existing pure forecasting through NATS.

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

Extend the **existing** `backend/src/flowstead_api/` FastAPI modules instead of copying the multi-package `the documented engineering patterns` compute/NATS architecture. Keep HTTP routes thin, strict typed forecast response models aligned to OpenAPI, a small deterministic forecast computation function with pure UTC/quality semantics, and parameterized `database.py` queries that enforce the same Plant authorization as current history/latest. This **historical T-004 implementation** persisted an issuance directly in PostgreSQL without a broker; that source behavior is merged and preserved. **Owner-approved successor T-004b** adds NATS/JetStream asynchronous messaging around this same pure forecasting logic without reimplementing the algorithm or rewriting T-004 history. Apply the tested separation-of-concerns ideas from `the documented engineering patterns` and isolated real-SQL test fixtures from `the documented engineering patterns` as summarized in `IMPLEMENTATION_SPEC.md` **without** importing reference code. Write `UT-M4-*` RED cases before forecast behavior when practical; verify `IT-M4-*` with disposable real PostgreSQL and report actual commands/outcomes. Do not assume a previously green API suite proves this forecast. The earlier failed fast-test was superseded by the observed merged PR #6, reported passing final exact-head Mac gates, and closed Issue #18; do not replay this job or invent extra review requirements.

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
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. OMP coordinates unattended handoff to **ordinary ChatGPT chat in the existing Loop OMP Project** using the owner's previously tested browser workflow. **ChatGPT normal chat is the only independent PR reviewer, bounded GitHub correction agent and final acceptance decision-maker**; OMP/SAIA model PASS is advisory only. OMP handles the Mac's final exact-head tests and only separately authorized merge/issue-status reconciliation. Do not invent a ChatGPT review or block unrelated approved implementation merely because review is pending. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
