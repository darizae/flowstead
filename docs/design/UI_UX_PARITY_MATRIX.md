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


| Flow / screen + state | Approved baseline and copy/hierarchy | Interaction, navigation and retained state | Size/accessibility & evidence | Status |
| --- | --- | --- | --- | --- |
| Public Plants overview/loading/empty | Header + Plants list + Florida map; all five public fictional Plants; live provider attribution | Select Plant via list or keyboard-accessible map marker; return without stale private data | 1330×900 + 390×844; exact API marker/list identity; live style and deterministic style/WebGL fallback; T-008 receipt and traces above | PASS |
| Authenticated Plants list/map | Same views for assigned Plants only; no inaccessible markers | Switch Plant, safe deep-link and back | Real disjoint-account browser + HTTP proof pending | UNVERIFIED |
| Plant current/latest | Four readings, quality and correct units; capacity omitted because the API does not supply it | All plants back action; no quality silent zero-fill | 1330×900 + 390×844 with no horizontal overflow; `plants-{desktop,mobile}-detail.png` | PASS |
| History 24/72/168h and four channels | Accessible SVG history with explicit channel axis, Plant-local time, units, timezone offsets and visible quality gaps | Switch metric/window while retaining selected Plant; download deterministic SVG with axes and gaps | Eastern/Central DST assertions, 23-point/two-segment M1 gap proof, desktop/mobile screenshots and traces in the T-008 receipt | PASS |
| 12-hour forecast/unavailable | Observed/predicted boundary, gal/h time labels, exactly 12 targets or unavailable | Export only while authorized/available | Repeated DST hour labels unambiguous, no invented predictions; evidence pending | UNVERIFIED |
| CSV/PNG/PDF exports | Visible download actions; PNG axes and PDF polished units/forecast | Actual files opened and inspected, no stale/foreign-Plant download | 1320px PNG, readable PDF 100% zoom; evidence pending | UNVERIFIED |
| Sign-in/invitation/expired/logout | No signup CTA, clear action and useful errors | Session transition clears private rows and restores public mode | Keyboard+mobile storyboard approved; real browser parity pending | UNVERIFIED |
| Forbidden/zero authorized Plants | `Plant not available` / `No plants assigned` | No existence disclosure; useful All plants/signout return | Direct URL plus real API negative case pending | UNVERIFIED |
| Offline/loading/map unavailable | Useful fallback text, functioning API Plants list, no false status or stray markers | Forced style-network and no-WebGL failures preserve list selection without exposing hidden IDs | Deterministic map failure PASS at desktop/mobile; generalized API-offline/loading recovery remains UNVERIFIED | UNVERIFIED |
| IndexedDB persisted public/private UX | Bounded public/individual principal Plant/chart/range prefs and authorized cache; tokens never stored | Reload restores safe preferences; logout/expiry/switch/revocation clears private cache; invalid/expired entry not rendered | Public `IDB-M7-PREF` desktop/mobile browser reload PASS in T-008; private `IDB-M9-ISOLATE` / `IDB-M9-BOUNDS` remain pending T-009 | UNVERIFIED |
| Async forecast lifecycle | Preserve v2 forecast panel and clear queued/processing/failed/unavailable copy; never display fabricated point | Real NATS/JetStream queued→completed state reflects persisted 12-point data; denied public command remains impossible | `MSG-M4B-FLOW`, `MSG-M4B-PAUSE`, `E2E-M12-PATH`, real broker + browser proof pending | UNVERIFIED |
