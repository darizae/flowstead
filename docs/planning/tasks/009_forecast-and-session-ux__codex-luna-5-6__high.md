# T-009 — 12h forecast charts and invite/session UX

**Status:** DRAFT — auth storyboard approved; blocked by H-10 real map/PDF/visual review and 005/008 (planning-only approval; NO implementation authorization). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
005 JWT/API integration and 008 chart/UI acceptance; H-10 owner approval includes signed-out, invite/sign-in, forbidden Plant, no assigned Plants, session expiry and logout storyboards. Live Supabase project may be unavailable; local browser tests must still run against deterministic test Auth provider.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `frontend/src` auth/navigation/chart code, approved design + parity matrix; API forecast output; session state tests. Only Supabase Auth client SDK docs as needed.

## Observable result and scope
Implement forecast observed-to-predicted line boundary showing 12 actual API target points with `issued_at`, local target labels, `model_version` when useful and explicit unavailable state; no fake forecast computed client-side. Provide invite-only sign-in/access-token refresh/logout states, never a public signup CTA. Browser Supabase Auth client is identity-only; data always from FastAPI; anonymous mode uses strictly separate public endpoints. Client cache is per-principal in memory by default and reset on login/logout/token expiry/account switch; no private IndexedDB persistence; optional bounded IndexedDB for **public-only** synthetic cache may be added only if a measured user benefit is demonstrated later. Protect direct Plant routes but rely on server for final authorization.



## Dependencies and allowed file closure
Authorize `@supabase/supabase-js` current supported 2.x version, `frontend/package.json`/`package-lock.json`, `frontend/.env.example` public URL/publishable-key placeholders only. Public variables must never hold Supabase secret/service-role keys, SQL URI, admin tokens or private source credentials. Test Auth provider seams allow offline scripted login/session failures; deploy requires actual configured project and invitation approval.

Allowed create/edit paths: `frontend/src/**`, `frontend/tests/**`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/.env.example`, `justfile`, `docs/design/UI_UX_PARITY_MATRIX.md`, `README.md`. New dependency installation is authorized **only** when this task itself is approved, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `UT-M9-FORECAST`: exactly 12 future points from API, visible observed/predicted boundary, local/DST axis/gal/h; outage/unavailable/empty handling.
- `UT-M9-SESSIONS`: logged-out mode, valid invite/login, expiry, logout, forbidden/zero-Plant states; no open-signup flow.
- `SEC-M9-CACHE`: auth switch clears all private rows/tokens from in-memory stores; unauthorized URL never renders stale previous Plant.
- `UI-M9-PARITY`: real browser invitation/login/expired/forbidden/logout evidence including keyboard/mobile and owner-approved copy.

## Local verification, gates and stopping condition
Run targeted `npm --prefix frontend test` selectors, typecheck/build and 390px/1330px real browser auth-state journeys. Unit mocks prove local logic only; live Supabase Auth integration is separately task 014.

Do not invite users, change Supabase Auth settings or create hosted service in this UI task.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Normal-chat ChatGPT independently reviews; use `waiting_chat` if unavailable. After corrections, rerun checks on the exact final SHA on Mac. No 24-hour soak.
