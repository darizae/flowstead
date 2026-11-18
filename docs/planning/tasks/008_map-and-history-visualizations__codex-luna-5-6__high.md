# T-008 — MapLibre Plants map and four monitoring charts

**Execution:** Start when explicitly assigned; no WAITING/READY/approval prerequisite. **Repository:** `darizae/flowstead`, local `main` checkout.

## Existing implementation and technical context
Use the frontend from T-007 and real API schemas when present. If a required component is missing, implement the narrow needed interface inside this task; do not wait for a task-status update.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: actual 007 route/feature components, typed API and UI state, `docs/design/UI_UX_BASELINE.md` (exact v2 `overviewGrid`, `mapPanel`, `detailGrid` layout), matrix rows, and history API tests. Review the original approved v2 HTML read-only if owner-authorized access exists, never copy sample data/source. Official MapLibre docs and current provider terms.

## Required Marisma UI library (binding)

Use the existing `@darizae/marisma@0.2.0` integration from T-007a for reusable React/Tailwind controls and application surfaces added or changed in this task. Import Marisma's public components and theme; do not introduce duplicate bespoke Tailwind/Radix buttons, cards, fields, dialogs or shell primitives where Marisma provides them. Preserve Flowstead's approved v2 layout, colors and interaction behavior; keep MapLibre, scientific charts and domain-specific UI logic within Flowstead. Exercise affected rendered UI and update `docs/design/UI_UX_PARITY_MATRIX.md`; do not vendor Marisma or edit its repository.

## Observable result and scope
Add real interactive MapLibre GL JS map using `https://tiles.openfreemap.org/styles/liberty` (subject to current provider availability/terms), visible attribution, fabricated lat/lon markers for only visible Plants, keyboard-accessible marker activation, navigation to selected Plant, fit bounds, safe offline/no-WebGL fallback back to list. On Plant detail show latest four values with quality and a history chart switcher for all four channels, 24h/72h/7d windows, proper x-axis `Plant-local time` incl DST EDT/EST/CDT/CST ambiguity, and correct y-axis titles/units. No misleading interpolation of missing/invalid values.



## Dependencies and allowed file closure
Use `maplibre-gl` 6.x and its stylesheet; chart rendering preferably accessible SVG with existing local CSS/React—prefer no separate charting library; if a compatible library materially simplifies implementation, install it in the named frontend manifest and lockfile, run audit and tests, and document the choice. No geocoding API/key and no real facility coordinates.

Allowed create/edit paths: `frontend/src/**`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts` if needed, `frontend/tests/**`, `frontend/e2e/**`, `frontend/playwright.config.ts` if changed, `justfile`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/design/evidence/**` synthetic browser captures, `README.md`. Necessary package, manifest, lockfile, fixture, command and test updates in the named owning paths are in scope when this task is assigned. Choose supported compatible versions, generate lockfiles with the package manager, audit dependencies and verify locally. Do not request separate permission for predictable dependency setup; keep changes related to this task. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Reference-anchored map, charts and browser proof (binding)

- Match prototype `overviewGrid` (list/map side by side on desktop, stacked mobile), `realMap` and `mapFallback`: a dedicated `PlantMap` component owns MapLibre mount/unmount and error fallback; markers derive from exactly the same API-visible Plant list as `PlantList`. Test that the marker button and list row open the same selected Plant and that *foreign Plant IDs have neither marker nor list item*. Keep tile attribution visible; the map must not be a static Florida SVG masquerading as live tiles.
- Create small, typed pure data transformations for `plantHourLabel`, four channel names/units, quality→gap rendering and UTC-to-Plant-IANA DST labels; keep SVG drawing separate from API fetching and page/navigation. Reuse the **approved prototype panel positions, metric tiles, four channel toggles, 24/72/168h controls and observed-forecast style distinction**. Do not introduce a large plot package or global data store by copying `analysis_b`; avoid silent interpolation of missing/invalid hours.
- Playwright **real browser + HTTP gate**: 1330×900 and 390×844 capture, live tile response/render and visible attribution, keyboard-accessible marker activation and list fallback under forced WebGL/network failure, no overflow, all four chart y-axis titles and Plant-local x-axis, Eastern/Central DST repeated-hour labels. Assert interactions and API payloads, not only screenshots. If provider unavailable, label live-tiles UNVERIFIED separately from fallback PASS; record exact SHA, screenshots and deviations in parity matrix. Prepare downloadable SVG chart data that task 010 will rasterize without losing axis labels.

## Test-first acceptance
- `UI-M8-MAP`: real tile render and marker selection from API list; forbidden Plant marker absent; attribution visible; internet/WebGL failure renders list fallback.
- `UT-M8-CHART`: all four charts preserve proper unit, quality flags, 24/72/168h and axis labels; no line joining across missing segments.
- `UT-M8-DST`: UTC fall-back repeated hours have explicit timezone offset/abbreviation; spring-forward gap not invented; Central/Eastern chosen per Plant.
- `UI-M8-PARITY`: desktop 1330px and mobile 390px real browser snapshots/actions, keyboard and zoom; matrix evidence PASS/FAIL/UNVERIFIED.

## Local verification and completion
Run named Vitest chart formatter tests and **`just test-e2e-local` against real local PostgreSQL/API** for browser/Playwright marker+tile and chart interactions at 1330px/390px; run `just frontend-build`, `just test-frontend-unit` and `just audit-frontend` if deps changed. A screenshot's existence is not a passing interactive check.

If OpenFreeMap unavailable, implement documented map-unavailable fallback but leave live tile gate UNVERIFIED; choose a safe fallback without fabricating tiles or switching providers silently.



## Local completion

Implement immediately when this file is explicitly assigned. Run the stated targeted local tests and fix failures in task-owned source and tests; record observed checks and any environment limitations. Make a focused local task-branch commit and **merge into local `main`** after resolving code/test failures and Git conflicts. Record the resulting SHA and changes. **Do not push**. Independent ChatGPT review, PR receipts, predecessor acceptance, task index statuses and extra owner authorization are **not prerequisites** to starting, committing or locally merging this task. If a real external resource is absent, finish all feasible local work and report what could not be exercised without inventing hosted results.
