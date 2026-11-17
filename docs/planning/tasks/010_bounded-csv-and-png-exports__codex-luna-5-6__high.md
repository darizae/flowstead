# T-010 — bounded authorized CSV downloads and chart PNG exports

**Status:** WAITING — prerequisite preflight (bounded local task may run when ordered prerequisites and OMP readiness are verified; external operations remain separately gated). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
008/009 chart/API and principal-switch guards accepted; 005 auth enforced at FastAPI. No bucket/report persistence.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `backend` history/forecast API schemas, `frontend` graph SVG renderer, UI parity matrix and approved v2 export-button locations.

## Observable result and scope
Add Download CSV and Download PNG actions for **each** history and forecast chart. CSV derived from the currently authorized API data only, with exact UTC timestamps, Plant names/IDs as permitted, measurement field, unit, numeric value or empty, quality flag; forecast CSV includes issue time, 12 target UTCs, model version and units. Proper quoting, Content-Disposition/file naming, no spreadsheet formula injection (escape formula-leading values). PNG rasterization of the visible SVG chart must preserve readable **both axes** and labels, source Plant/current selected range/units/timezone, width at least 1320px, and no invisible truncation. Disabled export for unavailable/loading/forbidden state, with no stale private data after logout.



## Dependencies and allowed file closure
Client `Blob`/SVG/canvas can avoid new package; if a rasterizer is necessary, use an explicitly vetted compatible npm package with manifest/lockfile/security scope. Prefer bounded in-browser export; **server CSV endpoints** only if an established scenario requires them, in which case reuse the authenticated API repository policy and add real negative HTTP tests. Never add a general unbounded bulk export endpoint.

Allowed create/edit paths: `frontend/src/**`, `frontend/tests/**`, `frontend/package.json`/`package-lock.json` if package added, `backend/src/flowstead_api/**` and `backend/tests/**` only if server CSV route is added, `justfile`, `docs/design/UI_UX_PARITY_MATRIX.md`, `README.md`. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `UT-M10-CSV`: header/order/quoting/null quality/source/UTC correct; no formula execution, bounded rows, 12 forecast entries.
- `UI-M10-PNG`: downloaded real PNG decodes, has both axes labels/units/time meaning at readable resolution for each chart in desktop and mobile sources.
- `SEC-M10-EXPORT`: denied/logout/expired states disable export and no private stale data persists; if server route is added, foreign Plant returns 404.
- `UI-M10-PARITY`: actions directly visible as approved, no filler/explanatory audit copy.

## Local verification, gates and stopping condition
Use unit tests for formatter, actual Playwright browser to download/inspect CSV and PNG (not filename-only), `just frontend-build`, small backend tests if routes changed. Visual check distinct from green build.

No persistence of PDFs/PNGs/CSVs to cloud or Git.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Independent distinct-agent review at exact PR head is required; until OMP unattended-review acceptance passes, leave `review_ready` blocked. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
