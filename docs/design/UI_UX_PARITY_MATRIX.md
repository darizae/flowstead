# Flowstead — UI/UX parity matrix

**Approved reference:** [flowstead-ui.html](reference/flowstead-ui.html) and [UI_UX_BASELINE.md](UI_UX_BASELINE.md). All rows are UNVERIFIED until checked in a real browser/PDF at the stated gate.

## Required evidence protocol for tasks 007–012

The indexed functional/UI cases are maintained in [the test plan](../testing/INDEXED_TEST_PLAN.md) with [the data-equivalence guide](../testing/TEST_DATA_GUIDE.md). Browser runs must produce the locally viewable Playwright HTML report plus an ID-to-test coverage receipt; a screenshot alone cannot establish test coverage. The immutable visual reference is [flowstead-ui.html](reference/flowstead-ui.html). It has three illustrative mock Plants; the real application lists **five authorized M1-backed Plants**. Treat that content difference as intended, not a visual deviation.

Each task that affects a matrix row must replace its generic `evidence pending` note with a **specific** reproducible receipt and status. Include: tested final source commit SHA; `just test-e2e-local` or exact Playwright command; desktop **1330×900** and mobile **390×844** viewport; authenticated principal/public mode; actual route/state; screenshot/trace paths under `docs/design/evidence/` for synthetic, scrubbed material; observed keyboard/map/download action and result; visual mismatch or explicit `NO DEVIATION`. Capture meaningful evidence, not decorative images or secrets. Record both **functional** and **visual** outcomes independently as PASS/FAIL/UNVERIFIED; a recorded screenshot does not establish usable interactions.

- In task 007: confirm header, app shell, list/detail/back flow, no unauthorized Plant, no horizontal overflow and visible keyboard focus in a launched browser—not just Vitest/DOM.
- In task 008: verify **live** Florida tiles loaded with attribution, map markers and list selection match the same API Plants; distinguish live provider failure (UNVERIFIED) from passing deterministic offline fallback; inspect real chart text/axes and DST label.
- In task 009: navigate signed-out → invited/test principal → authorized Plant → expired/logout → public; test disjoint principal cache clearing and a forbidden direct deep link using browser + HTTP.
- In task 010: download each CSV/PNG, **parse** CSV and **decode/view** actual PNG with both axes and timezone/units at intended resolution; no private data after principal change.
- In task 011: download and **open** the actual PDF and inspect layout, long names and units at 100% zoom; separately assert parsed text/authorization, not screenshot-only.
- In task 012: rerun integrated public/private/denied/offline/auth/export/map journeys, check 200% zoom and 390px; close every affected matrix row with real evidence or a clearly unresolved gate.

Browser runners use local FastAPI + Docker PostgreSQL seeded with the pinned M1 fixture. Test-only auth simulation is distinct from live Supabase identity verification, which requires a configured live service. Do not claim an unavailable map provider, browser runner, visual source or PDF renderer passed. Local UI tasks start on assignment; record actual parity evidence, but no presentation sign-off or review receipt is needed before implementing or merging locally.

## T-007 implementation receipt

The React/Vite foundation provides API-backed Plants overview/detail/back routes, explicit loading/empty/error/non-leaking unavailable states, the overview map slot later completed by T-008, four latest measurement cards, and bounded versioned IndexedDB preference storage. The bounded runner is `just test-e2e-local`; it requires `DATABASE_URL`, `FLOWSTEAD_M1_MANIFEST`, and `FLOWSTEAD_M1_DATA`, independently verifies source SHA `ad5c94d1f46e79312a99cb9721f38700f24fdf6b` and telemetry SHA-256 `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`, then records Playwright HTML/report artifacts under `docs/design/evidence/`. The browser test writes `plants-{desktop,mobile}-{overview,detail}.png` and `{desktop,mobile}-ui-m7-parity-public-list-detail-back-deep-link-and-reload.zip`. At the tested T-007 source commit `adf0bb08d4dffabeb0b2c80cd0128587fad93806`, `just test-frontend-unit`, `just frontend-build`, and `just audit-frontend` passed. The Playwright gate was attempted with the verified M1 inputs but the local Chromium framework was incomplete, so its browser result remained UNVERIFIED until the successful T-008 receipt below.

