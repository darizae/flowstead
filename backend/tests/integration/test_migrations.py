from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

from backend.migrate import MigrationStateError, migrate

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
INITIAL_SQL = REPO_ROOT / "migrations" / "001_initial.sql"
INITIAL_DOWN_SQL = REPO_ROOT / "migrations" / "001_initial_down.sql"
METADATA_SQL = REPO_ROOT / "backend" / "migrations" / "002_forecast_metadata.sql"
METADATA_DOWN_SQL = REPO_ROOT / "backend" / "migrations" / "002_forecast_metadata_down.sql"

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="set DATABASE_URL for real PostgreSQL migration acceptance tests",
)


@pytest.fixture(autouse=True)
def disposable_database() -> None:
    migrate(DATABASE_URL, rollback=True)  # type: ignore[arg-type]
    yield
    migrate(DATABASE_URL, rollback=True)  # type: ignore[arg-type]


def _historical_upgrade() -> None:
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        with connection.transaction():
            connection.execute(
                "CREATE TABLE IF NOT EXISTS public.schema_migrations ("
                "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()"
                ")"
            )
            connection.execute(INITIAL_SQL.read_text(encoding="utf-8"))
            connection.execute("INSERT INTO public.schema_migrations (version) VALUES ('001_initial')")
            connection.execute(METADATA_SQL.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO public.schema_migrations (version) VALUES ('002_forecast_metadata')"
            )
            connection.execute(
                "INSERT INTO app.ingest_batches "
                "(content_sha256, source_sha, schema_version, generator_version, seed, "
                "manifest_sha256, row_count, content_bytes) VALUES "
                "('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', "
                "'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'm1.v1', 'test', 20250101, "
                "'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 1, 1)"
            )
            connection.execute(
                "INSERT INTO app.plants "
                "(plant_id, name, city, state_code, timezone, latitude, longitude, hydraulic_capacity_gal_h) "
                "VALUES ('plant-01', 'Test Plant', 'Tampa', 'FL', 'America/New_York', "
                "27.95, -82.45, 1000)"
            )
            connection.execute(
                "INSERT INTO app.hourly_readings "
                "(plant_id, timestamp_utc, influent_flow, influent_flow_quality, rainfall, "
                "rainfall_quality, dissolved_oxygen, dissolved_oxygen_quality, effluent_ph, "
                "effluent_ph_quality, source_batch_id) VALUES "
                "('plant-01', '2025-01-01T00:00:00Z', 12.5, 'valid', NULL, 'missing', "
                "2.1, 'valid', 7.2, 'invalid', 1)"
            )
            connection.execute(
                "INSERT INTO app.forecast_issuances "
                "(plant_id, issued_at, model_version, source_revision, physical_bound_rule) "
                "VALUES ('plant-01', '2025-01-01T01:00:00Z', 'baseline-v1', 'm1', "
                "'nonnegative_influent_flow')"
            )
            connection.execute(
                "INSERT INTO app.forecast_hours "
                "(issuance_id, target_time, predicted_flow, hour_number) "
                "VALUES (1, '2025-01-01T02:00:00Z', 12.5, 1)"
            )


def _snapshot() -> tuple[tuple[tuple[object, ...], ...], ...]:
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        return (
            tuple(
                connection.execute(
                    "SELECT * FROM app.hourly_readings ORDER BY plant_id, timestamp_utc"
                ).fetchall()
            ),
            tuple(
                connection.execute(
                    "SELECT * FROM app.forecast_issuances ORDER BY id"
                ).fetchall()
            ),
            tuple(
                connection.execute(
                    "SELECT * FROM app.forecast_hours ORDER BY issuance_id, hour_number"
                ).fetchall()
            ),
        )


def test_fresh_alembic_head_has_approved_schema() -> None:
    """Case: DB-M4A-FRESH"""
    migrate(DATABASE_URL)  # type: ignore[arg-type]
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'app'"
            ).fetchall()
        }
        assert tables == {
            "ingest_batches",
            "plants",
            "hourly_readings",
            "operator_plant_access",
            "forecast_issuances",
            "forecast_hours",
        }
        assert connection.execute(
            "SELECT version FROM public.schema_migrations ORDER BY version"
        ).fetchall() == [("001_initial",), ("002_forecast_metadata",)]
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == (
            "002_forecast_metadata",
        )


def test_old_populated_database_is_stamped_without_data_change() -> None:
    """Case: DB-M4A-STAMP"""
    _historical_upgrade()
    before = _snapshot()
    migrate(DATABASE_URL)  # type: ignore[arg-type]
    assert _snapshot() == before
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        assert connection.execute("SELECT count(*) FROM app.plants").fetchone() == (1,)
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == (
            "002_forecast_metadata",
        )


def test_partial_schema_is_rejected_without_mutation() -> None:
    """Case: DB-M4A-MISMATCH"""
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        with connection.transaction():
            connection.execute("CREATE SCHEMA app")
            connection.execute("CREATE TABLE app.partial (id integer)")
    try:
        with pytest.raises(MigrationStateError, match="historical migration markers"):
            migrate(DATABASE_URL)  # type: ignore[arg-type]
        with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
            assert connection.execute("SELECT to_regclass('app.partial')").fetchone() == (
                "app.partial",
            )
            assert connection.execute(
                "SELECT to_regclass('public.alembic_version')"
            ).fetchone() == (None,)
    finally:
        with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
            with connection.transaction():
                connection.execute(INITIAL_DOWN_SQL.read_text(encoding="utf-8"))


def test_repeated_upgrade_does_not_change_revision_or_markers() -> None:
    """Case: DB-M4A-REPEAT"""
    migrate(DATABASE_URL)  # type: ignore[arg-type]
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        before = connection.execute(
            "SELECT version, applied_at FROM public.schema_migrations ORDER BY version"
        ).fetchall()
    migrate(DATABASE_URL)  # type: ignore[arg-type]
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        assert connection.execute(
            "SELECT version, applied_at FROM public.schema_migrations ORDER BY version"
        ).fetchall() == before
        assert connection.execute("SELECT count(*) FROM public.alembic_version").fetchone() == (1,)


def test_historical_migration_files_remain_reversible() -> None:
    """Case: IT-M2-MIGRATE"""
    assert INITIAL_DOWN_SQL.read_text(encoding="utf-8") == "DROP SCHEMA IF EXISTS app CASCADE;\n"
    assert METADATA_DOWN_SQL.read_text(encoding="utf-8") == (
        "ALTER TABLE app.forecast_issuances\n"
        "    DROP COLUMN IF EXISTS physical_bound_rule;\n"
        "ALTER TABLE app.forecast_issuances\n"
        "    DROP COLUMN IF EXISTS source_revision;\n"
    )
    migrate(DATABASE_URL)  # type: ignore[arg-type]
    migrate(DATABASE_URL, rollback=True)  # type: ignore[arg-type]
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        assert connection.execute("SELECT to_regclass('app.plants')").fetchone() == (None,)
