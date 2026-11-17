# Flowstead UI/UX baseline — session storyboard approved, live evidence pending

**Status:** Owner approved the v2-derived session-state storyboard and existing v2 visual direction on 2026-11-17. **H-10 remains PARTIALLY OPEN for actual connected-browser tiles/marker navigation, an openable PDF export and approved repo-accessible visual reference** before UI task 007 becomes eligible. This Markdown is not a substitute for a reviewed visual reference.

## User journeys

1. Signed-out public visitor opens **Plants**, sees all five validated fictional M1 Plants through read-only synthetic public endpoints, selects via actual Florida map or list, sees latest four measurements and 24/72/168-hour history, 12-hour forecast and permitted downloads. The dataset is approved for anonymous read-only visibility for all five Plants, but deployment/public exposure still requires separate H-14 authorization. Never display account-specific private fields or pretend to be logged in.
2. Invited operator signs in, sees only assigned Plants, navigates back/forward and switches Plants. Selected Plant/detail and history/forecast state recover from supported deep links if still authorized; never restore another principal's private cache.
3. Loading, empty, map offline, missing/invalid sensor data, unavailable forecast, expired session, zero assigned Plants, forbidden direct URL and logout each have understandable actions. No public signup, administration, compliance, incident or control features.

## Visual hierarchy and copy

Working design: calm white and pale mint surfaces; deep green typography, clear teal interactive actions. Representative source-v2 tokens: ink `#183734`, muted `#526a67`, teal `#087968`, pale mint `#def0e8`, paper `#f5f8f6`, border `#dce7e2`. Use normal legible sizes and clear hierarchy; desktop header + Plants list/map side by side, responsive stacked mobile, then Plant detail with metric summary, history and forecast panels. Typography system font/Inter fallback, legible at 100% desktop and 390px phone; no sideways scroll. No decorative status badges or internal audit/tutorial paragraphs.

User-facing terms: **Plants, Plant list, Florida map, All plants, Measurement history, Influent flow forecast, Download CSV, Download PNG, Download PDF**. Four exact axis labels: `Influent flow (gal/h)`, `Rainfall (in/h)`, `Dissolved oxygen (mg/L)`, `Effluent pH` with x-axis `Plant-local time` and unambiguous Eastern/Central daylight/standard hours. Real MapLibre/OpenFreeMap tiles with accessible markers and attribution; list remains usable when tile provider unavailable. Forecast clearly separates observed vs 12 projected hours, and unavailable means unavailable, never zero.

## Owner-approved session-state storyboard (2026-11-17)

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

## H-10 proof and deviations

The preceding session-state storyboard is **approved as design direction**. Before task 007, ChatGPT must still review an actual browser run of real Florida tiles/markers, an actual downloadable/openable PDF sample, and desktop/mobile visual reference export; record explicit owner acceptance or required corrections. Unverified/deviating UI elements remain blocked. Later UI tasks must update [`UI_UX_PARITY_MATRIX.md`](UI_UX_PARITY_MATRIX.md) with real browser evidence, not just selector tests.
