# Flowstead — implementation contract

**Status:** Canonical technical contract for the application repository. Execution order and actual completion state belong to [HANDOFF_SEQUENCE.md](HANDOFF_SEQUENCE.md); observable tests belong to [INDEXED_TEST_PLAN.md](../testing/INDEXED_TEST_PLAN.md). The current application includes the PostgreSQL importer, FastAPI read API and deterministic twelve-hour forecast. The frontend, Alembic adoption and NATS/JetStream integration are not yet implemented.

## Product boundary

Flowstead is a small-plant wastewater operations demonstration using **five fictional domestic/package wastewater Plants in Florida**. It is not connected to live treatment systems. Public visitors may browse the five manifest-validated fictional Plants through bounded anonymous read-only endpoints and permitted synthetic-data downloads; this is not permission to publish the application. Invited operators see only Plants independently assigned to their verified identity. No public signup, regulatory compliance reports, incident management, operator logs, industrial/N2O monitoring, or real control/SCADA operations.

The core user journey is Plants list and interactive Florida map → current metrics and 24/72/168-hour history → 12-hour forecast → CSV/PNG/PDF exports. All views and downloads obey the same server-side visibility policy. The [approved visual baseline](../design/UI_UX_BASELINE.md), [local HTML reference](../design/reference/flowstead-ui.html) and [parity matrix](../design/UI_UX_PARITY_MATRIX.md) govern the UI.

## Domain/data contract