## T-007a Marisma integration receipt

Tested source commit: `4a14ae6b2838b7d0b4e104dbc42dcbc250f42801`. The frontend installs exact `@darizae/marisma@0.2.0`, imports its compiled theme and source, and renders its `AppShell`, `AppNavbar`, `PageHeading`, `Card`, `Button`, `Select`, and `Spinner` primitives under the Reedwater light theme.

| Case | Functional evidence | Visual evidence | Status |
| --- | --- | --- | --- |
| `UT-M7A-MARISMA` | `just test-frontend-unit`, `just frontend-build`, and `just audit-frontend` passed; npm resolved Marisma 0.2.0 with React 19 and Tailwind 4 peers | Not applicable | PASS |
| `UI-M7A-RENDER` | Real local PostgreSQL/FastAPI and managed Chromium loaded five M1 Plants; keyboard Tab focus and Enter opened a Plant, All plants returned, the Plant select was labelled, and four latest metrics rendered | Independent Chromium review found no Marisma regression or overflow | PASS |
| `UI-M7A-PARITY` | 1330×900 and 390×844 overview/detail interactions passed with visible focus and no horizontal overflow | `docs/design/evidence/t007a-{desktop,mobile}-{overview,detail}.png`; NO DEVIATION from the approved hierarchy | PASS |

At the T-007a source commit, `just test-e2e-local` reached Playwright after verified M1 import and the FastAPI runner fix, but the local Chromium framework was incomplete and two repair downloads did not complete. The subsequent T-008 run used an explicit local Chromium executable and passed the retained desktop/mobile public list, detail, back, deep-link, reload and IndexedDB scenario; see the T-008 receipt below.

## T-008 map and history receipt

Tested source commit: `f8825cfd95e6fad6f5164075f589005820501f3a`. `just test-frontend-unit`, `just frontend-build`, `just audit-frontend`, and `just test-e2e-local` passed. The browser gate used a disposable local PostgreSQL database imported from the pinned M1 fixture, local FastAPI, and Chromium at desktop 1330×900 and mobile 390×844.

| Case | Functional evidence | Visual/browser evidence | Status |
| --- | --- | --- | --- |
| `UI-M8-MAP` | Five marker IDs exactly matched the five API Plant IDs; the same API-backed list remained usable; focused marker Enter opened its Plant; forced style-network and WebGL failures removed markers and showed the list fallback | Live OpenFreeMap Liberty style returned 200, interactive tiles rendered with visible OpenFreeMap/OpenMapTiles/OpenStreetMap attribution; `docs/design/evidence/t008-{desktop,mobile}-overview.png`; `{desktop,mobile}-ui-m8-map-*.zip` | PASS |
| `UT-M8-CHART` / `UT-M8-DST` | Half-open 24/72/168-hour requests were anchored one hour after the canonical latest reading; missing, invalid, and absent hours split SVG paths; Eastern/Central fall-back offsets and Central spring-forward labels passed | Four channel axes showed `gal/h`, `in/h`, `mg/L`, and pH; 23 valid M1 readings rendered as two segments without interpolation | PASS |
| `UI-M8-PARITY` | Marisma channel/range controls exercised all four channels and all three windows; responsive SVG had no internal/page overflow; the SVG download contained axes, timezone, gap note, and two quality segments | `docs/design/evidence/t008-{desktop,mobile}-history.png`; `{desktop,mobile}-ui-m8-parity-*.zip`; NO DEVIATION from the approved hierarchy | PASS |

Authenticated Plant filtering remains assigned to T-009 and is not claimed by this public-mode receipt.

## T-009 forecast + session/cache receipt

Tested source commit: `0489dfb363152f29db00dab6f599837600a5161c`. `just test-frontend-unit`, `just frontend-typecheck`, `just frontend-build`, `just audit-frontend`, and `just test-e2e-local` passed (26/26 browser tests, desktop 1330×900 + mobile 390×844). The browser gate used a disposable local PostgreSQL database imported from the pinned M1 fixture, built the deterministic 12-hour forecast for all public Plants, started a throwaway local Supabase-compatible JWKS Auth authority with two seeded disjoint test principals (`test-principal-a` → plant-01/02, `test-principal-b` → plant-03), and ran Chromium against the real local FastAPI via Vite's `/api` proxy. Hosted Supabase identity stays **UNVERIFIED**; every private read here is authorized/denied by the real API using deterministic RS256 test JWTs.

