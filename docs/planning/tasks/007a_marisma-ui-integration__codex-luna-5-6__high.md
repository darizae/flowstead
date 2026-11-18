# T-007a — Integrate Marisma into the existing Flowstead frontend

**Execution:** Start immediately when assigned, using the checkout where T-007 was completed. **Repository:** `darizae/flowstead`. This is an engineering implementation task, not another design review or a rerun of T-007.

## Existing state and initial read set

The owner reports T-007 complete locally. On 2026-11-18 the GitHub `main` branch did not yet contain `frontend/`; that remote observation does **not** mean the local work is absent. Inspect the actual local checkout first and preserve its files and commits. Incorporate the GitHub task-spec update into the local branch with normal non-destructive Git operations, not a reset/force-push.

Read root `AGENTS.md`, this task, the UI portion of `docs/planning/IMPLEMENTATION_SPEC.md`, `docs/design/UI_UX_BASELINE.md`, the local HTML reference, `docs/design/UI_UX_PARITY_MATRIX.md`, root `justfile`, current `frontend/package.json` and `frontend/package-lock.json`, and the relevant frontend source and tests. Use the public Marisma package documentation: https://github.com/darizae/marisma and https://www.npmjs.com/package/@darizae/marisma.

## Required implementation

**Use Marisma.** `@darizae/marisma` is Flowstead's mandatory reusable React/Tailwind UI library, not an optional dependency. Check whether the completed T-007 frontend already installs and actually renders Marisma components. If yes, retain the integration and correct any gaps. Otherwise install the published `@darizae/marisma@0.2.0` into `frontend/package.json` using npm and generate the lockfile through npm. Confirm the installed artifact and its React 19 / Tailwind CSS 4 peer dependencies using the package manager; do not confuse a GitHub source commit with an npm artifact.

Wire Marisma's compiled public exports and the required Tailwind 4 stylesheet setup into the existing Vite frontend. In the application's real CSS entry, import Tailwind and `@darizae/marisma/theme.css`, and configure the appropriate `@source` path for the package's built JavaScript as described by Marisma (adjust the relative path for the actual CSS location). Set the Marisma accent/mode on the app's owning DOM subtree (begin with `data-marisma-accent="reedwater"` and `data-marisma-mode="light"`) and preserve Flowstead's approved v2 white/pale-mint/teal visual direction through app-owned layout and token adjustments.

**Actually use the library's React components in rendered Flowstead screens**, not merely as a package dependency: replace duplicate generic buttons, cards/surfaces, form fields, dialogs, selection and shell controls with suitable Marisma exports. Prefer its available `Button`, `Card` slots, `Input`, `Select`, `Dialog`, `AppShell`, `PageHeading` and other relevant published components wherever they fit the approved screens. Keep feature-specific Plant rows, MapLibre, charts, forecasts, data/API/auth and IndexedDB in Flowstead; do not invent generic wrappers that duplicate Marisma primitives. Do not vendor/fork Marisma or change the `darizae/marisma` repository.

Reuse the current T-007 routes/state/cache and approved v2 prototype; do not rebuild a second frontend or change product behavior merely to consume components. Fix real styling/keyboard/responsive regressions produced by adoption.

## Allowed changes

`frontend/**` (including source, tests, npm manifest/lockfile and CSS), `justfile` if commands change, `README.md` for real installed package/setup, `docs/design/UI_UX_PARITY_MATRIX.md` and scrubbed synthetic `docs/design/evidence/**`. Keep changes limited to the library integration and associated tests and documentation.

## Observable local acceptance

- `UT-M7A-MARISMA`: installed package is present in the npm manifest and lockfile, version/peer compatibility is checked, and actual frontend React source imports public `@darizae/marisma` exports; no vendored copy or substitute component framework.
- `UI-M7A-RENDER`: the real browser renders Marisma controls with its compiled theme/CSS, including useful loading/disabled/focus/keyboard states, in the existing Plants list/detail flows; no styling regression or broken navigation.
- `UI-M7A-PARITY`: at 1330×900 and 390×844, compare app shell, list/detail/back, cards and controls to the approved reference; record real browser interactions, screenshots and deviations in the existing UI/UX parity matrix.

Use existing `just test-frontend-unit`, `just frontend-build`, `just test-e2e-local` and `just audit-frontend` when available; otherwise run the corresponding real frontend scripts and update `justfile` only as needed. Exercise the actual rendered app; a static import assertion or a green build alone is insufficient. Do the implementation without additional administrative approval checks. If an actual tool/registry/runtime fails, record what was attempted and the technical failure rather than silently replacing Marisma.

## Completion

Produce one focused local implementation commit following the repository's existing Git workflow, with the actual commands/results and final SHA. Preserve the completed local T-007 work. Do not force-reset or automatically push a developer's unpushed frontend commits. T-008 and later frontend tasks must continue using the installed Marisma components and theme.
