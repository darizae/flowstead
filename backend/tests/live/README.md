# Backend live-stack suite

These tests are opt-in because they create and remove a disposable PostgreSQL
database, a unique Docker NATS/JetStream container, and real Uvicorn and worker
processes.

```sh
FLOWSTEAD_RUN_LIVE=1 \
DATABASE_URL='postgresql://.../admin-db' \
uv run --project backend pytest -q backend/tests/live
```

`FLOWSTEAD_LIVE_DATABASE_URL` may be used instead of `DATABASE_URL`. The admin
URL must be loopback PostgreSQL; the suite creates a uniquely named database,
runs Alembic to head, imports the canonical fixture from
`backend/tests/fixtures/m1`, and drops only that database during cleanup.

Without `FLOWSTEAD_RUN_LIVE=1`, tests skip before provisioning. Missing local
Docker/NATS also skips by default; set `FLOWSTEAD_LIVE_STRICT=1` to make that
infrastructure absence a test failure for an orchestrated gate.
