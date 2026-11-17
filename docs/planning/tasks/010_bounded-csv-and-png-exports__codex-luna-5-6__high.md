# T-010 — bounded authorized CSV downloads and chart PNG exports

**Status:** WAITING — prerequisite preflight (bounded local scope approved; OMP handles ordinary execution setup). **Repository:** `darizae/flowstead`, private `main`. OMP resolves the current base commit at dispatch. No task may run solely because this file exists.

## Preconditions and order
008/009 chart/API and principal-switch guards accepted; 005 auth enforced at FastAPI. No bucket/report persistence.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: actual backend history/forecast OpenAPI responses, feature-owned SVG chart renderer, typed API/formatter utilities, v2 `historyPng`/`historyCsv`/`forecastPng`/`forecastCsv` positions and `docs/design/UI_UX_PARITY_MATRIX.md`. Use central reference-guided structure from `IMPLEMENTATION_SPEC.md`, not a standalone export framework.

## Observable result and scope
Add Download CSV and Download PNG actions for **each** history and forecast chart. CSV derived from the currently authorized API data only, with exact UTC timestamps, Plant names/IDs as permitted, measurement field, unit, numeric value or empty, quality flag; forecast CSV includes issue time, 12 target UTCs, model version and units. Proper quoting, Content-Disposition/file naming, no spreadsheet formula injection (escape formula-leading values). PNG rasterization of the visible SVG chart must preserve readable **both axes** and labels, source Plant/current selected range/units/timezone, width at least 1320px, and no invisible truncation. Disabled export for unavailable/loading/forbidden state, with no stale private data after logout.



## Dependencies and allowed file closure
Client `Blob`/SVG/canvas can avoid new package; if a rasterizer is necessary, use an explicitly vetted compatible npm package with manifest/lockfile/security scope. Prefer bounded in-browser export; **server CSV endpoints** only if an established scenario requires them, in which case reuse the authenticated API repository policy and add real negative HTTP tests. Never add a general unbounded bulk export endpoint.

Allowed create/edit paths: `frontend/src/**`, `frontend/tests/**`, `frontend/e2e/**`, `frontend/playwright.config.ts` if changed, `frontend/package.json`/`package-lock.json` if package added, `backend/src/flowstead_api/**` and `backend/tests/**` only if server CSV route is added, `justfile`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/design/evidence/**` scrubbed synthetic browser/media evidence, `README.md`. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Prototype-anchored exports and verified artifacts (binding)

- Keep actual download buttons exactly in the **v2 history/forecast card footers**, not an invented global Downloads page. Use small pure, typed `lib/exports/` CSV quoting/validation functions and a separate SVG→PNG adapter using the rendered history/forecast chart's **same data, axes and Plant-local timezone**; no second chart renderer with inconsistent labels. Put tiny React feature components around these utilities; API/network/auth remains in the established `lib/api/` boundary. Avoid unnecessary file-service, persistent storage, web worker or state-manager dependencies.
- Unit-test `UT-M10-CSV` test-first on actual quality flag, NULL, UTC and 12 forecast targets, malicious formula-like strings, quotation/line endings and bounded rows. Then use the **real browser download flow** at 1330px and 390px: parse CSV, decode actual PNG, visually inspect **both axes, timezone, channel units and complete title/legend**, verify no clipping at >=1320px export width, and assert inaccessible/logout/expiry exports are disabled and cannot reuse previous principal's Blob.
- Evidence for every export state is a named `UI_M10` parity matrix row with exact final SHA, commands, click/download/parsed-file assertions and a scrubbed locally generated synthetic sample in `docs/design/evidence/`. A successful link click, file extension or screenshot of a button is **not** export verification. No download leaks URLs or credentials or persists records to Git/cloud.

## Test-first acceptance
- `UT-M10-CSV`: header/order/quoting/null quality/source/UTC correct; no formula execution, bounded rows, 12 forecast entries.
- `UI-M10-PNG`: downloaded real PNG decodes, has both axes labels/units/time meaning at readable resolution for each chart in desktop and mobile sources.
- `SEC-M10-EXPORT`: denied/logout/expired states disable export and no private stale data persists; if server route is added, foreign Plant returns 404.
- `UI-M10-PARITY`: actions directly visible as approved, no filler/explanatory audit copy.

## Local verification, gates and stopping condition
Use unit tests for formatter and **`just test-e2e-local` against local real API/PostgreSQL** to download/inspect CSV and PNG (not filename-only), `just frontend-build`, small backend tests if routes changed. Visual check distinct from green build.

No persistence of PDFs/PNGs/CSVs to cloud or Git.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. OMP coordinates unattended handoff to **ordinary ChatGPT chat in the existing Loop OMP Project** using the owner's previously tested browser workflow. **ChatGPT normal chat is the only independent PR reviewer, bounded GitHub correction agent and final acceptance decision-maker**; OMP/SAIA model PASS is advisory only. OMP handles the Mac's final exact-head tests and only separately authorized merge/issue-status reconciliation. Do not invent a ChatGPT review or block unrelated approved implementation merely because review is pending. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
