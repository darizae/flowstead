# Flowstead — indexed integration / UI test data guide

This is the **test-data companion** to [INDEXED_TEST_PLAN.md](INDEXED_TEST_PLAN.md). Choose the **minimum dimensions that expose the intended distinction**, not a giant generic fixture. The test cases and data classes here are self-contained.

## Real local stack and ownership

Use a disposable local **PostgreSQL 16**, **NATS 2 with JetStream enabled** (after task 004b), real **FastAPI**, a bounded forecast worker, and **React/Chromium Playwright** (from task 007). Seed the **five exact fictional M1 Plants**, manifest m1.v1, seed 20250101, source SHA ad5c94d1f46e79312a99cb9721f38700f24fdf6b; validate telemetry SHA-256 e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e. No DHI records, real user credentials, remote Supabase writes or paid cloud broker resources.

A **shared stack** can serve independent tests with case-owned principals and data. Never assert global DB counts or empty queue in shared state. For paused workers, broker failure, migrations or delivery-order scenarios use an isolated **controllable stack**. Run real Alembic migrations against disposable PostgreSQL; metadata create_all does not substitute for migration tests.

## Equivalence classes

| Class | Minimum distinct variants | Bug to expose | Required observable proof |
|---|---|---|---|
| Identity | Principal A assigned Plant A, B assigned disjoint Plant B, unassigned C, anonymous | Unauthorized cross-Plant access, exports or map markers | HTTP status/response, owner-scoped SQL and no foreign UI content |
| Plant provenance | Five exact M1 IDs, extra sixth, known-unassigned, absent | Caller-chosen public allowlist or foreign cache | Exact public/assigned list, API query and manifest checks |
| Readings/time | valid, SQL NULL missing, flagged invalid; Eastern/Central DST; 24/72/168h | Zero fill, line interpolation, ambiguous DST hour | Real API, chart labels and decoded CSV/PNG |
| Immutable data | Same SHA/seed/manifest repeated, altered digest, identical numbers different Plant | Bad dedupe or mutable source | Exact checksum and SQL import identity |
| Forecast | Seasonal 24h, bounded 5h persistence, no valid source, 12 future targets | Future leakage, partial/duplicated rows, fake zero | Unit + real Postgres transaction and response |
| Event lifecycle | outbox pending, published, queued, processing, completed, failed, retried, dead-lettered | Message loss, duplicate or premature ACK | Real JetStream consumer and PG outbox/inbox/forecast by event ID |
| Broker faults | NATS offline/restart; consumer crash before/after commit; unknown version | Lost events, bad retries, wrong ack state | Controlled live outage/resume with bounded deadline and exact durable state |
| Alembic history | clean DB, SQL-migrated populated DB, partial/unknown schema, repeated upgrade | Reapplying old DDL or losing imported data | Actual Alembic head/current, constraints, pre/post data hash |
| IndexedDB privacy | public, A, B, forbidden Plant, revoked JWT, expired session, logout, reload | Private cached data leaks across principals | Playwright real IndexedDB stores plus API/UI response assertions |
| IndexedDB resilience | fresh, old version, corrupt item, expired TTL, quota full, unavailable | Stale data, startup crash, unbounded storage | Typed validation, safe eviction and fallback |
| Browser interaction | desktop 1330×900, phone 390×844, 200% zoom, keyboard, WebGL/tile outage | Screenshot-only pass, overflow or fake map | Real Chromium clicks, network/tile attribution, fallback and screenshots |
| Downloads | CSV formula-leading text, NULL, PNG both axes, PDF long name/12h forecast | Unsafe export, wrong units, unreadable/foreign report | Real downloads parsed/decoded/opened and independently visually inspected |

## T-004a — Alembic acceptance fixtures and indexed cases

All T-004a migration acceptance cases use fresh, uniquely named local `flowstead_test_<uuid>` PostgreSQL databases. Do not reset a shared or imported M1 database. Capture the real SQL assertions, source SHA, exact commands, actual PASS/FAIL/SKIP and reasons; without Mac receipts, each case below remains **UNVERIFIED**.

| Indexed ID | Real fixture / variants | Required observable proof |
|---|---|---|
| `DB-M4A-FRESH` | Empty disposable PostgreSQL 16; Alembic to head; importer and API regression fixtures | Exact historical tables/columns/identities/defaults, CHECK/FK/unique/index definitions and two markers, plus real importer/API results |
| `DB-M4A-STAMP` | Populated, historical-SQL-migrated database; exact five-Plant immutable M1 fixture and persisted 12-hour forecast when inputs configured | Validate schema before stamp; compare pre/post hashes of readings, ingest provenance, forecast receipts and historical marker records; no historical DDL rerun |
| `DB-M4A-MISMATCH` | Partial schema; unknown Alembic/history; malformed same-named historical CHECK/index; *recognized local descendant* missing historical table/column or modifying a baseline constraint/index | Explicit fail-closed error and unchanged Alembic version/data after rejection; no blind repair |
| `DB-M4A-REPEAT` | Migrated populated DB and isolated local 003 revision adding an extra Plant column | Repeated upgrade is no-op; new column allowed while original invariants remain intact; safe up/down without altered M1 rows |
| `IT-M2-MIGRATE` | Existing M1 importer and repeat-import invariants; isolated disposable rollback | Preserve migration/import equivalence and data; reject rollback on non-disposable or non-loopback DB |
| `UT-M4A-DB-LIFECYCLE` | Mock Docker healthy/stopped/unhealthy, foreign host/Compose project, and lookalike checkout/config labels | Exact project/service and canonical checkout/config identity, healthy reuse, stopped start, unhealthy one restart, and no mutating command for foreign port owners |

The integration Docker preflight requires an explicit local `DATABASE_URL`. Missing configuration is an environment failure, not a passing or failing migration assertion. The configured `COMPOSE_PROJECT_NAME` and canonical target checkout determine which service can be managed. Missing full M1 fixtures must produce a visible SKIP rather than successful preservation evidence.

## Case execution and visible reports

- Repeat every exact indexed ID in the **asserting pytest test docstring** (Case: ID or Cases: ID1, ID2), or in the **Vitest/Playwright test title**. Helpers, comments and fixtures do not count as coverage. Group cases only when assertions and fixture invariants genuinely coincide.
- Implement setup → real request/operation → public observable assertions, then SQL/broker/browser internal observations only when necessary for persistence, ordering, unchanged state or security. A foreign resource must not accidentally alias the allowed Plant by filename or content.
- In a shared stack use unique owned IDs; do not globally truncate/purge. Use a private controllable stack for paused/global failure only. Await terminal job states using bounded diagnostic polling; do not use arbitrary sleeps as proof.
- For **each ID** report test path/function/title, SHA, actual command and result, assertion summary and real/mocked boundary in the Markdown/JSON indexed coverage report. UI/E2E additionally produces a locally accessible **Playwright HTML report**, screenshot and trace where relevant, real tiles, and decoded exported files. Missing proofs stay UNVERIFIED.
- For each task use a small targeted local test-first RED/GREEN loop where practicable, then relevant real PostgreSQL/NATS/browser integration and milestone suite. Final green output does not prove historical TDD RED. Never call an unavailable dependency audit or unexecuted browser gate PASS.

This technical data guide does not require copying the analysis_b application, reference archives, external auth service, or test-case business domain. Local agents run task-specific tests directly. External ChatGPT review is optional; no reviewer, relay or acceptance receipt is needed to start, commit or merge an explicitly assigned task into local `main`.