- Every Plant has exactly four hourly channels: influent_flow (US gal/h hourly mean), rainfall (in/h hourly interval), dissolved_oxygen (mg/L representative sample), and effluent_ph (unitless representative sample).
- Data is keyed uniquely by (plant_id, timestamp_utc) in UTC; display uses each Plant's IANA Eastern/Central timezone with explicit DST disambiguation. Do not fabricate missing spring-forward hours or merge repeated fall-back hours.
- Quality distinguishes valid, missing (SQL NULL), and invalid (finite flagged value). Never zero-fill, interpolate silently, or count invalid data as valid.
- Each forecast issuance yields exactly twelve consecutive future UTC-hour influent-flow predictions (gal/h), with issued_at, target_time, predicted_flow and model_version. Retain observed/predicted boundary, unavailable cases, deterministic baseline and chronological synthetic-only evaluation. No claims of field predictive accuracy.
- Synthetic data comes from independent [flowstead-sim](https://github.com/darizae/flowstead-sim) generator source commit ad5c94d1f46e79312a99cb9721f38700f24fdf6b, manifest m1.v1, seed 20250101, telemetry SHA-256 e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e. M1 represents five Plants × 365 × 24 = 43,800 wide rows / 175,200 readings. Import from immutable verified output, not a mutable branch, unverified artifact, observed facility dataset or external research extract.
- Bound all windows, downloads and response sizes; retain provenance and quality flags in data exports. CSV formula-injection defenses, openable correctly labeled PNG charts and a concise accurate on-demand Plant PDF are required.

## Code and ownership boundaries

| Owner | Responsibility | Interface/constraint |
| --- | --- | --- |
| flowstead-sim repository | Deterministic independent synthetic generation, checksum manifest and generator tests | App imports validated output pinned to immutable source/manifest; does not vendor generator |
| Flowstead PostgreSQL | Sole authoritative operational/telemetry/forecast store, transactional outbox/inbox | Versioned schema through Alembic; validated atomic import; Plant-scoped SQL |
| Flowstead FastAPI | Typed HTTP read/command endpoints, validation and authorization; services and database adapters | Pydantic, stable OpenAPI, bounded queries, 401/404/422 semantics, server-enforced Plant policy |
| Flowstead forecast worker | Reuse deterministic forecast computation for asynchronous requested jobs | Commit twelve targets and idempotence receipt before acknowledging event |
| Flowstead NATS 2 / JetStream | Durable asynchronous message transport, delivery/replay | Not the system of record; no public command publisher |
| Flowstead React/Tailwind | Plants, map, charts, invite/session states, exports and local UX cache | Actual API schemas, per-principal IndexedDB, approved design and browser parity |
| OMP control-plane repository | Task execution, local runs and independent review handoff | Does not own product requirements or application data |

Maintain the existing backend/importer.py, backend/src/flowstead_api/{main,models,auth,database,forecast}.py and tests; extend with focused modules only when needed. API routes parse/authorize/serialize, typed services enforce forecast and report invariants, database adapters own parameterized SQL and transactions. Avoid service/repository proliferation, duplicate algorithm implementations or frontend-only authorization. Under frontend/src/, use small page/feature components and shared typed API/time/cache adapters; do not put all application state into one component or a global store.

### Authorization and caching

Invite-only Supabase Auth supplies identity; FastAPI validates JWT signature, issuer, audience, expiry and key rotation, and separately authorizes subject→Plant against server-owned assignments. Private and public lists, maps, history, forecasts, commands and exports have consistent permissions; forbidden and unknown Plant IDs are indistinguishable as 404 on protected lookups. Public visibility is derived only from the exact five verified imported M1 Plant IDs; default deny until import validation. Where Supabase Data API exposes tables, enforce least privilege and RLS. Never authorize from user-editable identity metadata.

Browser IndexedDB is a bounded non-authoritative convenience cache: anonymous/public and per-current-principal namespaces, versioned schema, last Plant/channel/window and small sanitized response snapshots with TTL, entry/byte caps and safe corrupt/quota handling. Store no credentials. Clear private caches on logout, expiry, principal switch, revoked access or relevant 401/403/404; never show cached private data without current server authorization.

### Asynchronous forecast and import events

NATS/JetStream uses versioned typed messages, correlation/event IDs, validated Plant and provenance, and the subjects flowstead.v1.ingest.completed, flowstead.v1.forecast.requested, flowstead.v1.forecast.completed and flowstead.v1.forecast.failed. PostgreSQL transactionally records business changes plus outbox entries; a bounded dispatcher publishes and records JetStream acknowledgement. Durable consumers validate, deduplicate through inbox/unique IDs, commit work before ACK, retry transient failures with bounded backoff and record terminal failures. Broker outage must not corrupt stored data or block ordinary GETs. Public endpoints never enqueue arbitrary jobs. The existing direct forecast command remains a maintenance/recovery path using the same computation.

### Schema and migrations

Adopt **Alembic as the real migration runner** in task 004a. Preserve already applied SQL migration history and records: validate old schema equivalence before stamping existing databases, create equivalent clean-database upgrades, and test repeated upgrades, mismatched states and rollback on disposable databases. Do not drop or reset populated data. Task 004b adds durable message tables and services after 004a, with real PostgreSQL/JetStream checks.

## UI/UX and exports

The approved reference calls for a roughly 72px white header, pale mint background, deep-green/teal tokens, centered ~1340px shell, Plants list and Florida map split on desktop/stacked on mobile, four latest-metric tiles, 24/72/168-hour historical channels, separate observed/12h forecast and visible CSV/PNG/PDF actions. Use MapLibre/OpenFreeMap with attribution, accessible markers and functional list fallback. Production data is API-backed five-Plant M1, not the reference HTML's illustrative fixtures. Copy and axes use Plant and Plants, exact measurement units, Plant-local time and unambiguous DST. No extra explanatory dashboard filler or unapproved navigation.

Forecast async states are queued/processing/completed/failed/unavailable; show only persisted forecast results. Browser work starts in task 007 using Mac-local Playwright at 1330×900 and 390×844, real local PostgreSQL/FastAPI, browser interactions, screenshot/trace evidence and the parity matrix. Parse/open actual exported files and visually inspect PDF and charts; screenshots or unit tests alone do not establish parity.

## Environments and hosting

The [deployment architecture](../setup/DEPLOYMENT_ARCHITECTURE.md) is the single place for environment isolation, cloud provider responsibilities, deployment and operational release gates. Application code remains locally testable with Docker PostgreSQL and NATS/JetStream. An existing private Supabase development database and an independently approved future public demonstration environment are distinct. Hosted composition requires static React frontend, Python FastAPI API and durable worker, persistent JetStream transport and hosted PostgreSQL; never depend on a Mac process for a hosted demo. No persistent export/object archive is required: CSV, PNG and PDF are generated on request. Cloud writes, provisioned services, public exposure, DNS and cost decisions are separately authorized operations.

## Verification and implementation handoff

Run the smallest failing observable test first where practical, then implementation and focused regressions. [Indexed cases and evidence rules](../testing/INDEXED_TEST_PLAN.md) specify exact assertions; [data classes](../testing/TEST_DATA_GUIDE.md) provide fixtures. Mandatory real local boundaries include PostgreSQL migration/import/Plant authorization, NATS replay/outage/recovery and actual browser/cache/map/export journeys. Keep fast unit and targeted integration tests distinct from full milestone/browser and hosted release gates. Use actual root justfile recipes; new commands must be added in the owning task alongside real scripts. Audit runtime/development dependencies and repair authorized advisories before release; an unavailable audit is UNVERIFIED. Update directly affected documentation and execute indexed milestone hygiene tasks. Merged source SHA and reported tests are receipts, not proof of unrun checks or of an independent review.

Only one explicit task file is dispatched at a time. Local tasks are bounded and technically approved subject to the current owner pause, prerequisites and independent review workflow. New architecture, repositories, secrets, cloud writes, invitations, DNS, spending, destructive changes and public launch require specific authorization.