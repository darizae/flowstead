# Flowstead — UI/UX baseline

**Design reference:** [flowstead-ui.html](reference/flowstead-ui.html) (approved layout and session-state direction). Tasks 007–012 produce real browser, map and export evidence; unavailable evidence remains UNVERIFIED, not a pre-implementation blocker.

## User journeys

1. Signed-out public visitor opens **Plants**, sees all five validated fictional M1 Plants through read-only synthetic public endpoints, selects via actual Florida map or list, sees latest four measurements and 24/72/168-hour history, 12-hour forecast and permitted downloads. Public deployment requires the separately approved release gate. Never display account-specific private fields or pretend to be logged in.
2. Invited operator signs in, sees only assigned Plants, navigates back/forward and switches Plants. Selected Plant/detail and history/forecast state recover from supported deep links if still authorized; never restore another principal's private cache.
3. Loading, empty, map offline, missing/invalid sensor data, unavailable forecast, expired session, zero assigned Plants, forbidden direct URL and logout each have understandable actions. No public signup, administration, compliance, incident or control features.

## Visual hierarchy and copy

Working design: calm white and pale mint surfaces; deep green typography, clear teal interactive actions. Representative reference tokens: ink `#183734`, muted `#526a67`, teal `#087968`, pale mint `#def0e8`, paper `#f5f8f6`, border `#dce7e2`. Use normal legible sizes and clear hierarchy; desktop header + Plants list/map side by side, responsive stacked mobile, then Plant detail with metric summary, history and forecast panels. Typography system font/Inter fallback, legible at 100% desktop and 390px phone; no sideways scroll. No decorative status badges or internal audit/tutorial paragraphs.

User-facing terms: **Plants, Plant list, Florida map, All plants, Measurement history, Influent flow forecast, Download CSV, Download PNG, Download PDF**. Four exact axis labels: `Influent flow (gal/h)`, `Rainfall (in/h)`, `Dissolved oxygen (mg/L)`, `Effluent pH` with x-axis `Plant-local time` and unambiguous Eastern/Central daylight/standard hours. Real MapLibre/OpenFreeMap tiles with accessible markers and attribution; list remains usable when tile provider unavailable. Forecast clearly separates observed vs 12 projected hours, and unavailable means unavailable, never zero.

## Canonical v2 prototype anatomy and fidelity rules

**Visual source:** [local reference HTML](reference/flowstead-ui.html), which uses three illustrative mock Plants and prototype-only state controls. The working app must instead load all five manifest-validated Plants from the authorized API.

| Prototype region | Implementation invariant / responsive transformation |
| --- | --- |
| `topbar`, `brand`, `topnav` | Approx. 72px white header, brand mark, clear active Plants navigation; accessible focus and signed-out/sign-in state, without creating unapproved navigation |
| `shell`, `pagehead` | Approx. 1340px maximum centered content, calm pale background, descriptive title and restrained metadata; proper 390px wrapping |
| `overviewGrid`, `listPanel`, `mapPanel` | Two side-by-side cards on desktop: Plant list and Florida map; stacked on phone. API list and map must agree on which Plant IDs are visible |
| `realMap`, `mapFallback` | True MapLibre/OpenFreeMap tiles, interactive accessible markers and attribution; on offline/WebGL error keep Plant list and its navigation usable |
| `detail`, `backBtn`, `plantPicker` | Back to All plants, selected Plant name/city/timezone and authorized Plant switcher; state and deep-link validity preserved |
| `metrics` | Four discrete latest tiles, exactly four canonical channels, unit/quality and explicit missing/invalid status; two columns or single flow on narrow screens as warranted |
| `detailGrid`, `historyView`, `channels`, `rangePicker` | History and forecast as adjacent desktop panels, stacked mobile; 24/72/168-hour selections and four measurement toggles; accurate DST-local axes, no misleading interpolation |
| `forecastView`, `historyPng`, `historyCsv`, `forecastPng`, `forecastCsv`, `downloadReport` | 12 separate future hourly targets, observed/predicted distinction, visible downloadable PNG/CSV/PDF actions, disabled on unauthorized/unavailable data; inspect genuine file contents |

