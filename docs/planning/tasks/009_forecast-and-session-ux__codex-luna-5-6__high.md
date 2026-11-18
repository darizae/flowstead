# T-009 — 12h forecast charts and invite/session UX

**Execution:** Start when explicitly assigned; no WAITING/READY/approval prerequisite. **Repository:** `darizae/flowstead`, local `main` checkout.

## Existing implementation and technical context
Use existing JWT/session, UI, forecast and chart interfaces as source context. Complete local browser scenarios even if hosted Supabase is unavailable; no prior design or review approval receipt is required.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: existing route/feature/hook/typed-API/IndexedDB boundaries, v2 UI baseline and parity matrix; `docs/testing/INDEXED_TEST_PLAN.md` and `docs/testing/TEST_DATA_GUIDE.md`; actual forecast OpenAPI data; session fixture and existing authorization tests. Use the owner-approved invitation/signed-out/forbidden/expired/logout storyboard, not a copied enterprise auth application. Only Supabase Auth client SDK docs as needed.

## Observable result and scope
Implement forecast observed-to-predicted line boundary showing 12 actual API target points with `issued_at`, local target labels, `model_version` when useful and explicit unavailable state; no fake forecast computed client-side. Provide invite-only sign-in/access-token refresh/logout states, never a public signup CTA. Browser Supabase Auth client is identity-only; data always from FastAPI; anonymous mode uses strictly separate public endpoints. **the current message/migration/cache architecture requires IndexedDB** for bounded authorized per-principal UX cache, not public-only or deferred: persist last Plant/chart/window selections plus only small sanitized 24/72/168h/forecast API response snapshots after fresh verified FastAPI authorization; namespaces are public vs authenticated principal ID, with schema version, TTL, entry/byte caps, runtime validation, LRU/eviction and automatic full private cache wipe on logout, expiry, account switch, revoked Plant 401/403/404 and invalid schema. Do not store tokens, secret claims or use a stale private snapshot when offline before reauthorization. Provide safe in-memory fallback when IndexedDB is unavailable. Protect direct Plant routes but rely on server for final authorization.



## Dependencies and allowed file closure
Authorize `@supabase/supabase-js` current supported 2.x version, `frontend/package.json`/`package-lock.json`, `frontend/.env.example` public URL/publishable-key placeholders only. Public variables must never hold Supabase secret/service-role keys, SQL URI, admin tokens or private source credentials. Test Auth provider seams allow offline scripted login/session failures; hosted login validation requires real configured Supabase project and invitation identities.

Allowed create/edit paths: `frontend/src/**`, `frontend/tests/**`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/.env.example`, `frontend/e2e/**`, `frontend/playwright.config.ts` if changed, `justfile`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/design/evidence/**` redacted synthetic screenshots, `README.md`. Necessary package, manifest, lockfile, fixture, command and test updates in the named owning paths are in scope when this task is assigned. Choose supported compatible versions, generate lockfiles with the package manager, audit dependencies and verify locally. Do not request separate permission for predictable dependency setup; keep changes related to this task. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Reference-anchored state design and real browser checks (binding)

**Read-only local source root:** `/Users/danie/repos/repomix-static-reconstructor/reconstructed/analysis_b/apps/frontend/src/`. Inspect only applicable auth/session hooks, route guards, state/cache/service and IndexedDB boundaries; verify child paths on the Mac. Do not copy code, bring over the reference auth service or import its dependencies. Flowstead's own principal-scoped authorization and cache rules are binding.

- Apply the `analysis_b` **concepts**, not its code: keep a typed `auth` boundary, narrow route-level session checks, small data-fetch hooks and versioned **IndexedDB state explicitly scoped to each authenticated principal/public visibility**. Adapt its small IndexedDB persistence/validation pattern for selected Plant/chart/window and bounded authorized response snapshots; do not port unrelated analysis-version stores, global workspaces or an auth microservice. Revalidate allowed Plant IDs from FastAPI after session transitions; a previous principal's Plant, forecast or report must never briefly render while new identity loads.
- Follow v2's `detailGrid` and `forecastView`: the forecast remains a separate panel, uses **only 12 real API target hours** with observed/predicted boundary, issue time/model label and clear unavailability; no client-side invented forecast. Page navigation and chart styles match the approved v2; for signed-out/invited/zero-Plants/forbidden/expired/logout use the approved additional storyboard, not prototype-only fake state controls.
- Reuse the Playwright harness from 007. Browser scenarios at 1330×900 and 390×844: public view; test principal A assigned a Plant; principal B denied A by actual API; expired session; sign out clears all private caches; back/deep links; zero-Plants; keyboard/focus and sensitive state not reappearing after a history/forecast fetch race. Capture redacted synthetic screenshot/trace and exact HTTP results; assert negative 401/404 responses. Keep hosted real Auth integration UNVERIFIED until separately approved.

## Test-first acceptance
- `UT-M9-FORECAST`: exactly 12 future points from API, visible observed/predicted boundary, local/DST axis/gal/h; outage/unavailable/empty handling.
- `UT-M9-SESSIONS`: logged-out mode, valid invite/login, expiry, logout, forbidden/zero-Plant states; no open-signup flow.
- `SEC-M9-CACHE`: auth switch clears all private rows from memory **and IndexedDB**; no tokens stored; unauthorized URL never renders stale previous Plant.
- `IDB-M9-ISOLATE`: real browser IndexedDB partitions A/B/public; after logout, expiry, switch or revoked Plant, clear private records and never render stale data even across reload/offline.
- `IDB-M9-BOUNDS`: TTL, size/entry caps, schema-corruption recovery, quota errors and missing IndexedDB fail closed and preserve usable public UI without private leakage.
- `UI-M9-PARITY`: real browser invitation/login/expired/forbidden/logout evidence including keyboard/mobile and owner-approved copy.

## Local verification and completion
Run targeted `npm --prefix frontend test` selectors, typecheck/build and **`just test-e2e-local`** with 390px/1330px real browser auth-state journeys against local FastAPI/PostgreSQL (deterministic test-only principal fixture); do not claim mock Auth verifies hosted Supabase. Unit mocks prove local logic only; live Supabase Auth integration is separately task 014.

Do not invite users, change Supabase Auth settings or create hosted service in this UI task.



## Local completion

Implement immediately when this file is explicitly assigned. Run the stated targeted local tests and fix failures in task-owned source and tests; record observed checks and any environment limitations. Make a focused local task-branch commit and **merge into local `main`** after resolving code/test failures and Git conflicts. Record the resulting SHA and changes. **Do not push**. Independent ChatGPT review, PR receipts, predecessor acceptance, task index statuses and extra owner authorization are **not prerequisites** to starting, committing or locally merging this task. If a real external resource is absent, finish all feasible local work and report what could not be exercised without inventing hosted results.
