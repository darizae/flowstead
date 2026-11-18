# Flowstead — implementation contract

**Status:** Canonical technical contract for the application repository. Execution order and actual completion state belong to [HANDOFF_SEQUENCE.md](HANDOFF_SEQUENCE.md); observable tests belong to [INDEXED_TEST_PLAN.md](../testing/INDEXED_TEST_PLAN.md). The current application includes the PostgreSQL importer, Alembic migrations, deterministic twelve-hour forecast, Plant-scoped FastAPI read/forecast-command API and local Supabase-compatible JWT verifier. The frontend remains planned. Backend NATS/JetStream is present on `main` at commit `388a5ad`, and auth verification at commit `e5482fd`, without implying that tests were rerun for this documentation update.

## Product boundary

Flowstead is a small-plant wastewater operations demonstration using **five fictional domestic/package wastewater Plants in Florida**. It is not connected to live treatment systems. Public visitors may browse the five manifest-validated fictional Plants through bounded anonymous read-only endpoints and permitted synthetic-data downloads; this is not permission to publish the application. Invited operators see only Plants independently assigned to their verified identity. No public signup, regulatory compliance reports, incident management, operator logs, industrial/N2O monitoring, or real control/SCADA operations.

The core user journey is Plants list and interactive Florida map → current metrics and 24/72/168-hour history → 12-hour forecast → CSV/PNG/PDF exports. All views and downloads obey the same server-side visibility policy. The [approved visual baseline](../design/UI_UX_BASELINE.md), [local HTML reference](../design/reference/flowstead-ui.html) and [parity matrix](../design/UI_UX_PARITY_MATRIX.md) govern the UI.

## Domain/data contract

