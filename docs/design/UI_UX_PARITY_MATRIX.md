# Flowstead — UI/UX parity matrix

**Session-state storyboard and v2 direction:** OWNER APPROVED 2026-11-17. OMP should produce and inspect real map tiles/marker interaction, an openable PDF and desktop/mobile visual references **during implementation tasks 007–012**, not demand screenshots before task 007. The private original `flowstead_ui_v2.html` remains in Software Planner Kit and is not copied into the app repo. **All parity rows remain UNVERIFIED until checked in a real browser/PDF.** Baseline: [UI_UX_BASELINE.md](UI_UX_BASELINE.md).

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
