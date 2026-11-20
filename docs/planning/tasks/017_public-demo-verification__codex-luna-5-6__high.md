# T-017 — live demo smoke, security, and rollback acceptance

**Execution:** Start immediately when assigned; planning-status and reviewer approvals are not prerequisites. **Repository:** `darizae/flowstead`, local `main`.

## Technical context
Create and run hosted verification where actual URLs and identities are configured. If no deployed environment exists, implement the verification harness and local simulations without inventing hosted results.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `docs/deployment/OCI_ALWAYS_FREE.md`, `docs/deployment/LOCAL_AND_RECOVERY.md`, live deployment config (FastAPI, **NATS/JetStream + worker**, real Alembic head, PostgreSQL), app API contracts, [indexed test catalog](../../testing/INDEXED_TEST_PLAN.md), [data guide](../../testing/TEST_DATA_GUIDE.md), UI parity matrix, configured demo Auth test identities handled securely out-of-band and current deployed URLs.

## Required Marisma frontend usage (binding)

Keep `@darizae/marisma@0.2.0` as the installed component library and theme for Flowstead's reusable frontend controls, as established in T-007a. If this task changes frontend code, reuse Marisma's public exports rather than introducing duplicate substitutes. During relevant frontend build/browser checks, confirm that the actual app still renders Marisma controls and follows the approved Flowstead design; do not alter the separate Marisma repository or expand this task into a UI redesign.

## Observable result and scope
Test hosted public and invited-operator journeys in actual browsers through TLS against the separate `flowstead-demo` data, including all five fixed fictional public Plants, map tiles, history, forecast, exports and owner account restrictions. Verify free-tier cold start, **broker/consumer restart and queued→persisted 12h forecast delivery**, failed/retried message recovery without duplication, real Alembic head, bounded per-principal **IndexedDB** expiry/logout/revocation cleanup, paused DB messaging, signed-out/expired/revoked token, disjoint assigned Plants and no private-source leak. No public message-command endpoint. Validate backup/reseed procedure against disposable copy, rollback drill where safe/authorized, source/digest/version tracking and alert/log access without credentials exposed. Request owner acceptance of PDF sample, map and public presentation; do not assert uptime guarantees.




## OCI Frankfurt hosted verification — required T-016 handoff receipts

Read `docs/deployment/OCI_ALWAYS_FREE.md` and the actual T-016 evidence before claiming a hosted pass. The Console link's `eu-frankfurt-1` query does not prove home region or free eligibility. Obtain read-only verified actual OCI home region, account type, A1 shape and usage (max 2 total OCPUs/12 GB within remaining allowance), boot+block storage (max 200 GB combined across Always Free allocation), instance health, firewall/NSG and existing budgets. If `brave-browser-relay` is available, discover supported commands and inspect the live UI; login/MFA/billing prompts belong to the owner, not an automated workaround. A missing relay/role is UNVERIFIED, not PASS.

Exercise actual Oracle-hosted `linux/arm64` FastAPI, persistent NATS 2 JetStream and worker, not a local or mocked Compose substitute. Inspect remote healthy/failed state, Docker process restart and surviving JetStream stream/consumer storage, idempotent pending→persisted forecast, and TLS reverse proxy. Verify from outside OCI that only HTTPS (and optional HTTP for certificate issuance) and source-restricted SSH are reachable; ports 8000, 4222, 8222 and 5432/6543 must not be public. Use only synthetic data; never perform a destructive reset on `flowstead-demo`, spin artificial CPU load to defeat reclaim, or start costly/soak tests. Record reclaim/Supabase inactivity limitations without promising availability.

Verify the *actual* OCI Cost Analysis/current spend, account/free status, quota and alert rule outcomes after deployment. Oracle's minimum budget is 1 currency unit and alerts do not hard-limit spending; no cost observed today is not proof of future zero billing. Record UI/CLI evidence with tenant/private keys/recipients redacted. If hosting could incur fees, stop further deployment and ask the owner.

Additional test cases: `OPS-M17-OCI-ARM` (observed Arm64 images, processes and persistent worker/broker restart); `SEC-M17-OCI-INGRESS` (external ingress/tls/proxy), `OPS-M17-OCI-COST` (actual free-eligibility/cost/alert state, no paid resource), `OPS-M17-OCI-RECOVERY` (safe restore/queue replay without wiping hosted data). Do not close T-017 until these have real hosted receipts or are explicitly marked blocked/unverified.

## Dependencies and allowed file closure
No new dependency expected. Additional live test tools must be explicitly named/approved before installation; no volume/load/24h soak default. Remote smoke uses minimum necessary requests.

Allowed create/edit paths: `docs/deployment/**`, `docs/design/UI_UX_PARITY_MATRIX.md`, `frontend/tests/e2e/**` targeted hosted checks, `backend/tests/` targeted auth tests, `README.md` for real live URL/status only, `justfile` only if adding existing safe smoke recipe. Any necessary new dependency installation inside the task's named owning paths is included in this assignment; install compatible versions using the package manager, update the lockfile and tests and report findings. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `E2E-M17-PUBLIC`: anonymous sees exactly approved synthetic subset and no private IDs; list/map/history/chart/exports work.
- `E2E-M17-AUTH`: invite operator restricted to assigned Plants through direct crafted API/CSV/PDF requests; expired/revoked tokens fail.
- `UI-M17-LIVE`: actual 390px and desktop map/PDF/PNG/axis/keyboard parity; visible attribution and fail states.
- `OPS-M17-RECOVER`: documented reproducible seed, real **NATS/worker recovery and idempotent queued-event replay** plus authorized DB backup/rollback drill with exact SHAs; no blind destructive DB reset.
- `OPS-M17-COST`: verified free tier/usage alerts and no unexpected paid service, with owner decision for any exception.

## Local verification and completion
Run bounded actual live browser tests (including safe IndexedDB isolation), API/worker/broker/JetStream smoke, confirmed Alembic head, provider logs/health and release-local unit regression; record exact deployment URL/time/SHA and distinguish local from remote evidence. No unattended status claim if owner/ChatGPT review unavailable.

If hosted privacy leak/security defect discovered, stop public traffic only through configured host controls and escalate to owner; do not independently make destructive changes.



## Local completion

Start coding when this task is explicitly assigned. Run focused local tests and repair real failures; never wait for reviewer certification, a READY table entry, earlier merge receipts or permission to install task dependencies. Commit a focused local task branch, **merge it into local `main`**, and report the commit/merge SHA and actual test results. **Do not push**. Real external writes require a concrete configured target and credentials, not planning-status approvals; complete all possible code/tests if a hosted environment is absent. Never invent secret values, paid service plans or successful deployment evidence.
