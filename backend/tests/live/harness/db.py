"""Disposable loopback PostgreSQL database and migrated live fixture."""

from __future__ import annotations

import gzip
import re
import shutil
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlunsplit

import psycopg
from backend.importer import SOURCE_SHA, import_m1
from backend.migrate import _require_local_database_url, migrate
from psycopg import sql

_DATABASE_NAME = re.compile(r"flowstead_test_[0-9a-f]{32}")
_M1_FIXTURE_DIRECTORY = (
    Path(__file__).resolve().parents[4] / "backend" / "tests" / "fixtures" / "m1"
)


def admin_url_from_environment(environ: dict[str, str]) -> str | None:
    return environ.get("FLOWSTEAD_LIVE_DATABASE_URL") or environ.get("DATABASE_URL")


def _target_url(admin_url: str, database_name: str) -> str:
    parsed = _require_local_database_url(admin_url)
    return urlunsplit(parsed._replace(path=f"/{database_name}", query="", fragment=""))


@contextmanager
def disposable_database(admin_url: str) -> Iterator[str]:
    """Create, migrate, seed, and finally drop one runner-owned database."""
    database_name = f"flowstead_test_{uuid.uuid4().hex}"
    target_url = _target_url(admin_url, database_name)
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {} ").format(sql.Identifier(database_name)))
    try:
        migrate(target_url)
        seed_live_data(target_url)
        yield target_url
    finally:
        if not _DATABASE_NAME.fullmatch(database_name):
            raise RuntimeError("refusing to drop a database outside the live test name format")
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} ").format(sql.Identifier(database_name))
            )


def seed_live_data(database_url: str) -> None:
    """Import the canonical M1 fixture, then add only live-test identities."""
    manifest = _M1_FIXTURE_DIRECTORY / "manifest.json"
    compressed_data = _M1_FIXTURE_DIRECTORY / "telemetry.csv.gz"
    if not manifest.is_file() or not compressed_data.is_file():
        raise RuntimeError(f"canonical M1 fixture is incomplete: {_M1_FIXTURE_DIRECTORY}")
    with tempfile.TemporaryDirectory(prefix="flowstead-live-m1-") as temporary_directory:
        fixture_manifest = Path(temporary_directory) / "manifest.json"
        shutil.copy2(manifest, fixture_manifest)
        data = Path(temporary_directory) / "telemetry.csv"
        with (
            compressed_data.open("rb") as source,
            data.open("wb") as destination,
            gzip.GzipFile(fileobj=source) as decompressed,
        ):
            shutil.copyfileobj(decompressed, destination)
        assert import_m1(database_url, fixture_manifest, data, SOURCE_SHA)

    with (
        psycopg.connect(database_url) as connection,
        connection.transaction(),
        connection.cursor() as cursor,
    ):
        cursor.executemany(
            "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s)",
            [
                ("live-user-a", "plant-01"),
                ("live-user-a", "plant-02"),
                ("live-user-b", "plant-03"),
                ("live-user-shared", "plant-01"),
            ],
        )


__all__ = ["admin_url_from_environment", "disposable_database", "seed_live_data"]