- Every Plant has exactly four hourly channels: influent_flow (US gal/h hourly mean), rainfall (in/h hourly interval), dissolved_oxygen (mg/L representative sample), and effluent_ph (unitless representative sample).
- Data is keyed uniquely by (plant_id, timestamp_utc) in UTC; display uses each Plant's IANA Eastern/Central timezone with explicit DST disambiguation. Do not fabricate missing spring-forward hours or merge repeated fall-back hours.
- Quality distinguishes valid, missing (SQL NULL), and invalid (finite flagged value). Never zero-fill, interpolate silently, or count invalid data as valid.
- Each forecast issuance yields exactly twelve consecutive future UTC-hour influent-flow predictions (gal/h), with issued_at, target_time, predicted_flow and model_version. Retain observed/predicted boundary, unavailable cases, deterministic baseline and chronological synthetic-only evaluation. No claims of field predictive accuracy.
- Synthetic data comes from independent [flowstead-sim](https://github.com/darizae/flowstead-sim) generator source commit ad5c94d1f46e79312a99cb9721f38700f24fdf6b, manifest m1.v1, seed 20250101, telemetry SHA-256 e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e. M1 represents five Plants × 365 × 24 = 43,800 wide rows / 175,200 readings. Before import, the caller independently verifies that the supplied manifest names this canonical telemetry digest. The importer validates the pinned source/schema/seed and compares CSV checksum, size and rows to that supplied manifest; it does not itself pin the canonical telemetry digest. Import from immutable verified output, not a mutable branch, unverified artifact, observed facility dataset or external research extract.
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

Keep the focused ownership boundaries in `backend/importer.py`, `backend/migrate.py`, and `backend/src/flowstead_api/{main,models,auth,database,forecast,messages,message_store,messaging}.py`. API routes parse, authorize and serialize; forecast code owns the reusable calculation; the database and message-store adapters own parameterized SQL and transactions; messaging owns JetStream topology, outbox dispatch and durable consumption. Avoid service/repository proliferation, duplicate algorithm implementations or frontend-only authorization. Under `frontend/src/`, use small page/feature components and shared typed API/time/cache adapters; do not put all application state into one component or a global store.

### Current backend HTTP routes

`backend/src/flowstead_api/main.py` is authoritative and FastAPI generates `/openapi.json` from it. The implemented application routes are:

- `GET /api/v1/health`
- public reads: `GET /api/v1/public/plants`, `GET /api/v1/public/plants/{plant_id}/latest`, `GET /api/v1/public/plants/{plant_id}/history`, and `GET /api/v1/public/plants/{plant_id}/forecast`
- bearer-authenticated reads: `GET /api/v1/plants`, `GET /api/v1/plants/{plant_id}/latest`, `GET /api/v1/plants/{plant_id}/history`, and `GET /api/v1/plants/{plant_id}/forecast`
- bearer-authenticated asynchronous commands: `POST /api/v1/plants/{plant_id}/forecast-requests` and `GET /api/v1/forecast-requests/{correlation_id}`

History requests require bounded `from` and `to` query parameters. There is no public forecast-command route.

### Authorization and caching

Invite-only Supabase Auth supplies identity; FastAPI validates JWT signature, issuer, audience, expiry and key rotation, and separately authorizes subject→Plant against server-owned assignments. Private and public lists, maps, history, forecasts, commands and exports have consistent permissions; forbidden and unknown Plant IDs are indistinguishable as 404 on protected lookups. Public visibility is derived only from the exact five verified imported M1 Plant IDs; default deny until import validation. Where Supabase Data API exposes tables, enforce least privilege and RLS. Never authorize from user-editable identity metadata.

Browser IndexedDB is a bounded non-authoritative convenience cache: anonymous/public and per-current-principal namespaces, versioned schema, last Plant/channel/window and small sanitized response snapshots with TTL, entry/byte caps and safe corrupt/quota handling. Store no credentials. Clear private caches on logout, expiry, principal switch, revoked access or relevant 401/403/404; never show cached private data without current server authorization.

### Asynchronous forecast and import events

NATS/JetStream uses versioned typed messages, correlation/event IDs, validated Plant and provenance, and the subjects flowstead.v1.ingest.completed, flowstead.v1.forecast.requested, flowstead.v1.forecast.completed and flowstead.v1.forecast.failed. PostgreSQL transactionally records business changes plus outbox entries; a bounded dispatcher publishes and records JetStream acknowledgement. Durable consumers validate, deduplicate through inbox/unique IDs, commit work before ACK, retry transient failures with bounded backoff and record terminal failures. Broker outage must not corrupt stored data or block ordinary GETs. Public endpoints never enqueue arbitrary jobs. The existing direct forecast command remains a maintenance/recovery path using the same computation.

### Schema and migrations

Alembic is the real forward migration runner through `backend/migrate.py` and `backend/migrations/alembic/`. Revisions `001_initial.py` and `002_forecast_metadata.py` preserve and validate the historical schema before stamping populated compatible databases; `003_jetstream_messages.py` adds durable outbox, inbox and forecast-job state. Repeated upgrades and mismatched states fail safely, and downgrade is restricted to explicitly disposable local databases. The historical SQL files and markers remain compatibility evidence, not a second forward runner.

## UI/UX and exports

**Mandatory reusable UI dependency:** Flowstead's React 19/Tailwind CSS 4 frontend uses the published `@darizae/marisma@0.2.0` package for available generic app shells, buttons, cards, inputs, selection, dialogs and similar controls. T-007a reconciles this with the locally completed T-007 frontend. Subsequent frontend tasks reuse the installed library and its compiled theme, not duplicate bespoke primitives or a vendored Marisma source tree. Flowstead owns its approved v2 visual composition, map, charts, API, identity and domain behavior. Preserve browser parity and meaningful accessibility states.

The approved reference calls for a roughly 72px white header, pale mint background, deep-green/teal tokens, centered ~1340px shell, Plants list and Florida map split on desktop/stacked on mobile, four latest-metric tiles, 24/72/168-hour historical channels, separate observed/12h forecast and visible CSV/PNG/PDF actions. Use MapLibre/OpenFreeMap with attribution, accessible markers and functional list fallback. Production data is API-backed five-Plant M1, not the reference HTML's illustrative fixtures. Copy and axes use Plant and Plants, exact measurement units, Plant-local time and unambiguous DST. No extra explanatory dashboard filler or unapproved navigation.

Forecast async states are queued/processing/completed/failed/unavailable; show only persisted forecast results. Browser work starts in task 007 using Mac-local Playwright at 1330×900 and 390×844, real local PostgreSQL/FastAPI, browser interactions, screenshot/trace evidence and the parity matrix. Parse/open actual exported files and visually inspect PDF and charts; screenshots or unit tests alone do not establish parity.

## Environments and hosting

The [deployment architecture](../setup/DEPLOYMENT_ARCHITECTURE.md) documents environment isolation, hosting responsibilities and release verification. Application code remains locally testable with Docker PostgreSQL and NATS/JetStream. An existing private Supabase development database and a possible separate public demonstration environment are distinct. Hosted composition requires static React frontend, Python FastAPI API and durable worker, persistent JetStream transport and hosted PostgreSQL; never depend on a Mac process for a hosted demo. No persistent export/object archive is required: CSV, PNG and PDF are generated on request. Do not use invented cloud project names, access rights, paid plans, DNS records or secrets; assigned local work proceeds regardless of hosted configuration.

## Verification and implementation handoff

Run the smallest failing observable test first where practical, then implementation and focused regressions. [Indexed cases and evidence rules](../testing/INDEXED_TEST_PLAN.md) specify exact assertions; [data classes](../testing/TEST_DATA_GUIDE.md) provide fixtures. Mandatory real local boundaries include PostgreSQL migration/import/Plant authorization, NATS replay/outage/recovery and actual browser/cache/map/export journeys. Keep fast unit and targeted integration tests distinct from full milestone/browser and hosted release gates. Use actual root justfile recipes; new commands must be added in the owning task alongside real scripts. Audit runtime/development dependencies and repair actionable advisories; an unavailable audit is UNVERIFIED. Update directly affected documentation and execute indexed milestone hygiene tasks. Report genuine test results; missing review receipts never block starting or locally committing a task.

An explicit owner instruction to implement a task is sufficient to start immediately, regardless of predecessor status or missing approval/review receipts. Workers handle normal dependency setup, development and local verification as part of that task, then commit/merge locally without a push. Preserve real security boundaries and do not invent paid resources, credentials, public targets or destructive effects.
