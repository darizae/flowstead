# T-012 — local MVP security, UX and recovery acceptance

**Status:** WAITING — prerequisite preflight (bounded local scope approved; OMP handles ordinary execution setup). **Repository:** `darizae/flowstead`, private `main`. OMP resolves the current base commit at dispatch. No task may run solely because this file exists.

## Preconditions and order
007–011 implemented and integrated; backend 002–005 functioning with local PostgreSQL, deterministic offline JWKS/test principals. Owner the UI acceptance gate visual direction approved and export sample available. Hosted Auth and public deployment are separate future gates.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: actual existing FastAPI models/auth/database and feature services; frontend routes/features/hooks/typed API and IndexedDB cache; `docs/testing/INDEXED_TEST_PLAN.md`, `docs/testing/TEST_DATA_GUIDE.md`, `docs/design/UI_UX_BASELINE.md`, complete UI/UX matrix and **source-derived approved v2 tokens/layout**; synthetic samples under `docs/design/evidence/`; real Compose/justfile and runtime locks. Do not copy any private reference archive into implementation repo. Read original approved prototype only by authorized read-only access, if available.

## Observable result and scope
Run a reproducible local full-journey gate (not ordinary edit loop): database rebuild from pinned generator/checksummed manifest, API start, frontend start, two disjoint operator-private sessions plus public read-only access to all five validated fictional Plants, map/list/history/forecast/download, logout/session expiry, no JS error overflow and proper mobile/desktop accessibility. Audit direct+transitive Python and npm dependencies, runtime pins, CSP/CORS/cache/referrer policy, SQL parameterization, JWT negative paths, unbounded request caps, rate-limit/failure policy under local harness (implement a bounded single-process server-side limiter with trusted-proxy handling and explicit denial semantics for the initial single-instance demo; multi-instance deployment remains a separate approval gate), cleanup/reseed. Fix defects in owning modules only, record measurements and explicit remaining live provider/cloud limitations.



## Dependencies and allowed file closure
Use existing test libraries and Playwright (if absent, authorize compatible `@playwright/test` dev dependency in `frontend/package.json` + generated lockfile; browser binaries installed only on Mac). No optional cloud CI/soak. If a proposed dependency security remediation requires major-version updates, authorize within approved task only after planner confirms impact; don't silently suppress advisories.

Allowed create/edit paths: `backend/**`, `frontend/**`, `compose.yml`, `justfile`, `README.md`, `.env.example`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/design/evidence/**` scrubbed synthetic screenshots/media/trace receipts, `AGENTS.md` directly affected rows and checked docs. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Integrated reference-pattern and prototype fidelity gate (binding)

- Audit **actual implemented code boundaries against the approved architecture**: Python routes thin, typed Pydantic schemas, small domain/forecast/report functions and parameterized Plant-authorized PostgreSQL queries; React route/page components, typed API services, small feature hooks, limited ephemeral principal-scoped state and no hardcoded prototype data. Follow the useful `analysis_b`/`toolkit` structure and real-integration fixture ideas as written in `IMPLEMENTATION_SPEC.md`: verify **Flowstead's own NATS/JetStream broker/worker and bounded per-principal IndexedDB** without copying the reference app's unrelated compute domains, global persistence/workspace objects or entire monorepo stack. Refactor **only** concrete violations within this accepted task scope, with regression tests; no speculative rewrite.
- Rerun full **Mac-local** real PostgreSQL + NATS/JetStream + durable forecast worker + FastAPI + React Chromium Playwright journeys using the pinned synthetic M1 fixture. **Also exercise IndexedDB reload/expiry/denial/subject-switch and message-queued→completed UI behavior**, not memory-only toggles. Test 1330×900, 390×844 and 200% zoom; real tiles/attribution and no-WebGL fallback; list↔map↔detail↔history 24/72/168 ↔forecast 12; DST/quality gaps; public five-Plant only; disjoint private principals, 401/404, expiry/logout/cache and navigation; download and open/parse PNG/CSV/PDF. Use test-only principal fixtures for local identity, real SQL authorization for trust, and actual browser actions for behavior.
- **Every** UI/UX parity matrix row must include a final-SHA, command, fixture, viewport, browser action, synthetic screenshot/trace/sample artifact path and **functional/visual PASS/FAIL/UNVERIFIED** plus precise deviations. Compare to actual approved local reference HTML only through authorized read-only access; if inaccessible, verify against the explicit baseline and leave original-source comparison UNVERIFIED. Mark missing live tiles/PDF renderer/browser tests honestly, not magically PASS. No public UI release or owner final-presentation signoff inferred from a good local screenshot.
- Preserve TDD chronology honestly: evaluate indexed `UT`/`IT`/`SEC`/`E2E` tests, fix failing cases first and run targeted regressions; cannot retroactively assert RED history from green output. Record direct/transitive dependency audit status and any blocked check. No 24-hour soak or hosted tests unless independently authorized.

## Test-first acceptance
- `E2E-M12-PATH`: public view/list/map; user A list/history/12h/download; user B denied A; 401/404 states; logout **in-memory and IndexedDB** cache clear and no JS leaks.
- `E2E-M12-MAP`: real tile/marker/attribution and controlled offline fallback.
- `E2E-M12-FILES`: PNG axes and PDF visual quality, CSV columns, inspected downloaded file contents.
- `SEC-M12-RATE`: bounded windows/rows/files, rate limit/timeout/cors constraints, SQL+JWT adversarial tests.
- `SEC-M12-AUDIT`: `npm audit` and Python locked dependency audit with remediations and unresolved advisory inventory.
- `UI-M12-ALL`: matrix row evidence for responsive desktop + mobile, zoom, keyboard, loading/missing/expired and justified intentional deviations.
- `E2E-M12-INDEX`: every indexed UI/E2E case has a matching asserting Playwright/Vitest test title, real boundary, exact command + SHA and inspectable Playwright HTML and Markdown/JSON coverage reports; unverified cases explicit.

## Local verification, gates and stopping condition
`just test-backend-unit`, `just test-db-integration`, `just test-frontend-unit`, `just test-e2e-local` (the **real Playwright harness established in task 007**), `just frontend-build`, `just audit-backend`, `just audit-frontend`, then docs check; local only. Full suite runs at milestone gate, never every edit. Store receipts and exact head SHA; missing real browser ≠ PASS.

Do not label live Supabase Auth or hosted recoverability verified in this local milestone.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. OMP coordinates unattended handoff to **ordinary ChatGPT chat in the existing Loop OMP Project** using the owner's previously tested browser workflow. **ChatGPT normal chat is the only independent PR reviewer, bounded GitHub correction agent and final acceptance decision-maker**; OMP/SAIA model PASS is advisory only. OMP handles the Mac's final exact-head tests and only separately authorized merge/issue-status reconciliation. Do not invent a ChatGPT review or block unrelated approved implementation merely because review is pending. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
