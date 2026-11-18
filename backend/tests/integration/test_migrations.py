"""Real PostgreSQL T-004a migration acceptance in isolated disposable databases."""

from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlunsplit

import psycopg
from psycopg import sql
import pytest

import backend.migrate as migrations
from backend.importer import import_m1
from backend.migrate import MigrationStateError, _require_local_database_url, migrate
from flowstead_api.database import Database

DATABASE_URL = os.environ.get("DATABASE_URL")
MANIFEST = os.environ.get("FLOWSTEAD_M1_MANIFEST")
DATA = os.environ.get("FLOWSTEAD_M1_DATA")
SOURCE_SHA = "ad5c94d1f46e79312a99cb9721f38700f24fdf6b"
REPO_ROOT = Path(__file__).resolve().parents[3]
INITIAL_SQL = REPO_ROOT / "migrations" / "001_initial.sql"
INITIAL_DOWN_SQL = REPO_ROOT / "migrations" / "001_initial_down.sql"
METADATA_SQL = REPO_ROOT / "backend" / "migrations" / "002_forecast_metadata.sql"
METADATA_DOWN_SQL = REPO_ROOT / "backend" / "migrations" / "002_forecast_metadata_down.sql"

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is required for real PostgreSQL T-004a acceptance",
)


@pytest.fixture
def isolated_url() -> str:
    """Create one never-before-used local database; never reset shared M1 records."""
    assert DATABASE_URL is not None
    admin_url = DATABASE_URL  # keep the validated endpoint stable for teardown
    # Reject libpq target overrides before CREATE/DROP DATABASE admin I/O.
    parsed = _require_local_database_url(admin_url)
    name = "flowstead_test_" + uuid.uuid4().hex
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    target = urlunsplit(parsed._replace(path="/" + name, query="", fragment=""))
    try:
        yield target
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()", (name,)
            )
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def _historical_upgrade(url: str, *, sample: bool = True) -> None:
    with psycopg.connect(url) as connection:
        with connection.transaction():
            connection.execute(
                "CREATE TABLE public.schema_migrations ("
                "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            connection.execute(INITIAL_SQL.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO public.schema_migrations(version) VALUES ('001_initial')"
            )
            connection.execute(METADATA_SQL.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO public.schema_migrations(version) VALUES ('002_forecast_metadata')"
            )
            if sample:
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
                    "(plant_id, name, city, state_code, timezone, latitude, longitude, "
                    "hydraulic_capacity_gal_h) VALUES "
                    "('plant-01', 'Test Plant', 'Tampa', 'FL', 'America/New_York', "
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


def _snapshot(url: str) -> dict[str, str]:
    """Hash all rows, including forecast receipts and immutable old markers."""
    tables = {
        "app.ingest_batches": "id",
        "app.plants": "plant_id",
        "app.hourly_readings": "plant_id, timestamp_utc",
        "app.operator_plant_access": "subject_id, plant_id",
        "app.forecast_issuances": "id",
        "app.forecast_hours": "issuance_id, hour_number",
        "public.schema_migrations": "version",
    }
    result: dict[str, str] = {}
    with psycopg.connect(url) as connection:
        with connection.cursor() as cursor:
            for table, order in tables.items():
                digest = hashlib.sha256()
                # Hash the immutable *historical* fields. A later Alembic
                # revision is allowed to add columns without changing M1 data.
                selected = (
                    ", ".join(migrations.EXPECTED_COLUMNS[table.removeprefix("app.")])
                    if table.startswith("app.") else "*"
                )
                with cursor.copy(
                    f"COPY (SELECT {selected} FROM {table} ORDER BY {order}) "
                    "TO STDOUT WITH (FORMAT CSV)"
                ) as copy:
                    for block in copy:
                        digest.update(block)
                result[table] = digest.hexdigest()
    return result


