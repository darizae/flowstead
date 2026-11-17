# T-007 — React frontend foundation and Plants navigation

**Status:** DRAFT — owner H-10 UI design gate open (bounded local task may run when ordered prerequisites and OMP readiness are verified; external operations remain separately gated). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
002–006 backend contract accepted; **H-10 owner-reviewed v2 UI baseline and concise auth-state storyboard approved**; committed `docs/design/UI_UX_BASELINE.md` with visual references and populated parity matrix. No UI implementation before approval. Node latest stable non-prerelease `26.13.1` verified 2026-11-17; recheck dispatch and Vite/host package compatibility. Owner decision D-041 already approves anonymous read-only visibility for **all five** manifest-verified fictional M1 Plants; database defaults remain deny until verified M1 import. This does not authorize public hosting or arbitrary Plant IDs.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `docs/design/UI_UX_BASELINE.md`, `docs/design/UI_UX_PARITY_MATRIX.md`, actual API OpenAPI contract, app README and CSS assets only; audit `darizae/marisma` published package metadata before consuming it.

## Observable result and scope
Initialize a single `frontend/` TypeScript React 19 + Vite 8 + Tailwind CSS 4 app (not a new repo), typed API client, accessible list of authorized Plants, empty/loading/error states, responsive app shell, Plants list→Plant detail→back, stable selected Plant handling and theme matching approved v2. Never leak any private Plant from UI defaults. No fake hardcoded plant data in production. Default public mode shows **all five manifest-verified fictional M1 Plants** once the API's approved local public allowlist is enabled; before import/validation, show a safe empty state. Never hardcode Plant IDs, show operator-only records, or infer public deployment authorization.



## Dependencies and allowed file closure
Use Node 26.13.1 pin in `frontend/.node-version` and `package.json.engines`, `react`/`react-dom` 19.x, `vite` 8.x, `@vitejs/plugin-react` 6.x, `typescript` 6.x, `tailwindcss` 4.x, `@tailwindcss/vite` 4.x, `vitest` 4.x, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`; install current compatible patched non-prerelease releases with **npm** into `frontend/package.json` + generated `frontend/package-lock.json` (`npm install`, no hand-edited lockfile). Marisma optional only after verifying a real registry artifact, published license and matching React 19/Tailwind 4 peer API; else use local semantic accessible Tailwind controls **without** vendoring Marisma or touching its repo. Record registry/audit outcome; not a late-time scope expansion. Build a small `frontend/src` data-client seam to test error/timeout and principal changes.

Allowed create/edit paths: `frontend/**` incl lockfile/scripts/assets/test configs, `justfile`, `README.md`, `.gitignore`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/agent/ROUTING.md` row if present. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `UT-M7-NAV`: list renders only API-returned Plants; click/back and inaccessible direct link handle state correctly.
- `UT-M7-FAIL`: empty/unauthorized/loading/offline/API error show useful, non-leaking copy and retry; no hardcoded demo data in shipped build.
- `UI-M7-PARITY`: owner-approved v2 hierarchy/colors/type, 390px + desktop no overflow; keyboard/focus/accessible navigation checked in real browser.
- `SEC-M7-CLIENT`: server-only keys not in bundle; API URL config is explicit; isolated principal transitions clear in-memory cache.

## Local verification, gates and stopping condition
Introduce `just frontend-dev`, `just test-frontend-unit`, `just frontend-build`, `just audit-frontend`. Fast `npm --prefix frontend test -- --run` (or actual Vitest script selector), `npm --prefix frontend run typecheck`, `npm --prefix frontend run build`; `npm --prefix frontend audit --audit-level=moderate` with current registry. Real Playwright browser parity at task gate; do not confuse DOM test with screenshot parity.

If owner-approved baseline images are unavailable to Mac, BLOCK UI work and request ChatGPT to export reviewed visual snapshots; do not invent a new visual direction.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Independent distinct-agent review at exact PR head is required; until OMP unattended-review acceptance passes, leave `review_ready` blocked. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
