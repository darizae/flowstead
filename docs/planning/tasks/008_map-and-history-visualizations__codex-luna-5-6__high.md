# T-008 — MapLibre Plants map and four monitoring charts

**Status:** WAITING — 007 (bounded local scope approved; OMP handles ordinary execution setup). **Repository:** `darizae/flowstead`, private `main`. OMP resolves the current base commit at dispatch. No task may run solely because this file exists.

## Preconditions and order
007 passed app shell + parity baseline and 003 typed API contract. Map uses only authorized/API-public list. Live OpenFreeMap tile connectivity and attribution must be actually checked, not inferred from bundled assets.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: actual 007 route/feature components, typed API and UI state, `docs/design/UI_UX_BASELINE.md` (exact v2 `overviewGrid`, `mapPanel`, `detailGrid` layout), matrix rows, and history API tests. Review the original approved v2 HTML read-only if owner-authorized access exists, never copy sample data/source. Official MapLibre docs and current provider terms.

## Observable result and scope
Add real interactive MapLibre GL JS map using `https://tiles.openfreemap.org/styles/liberty` (subject to current provider availability/terms), visible attribution, fabricated lat/lon markers for only visible Plants, keyboard-accessible marker activation, navigation to selected Plant, fit bounds, safe offline/no-WebGL fallback back to list. On Plant detail show latest four values with quality and a history chart switcher for all four channels, 24h/72h/7d windows, proper x-axis `Plant-local time` incl DST EDT/EST/CDT/CST ambiguity, and correct y-axis titles/units. No misleading interpolation of missing/invalid values.



## Dependencies and allowed file closure
Use `maplibre-gl` 6.x and its stylesheet; chart rendering preferably accessible SVG with existing local CSS/React—do not add a separate charting library unless task approval explicitly covers package, `frontend/package.json`, `package-lock.json`, tests and audit. If a graph package materially reduces code, return scoped choice upstream rather than install unapproved alternative. No geocoding API/key and no real facility coordinates.

Allowed create/edit paths: `frontend/src/**`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts` if needed, `frontend/tests/**`, `frontend/e2e/**`, `frontend/playwright.config.ts` if changed, `justfile`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/design/evidence/**` synthetic browser captures, `README.md`. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Reference-anchored map, charts and browser proof (binding)

- Match prototype `overviewGrid` (list/map side by side on desktop, stacked mobile), `realMap` and `mapFallback`: a dedicated `PlantMap` component owns MapLibre mount/unmount and error fallback; markers derive from exactly the same API-visible Plant list as `PlantList`. Test that the marker button and list row open the same selected Plant and that *foreign Plant IDs have neither marker nor list item*. Keep tile attribution visible; the map must not be a static Florida SVG masquerading as live tiles.
- Create small, typed pure data transformations for `plantHourLabel`, four channel names/units, quality→gap rendering and UTC-to-Plant-IANA DST labels; keep SVG drawing separate from API fetching and page/navigation. Reuse the **approved prototype panel positions, metric tiles, four channel toggles, 24/72/168h controls and observed-forecast style distinction**. Do not introduce a large plot package or global data store by copying `analysis_b`; avoid silent interpolation of missing/invalid hours.
- Playwright **real browser + HTTP gate**: 1330×900 and 390×844 capture, live tile response/render and visible attribution, keyboard-accessible marker activation and list fallback under forced WebGL/network failure, no overflow, all four chart y-axis titles and Plant-local x-axis, Eastern/Central DST repeated-hour labels. Assert interactions and API payloads, not only screenshots. If provider unavailable, label live-tiles UNVERIFIED separately from fallback PASS; record exact SHA, screenshots and deviations in parity matrix. Prepare downloadable SVG chart data that task 010 will rasterize without losing axis labels.

## Test-first acceptance
- `UI-M8-MAP`: real tile render and marker selection from API list; forbidden Plant marker absent; attribution visible; internet/WebGL failure renders list fallback.
- `UT-M8-CHART`: all four charts preserve proper unit, quality flags, 24/72/168h and axis labels; no line joining across missing segments.
- `UT-M8-DST`: UTC fall-back repeated hours have explicit timezone offset/abbreviation; spring-forward gap not invented; Central/Eastern chosen per Plant.
- `UI-M8-PARITY`: desktop 1330px and mobile 390px real browser snapshots/actions, keyboard and zoom; matrix evidence PASS/FAIL/UNVERIFIED.

## Local verification, gates and stopping condition
Run named Vitest chart formatter tests and **`just test-e2e-local` against real local PostgreSQL/API** for browser/Playwright marker+tile and chart interactions at 1330px/390px; run `just frontend-build`, `just test-frontend-unit` and `just audit-frontend` if deps changed. A screenshot's existence is not a passing interactive check.

If OpenFreeMap unavailable, implement documented map-unavailable fallback but leave live tile gate UNVERIFIED; no silent provider substitution without planner review.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. OMP owns review/status automation as a follow-up; do not make it a startup gate. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
