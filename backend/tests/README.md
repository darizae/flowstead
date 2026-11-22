# Backend integration acceptance

The backend suite follows the archived `integration_tests` **testing guarantees**,
not its unrelated analysis/file-upload API. Tests exercise Flowstead's own
Plant-scoped FastAPI, signed-JWT authorization, deterministic forecast worker,
PostgreSQL 16, NATS/JetStream, Alembic migration history and transactional
outbox/inbox. The archive is a read-only reference, not a dependency.

## Test tiers

| Tier | Location | Boundary and isolation |
| --- | --- | --- |
| Unit | `backend/tests/unit` | No external services required; use focused mocks where applicable |
| Database/API integration | `backend/tests/integration` | Real disposable PostgreSQL database **per test**; direct application calls or in-process FastAPI `TestClient` |
| Live backend acceptance | `backend/tests/live` | Real OS processes, local HTTP, signed test principals, PostgreSQL and independently owned NATS/JetStream |

The per-test integration databases are intentionally stricter isolation than
the reference's shared mutable DB. A live test may instead share one owned
stack among its concurrent clients to detect authorization and worker
interference that cannot be exposed by independent databases.

## Commands

Set `DATABASE_URL` to the local PostgreSQL administrative connection
(`127.0.0.1`, never production), and provide the **verified synthetic M1**
fixture for database integration: `FLOWSTEAD_M1_MANIFEST` and
`FLOWSTEAD_M1_DATA`. The preflight requires an available Docker daemon for
live and messaging tests. Test setup must never truncate or drop the database
named by `DATABASE_URL`; only generated disposable databases and containers
are eligible for teardown.

```sh
just test-db-integration
just test-message-integration
just test-live-integration
just test-backend-integration
```

The last command is the full **backend-only** acceptance gate. Its implementation
is `backend/tests/run_integration_gate.py`. To get machine-readable evidence:

```sh
uv run --project backend python -m backend.tests.run_integration_gate \
  --suite all --receipt /tmp/flowstead-backend-integration.json
```

The gate fails on **zero tests, any skip, any failure, any error, or missing
required environment**. Plain `pytest` remains useful for test discovery and
focused development, but its green exit code with skipped tests must not be
interpreted as integration acceptance. The receipt records commit SHA, selected
suite, collected/passed/failed/skipped numbers, skip reasons and preflight
errors. Results are only evidence for the actual source revision and run.

## Isolation and assertion policy

Use unique principals and true Plant assignments; never trust a client-supplied
Plant ID as authorization. Test own/foreign/absent resources with equivalent
HTTP responses where the contract requires non-disclosure. Inspect SQL only
for effects a client cannot establish, such as outbox atomicity, inbox
idempotency, and persistence across broker faults.

Do not purge, stop or restart an existing developer's Compose broker. Broker
outage and retry tests own their disposable broker and clean up only that
container. Tests that deliberately pause compute or alter the entire broker
must use their private stack; do not suspend a shared worker. Wait for queued
jobs with a bounded deadline and a failure diagnostic, not arbitrary sleeps.

Use the exact case IDs in `docs/testing/INDEXED_TEST_PLAN.md` as short
`Case: ...` or `Cases: ...` test docstrings; test names and code alone are not
a passing receipt. Run local acceptance separately from GitHub Actions during
the repository's November 22–30, 2026 CI pause.