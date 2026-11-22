"""Real M1 importer regressions on isolated disposable PostgreSQL databases."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlunsplit

import psycopg
import pytest
from backend.importer import ImportValidationError, import_m1
from backend.migrate import _require_local_database_url, migrate
from psycopg import sql

DATABASE_URL = os.environ.get("DATABASE_URL")
MANIFEST = os.environ.get("FLOWSTEAD_M1_MANIFEST")
DATA = os.environ.get("FLOWSTEAD_M1_DATA")
SOURCE_SHA = os.environ.get("FLOWSTEAD_M1_SOURCE_SHA", "ad5c94d1f46e79312a99cb9721f38700f24fdf6b")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not MANIFEST or not DATA,
    reason="set DATABASE_URL, FLOWSTEAD_M1_MANIFEST and FLOWSTEAD_M1_DATA for the immutable M1 source",
)


@pytest.fixture
def isolated_url() -> Iterator[str]:
    """Never TRUNCATE or recreate the database named by DATABASE_URL."""
    assert DATABASE_URL is not None
    admin_url = DATABASE_URL  # pin the validated endpoint through teardown
    # Validate before opening the admin connection: URI query parameters such
    # as hostaddr/host/dbname can override the visually checked destination.
    parsed = _require_local_database_url(admin_url)
    name = "flowstead_test_" + uuid.uuid4().hex
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    target = urlunsplit(parsed._replace(path="/" + name, query="", fragment=""))
    try:
        migrate(target)
        yield target
    finally:
        # Only the uniquely generated test database is eligible for teardown.
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def _count(url: str, table: str) -> int:
    with psycopg.connect(url) as connection:
        return connection.execute(f"SELECT count(*) FROM app.{table}").fetchone()[0]


def test_migration_and_full_import_are_idempotent(isolated_url: str) -> None:
    """Cases: DB-M4A-FRESH, IT-M2-MIGRATE"""
    migrate(isolated_url)
    assert import_m1(isolated_url, Path(MANIFEST), Path(DATA), SOURCE_SHA)
    first = (
        _count(isolated_url, "plants"),
        _count(isolated_url, "hourly_readings"),
        _count(isolated_url, "ingest_batches"),
    )
    assert first == (5, 43_800, 1)
    assert not import_m1(isolated_url, Path(MANIFEST), Path(DATA), SOURCE_SHA)
    assert (
        _count(isolated_url, "plants"),
        _count(isolated_url, "hourly_readings"),
        _count(isolated_url, "ingest_batches"),
    ) == first


def test_tampered_source_sha_does_not_change_database(isolated_url: str) -> None:
    with pytest.raises(ImportValidationError):
        import_m1(isolated_url, Path(MANIFEST), Path(DATA), "0" * 40)
    assert _count(isolated_url, "ingest_batches") == 0


def test_repeated_migration_preserves_imported_data(isolated_url: str) -> None:
    """Case: IT-M2-MIGRATE"""
    assert import_m1(isolated_url, Path(MANIFEST), Path(DATA), SOURCE_SHA)
    before = (
        _count(isolated_url, "plants"),
        _count(isolated_url, "hourly_readings"),
        _count(isolated_url, "ingest_batches"),
    )
    assert before == (5, 43_800, 1)
    migrate(isolated_url)
    migrate(isolated_url)
    assert (
        _count(isolated_url, "plants"),
        _count(isolated_url, "hourly_readings"),
        _count(isolated_url, "ingest_batches"),
    ) == before
