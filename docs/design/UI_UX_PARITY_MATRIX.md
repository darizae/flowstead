# Flowstead — UI/UX parity matrix

**Session-state storyboard and v2 direction:** OWNER APPROVED 2026-11-17. OMP should produce and inspect real map tiles/marker interaction, an openable PDF and desktop/mobile visual references **during implementation tasks 007–012**, not demand screenshots before task 007. The private original `flowstead_ui_v2.html` remains in Software Planner Kit and is not copied into the app repo. **All parity rows remain UNVERIFIED until checked in a real browser/PDF.** Baseline: [UI_UX_BASELINE.md](UI_UX_BASELINE.md).

## Required evidence protocol for tasks 007–012

The immutable reference is the **owner-approved private v2 HTML** in `software-planner-kit/projects/wastewater-saas-exploration/prototypes/flowstead_ui_v2.html`. `UI_UX_BASELINE.md` records its actual UI hierarchy and style tokens so workers need not copy the prototype or the private `analysis_b.zip` reference into the application repository. The v2 prototype has three illustrative mock Plants; the real application lists **five authorized M1-backed Plants**. Treat that content difference as intended, not a visual deviation.

Each task that affects a matrix row must replace its generic `evidence pending` note with a **specific** reproducible receipt and status. Include: tested final source commit SHA; `just test-e2e-local` or exact Playwright command; desktop **1330×900** and mobile **390×844** viewport; authenticated principal/public mode; actual route/state; screenshot/trace paths under `docs/design/evidence/` for synthetic, scrubbed material; observed keyboard/map/download action and result; visual mismatch or explicit `NO DEVIATION`. Capture meaningful evidence, not decorative images or secrets. Record both **functional** and **visual** outcomes independently as PASS/FAIL/UNVERIFIED; a recorded screenshot does not establish usable interactions.

- In task 007: confirm header, app shell, list/detail/back flow, no unauthorized Plant, no horizontal overflow and visible keyboard focus in a launched browser—not just Vitest/DOM.
- In task 008: verify **live** Florida tiles loaded with attribution, map markers and list selection match the same API Plants; distinguish live provider failure (UNVERIFIED) from passing deterministic offline fallback; inspect real chart text/axes and DST label.
- In task 009: navigate signed-out → invited/test principal → authorized Plant → expired/logout → public; test disjoint principal cache clearing and a forbidden direct deep link using browser + HTTP.
- In task 010: download each CSV/PNG, **parse** CSV and **decode/view** actual PNG with both axes and timezone/units at intended resolution; no private data after principal change.
- In task 011: download and **open** the actual PDF and inspect layout, long names and units at 100% zoom; separately assert parsed text/authorization, not screenshot-only.
- In task 012: rerun integrated public/private/denied/offline/auth/export/map journeys, check 200% zoom and 390px; close every affected matrix row with real evidence or a clearly unresolved gate.

Browser runners use local FastAPI + Docker PostgreSQL seeded with the pinned M1 fixture. Test-only auth simulation is distinct from live Supabase identity verification, which remains separately gated. Do not claim an unavailable map provider, browser runner, visual source or PDF renderer passed. Owner final public-facing presentation acceptance remains a separate release condition, not a pre-007 blocker.

| Flow / screen + state | Approved baseline and copy/hierarchy | Interaction, navigation and retained state | Size/accessibility & evidence | Status |
| --- | --- | --- | --- | --- |
| Public Plants overview/loading/empty | Header + Plants list + Florida map; all five public fictional Plants; `Sign in`, actual attribution | Select Plant via list or map; return without stale private data | 1330px + 390px; keyboard; real tiles and fallback; browser evidence pending | UNVERIFIED |
| Authenticated Plants list/map | Same views for assigned Plants only; no inaccessible markers | Switch Plant, safe deep-link and back | Real disjoint-account browser + HTTP proof pending | UNVERIFIED |
| Plant current/latest | Four readings, quality, units, capacity if actually supplied | All plants back action; no quality silent zero-fill | Mobile no overflow, readable hierarchy; evidence pending | UNVERIFIED |
| History 24/72/168h and four channels | Measurement history chart with explicit both axes/timezone/units | Switch metric/window, preserve selected Plant and valid state | DST fall-back distinction, keyboard and missing gaps; evidence pending | UNVERIFIED |
| 12-hour forecast/unavailable | Observed/predicted boundary, gal/h time labels, exactly 12 targets or unavailable | Export only while authorized/available | Repeated DST hour labels unambiguous, no invented predictions; evidence pending | UNVERIFIED |
| CSV/PNG/PDF exports | Visible download actions; PNG axes and PDF polished units/forecast | Actual files opened and inspected, no stale/foreign-Plant download | 1320px PNG, readable PDF 100% zoom; evidence pending | UNVERIFIED |
| Sign-in/invitation/expired/logout | No signup CTA, clear action and useful errors | Session transition clears private rows and restores public mode | Keyboard+mobile storyboard approved; real browser parity pending | UNVERIFIED |
| Forbidden/zero authorized Plants | `Plant not available` / `No plants assigned` | No existence disclosure; useful All plants/signout return | Direct URL plus real API negative case pending | UNVERIFIED |
| Offline/loading/map unavailable | Useful fallback text, functioning Plants list, no false status | Retry/use list without exposing hidden IDs | Browser throttling/no-WebGL and 390px proof pending | UNVERIFIED |
