# T-004a local acceptance receipt — 2026-11-18

## Scope

Local-only PostgreSQL/Alembic and immutable M1 acceptance for Flowstead `main`.
No cloud, Supabase, deployment, or production database was touched.

- Flowstead source commit: `78b109c598a7e2a8441ee6cc5ced1ca1525068cb`
- Pinned M1 generator source: `ad5c94d1f46e79312a99cb9721f38700f24fdf6b`
- Generated M1 profile: seed `20250101`, 43,800 rows, 175,200 readings
- M1 manifest SHA-256: `61432fa39f02249617f5f7b9d25f8274f3ac26a41a8a11e67a994afd37bf5881`
- M1 telemetry SHA-256: `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`
- Database: controller-owned Docker `postgres:16-alpine`, loopback `127.0.0.1:54329`, healthy
- Database revision after upgrade: `002_forecast_metadata` (head)

## Commands and results

Environment for integration commands:

```text
DATABASE_URL=postgresql://flowstead:***@127.0.0.1:54329/flowstead
FLOWSTEAD_M1_MANIFEST=/Users/danie/repos/flowstead-sim/generated-m1/manifest.json
FLOWSTEAD_M1_DATA=/Users/danie/repos/flowstead-sim/generated-m1/telemetry.csv
FLOWSTEAD_M1_SOURCE_SHA=ad5c94d1f46e79312a99cb9721f38700f24fdf6b
```

| Command | Result |
|---|---|
| `uv run --project backend pytest -q backend/tests/unit backend/tests/integration/test_migrations.py` | **PASS** |
| `just test-db-integration` | **PASS** |
| `just db-upgrade` | **PASS** |
| `just db-current` | **PASS** — `002_forecast_metadata` |
| `git diff --check` | **PASS** |

The integration recipe exercised the isolated-database API, forecast, importer, and migration suites. Each integration database was created and dropped by the fixture; the configured base database was not reset.

## Indexed case receipts

| Case | Result | Asserting coverage |
|---|---|---|
| `DB-M4A-FRESH` | **PASS** | Fresh Alembic head schema and approved objects |
| `DB-M4A-STAMP` | **PASS** | Historical populated schema stamped without data mutation; M1/forecast snapshot preserved |
| `DB-M4A-MISMATCH` | **PASS** | Partial, drifted, malformed, and unknown migration states rejected without mutation |
| `DB-M4A-REPEAT` | **PASS** | Repeat upgrade is idempotent; disposable local descendant upgrade/revert preserves baseline |
| `IT-M2-MIGRATE` | **PASS** | Historical migration/importer invariant and disposable rollback |

Related integration regressions passed in the same full gate: immutable M1 import/idempotence and tamper rejection, API authorization/public allowlist behavior, and forecast persistence/idempotence/authorization.

## Repair made during acceptance

The first real integration run exposed an implementation defect in `backend/migrate.py`: PostgreSQL's `information_schema` reports integer-family precision/scale (`bigint=64/0`, `integer=32/0`, `smallint=16/0`), while the validator expected `None`. The expected baseline tuples were corrected to match the actual PostgreSQL catalog. The migration rollback fixture also required the exact historical SQL text; `backend/migrations/002_forecast_metadata_down.sql` was normalized to that contract.

The focused migration suite and full integration gate were rerun after these corrections and passed.

## Limits

This is local acceptance evidence only. It does not establish independent ChatGPT review, hosted deployment readiness, or production-database safety beyond the exercised disposable/local paths.