def _version(url: str) -> str | None:
    with psycopg.connect(url) as connection:
        row = connection.execute(
            "SELECT to_regclass('public.alembic_version')"
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return connection.execute("SELECT version_num FROM public.alembic_version").fetchone()[0]


def test_fresh_alembic_head_has_approved_schema(isolated_url: str) -> None:
    """Case: DB-M4A-FRESH"""
    migrate(isolated_url)
    with psycopg.connect(isolated_url) as connection:
        assert set(
            row[0] for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'app'"
            ).fetchall()
        ) == set(migrations.EXPECTED_COLUMNS) | {
            "message_outbox",
            "message_inbox",
            "message_failures",
            "forecast_jobs",
        }
        # Compare actual parsed CHECK/FK/unique/index definitions and defaults
        # with the exact applied historical SQL, not merely object names.
        migrations._validate_schema(
            connection, include_forecast_metadata=True, allow_extensions=True
        )
        assert connection.execute(
            "SELECT version FROM public.schema_migrations ORDER BY version"
        ).fetchall() == [
            ("001_initial",),
            ("002_forecast_metadata",),
            ("003_jetstream_messages",),
        ]
    assert _version(isolated_url) == "003_jetstream_messages"


def test_old_populated_database_is_stamped_without_data_change(isolated_url: str) -> None:
    """Case: DB-M4A-STAMP"""
    _historical_upgrade(isolated_url)
    before = _snapshot(isolated_url)
    migrate(isolated_url)
    after = _snapshot(isolated_url)
    assert {
        table: digest for table, digest in after.items()
        if table != "public.schema_migrations"
    } == {
        table: digest for table, digest in before.items()
        if table != "public.schema_migrations"
    }
    assert _version(isolated_url) == "003_jetstream_messages"


def test_full_immutable_m1_and_forecast_are_preserved_on_stamp(isolated_url: str) -> None:
    """Case: DB-M4A-STAMP"""
    if not MANIFEST or not DATA:
        pytest.skip("full immutable M1 files are required for DB-M4A-STAMP")
    _historical_upgrade(isolated_url, sample=False)
    assert import_m1(isolated_url, Path(MANIFEST), Path(DATA), SOURCE_SHA)
    receipt = Database(isolated_url).build_forecast("plant-01")
    assert receipt.available and len(receipt.points) == 12
    with psycopg.connect(isolated_url) as connection:
        assert connection.execute("SELECT count(*) FROM app.hourly_readings").fetchone() == (43_800,)
    before = _snapshot(isolated_url)
    migrate(isolated_url)
    after = _snapshot(isolated_url)
    assert {
        table: digest for table, digest in after.items()
        if table != "public.schema_migrations"
    } == {
        table: digest for table, digest in before.items()
        if table != "public.schema_migrations"
    }
    assert _version(isolated_url) == "003_jetstream_messages"


def test_partial_schema_is_rejected_without_mutation(isolated_url: str) -> None:
    """Case: DB-M4A-MISMATCH"""
    with psycopg.connect(isolated_url) as connection:
        connection.execute("CREATE SCHEMA app")
        connection.execute("CREATE TABLE app.partial (id integer)")
    with pytest.raises(MigrationStateError, match="historical migration markers"):
        migrate(isolated_url)
    with psycopg.connect(isolated_url) as connection:
        assert connection.execute("SELECT to_regclass('app.partial')").fetchone()[0] is not None
    assert _version(isolated_url) is None


@pytest.mark.parametrize("mismatch", ["index", "constraint"])
def test_same_name_wrong_definition_is_never_stamped(
    isolated_url: str, mismatch: str
) -> None:
    """Case: DB-M4A-MISMATCH"""
    _historical_upgrade(isolated_url)
    with psycopg.connect(isolated_url) as connection:
        if mismatch == "index":
            connection.execute("DROP INDEX app.hourly_readings_timestamp_idx")
            connection.execute(
                "CREATE INDEX hourly_readings_timestamp_idx "
                "ON app.hourly_readings (plant_id)"
            )
        else:
            connection.execute(
                "ALTER TABLE app.plants DROP CONSTRAINT plants_state_code_check"
            )
            connection.execute(
                "ALTER TABLE app.plants ADD CONSTRAINT plants_state_code_check "
                "CHECK (state_code IN ('FL', 'TX'))"
            )
    before = _snapshot(isolated_url)
    with pytest.raises(MigrationStateError, match="definitions differ"):
        migrate(isolated_url)
    assert _snapshot(isolated_url) == before
    assert _version(isolated_url) is None


