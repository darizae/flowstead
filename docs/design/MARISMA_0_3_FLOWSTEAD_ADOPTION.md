# Flowstead adoption of Marisma 0.3.0 — November 22, 2026

## Delivered

- Upgraded the published `@darizae/marisma` dependency from 0.2.0 to 0.3.0. The existing navbar, buttons, cards, selects and alerts inherit the library's updated, reduced-motion-aware interaction styling.
- Standardized overview API errors with the Marisma `Alert` component; removed the inherited orange error panel.
- Added five-per-page plant list navigation while keeping the map based on all accessible plants, so pagination never hides map coverage.
- Replaced the hard-coded overview label `Florida map` with `Map View`; real-map bounds are still computed from actual plant coordinates.
- Added hover/focus plant-preview details to real MapLibre markers and mock-map pins; clicking a marker still selects its plant.
- Added chart information tooltips via Marisma components, improved detail card spacing and clarified export navigation.
- Added a short, restartable brand-mark elastic jump with an accessible reduced-motion fallback.

## Next daily-use workflows to explore

1. **Shift-start overview:** a compact Marisma metric-and-status strip showing how many plants have fresh measurements, stale feeds or missing channels; selecting an affected status would filter the overview list and map together. This requires explicit product/API semantics for freshness and should not fabricate status from missing data.
2. **Forecast request feedback:** use Marisma 0.3's accessible, stackable `ToastProvider` for requested/queued/completed/failed forecast operations, connected to actual server response states rather than assumed success. Include a direct action to return to the affected plant.
3. **Comparison workspace:** add a Marisma tabbed or drawer-based comparison between selected authorized plants, supporting synchronized measurements and history ranges. Preserve server-side plant authorization and never persist private measurements into public scope.
4. **Plant quick actions:** an accessible menu opened from list/map markers with `Open details`, `View history` and `View forecast` actions; add hover/focus intent, but avoid a menu that obscures map controls.
5. **Export confirmations:** show a Marisma notification only after the browser actually initiates the relevant CSV/PNG/PDF operation, with appropriate failure handling and no false claims of a completed file download.
6. **Progressive chart discovery:** opt-in `marisma-motion-rise` for freshly arrived data summaries, and `marisma-motion-pulse` only for meaningful status transitions; never animate every polling update. Respect reduced-motion preferences and avoid layout shift.

## Verification and constraints

Local frontend typecheck, lint, 52 unit tests, production build and Prettier check passed. A browser visual audit against `/Users/danie/Desktop/flowstead_diagnosis/Screenshot 2026-11-22 at 10.26.10.png` remains outstanding because macOS denied access to Desktop from the local connector. Manual Safari, screen-reader and physical mobile checks were not run. MapLibre remains a large lazy-loaded bundle, and its JavaScript test environment logs expected canvas-implementation warnings. No backend or authorization contract was changed.
