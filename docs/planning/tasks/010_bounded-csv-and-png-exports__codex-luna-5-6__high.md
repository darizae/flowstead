# T-010 — bounded authorized CSV downloads and chart PNG exports

**Execution:** Start when explicitly assigned; no WAITING/READY/approval prerequisite. **Repository:** `darizae/flowstead`, local `main` checkout.

## Existing implementation and technical context
Use the actual current history/forecast API and chart renderer; build any missing narrow export seam as part of this task. Previous task status is informational only.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: actual backend history/forecast OpenAPI responses, feature-owned SVG chart renderer, typed API/formatter utilities, v2 `historyPng`/`historyCsv`/`forecastPng`/`forecastCsv` positions and `docs/design/UI_UX_PARITY_MATRIX.md`. Use central reference-guided structure from `IMPLEMENTATION_SPEC.md`, not a standalone export framework.

## Required Marisma UI library (binding)

Use the existing `@darizae/marisma@0.2.0` integration from T-007a for reusable React/Tailwind controls and application surfaces added or changed in this task. Import Marisma's public components and theme; do not introduce duplicate bespoke Tailwind/Radix buttons, cards, fields, dialogs or shell primitives where Marisma provides them. Preserve Flowstead's approved v2 layout, colors and interaction behavior; keep MapLibre, scientific charts and domain-specific UI logic within Flowstead. Exercise affected rendered UI and update `docs/design/UI_UX_PARITY_MATRIX.md`; do not vendor Marisma or edit its repository.

## Observable result and scope
Add Download CSV and Download PNG actions for **each** history and forecast chart. CSV derived from the currently authorized API data only, with exact UTC timestamps, Plant names/IDs as permitted, measurement field, unit, numeric value or empty, quality flag; forecast CSV includes issue time, 12 target UTCs, model version and units. Proper quoting, Content-Disposition/file naming, no spreadsheet formula injection (escape formula-leading values). PNG rasterization of the visible SVG chart must preserve readable **both axes** and labels, source Plant/current selected range/units/timezone, width at least 1320px, and no invisible truncation. Disabled export for unavailable/loading/forbidden state, with no stale private data after logout.



## Dependencies and allowed file closure
Client `Blob`/SVG/canvas can avoid new package; if a rasterizer is necessary, use an explicitly vetted compatible npm package with manifest/lockfile/security scope. Prefer bounded in-browser export; **server CSV endpoints** only if an established scenario requires them, in which case reuse the authenticated API repository policy and add real negative HTTP tests. Never add a general unbounded bulk export endpoint.

Allowed create/edit paths: `frontend/src/**`, `frontend/tests/**`, `frontend/e2e/**`, `frontend/playwright.config.ts` if changed, `frontend/package.json`/`package-lock.json` if package added, `backend/src/flowstead_api/**` and `backend/tests/**` only if server CSV route is added, `justfile`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/design/evidence/**` scrubbed synthetic browser/media evidence, `README.md`. Necessary package, manifest, lockfile, fixture, command and test updates in the named owning paths are in scope when this task is assigned. Choose supported compatible versions, generate lockfiles with the package manager, audit dependencies and verify locally. Do not request separate permission for predictable dependency setup; keep changes related to this task. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Prototype-anchored exports and verified artifacts (binding)

- Keep actual download buttons exactly in the **v2 history/forecast card footers**, not an invented global Downloads page. Use small pure, typed `lib/exports/` CSV quoting/validation functions and a separate SVG→PNG adapter using the rendered history/forecast chart's **same data, axes and Plant-local timezone**; no second chart renderer with inconsistent labels. Put tiny React feature components around these utilities; API/network/auth remains in the established `lib/api/` boundary. Avoid unnecessary file-service, persistent storage, web worker or state-manager dependencies.
- Unit-test `UT-M10-CSV` test-first on actual quality flag, NULL, UTC and 12 forecast targets, malicious formula-like strings, quotation/line endings and bounded rows. Then use the **real browser download flow** at 1330px and 390px: parse CSV, decode actual PNG, visually inspect **both axes, timezone, channel units and complete title/legend**, verify no clipping at >=1320px export width, and assert inaccessible/logout/expiry exports are disabled and cannot reuse previous principal's Blob.
- Evidence for every export state is a named `UI_M10` parity matrix row with exact final SHA, commands, click/download/parsed-file assertions and a scrubbed locally generated synthetic sample in `docs/design/evidence/`. A successful link click, file extension or screenshot of a button is **not** export verification. No download leaks URLs or credentials or persists records to Git/cloud.

## Test-first acceptance
- `UT-M10-CSV`: header/order/quoting/null quality/source/UTC correct; no formula execution, bounded rows, 12 forecast entries.
- `UI-M10-PNG`: downloaded real PNG decodes, has both axes labels/units/time meaning at readable resolution for each chart in desktop and mobile sources.
- `SEC-M10-EXPORT`: denied/logout/expired states disable export and no private stale data persists; if server route is added, foreign Plant returns 404.
- `UI-M10-PARITY`: actions directly visible as approved, no filler/explanatory audit copy.

## Local verification and completion
Use unit tests for formatter and **`just test-e2e-local` against local real API/PostgreSQL** to download/inspect CSV and PNG (not filename-only), `just frontend-build`, small backend tests if routes changed. Visual check distinct from green build.

No persistence of PDFs/PNGs/CSVs to cloud or Git.



## Local completion

Implement immediately when this file is explicitly assigned. Run the stated targeted local tests and fix failures in task-owned source and tests; record observed checks and any environment limitations. Make a focused local task-branch commit and **merge into local `main`** after resolving code/test failures and Git conflicts. Record the resulting SHA and changes. **Do not push**. Independent ChatGPT review, PR receipts, predecessor acceptance, task index statuses and extra owner authorization are **not prerequisites** to starting, committing or locally merging this task. If a real external resource is absent, finish all feasible local work and report what could not be exercised without inventing hosted results.