@pytest.mark.parametrize("broken", ("primary_key", "column_width", "default"))
def test_known_revision_in_malformed_alembic_table_is_rejected(
    isolated_url: str, broken: str
) -> None:
    """Case: DB-M4A-MISMATCH"""
    _historical_upgrade(isolated_url)
    with psycopg.connect(isolated_url) as connection:
        connection.execute(
            "CREATE TABLE public.alembic_version "
            "(version_num varchar(32) PRIMARY KEY)"
        )
        connection.execute(
            "INSERT INTO public.alembic_version VALUES ('002_forecast_metadata')"
        )
        if broken == "primary_key":
            connection.execute(
                "ALTER TABLE public.alembic_version "
                "DROP CONSTRAINT alembic_version_pkey"
            )
        elif broken == "column_width":
            connection.execute(
                "ALTER TABLE public.alembic_version "
                "ALTER COLUMN version_num TYPE varchar(64)"
            )
        else:
            connection.execute(
                "ALTER TABLE public.alembic_version "
                "ALTER COLUMN version_num SET DEFAULT '002_forecast_metadata'"
            )
    before = _snapshot(isolated_url)
    with pytest.raises(MigrationStateError, match=r"public[.]alembic_version"):
        migrate(isolated_url)
    assert _snapshot(isolated_url) == before
    assert _version(isolated_url) == "002_forecast_metadata"


def test_unknown_alembic_revision_is_rejected_without_mutation(isolated_url: str) -> None:
    """Case: DB-M4A-MISMATCH"""
    _historical_upgrade(isolated_url)
    with psycopg.connect(isolated_url) as connection:
        connection.execute(
            "CREATE TABLE public.alembic_version (version_num varchar(32) PRIMARY KEY)"
        )
        connection.execute(
            "INSERT INTO public.alembic_version VALUES ('unrecognized_change')"
        )
    before = _snapshot(isolated_url)
    with pytest.raises(MigrationStateError, match="unknown Alembic revision"):
        migrate(isolated_url)
    assert _snapshot(isolated_url) == before
    assert _version(isolated_url) == "unrecognized_change"


@pytest.mark.parametrize("broken", ("primary_key", "default"))
def test_drifted_historical_marker_table_is_never_stamped(
    isolated_url: str, broken: str
) -> None:
    """Case: DB-M4A-MISMATCH"""
    _historical_upgrade(isolated_url)
    with psycopg.connect(isolated_url) as connection:
        if broken == "primary_key":
            connection.execute(
                "ALTER TABLE public.schema_migrations "
                "DROP CONSTRAINT schema_migrations_pkey"
            )
        else:
            connection.execute(
                "ALTER TABLE public.schema_migrations "
                "ALTER COLUMN applied_at DROP DEFAULT"
            )
    before = _snapshot(isolated_url)
    with pytest.raises(MigrationStateError, match=r"public[.]schema_migrations"):
        migrate(isolated_url)
    assert _snapshot(isolated_url) == before
    assert _version(isolated_url) is None


