# T-003 — FastAPI read contracts and Plant authorization

**Status: IMPLEMENTED AND MERGED** — [Flowstead PR #5](https://github.com/darizae/flowstead/pull/5), merge `647b435e03b4b47b2fc8afca4e81b57e6624cd66`. Control Issue #16 was corrected/reconciled after its earlier schema and allowlist errors. Mac reported 12 backend tests and exact-head verification; dependency audit UNVERIFIED. OMP/SAIA review was recorded, **ordinary ChatGPT review not evidenced**; do not fabricate a chat receipt or reimplement T-003. Owner later paused after T-004. **Repository:** `darizae/flowstead`, private `main`.

## Preconditions and order
002 is **merged, not yet independently ChatGPT-accepted**; use the actual migration+import schema from PR #4 and the recorded immutable M1 source SHA/digest. Do not treat OMP/SAIA PASS as ChatGPT acceptance; do not redo task 002. No live Supabase required. Local deterministic principal fixture can be used only in local test/development, with production default deny. Owner approved all five fictional M1 Plants as the anonymous public **read-only** synthetic dataset on 2026-11-17. Derive public IDs exclusively from the five validated/imported manifest Plants; keep default deny on unverified/extra IDs and keep actual public deployment gated.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `backend/` migrations/models/importer from 002 and owning DB tests; do not read private UI prototype. Actual database schema takes precedence over example file names.

## Observable result and scope
Expose API `GET /api/v1/health`, `/api/v1/public/plants`, `/api/v1/public/plants/{id}/latest`, `/api/v1/public/plants/{id}/history?from=&to=`, `/api/v1/plants`, `/api/v1/plants/{id}/latest`, `/api/v1/plants/{id}/history?from=&to=`, and future forecast link contracts. All Plants/map/latest/history are server-filtered to the authenticated subject's assigned Plant IDs or an independent server-side `public_demo` allowlist containing exactly the five manifest-verified fictional M1 Plants. Public mode is read-only and synthetic for all five validated Plants; it must never return account/private metadata or authorize private endpoints.

Return consistent typed JSON with stable `plant_id`, name, fictional location, IANA timezone, four named measurements with value/quality/units and UTC timestamp. `latest` means latest hourly record **including** missing/invalid flags, not silent interpolation. `history` is half-open `[from_utc,to_utc)` with max 168 hours, min 1 hour, UTC aligned hours, max 1 Plant/request, documented result ordering, per-Plant timezone field and capped response bytes. Reject malformed/non-UTC inputs (422), unauthenticated private access (401), and denied/nonexistent Plant IDs with indistinguishable 404; do not disclose which private IDs exist. No write endpoint or public arbitrary filtering/generation. Use SQL parameter binding, one bounded indexed query per read and no N+1; include OpenAPI validation and safe errors. Local principal injection is constructed explicitly only under test mode, never from caller-provided headers in deployed profiles.

## Dependencies and allowed file closure
Add `fastapi>=0.115,<1`, `uvicorn>=0.30,<1`, `httpx>=0.27,<1` (test), dependency and tests with `uv add --project backend` and locked `backend/uv.lock`. Do not assume these exist from 002. Keep SQLAlchemy/Pydantic versions as resolved by 002, avoid adding an auth provider yet.

Allowed create/edit paths: `backend/src/flowstead_api/**`, `backend/tests/**`, `backend/pyproject.toml`, `backend/uv.lock`, `backend/README.md` if present, `justfile`, `README.md`, `.env.example`. Relevant task dependencies and their owning manifests/lockfiles were part of the original technical scope; do not require an additional planning-status permission check. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `UT-M3-CONTRACT`: OpenAPI models validate canonical four channels/units and preserve flagged NULL/invalid.
- `IT-M3-PLANT`: two local principals with disjoint assigned Plants get disjoint list/map/latest/history results against real PG, never other Plant IDs.
- `IT-M3-DENY`: missing/bad auth=401 for private routes; forbidden and missing Plant both 404; invalid window/cap=422; malformed SQL-resistant input has no side effect.
- `IT-M3-BOUND`: SQL query count/index and payload/window caps checked; no unbounded all-Plant query.
- `IT-M3-PUBLIC`: public list empty until enabled; public handler cannot enumerate operator-restricted Plants.

## Local verification and actual historical evidence
Create `just api-dev` (localhost only), `just test-api-unit` and `just test-api-integration` mapping to real `uv run --project backend pytest -q backend/tests/...`; run contract test, then real local Postgres HTTP integration. Verify `just --list` and `uv audit --project backend` with network or mark UNVERIFIED. API startup must not require Supabase credentials in local test mode.

Public five-Plant visibility is decided; **public deployment remains separately blocked**. Do not expose the API publicly or claim auth provider verified.



## Historical Git and verification record

The implementation and recorded merge already happened. Preserve the historical commit/test evidence as factual context. Independent ChatGPT review receipts, old approval decisions and task statuses do not constrain the start or local merge of subsequent tasks. Do not reimplement this historical task or infer test results that were not observed.
