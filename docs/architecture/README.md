# Flowstead architecture

This is the current developer entry point for Flowstead's single-service architecture. For fixed product and data contracts, see [Implementation spec](../planning/IMPLEMENTATION_SPEC.md). For testing, see [Indexed test plan](../testing/INDEXED_TEST_PLAN.md).

## Boundaries

- **Domain**: immutable plant identities, readings, forecast rules, and event invariants. Must not import FastAPI, NATS, psycopg or CLI internals.
- **Application**: operations involving authorized reads, forecast generation, command submission, outbox publication and report assembly. Application logic depends on domain models and narrow repository interfaces.
- **Infrastructure**: PostgreSQL repositories and transactions, NATS/JetStream connection and delivery, Supabase JWT verification and PDF encoding.
- **Interfaces**: FastAPI routers and schemas, worker/dispatcher CLIs and deterministic data-import tools. These translate transport inputs and outputs; they should not own SQL.
- **Frontend**: application/session composition, feature-owned plant/history/forecast modules, API boundary, principal-scoped IndexedDB and rendering/export utilities.

Keep this as a **single backend Python distribution**, not a microservice fleet. The frontend remains an independent Vite/React application. Do not vendor the reference toolkit.

## Key flows

1. A public request can access only Plant IDs in the verified allowlist **and** marked `public_demo`; an authenticated request derives a principal from a verified JWT and applies scope in SQL. Never apply Plant authorization only after fetching unrestricted rows.
2. A forecast request validates Plant permissions and records a durable command and outbox event in one PostgreSQL transaction.
3. The dispatcher publishes pending outbox entries to JetStream. The worker processes idempotently with retry/dead-letter boundaries. Forecast calculation itself is deterministic and independent of the transport.
4. M1 importer validates pinned source commit, schema, seed, manifest and telemetry provenance before atomic persistence. The repository stores synthetic demonstration data, not real plant measurements.
5. Reports are produced from authorized application data, with PDF/CSV/SVG/PNG as output adapters. Browser caches must remain isolated per principal.

## Developer validation

Use `just lint`, `just test`, `just check`, `just coverage`, `just docs-check`. For PostgreSQL/NATS integration tests use local disposable services and `just test-db-integration` / `just test-message-integration`. Browser end-to-end tests use `just test-e2e-local`.

The configured CI checks backend Ruff lint/format and unit tests, frontend ESLint/Prettier/typecheck/unit/build with frozen pnpm dependencies, documentation, and PostgreSQL/JetStream integration. **Remote CI investigation is paused until December 1, 2026** because of GitHub billing restrictions; run the corresponding local gates instead. See [agent instructions](../../AGENTS.md) and the [frontend dependency audit](../security/2026-11-22-frontend-dependency-audit.md). Do not weaken the acceptance rules when restructuring the code.

## Decisions

See [Architecture decisions](decisions/README.md) for the rationale and constraints of the chosen boundaries. Historical implementation records live in `docs/planning/tasks/`; they are provenance, not current API design guidance.

## Detailed ownership, operations, and provenance

- [Module ownership](PACKAGE_OWNERSHIP.md)
- [Runtime settings](OPERATIONAL_SETTINGS.md)
- [Local and hosted operations](OPERATIONS.md)
- [Migration history and active Alembic workflow](MIGRATIONS.md)
- [Evidence retention policy](EVIDENCE_POLICY.md)
- [Historical task records](HISTORY.md)
