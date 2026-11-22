# Flowstead module ownership and import boundaries

**Current implementation · November 22, 2026**

Flowstead is a **single installable backend distribution** and one React/Vite frontend, not a group of microservices. This file documents actual code ownership and the direction new code should take; do not infer that every historical adapter has already been eliminated.

## Backend

| Code location | Responsibility | Dependencies and constraints |
| --- | --- | --- |
| `flowstead_api/domain/` | Immutable plant identities, M1 values and readings | Standard library only; no FastAPI, database, NATS or infrastructure imports; CI checks this |
| `flowstead_api/forecast.py` | Deterministic 12-hour forecasting and backtesting | Business calculation remains testable without PostgreSQL; CLI is separate |
| `flowstead_api/application/plants.py` | Scoped plant/latest/history/forecast read use cases | Explicit `PublicAccess` or `OperatorAccess`; delegates scope enforcement to SQL repositories |
| `flowstead_api/application/forecasts.py` | Forecast-request, status and transactional processing workflows | Owns the unit-of-work boundary for job/inbox/outbox/forecast changes |
| `flowstead_api/application/ports/` | Narrow repository and unit-of-work interfaces | Interface signatures are tested against real adapters |
| `flowstead_api/application/reports.py` | Persistence-independent report data projection | PDF renderer consumes projected data rather than database record classes |
| `flowstead_api/infrastructure/persistence/` | Plant/forecast SQL, record mapping, PostgreSQL transaction | Enforces allowlist+public_demo or operator grants **inside SQL** |
| `flowstead_api/infrastructure/messaging/` | NATS/JetStream transport and worker adapters | Preserve outbox, retry, dead-letter, dedupe and idempotency |
| `flowstead_api/infrastructure/importing/` | M1 manifest/CSV validation | Rejects data with incorrect provenance/size/digest before writes |
| `flowstead_api/infrastructure/migrations/` | Schema inspection and real Alembic execution | Never bypass disposable rollback guards or historical adoption validation |
| `flowstead_api/interfaces/http/` | FastAPI application, routers, schemas and response mapping | Verify JWT first; only call authorized use cases, never filter private rows after fetch |
| `flowstead_api/auth.py`, `security.py` | Authentication and HTTP security compatibility interfaces | Legacy import paths are retained while implementations are extracted |
| `flowstead_api/database.py`, `main.py`, `messaging.py` | Stable public entry-point facades | Avoid growing new business logic in facades |
| `backend/importer.py`, `backend/migrate.py` | Historical CLI/import compatibility | Delegate validation/migration execution to installed infrastructure modules |

The import-direction check is `python3 scripts/check_architecture.py`. Real database constraints are enforced by `backend/tests/integration/`; static structural protocol compatibility lives in `backend/tests/unit/test_application_ports.py`. A package is not a separately deployed service.

## Frontend

| Code location | Responsibility |
| --- | --- |
| `frontend/src/app/` | Top-level routing, session composition and principal changes |
| `frontend/src/features/auth/` | Sign-in form and auth UI |
| `frontend/src/features/plants/` | Authorized list, detail, mock geographic preview and lazy map |
| `frontend/src/features/history/` | Time-window history transforms and chart |
| `frontend/src/features/forecast/` | Forecast transforms, request polling and chart |
| `frontend/src/lib/api/` | HTTP client, runtime validators, generated OpenAPI contract and types |
| `frontend/src/lib/auth/` | Supabase verifier-provider integration; unconfigured production mode fails closed |
| `frontend/src/lib/cache/` | Principal-scoped IndexedDB UI preferences, not a forecast snapshot store |
| `frontend/src/lib/exports/` | Bounded CSV, PNG and PDF exports |
| `frontend/src/shared/` | Chart primitives, UTC conversion, state hooks and UI components |
| `frontend/e2e/` | Guarded local Playwright runner and browser acceptance tests |

`pnpm --dir frontend run api:types:check` verifies that the checked-in OpenAPI schema and generated TypeScript declarations match the backend. `pnpm --dir frontend run typecheck`, `lint`, and `format:check` validate frontend code.

## Architectural non-goals

Do not introduce microservice splits, a generic dependency-injection container, a new event-bus framework or copied reference-project package graphs without a demonstrated requirement. Keep data provenance, PostgreSQL scope and the transactional outbox as release-blocking invariants.

See [architecture decisions](decisions/README.md), [migrations](MIGRATIONS.md) and [operational settings](OPERATIONAL_SETTINGS.md).
