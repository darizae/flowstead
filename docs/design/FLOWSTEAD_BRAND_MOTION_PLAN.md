# Flowstead brand-mark elastic jump — exact implementation plan

**State:** DESIGN/IMPLEMENTATION PLAN ONLY — **NOT IMPLEMENTED**. Recorded 2026-11-22 on local Flowstead `main` at `c943971`. This document authorizes **no code changes, deployment, dependency upgrade or release** by itself. It translates the owner's request that clicking the **Flowstead icon** should make it perform a short, elastic jump. The existing UI, domain behavior, authentication and unfinished architecture worktrees are to be preserved until an explicitly assigned implementation task.

## 1. Existing implementation and ownership

| Responsibility | Current file / symbol | Verified current behavior |
| --- | --- | --- |
| Header and icon markup | `frontend/src/app/App.tsx` → `FlowsteadApp` → `AppShell` / `AppNavbar` `brand` | Native `<a className="brand" href="/plants">…</a>`, containing decorative `<span className="mark" aria-hidden="true">≈</span>` and visible name `Flowstead`. Link `onClick` calls `event.preventDefault(); goBack()`. |
| Existing mark styling | `frontend/src/app.css` → `.brand`, `.mark` | 34×34px teal rounded tile, glyph centered, default `transform: rotate(-4deg)`; no bounce. |
| Route behavior | `frontend/src/app/App.tsx` → `goBack` and `frontend/src/app/routing.ts` | Clicking the brand navigates to `/plants` and clears selected detail through the current app state. Keyboard activation of the native anchor invokes its click. |
| Unit integration | `frontend/src/app/App.test.tsx`, `frontend/src/test/setup.ts` | React Testing Library navigation/session/authorization tests already exist. |
| Real browser | `frontend/e2e/plants.spec.ts`, `frontend/playwright.config.ts` and `frontend/e2e/run_local.py` | Existing Playwright evidence and owner-approved isolated browser setup. Do not invent a new backend or run external resources merely for this animation. |
| UI contract | `docs/design/UI_UX_BASELINE.md`, `docs/design/UI_UX_PARITY_MATRIX.md` | Brand is a real navbar link; light, calm, accessible coastal typography and no mobile clipping. |

