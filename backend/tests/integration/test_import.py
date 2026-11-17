from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

from backend.importer import ImportValidationError, import_m1
from backend.migrate import migrate

DATABASE_URL = os.environ.get("DATABASE_URL")
MANIFEST = os.environ.get("FLOWSTEAD_M1_MANIFEST")
DATA = os.environ.get("FLOWSTEAD_M1_DATA")
SOURCE_SHA = os.environ.get("FLOWSTEAD_M1_SOURCE_SHA", "ad5c94d1f46e79312a99cb9721f38700f24fdf6b")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not MANIFEST or not DATA,
    reason="set DATABASE_URL, FLOWSTEAD_M1_MANIFEST and FLOWSTEAD_M1_DATA for the immutable M1 source",
)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    migrate(DATABASE_URL)  # type: ignore[arg-type]
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        with connection.transaction():
            connection.execute("TRUNCATE app.hourly_readings, app.forecast_hours, app.forecast_issuances, "
                               "app.operator_plant_access, app.plants, app.ingest_batches RESTART IDENTITY")


def _count(table: str) -> int:
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        return connection.execute(f"SELECT count(*) FROM app.{table}").fetchone()[0]


def test_migration_and_full_import_are_idempotent() -> None:
    migrate(DATABASE_URL)  # type: ignore[arg-type]
    assert import_m1(DATABASE_URL, Path(MANIFEST), Path(DATA), SOURCE_SHA)  # type: ignore[arg-type]
    first = (_count("plants"), _count("hourly_readings"), _count("ingest_batches"))
    assert first == (5, 43_800, 1)
    assert not import_m1(DATABASE_URL, Path(MANIFEST), Path(DATA), SOURCE_SHA)  # type: ignore[arg-type]
    assert (_count("plants"), _count("hourly_readings"), _count("ingest_batches")) == first


def test_tampered_source_sha_does_not_change_database() -> None:
    with pytest.raises(ImportValidationError):
        import_m1(DATABASE_URL, Path(MANIFEST), Path(DATA), "0" * 40)  # type: ignore[arg-type]
    assert _count("ingest_batches") == 0


def test_migration_is_reversible_on_disposable_database() -> None:
    migrate(DATABASE_URL, rollback=True)  # type: ignore[arg-type]
    with psycopg.connect(DATABASE_URL) as connection:
        assert connection.execute(
            "SELECT to_regclass('app.hourly_readings')"
        ).fetchone()[0] is None
    migrate(DATABASE_URL)  # type: ignore[arg-type]
