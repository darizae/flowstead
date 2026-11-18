# T-004b — NATS/JetStream asynchronous messaging

**Execution:** NATS/JetStream implementation code is already committed to `main` at `388a5ad`. Its review receipt is not a prerequisite for T-005 or any explicitly assigned follow-up.

## Read and respect
Read AGENTS.md, docs/planning/HANDOFF_SEQUENCE.md, this file, docs/planning/IMPLEMENTATION_SPEC.md, docs/testing/INDEXED_TEST_PLAN.md, docs/testing/TEST_DATA_GUIDE.md, existing backend API/forecast/importer, migration code, compose.yml and nearest real integration tests. the Flowstead implementation contract is authoritative; read-only engineering examples under `/Users/danie/repos/repomix-static-reconstructor/reconstructed/toolkit` and `/Users/danie/repos/repomix-static-reconstructor/reconstructed/integration_tests` may inform tests, but do not copy or execute them.

## Observable event-driven behavior
Use a pinned compatible NATS 2 Docker service **with JetStream enabled**, loopback-only port and health/readiness checks alongside existing PostgreSQL (no cloud broker). Add audited nats-py in backend lock. Keep FastAPI HTTP reads on parameterized PostgreSQL projections with current Plant-scoped auth; GET endpoints must not mutate or wait for a broker. Keep one reusable deterministic forecast calculation; adapt current local forecast CLI as a maintenance/backfill path.

Implement one small typed message boundary (e.g. backend/src/flowstead_api/messages.py), app-owned PostgreSQL outbox + inbox/dedupe tables through **new Alembic forward revision**, and a bounded outbox dispatcher plus JetStream durable forecast consumer. Versioned message schema includes event_id, correlation_id, plant_id, source_sha, occurred_at_utc and well-defined action-specific fields; validate versions, sizes, timestamps, allowed Plant IDs and provenance. Subjects: flowstead.v1.ingest.completed, flowstead.v1.forecast.requested, flowstead.v1.forecast.completed, flowstead.v1.forecast.failed. Define stream, explicit durable consumer names, delivery count/max age, retention, ack wait, retry and dead-letter/error visibility. Never use NATS itself as source of truth.

After a validated import or approved private forecast command, commit state **and outbox** transactionally; dispatcher publishes with event-id dedupe and marks confirmed dispatch. Consumer commits deterministic forecast + inbox receipt in a transaction **before JetStream ack**. Duplicate delivery, delayed messages, worker/broker restart, publish-before-crash and consumer-after-commit-before-ack must not duplicate forecasts or leak another Plant. Public visitor APIs stay synthetic read-only; only authorized operator/CLI can enqueue forecast commands. Expose a bounded status/correlation query or local command; avoid a new admin UI/microservice/compute framework.

## Allowed code closure
compose.yml; backend/src/flowstead_api/**; backend/importer.py (only small emission hook after accepted commit); backend/migrations/** (new Alembic revision); backend/tests/**; backend/pyproject.toml and backend/uv.lock via approved package manager; root justfile; .env.example; README.md; docs/testing/INDEXED_TEST_PLAN.md evidence update. No hosted credentials, unrelated dependencies or separate repository. Use smallest isolated modules and existing FastAPI/SQL style.

## Indexed test-first acceptance
- **MSG-M4B-PUBLISH:** ingest-completed/forecast-requested are persisted in transactional outbox and published to real JetStream using exact schema/message IDs; no phantom message after rollback.
- **MSG-M4B-FLOW:** the real consumer processes an approved Plant request, persists exactly 12 correct UTC forecast targets using existing deterministic model, emits completed event and acknowledges only after commit.
- **MSG-M4B-DUP:** twice-delivered, redelivered, reordered and restarted messages remain idempotent; one issuance and no repeated side effects.
- **MSG-M4B-OUTAGE:** with broker unavailable, API DB reads still work, outbox remains pending, safe retries resume after NATS returns; no lost write/false success or unbounded hang.
- **MSG-M4B-PAUSE:** controllable worker pause makes queued-vs-complete observable; no false forecast when not processed; bounded resume reaches terminal result.
- **MSG-M4B-POISON:** unknown version, invalid payload/Plant ID and max-delivery failure are rejected/dead-lettered with safe bounded diagnostic receipt and no SQL mutation.
- **MSG-M4B-AUTH:** private command cross-Plant denied; public read-only route cannot enqueue; no unverified Plant data appears in messages or response.
- **DB-M4A-FRESH:** the Alembic chain still rebuilds schema including new outbox/inbox tables in clean PostgreSQL.

Run real local PostgreSQL + NATS/JetStream stack, real HTTP, real publisher/consumer, focused unit cases and controlled broker pause/restart. Follow indexed test skill philosophy: exact IDs in asserting tests, owner-isolated data, public behavior-first assertions, no sleep-only proof; link evidence to the Markdown index. Root just recipes should cover broker start, message-unit, message-integration and backend regression.

## Local completion

Use the existing NATS/JetStream implementation on `main` and run its targeted tests as needed. Task-status tables, ChatGPT reviewer availability or missing approval receipts are not prerequisites for the next explicitly assigned implementation. For any new task-owned corrections, commit and merge locally; do not push automatically. Preserve broker/data security invariants.