| Case | Functional evidence | Visual/browser evidence | Status |
| --- | --- | --- | --- |
| `UT-M9-FORECAST` | Real API returned `status: available` with exactly 12 gal/h forecast targets; observed→predicted boundary (boundary line + observed + predicted segments); issued/model label; explicit unavailable and empty states; never a client-computed point | `docs/design/evidence/plants-{desktop,mobile}-forecast.png`; `{desktop,mobile}-ut-m9-forecast-*.zip` | PASS |
| `UT-M9-SESSIONS` / `UI-M9-PARITY` | No public signup CTA anywhere; signed-out shows `Sign in`; invited principal A lists only assigned Plants via `/api/v1/plants`; principal B deep-linking to A's Plant shows `Plant not available` and the real API returns 404; expired RS256 JWT returns 401 and the app returns to public with `Session expired`; unassigned `test-principal-c` sees `No plants assigned`; `Sign out` clears identity | `{desktop,mobile}-ut-m9-sessions-*.zip`, `{desktop,mobile}-ui-m9-parity-*.zip`; keyboard/mobile topbar with Sign in/Sign out/Operator identity at 390×844 | PASS* |
| `SEC-M9-CACHE` / `IDB-M9-ISOLATE` | Auth switch clears the prior principal's private rows from IndexedDB and memory; no token/secret claim ever stored; unauthorized deep-link never renders a stale previous Plant; sign out clears all private IndexedDB rows across reload | `{desktop,mobile}-sec-m9-cache-idb-m9-isolate-*.zip` | PASS |
| `IDB-M9-BOUNDS` | Schema v2 per-principal namespaces, forecast snapshots after fresh authorization, per-kind TTL, byte/entry caps, LRU eviction, corrupt/expired row recovery, and IndexedDB-unavailable memory fallback | Unit-only (`frontend/src/lib/cache/preferences.test.ts`) | PASS |

`*` Deterministic local test-only auth. Live hosted identity/invitation is covered by task 014 and remains UNVERIFIED here.

## T-010 bounded CSV/PNG export receipt

Verified on the focused T-010 task branch before commit. `npm --prefix frontend test -- --run src/lib/exports/csv.test.ts src/lib/exports/svgToPng.test.ts src/features/forecast/ForecastChart.test.tsx`, `just frontend-build`, and `just test-e2e-local` passed; the browser gate ran 30 tests against disposable PostgreSQL, the canonical M1 fixture, real FastAPI, and Chromium at 1330×900 and 390×844. The final task commit SHA is recorded in Git history and the completion report.

| Case | Functional evidence | Visual/browser evidence | Status |
| --- | --- | --- | --- |
| `UT-M10-CSV` | Focused Vitest asserts headers/order, UTC normalization, quoted empty values, quality preservation, formula-leading string escaping, finite/bounded rows, and exactly 12 forecast targets | Not applicable | PASS |
| `UI-M10-PNG` / `UI-M10-PARITY` | Playwright parsed both CSV downloads and decoded PNG signatures/IHDR dimensions; each PNG was at least 1320px wide. The adapter uniformly scales the same rendered SVG and keeps complete titles, legends, axes, units and Plant timezone. | `docs/design/evidence/plants-{desktop,mobile}-ui-m10-exports.png` and matching Playwright traces. Locally saved synthetic export PNGs were opened: desktop/mobile history and forecast axes, first/middle/last Plant-local labels, full title and legend were readable with no clipping; NO DEVIATION. | PASS |
| `SEC-M10-EXPORT` | Real private-principal browser flow proved logout removes prior export controls; asynchronous generation is keyed to Plant/range/channel/issuance and transient Blob URLs are revoked. | Desktop/mobile private auth traces; no exported record persisted to Git or cloud. | PASS |