def _install_local_descendant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Create a disposable 004 revision for repeat and drift checks."""
    local_script = tmp_path / "alembic"
    shutil.copytree(migrations.ALEMBIC_INI.parent / "alembic", local_script)
    (local_script / "versions" / "004_local_roundtrip.py").write_text(
        '"""Local disposable-only revision for DB-M4A-REPEAT."""\n'
        "from alembic import op\n"
        "revision = '004_local_roundtrip'\n"
        "down_revision = '003_jetstream_messages'\n"
        "branch_labels = None\n"
        "depends_on = None\n"
        "def upgrade():\n"
        "    op.execute('ALTER TABLE app.plants ADD COLUMN local_probe integer')\n"
        "def downgrade():\n"
        "    op.execute('ALTER TABLE app.plants DROP COLUMN local_probe')\n",
        encoding="utf-8",
    )
    local_ini = tmp_path / "alembic.ini"
    local_ini.write_text(
        f"[alembic]\nscript_location = {local_script}\n"
        "sqlalchemy.url = postgresql+psycopg://\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(migrations, "ALEMBIC_INI", local_ini)


def test_repeat_and_local_descendant_upgrade_revert(
    isolated_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Case: DB-M4A-REPEAT"""
    _historical_upgrade(isolated_url)
    migrate(isolated_url)
    before = _snapshot(isolated_url)
    migrate(isolated_url)
    assert _snapshot(isolated_url) == before

    _install_local_descendant(tmp_path, monkeypatch)
    migrate(isolated_url)
    assert _version(isolated_url) == "004_local_roundtrip"
    migrate(isolated_url)  # recognized descendant may have an extra column
    assert _snapshot(isolated_url) == before
    migrations._run(isolated_url, "downgrade", "003_jetstream_messages")
    assert _version(isolated_url) == "003_jetstream_messages"
    assert _snapshot(isolated_url) == before
    migrate(isolated_url)
    assert _version(isolated_url) == "004_local_roundtrip"


@pytest.mark.parametrize("malformed", ("table", "column", "constraint", "index"))
def test_recognized_descendant_rejects_baseline_drift(
    isolated_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    malformed: str,
) -> None:
    """Case: DB-M4A-MISMATCH"""
    _historical_upgrade(isolated_url)
    migrate(isolated_url)
    _install_local_descendant(tmp_path, monkeypatch)
    migrate(isolated_url)
    assert _version(isolated_url) == "004_local_roundtrip"

    with psycopg.connect(isolated_url) as connection:
        if malformed == "table":
            connection.execute("DROP TABLE app.operator_plant_access")
        elif malformed == "column":
            connection.execute("ALTER TABLE app.plants DROP COLUMN city")
        elif malformed == "constraint":
            connection.execute(
                "ALTER TABLE app.plants DROP CONSTRAINT plants_state_code_check"
            )
            connection.execute(
                "ALTER TABLE app.plants ADD CONSTRAINT plants_state_code_check "
                "CHECK (state_code IN ('FL', 'TX'))"
            )
        else:
            connection.execute("DROP INDEX app.hourly_readings_timestamp_idx")
            connection.execute(
                "CREATE INDEX hourly_readings_timestamp_idx "
                "ON app.hourly_readings (plant_id)"
            )

    before = None if malformed in {"table", "column"} else _snapshot(isolated_url)
    with pytest.raises(MigrationStateError, match="approved baseline"):
        migrate(isolated_url)
    assert _version(isolated_url) == "004_local_roundtrip"
    if before is not None:
        assert _snapshot(isolated_url) == before
    else:
        with psycopg.connect(isolated_url) as connection:
            if malformed == "table":
                assert connection.execute(
                    "SELECT to_regclass('app.operator_plant_access')"
                ).fetchone() == (None,)
            else:
                assert connection.execute(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema = 'app' AND table_name = 'plants' "
                    "AND column_name = 'city'"
                ).fetchone() == (0,)


def test_historical_migrations_are_reversible_only_on_disposable_db(isolated_url: str) -> None:
    """Case: IT-M2-MIGRATE"""
    assert INITIAL_DOWN_SQL.read_text(encoding="utf-8") == "DROP SCHEMA IF EXISTS app CASCADE;\n"
    assert METADATA_DOWN_SQL.read_text(encoding="utf-8") == (
        "ALTER TABLE app.forecast_issuances\n"
        "    DROP COLUMN IF EXISTS physical_bound_rule;\n"
        "ALTER TABLE app.forecast_issuances\n"
        "    DROP COLUMN IF EXISTS source_revision;\n"
    )
    migrate(isolated_url)
    migrate(isolated_url, rollback=True, disposable=True)
    with psycopg.connect(isolated_url) as connection:
        assert connection.execute("SELECT to_regclass('app.plants')").fetchone() == (None,)
