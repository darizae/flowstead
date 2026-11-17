# T-008 — MapLibre Plants map and four monitoring charts

**Status:** DRAFT — blocked by H-10 and 007 (planning-only approval; NO implementation authorization). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
007 passed app shell + parity baseline and 003 typed API contract. Map uses only authorized/API-public list. Live OpenFreeMap tile connectivity and attribution must be actually checked, not inferred from bundled assets.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `frontend/src` App/list/page components, `docs/design/UI_UX_BASELINE.md`, matrix rows and history API tests; official MapLibre current docs and map provider terms.

## Observable result and scope
Add real interactive MapLibre GL JS map using `https://tiles.openfreemap.org/styles/liberty` (subject to current provider availability/terms), visible attribution, fabricated lat/lon markers for only visible Plants, keyboard-accessible marker activation, navigation to selected Plant, fit bounds, safe offline/no-WebGL fallback back to list. On Plant detail show latest four values with quality and a history chart switcher for all four channels, 24h/72h/7d windows, proper x-axis `Plant-local time` incl DST EDT/EST/CDT/CST ambiguity, and correct y-axis titles/units. No misleading interpolation of missing/invalid values.



## Dependencies and allowed file closure
Use `maplibre-gl` 6.x and its stylesheet; chart rendering preferably accessible SVG with existing local CSS/React—do not add a separate charting library unless task approval explicitly covers package, `frontend/package.json`, `package-lock.json`, tests and audit. If a graph package materially reduces code, return scoped choice upstream rather than install unapproved alternative. No geocoding API/key and no real facility coordinates.

Allowed create/edit paths: `frontend/src/**`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts` if needed, `frontend/tests/**`, `justfile`, `docs/design/UI_UX_PARITY_MATRIX.md`, `README.md`. New dependency installation is authorized **only** when this task itself is approved, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `UI-M8-MAP`: real tile render and marker selection from API list; forbidden Plant marker absent; attribution visible; internet/WebGL failure renders list fallback.
- `UT-M8-CHART`: all four charts preserve proper unit, quality flags, 24/72/168h and axis labels; no line joining across missing segments.
- `UT-M8-DST`: UTC fall-back repeated hours have explicit timezone offset/abbreviation; spring-forward gap not invented; Central/Eastern chosen per Plant.
- `UI-M8-PARITY`: desktop 1330px and mobile 390px real browser snapshots/actions, keyboard and zoom; matrix evidence PASS/FAIL/UNVERIFIED.

## Local verification, gates and stopping condition
Run named Vitest chart formatter tests and actual browser/Playwright marker+tile and chart interactions; run `just frontend-build`, `just test-frontend-unit` and `just audit-frontend` if deps changed. A screenshot's existence is not a passing interactive check.

If OpenFreeMap unavailable, implement documented map-unavailable fallback but leave live tile gate UNVERIFIED; no silent provider substitution without planner review.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Normal-chat ChatGPT independently reviews; use `waiting_chat` if unavailable. After corrections, rerun checks on the exact final SHA on Mac. No 24-hour soak.
