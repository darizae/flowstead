# T-009 — 12h forecast charts and invite/session UX

**Status:** WAITING — 005/008; approved auth storyboard (bounded local scope approved; OMP handles ordinary execution setup). **Repository:** `darizae/flowstead`, private `main`. OMP resolves the current base commit at dispatch. No task may run solely because this file exists.

## Preconditions and order
005 JWT/API integration and 008 chart/UI acceptance; H-10 owner approval includes signed-out, invite/sign-in, forbidden Plant, no assigned Plants, session expiry and logout storyboards. Live Supabase project may be unavailable; local browser tests must still run against deterministic test Auth provider.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: existing route/feature/hook/typed-API boundaries, v2 UI baseline and parity matrix; actual forecast OpenAPI data; session fixture and existing authorization tests. Use the owner-approved invitation/signed-out/forbidden/expired/logout storyboard, not a copied enterprise auth application. Only Supabase Auth client SDK docs as needed.

## Observable result and scope
Implement forecast observed-to-predicted line boundary showing 12 actual API target points with `issued_at`, local target labels, `model_version` when useful and explicit unavailable state; no fake forecast computed client-side. Provide invite-only sign-in/access-token refresh/logout states, never a public signup CTA. Browser Supabase Auth client is identity-only; data always from FastAPI; anonymous mode uses strictly separate public endpoints. Client cache is per-principal in memory by default and reset on login/logout/token expiry/account switch; no private IndexedDB persistence; optional bounded IndexedDB for **public-only** synthetic cache may be added only if a measured user benefit is demonstrated later. Protect direct Plant routes but rely on server for final authorization.



## Dependencies and allowed file closure
Authorize `@supabase/supabase-js` current supported 2.x version, `frontend/package.json`/`package-lock.json`, `frontend/.env.example` public URL/publishable-key placeholders only. Public variables must never hold Supabase secret/service-role keys, SQL URI, admin tokens or private source credentials. Test Auth provider seams allow offline scripted login/session failures; deploy requires actual configured project and invitation approval.

Allowed create/edit paths: `frontend/src/**`, `frontend/tests/**`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/.env.example`, `frontend/e2e/**`, `frontend/playwright.config.ts` if changed, `justfile`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/design/evidence/**` redacted synthetic screenshots, `README.md`. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Reference-anchored state design and real browser checks (binding)

- Apply the `analysis_b` **concepts**, not its code: keep a typed `auth` boundary, narrow route-level session checks, small data-fetch hooks and per-principal/visibility-scoped in-memory state. Do not port its persisted IndexedDB analysis/version state, global stores or auth-service architecture. Revalidate allowed Plant IDs from FastAPI after session transitions; a previous principal's Plant, forecast or report must never briefly render while new identity loads.
- Follow v2's `detailGrid` and `forecastView`: the forecast remains a separate panel, uses **only 12 real API target hours** with observed/predicted boundary, issue time/model label and clear unavailability; no client-side invented forecast. Page navigation and chart styles match the approved v2; for signed-out/invited/zero-Plants/forbidden/expired/logout use the approved additional storyboard, not prototype-only fake state controls.
- Reuse the Playwright harness from 007. Browser scenarios at 1330×900 and 390×844: public view; test principal A assigned a Plant; principal B denied A by actual API; expired session; sign out clears all private caches; back/deep links; zero-Plants; keyboard/focus and sensitive state not reappearing after a history/forecast fetch race. Capture redacted synthetic screenshot/trace and exact HTTP results; assert negative 401/404 responses. Keep hosted real Auth integration UNVERIFIED until separately approved.

## Test-first acceptance
- `UT-M9-FORECAST`: exactly 12 future points from API, visible observed/predicted boundary, local/DST axis/gal/h; outage/unavailable/empty handling.
- `UT-M9-SESSIONS`: logged-out mode, valid invite/login, expiry, logout, forbidden/zero-Plant states; no open-signup flow.
- `SEC-M9-CACHE`: auth switch clears all private rows/tokens from in-memory stores; unauthorized URL never renders stale previous Plant.
- `UI-M9-PARITY`: real browser invitation/login/expired/forbidden/logout evidence including keyboard/mobile and owner-approved copy.

## Local verification, gates and stopping condition
Run targeted `npm --prefix frontend test` selectors, typecheck/build and **`just test-e2e-local`** with 390px/1330px real browser auth-state journeys against local FastAPI/PostgreSQL (deterministic test-only principal fixture); do not claim mock Auth verifies hosted Supabase. Unit mocks prove local logic only; live Supabase Auth integration is separately task 014.

Do not invite users, change Supabase Auth settings or create hosted service in this UI task.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. OMP owns review/status automation as a follow-up; do not make it a startup gate. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