**Implementation tokens:** preserve reference `--ink:#183734`, `--ink2:#526a67`, `--teal:#087968`, `--teal-dark:#07584c`, `--mint:#def0e8`, `--line:#dce7e2`, `--paper:#f5f8f6`, plus typography/spacing/line-heights/radii/shadow relationships. Prefer one centrally defined `frontend/src/styles/` or Tailwind 4 theme token source rather than independent magic colors in components. The old prototype's exact pixels are **reference geometry**; retain accessibility, legibility and responsive behavior instead of forcing clipping to match a screenshot.

**Code and test anchors:** The [implementation contract](../planning/IMPLEMENTATION_SPEC.md) owns React/FastAPI module boundaries. Task 007 establishes local Playwright and tasks 007–012 record real 1330px/390px browser parity using [the reference](reference/flowstead-ui.html) and the [parity matrix](UI_UX_PARITY_MATRIX.md). Store only scrubbed synthetic evidence. A static screenshot or DOM-only test is not sufficient.

## Session-state storyboard

| State | Meaningful visible content | Allowed next action |
| --- | --- | --- |
| Public/signed out | `Plants` list/map contains all five fictional M1 Plants in bounded read-only public mode; `Sign in` entry | Choose public Plant or sign in; no signup |
| Invite accepted/sign in | Email/password or approved Supabase invite flow; clear validation, no account-creation link | Sign in; reset recovery only if provider supports invite policy |
| Authenticated with Plants | List/map includes only authorized assigned Plants | Open Plant; choose range/signal; forecast/exports |
| Authenticated, zero assigned | `No plants assigned` | Sign out or contact administrator (do not invent self-service grant) |
| Direct forbidden Plant URL | `Plant not available` without disclosing existence | `All plants` return; no data/cached export shown |
| Expired/revoked session | `Session expired` with existing work cleared | `Sign in` (return target only if still authorized) |
| Sign out | Confirm signed-out public mode; private client cache/tokens cleared | Sign in again or use public demo |
| Map offline/no WebGL | `Map unavailable. Select a plant from the list.` | Use real accessible list |
| Data missing/invalid | Missing cell `—` and `Missing`/`Invalid` quality when useful | Change period/metric; exports preserve flags |
| Forecast unavailable | `Forecast unavailable` | View history; no phantom predictions |

## IndexedDB and asynchronous forecast states

The approved eight-part plan explicitly requires a **bounded per-user IndexedDB cache**; later memory-only language was an erroneous loss, now corrected. Implement typed IndexedDB in `frontend/src/lib/cache/` with schema version, anonymous/public and current-principal partitions, last Plant/channel/history range, bounded sanitized authorized history/forecast cache, TTL and maximum size/entries. Never store tokens or render a private cached response without the **current** FastAPI principal/Plant authorization. Wipe private namespaces on logout/expiry/principal switch/revocation and test actual browser IndexedDB reload/offline/quota/corrupt-state behavior under `IDB-M7-PREF`, `IDB-M9-ISOLATE`, `IDB-M9-BOUNDS`. Keep the v2 visuals; this is implementation behavior, not a new visual theme.

The required NATS/JetStream forecast pipeline may be **queued**, **processing**, **completed**, **failed** or **unavailable**. Preserve the prototype's distinct 12h forecast panel. Show a succinct useful loading/queued/failed state without invented prediction values, permit refresh/poll with bounded backoff, and render only the actual persisted API forecast after completion; do not expose internal broker commands or identifiers in consumer-facing UI. All public access remains read-only. Test actual queued→completed transition with real backend/NATS and Playwright; see `docs/testing/INDEXED_TEST_PLAN.md`.

## Screen and interaction acceptance

The storyboard is the accepted design direction. During tasks 007–012, OMP must produce and check an actual browser run with Florida tiles/markers, an openable/downloadable PDF and desktop/mobile screenshots. Record deviations and fixes against the approved v2 design. Unverified visual parity blocks **final UI acceptance**, not starting implementation. Later UI tasks must update [`UI_UX_PARITY_MATRIX.md`](UI_UX_PARITY_MATRIX.md) with real browser evidence, not just selector tests.
