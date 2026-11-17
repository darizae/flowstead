# T-012 — local MVP security, UX and recovery acceptance

**Status:** WAITING — prerequisite preflight (bounded local task may run when ordered prerequisites and OMP readiness are verified; external operations remain separately gated). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
007–011 implemented and integrated; backend 002–005 functioning with local PostgreSQL, deterministic offline JWKS/test principals. Owner H-10 visual direction approved and export sample available. Hosted Auth and public deployment are separate future gates.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: Actual source and focused tests across backend/frontend, UI/UX matrix, generated PDF/PNG samples, Compose/justfile and runtime/lockfiles. No private owner record or prototype archives.

## Observable result and scope
Run a reproducible local full-journey gate (not ordinary edit loop): database rebuild from pinned generator/checksummed manifest, API start, frontend start, two disjoint operator-private sessions plus public read-only access to all five validated fictional Plants, map/list/history/forecast/download, logout/session expiry, no JS error overflow and proper mobile/desktop accessibility. Audit direct+transitive Python and npm dependencies, runtime pins, CSP/CORS/cache/referrer policy, SQL parameterization, JWT negative paths, unbounded request caps, rate-limit/failure policy under local harness (implement a bounded single-process server-side limiter with trusted-proxy handling and explicit denial semantics for the initial single-instance demo; multi-instance deployment remains a separate approval gate), cleanup/reseed. Fix defects in owning modules only, record measurements and explicit remaining live provider/cloud limitations.



## Dependencies and allowed file closure
Use existing test libraries and Playwright (if absent, authorize compatible `@playwright/test` dev dependency in `frontend/package.json` + generated lockfile; browser binaries installed only on Mac). No optional cloud CI/soak. If a proposed dependency security remediation requires major-version updates, authorize within approved task only after planner confirms impact; don't silently suppress advisories.

Allowed create/edit paths: `backend/**`, `frontend/**`, `compose.yml`, `justfile`, `README.md`, `.env.example`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/agent/ROUTING.md` directly affected rows and checked docs. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `E2E-M12-PATH`: public view/list/map; user A list/history/12h/download; user B denied A; 401/404 states; logout cache clear and no JS leaks.
- `E2E-M12-MAP`: real tile/marker/attribution and controlled offline fallback.
- `E2E-M12-FILES`: PNG axes and PDF visual quality, CSV columns, inspected downloaded file contents.
- `SEC-M12-RATE`: bounded windows/rows/files, rate limit/timeout/cors constraints, SQL+JWT adversarial tests.
- `SEC-M12-AUDIT`: `npm audit` and Python locked dependency audit with remediations and unresolved advisory inventory.
- `UI-M12-ALL`: matrix row evidence for responsive desktop + mobile, zoom, keyboard, loading/missing/expired, intentional deviations owner-signed.

## Local verification, gates and stopping condition
`just test-backend-unit`, `just test-db-integration`, `just test-frontend-unit`, `just test-e2e-local`, `just frontend-build`, `just audit-backend`, `just audit-frontend`, then docs check; local only. Full suite runs at milestone gate, never every edit. Store receipts and exact head SHA; missing real browser ≠ PASS.

Do not label live Supabase Auth or hosted recoverability verified in this local milestone.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Independent distinct-agent review at exact PR head is required; until OMP unattended-review acceptance passes, leave `review_ready` blocked. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