| Flow / screen + state | Approved baseline and copy/hierarchy | Interaction, navigation and retained state | Size/accessibility & evidence | Status |
| --- | --- | --- | --- | --- |
| Public Plants overview/loading/empty | Header + Plants list + Florida map; all five public fictional Plants; live provider attribution | Select Plant via list or keyboard-accessible map marker; return without stale private data | 1330×900 + 390×844; exact API marker/list identity; live style and deterministic style/WebGL fallback; T-008 receipt and traces above | PASS |
| Authenticated Plants list/map | Same views for assigned Plants only; no inaccessible markers | Switch Plant, safe deep-link and back | Real disjoint-account browser + HTTP proof pending | UNVERIFIED |
| Plant current/latest | Four readings, quality and correct units; capacity omitted because the API does not supply it | All plants back action; no quality silent zero-fill | 1330×900 + 390×844 with no horizontal overflow; `plants-{desktop,mobile}-detail.png` | PASS |
| History 24/72/168h and four channels | Accessible SVG history with explicit channel axis, Plant-local time, units, timezone offsets and visible quality gaps | Switch metric/window while retaining selected Plant; bounded Download CSV and Download PNG actions use the currently authorized response | T-008 chart evidence plus T-010 parsed CSV, decoded/opened >=1320px PNG and desktop/mobile export screenshots/traces | PASS |
| 12-hour forecast/unavailable | Observed/predicted boundary, gal/h time labels, exactly 12 targets or unavailable | CSV/PNG controls enable only for authorized available forecasts with exactly 12 API targets; narrow charts retain readable first/middle/last labels | T-009 forecast evidence plus T-010 parsed 12-row CSV and decoded/opened desktop/mobile PNG | PASS |
| CSV/PNG/PDF exports | Visible CSV/PNG actions in each history and forecast card footer; PNG rasterizes the rendered SVG at >=1320px with axes, title, legend, units and Plant timezone; PDF remains future scope | Actual CSV files parsed, PNGs decoded and opened, and logout removed private controls; no persistent export records | T-010 screenshots/traces above; CSV/PNG functional and visual checks PASS. PDF remains assigned to T-011. | PASS* |
| Sign-in/invitation/expired/logout | No signup CTA, clear action and useful errors | Session transition clears private rows and restores public mode | T-009: no signup CTA, Sign in / Operator identity / Sign out in the topbar at 1330×900 and 390×844; signed-out, invited principal A, B-denied-404, expired-401, sign-out and zero-Plants scenarios against the real local FastAPI; hosted Supabase identity stays UNVERIFIED; see T-009 receipt | PASS* |
| Forbidden/zero authorized Plants | `Plant not available` / `No plants assigned` | No existence disclosure; useful All plants/signout return | T-009: principal B deep-link to A's Plant yields `Plant not available` and a real API 404; an unassigned principal-c sees `No plants assigned`; see T-009 receipt | PASS |
| Offline/loading/map unavailable | Useful fallback text, functioning API Plants list, no false status or stray markers | Forced style-network and no-WebGL failures preserve list selection without exposing hidden IDs | Deterministic map failure PASS at desktop/mobile; generalized API-offline/loading recovery remains UNVERIFIED | UNVERIFIED |
| IndexedDB persisted public/private UX | Bounded public/individual principal Plant/chart/range prefs and authorized cache; tokens never stored | Reload restores safe preferences; logout/expiry/switch/revocation clears private cache; invalid/expired entry not rendered | T-009: schema-v2 per-principal cache with forecast snapshots, TTL/byte/entry caps and LRU eviction; `IDB-M9-ISOLATE`/`IDB-M9-BOUNDS` unit tests + browser sign-out clears all private rows across reload; tokens never stored; see T-009 receipt | PASS |
| Async forecast lifecycle | Preserve v2 forecast panel and clear queued/processing/failed/unavailable copy; never display fabricated point | Real NATS/JetStream queued→completed state reflects persisted 12-point data; denied public command remains impossible | `MSG-M4B-FLOW`, `MSG-M4B-PAUSE`, `E2E-M12-PATH`, real broker + browser proof pending | UNVERIFIED |
