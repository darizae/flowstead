# T-003 — FastAPI read contracts and Plant authorization

**Status:** WAITING — prerequisite preflight (bounded local task may run when ordered prerequisites and OMP readiness are verified; external operations remain separately gated). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
002 accepted, migration+import receipt exact and schema as built. No live Supabase required. Local deterministic principal fixture can be used only in local test/development, with production default deny. Owner approved all five fictional M1 Plants as the anonymous public **read-only** synthetic dataset on 2026-11-17. Derive public IDs exclusively from the five validated/imported manifest Plants; keep default deny on unverified/extra IDs and keep actual public deployment gated.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `backend/` migrations/models/importer from 002 and owning DB tests; do not read private UI prototype. Actual database schema takes precedence over example file names.

## Observable result and scope
Expose API `GET /api/v1/health`, `/api/v1/public/plants`, `/api/v1/public/plants/{id}/latest`, `/api/v1/public/plants/{id}/history?from=&to=`, `/api/v1/plants`, `/api/v1/plants/{id}/latest`, `/api/v1/plants/{id}/history?from=&to=`, and future forecast link contracts. All Plants/map/latest/history are server-filtered to the authenticated subject's assigned Plant IDs or an independent server-side `public_demo` allowlist containing exactly the five manifest-verified fictional M1 Plants. Public mode is read-only and synthetic for all five validated Plants; it must never return account/private metadata or authorize private endpoints.

Return consistent typed JSON with stable `plant_id`, name, fictional location, IANA timezone, four named measurements with value/quality/units and UTC timestamp. `latest` means latest hourly record **including** missing/invalid flags, not silent interpolation. `history` is half-open `[from_utc,to_utc)` with max 168 hours, min 1 hour, UTC aligned hours, max 1 Plant/request, documented result ordering, per-Plant timezone field and capped response bytes. Reject malformed/non-UTC inputs (422), unauthenticated private access (401), and denied/nonexistent Plant IDs with indistinguishable 404; do not disclose which private IDs exist. No write endpoint or public arbitrary filtering/generation. Use SQL parameter binding, one bounded indexed query per read and no N+1; include OpenAPI validation and safe errors. Local principal injection is constructed explicitly only under test mode, never from caller-provided headers in deployed profiles.

## Dependencies and allowed file closure
Add `fastapi>=0.115,<1`, `uvicorn>=0.30,<1`, `httpx>=0.27,<1` (test), dependency and tests with `uv add --project backend` and locked `backend/uv.lock`. Do not assume these exist from 002. Keep SQLAlchemy/Pydantic versions as resolved by 002, avoid adding an auth provider yet.

Allowed create/edit paths: `backend/src/flowstead_api/**`, `backend/tests/**`, `backend/pyproject.toml`, `backend/uv.lock`, `backend/README.md` if present, `justfile`, `README.md`, `.env.example`. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `UT-M3-CONTRACT`: OpenAPI models validate canonical four channels/units and preserve flagged NULL/invalid.
- `IT-M3-PLANT`: two local principals with disjoint assigned Plants get disjoint list/map/latest/history results against real PG, never other Plant IDs.
- `IT-M3-DENY`: missing/bad auth=401 for private routes; forbidden and missing Plant both 404; invalid window/cap=422; malformed SQL-resistant input has no side effect.
- `IT-M3-BOUND`: SQL query count/index and payload/window caps checked; no unbounded all-Plant query.
- `IT-M3-PUBLIC`: public list empty until enabled; public handler cannot enumerate operator-restricted Plants.

## Local verification, gates and stopping condition
Create `just api-dev` (localhost only), `just test-api-unit` and `just test-api-integration` mapping to real `uv run --project backend pytest -q backend/tests/...`; run contract test, then real local Postgres HTTP integration. Verify `just --list` and `uv audit --project backend` with network or mark UNVERIFIED. API startup must not require Supabase credentials in local test mode.

Public five-Plant visibility is decided; **public deployment remains separately blocked**. Do not expose the API publicly or claim auth provider verified.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Independent distinct-agent review at exact PR head is required; until OMP unattended-review acceptance passes, leave `review_ready` blocked. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