**Dependency boundary:** Flowstead currently consumes the **published** `@darizae/marisma@0.2.0`. The new Marisma motion tokens and `marisma-motion-bounce` utility proposed in [Marisma PR #8](https://github.com/darizae/marisma/pull/8) are **not yet published**. Do not install an unpublished/local source package or change `frontend/package.json`, `frontend/pnpm-lock.yaml` or other lockfiles to implement this plan. The implementation task must verify the exact approved published Marisma version first and decide whether to reuse its utility or implement a small Flowstead-owned keyframe respecting the same timing.

## 2. Observable behavior (acceptance contract)

1. User **clicks or taps** the header brand mark (or activates the containing brand link with **Enter**). The `≈` teal tile compresses slightly, lifts **about 7–9 CSS pixels**, settles with a brief elastic overshoot and returns to the same visually tilted (`-4deg`) resting pose. Approximate duration **620ms**; easing `cubic-bezier(.34,1.56,.64,1)`, matching Marisma's proposed optional bounce family. This is a small one-shot flourish, **not** a perpetual pulse.
2. The existing `goBack()` navigation occurs **immediately**, not after the animation. Clicking from a detail view goes to `/plants`; clicking again on `/plants` replays the jump without refreshing, replacing or navigating to a different route.
3. Only the decorative `.mark` animates. The link's label, hit area, entire header, selected Plant data and focus outline **do not move**. Avoid swapping markup or using `scale` on the entire anchor.
4. Rapid consecutive activation **restarts one animation** from the beginning rather than stacking transforms, leaking timers, or preventing navigation. Repeated keyboard Enter is handled; Space continues to follow native **link**, not button, semantics.
5. Hover alone and keyboard focus alone **do not start** the jump. Link remains accessible as `Flowstead`, decorative glyph remains `aria-hidden="true"`; existing focus-visible outline and contrast remain visible.
6. At `prefers-reduced-motion: reduce`, omit the bounce entirely. The route/action still works and the glyph stays at the resting `rotate(-4deg)`. Also avoid motion in forced-colors when it conflicts with contrast; the mark remains visually identifiable.
7. No audio, vibration, network requests, timers running after unmount, global event handler, auth changes, persistence, tracking event or state leakage. Works under desktop, touch and zoom/mobile at **320px**, **390px**, and **1440px**.

## 3. Minimal implementation sequence (after release/owner approval)

**Change only** `frontend/src/app/App.tsx`, `frontend/src/app.css`, `frontend/src/app/App.test.tsx` and a narrowly scoped `frontend/e2e/plants.spec.ts` addition. Update the UI parity ledger with real evidence. Do not touch the backend, API client, authentication/session, selected-Plant persistence, data/forecast/map/export components, IndexedDB or unrelated refactor worktrees.

1. Add a `useRef<HTMLSpanElement>(null)` for the existing `.mark` and a small, explicit `replayBrandJump()` callback inside `FlowsteadApp`. Keep the `span` itself mounted. In the current brand link's `onClick`, invoke `replayBrandJump()` **before** the existing `goBack()`; retain `event.preventDefault()`. Do not move routing into an animation-end callback.
2. Implementation approach: remove a local `brand-mark--jumping` class from `markRef.current`, force one layout read (e.g. `void mark.offsetWidth`) to allow consecutive-click replay, and add the class again. Handle `onAnimationEnd` on the mark, removing the class only for the named brand animation; this prevents a permanent active flag. Alternatively, use the Web Animations API with a single cancelable `Animation` ref if existing browser support and test harness justify it. Choose **one** approach; do not run a React render per frame. Class replay is preferred for the small scope.
3. In `frontend/src/app.css` keep the existing `.mark` resting rule. Add a local named keyframe (`flowstead-brand-jump`) confined to `.brand-mark--jumping`, with `transform-origin:50% 100%` and keyframes roughly:
   - `0%`: `translateY(0) rotate(-4deg) scale(1)`;
   - `22%`: `translateY(2px) rotate(-4deg) scale(1.06,.90)` (anticipation/compression);
   - `48%`: `translateY(-8px) rotate(-1deg) scale(.96,1.08)` (peak);
   - `75%`: `translateY(1px) rotate(-5deg) scale(1.03,.98)` (settle);
   - `100%`: `translateY(0) rotate(-4deg) scale(1)`.
   Apply a `620ms` animation with the Marisma spring curve `cubic-bezier(.34,1.56,.64,1)`; if this curve overshoots too far on a small mark, tune **only** the keyframe offsets in reviewed browser screenshots. Preserve rounded corners and static text rendering, and use `will-change:transform` **only during** the animation.
4. Add a scoped `@media(prefers-reduced-motion:reduce)` rule so `.brand-mark--jumping` has `animation:none` and `transform:rotate(-4deg)`. Under forced-colors, explicitly verify the mark outline remains visible and color remains semantic; avoid relying on transform to indicate state.
5. Keep the code independent of new global Marisma APIs unless the exact post-review published Marisma version is approved for Flowstead. If a future published utility `.marisma-motion-bounce` is used, verify it retains the `-4deg` resting tilt; otherwise this scoped app-specific keyframe is safer and requires no dependency change.

## 4. Exact acceptance checks

| ID | Test / technique | Pass criteria |
| --- | --- | --- |
| FBM-01 | `frontend/src/app/App.test.tsx`, render signed-out plant overview and click `getByRole('link',{name:'Flowstead'})` | `.mark` receives active class, existing `/plants` navigation and list state remain correct, no new API/auth calls |
| FBM-02 | Same unit harness from a selected Plant detail route | `goBack` clears selection and navigates promptly, animation does not delay state/route update |
| FBM-03 | Two immediate clicks/Enter activations on the brand | Animation restarts; no duplicate nodes, no unfinished timers; cleanup after named `animationend` |
| FBM-04 | Playwright Chromium at 1440×900 | Capture before/peak/settled screenshots; `.mark` vertical movement at peak ~7–9px and returns to original baseline within 620ms (+ scheduling tolerance) |
| FBM-05 | Keyboard Tab to brand then press Enter, and focus-visible check | Accessible name `Flowstead`, functional navigation, focus indicator stays stationary while only glyph moves |
| FBM-06 | `page.emulateMedia({reducedMotion:'reduce'})` | `animation-name:none`, no movement; route still works |
| FBM-07 | Playwright at 390×844 and 320×700 plus 200% zoom | No horizontal document overflow, no clipped glyph or collision with session actions |
| FBM-08 | Forced-colors emulation and disabled-network mode | Decorative mark remains perceivable, nav still works, no unnecessary fetches or reliance on a new dependency |
| FBM-09 | Regression: signed-in operator, signed-out public, sample-data toggle, direct detail URL, logout | Header does not expose private data or alter original session, preference, authorization, map, CSV/PNG/PDF or forecast behavior |

**Suggested local commands**, after owner assigns implementation and verifies the current branch/worktree ownership:

```bash
cd /Users/danie/repos/flowstead
just test-frontend-unit
just frontend-typecheck
just frontend-build
# If existing E2E backend fixtures are available, use the repository's isolated harness:
just test-e2e-local
```

For a focused unit rerun from `frontend/`: `pnpm run test --run src/app/App.test.tsx`. Do not claim E2E PASS without actually running the isolated fixture harness and reviewing its screenshots. Save any new synthetic screenshots only to the established evidence location; do not overwrite unrelated evidence files.

## 5. Integration/order, risks and boundaries

When this plan was originally recorded, the checkout had four *active, unrelated* refactor worktrees; that is historical context, **not a statement about worktrees currently present**. At implementation time, check `git status --short --branch` and `git worktree list`, pick an approved isolated worktree/branch without conflicting ownership, and run relevant local tests. The owner may authorize a merge separately; follow the then-current Flowstead project conventions. **No change to Flowstead frontend code is made as part of this plan.**

**Risk ledger:** CSS animation could override the existing rotated pose; compensate by retaining the tilt in every keyframe. Delaying `goBack` could break route/auth state; keep navigation synchronous. Transforming the anchor could shift a focus ring/hitbox; animate only the decorative mark. Remounting the header could drop the animation; keep the existing `AppNavbar` structure. Repeated clicks could accumulate animations; explicitly restart/clean. Reduced motion must not suppress navigation. A Marisma dependency bump before owner release would violate release boundaries; use only an approved published version.

**Completion criteria for the future implementation:** passing FBM-01–09 as applicable, independently reviewed desktop/mobile/reduced-motion screenshots, unchanged navigation/auth behavior, and an explicit review of whether a Marisma version upgrade was authorized. No Flowstead release is implied.
