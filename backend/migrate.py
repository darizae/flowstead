"""Run the app-local Alembic migrations without resetting PostgreSQL data."""

from __future__ import annotations

import argparse
import os
import re
import uuid
from urllib.parse import SplitResult, unquote, urlsplit
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine


BACKEND_ROOT = Path(__file__).resolve().parent
ALEMBIC_INI = BACKEND_ROOT / "migrations" / "alembic.ini"

EXPECTED_COLUMNS: dict[str, dict[str, tuple[Any, ...]]] = {
    "ingest_batches": {
        "id": ("bigint", None, 64, 0, "NO"),
        "content_sha256": ("character", 64, None, None, "NO"),
        "source_sha": ("character", 40, None, None, "NO"),
        "schema_version": ("text", None, None, None, "NO"),
        "generator_version": ("text", None, None, None, "NO"),
        "seed": ("integer", None, 32, 0, "NO"),
        "manifest_sha256": ("character", 64, None, None, "NO"),
        "row_count": ("integer", None, 32, 0, "NO"),
        "content_bytes": ("integer", None, 32, 0, "NO"),
        "imported_at": ("timestamp with time zone", None, None, None, "NO"),
    },
    "plants": {
        "plant_id": ("text", None, None, None, "NO"),
        "name": ("text", None, None, None, "NO"),
        "city": ("text", None, None, None, "NO"),
        "state_code": ("text", None, None, None, "NO"),
        "timezone": ("text", None, None, None, "NO"),
        "latitude": ("numeric", None, 8, 5, "NO"),
        "longitude": ("numeric", None, 8, 5, "NO"),
        "hydraulic_capacity_gal_h": ("numeric", None, 14, 2, "NO"),
        "public_demo": ("boolean", None, None, None, "NO"),
    },
    "hourly_readings": {
        "plant_id": ("text", None, None, None, "NO"),
        "timestamp_utc": ("timestamp with time zone", None, None, None, "NO"),
        "influent_flow": ("numeric", None, None, None, "YES"),
        "influent_flow_quality": ("text", None, None, None, "NO"),
        "rainfall": ("numeric", None, None, None, "YES"),
        "rainfall_quality": ("text", None, None, None, "NO"),
        "dissolved_oxygen": ("numeric", None, None, None, "YES"),
        "dissolved_oxygen_quality": ("text", None, None, None, "NO"),
        "effluent_ph": ("numeric", None, None, None, "YES"),
        "effluent_ph_quality": ("text", None, None, None, "NO"),
        "source_batch_id": ("bigint", None, 64, 0, "NO"),
    },
    "operator_plant_access": {
        "subject_id": ("text", None, None, None, "NO"),
        "plant_id": ("text", None, None, None, "NO"),
    },
    "forecast_issuances": {
        "id": ("bigint", None, 64, 0, "NO"),
        "plant_id": ("text", None, None, None, "NO"),
        "issued_at": ("timestamp with time zone", None, None, None, "NO"),
        "model_version": ("text", None, None, None, "NO"),
        "source_revision": ("text", None, None, None, "YES"),
        "physical_bound_rule": ("text", None, None, None, "YES"),
    },
    "forecast_hours": {
        "issuance_id": ("bigint", None, 64, 0, "NO"),
        "target_time": ("timestamp with time zone", None, None, None, "NO"),
        "predicted_flow": ("numeric", None, None, None, "NO"),
        "hour_number": ("smallint", None, 16, 0, "NO"),
    },
}

REQUIRED_INDEXES = {
    "ingest_batches_pkey",
    "ingest_batches_content_sha256_key",
    "plants_pkey",
    "hourly_readings_pkey",
    "hourly_readings_timestamp_idx",
    "hourly_readings_plant_time_idx",
    "operator_plant_access_pkey",
    "forecast_issuances_pkey",
    "forecast_issuances_plant_id_issued_at_key",
    "forecast_hours_pkey",
    "forecast_hours_issuance_id_hour_number_key",
    "forecast_hours_target_idx",
}

REQUIRED_CONSTRAINTS = {
    "ingest_batches_pkey",
    "ingest_batches_content_sha256_key",
    "ingest_batches_row_count_check",
    "ingest_batches_content_bytes_check",
    "ingest_batches_source_sha_check",
    "ingest_batches_content_sha256_check",
    "ingest_batches_manifest_sha256_check",
    "plants_pkey",
    "plants_state_code_check",
    "plants_latitude_check",
    "plants_longitude_check",
    "plants_hydraulic_capacity_gal_h_check",
    "plants_plant_id_check",
    "hourly_readings_pkey",
    "hourly_readings_plant_id_fkey",
    "hourly_readings_source_batch_id_fkey",
    "hourly_readings_utc",
    "hourly_readings_influent_quality",
    "hourly_readings_rainfall_quality",
    "hourly_readings_do_quality",
    "hourly_readings_ph_quality",
    "operator_plant_access_pkey",
    "operator_plant_access_plant_id_fkey",
    "operator_plant_access_subject_id_check",
    "forecast_issuances_pkey",
    "forecast_issuances_plant_id_fkey",
    "forecast_issuances_plant_id_issued_at_key",
    "forecast_hours_pkey",
    "forecast_hours_issuance_id_fkey",
    "forecast_hours_predicted_flow_check",
    "forecast_hours_hour_number_check",
    "forecast_hours_issuance_id_hour_number_key",
}


class MigrationStateError(RuntimeError):
    """Raised when database state is not a recognized migration boundary."""


@dataclass(frozen=True)
class DatabaseState:
    clean: bool
    marker_revision: str | None
    alembic_revision: str | None


def _sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


def _alembic_config(connection: Any) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["connection"] = connection
    return config


def _script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))


def _is_descendant(script: ScriptDirectory, revision: str, ancestor: str) -> bool:
    current = script.get_revision(revision)
    while current is not None:
        if current.revision == ancestor:
            return True
        down_revision = current.down_revision
        if isinstance(down_revision, tuple):
            if len(down_revision) != 1:
                return False
            down_revision = down_revision[0]
        current = script.get_revision(down_revision) if down_revision else None
    return False


def _table_columns(
    connection: psycopg.Connection[Any], schema: str, table: str
) -> dict[str, tuple[Any, ...]]:
    rows = connection.execute(
        """
        SELECT column_name, data_type, character_maximum_length,
               numeric_precision, numeric_scale, is_nullable
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        """,
        (schema, table),
    ).fetchall()
    return {row[0]: (row[1], row[2], row[3], row[4], row[5]) for row in rows}


def _schema_catalog(
    connection: psycopg.Connection[Any], schema: str
) -> dict[str, tuple[tuple[Any, ...], ...]]:
    """Compare PostgreSQL-parsed definitions, not user-controlled object names alone."""
    queries = {
        "columns": """
            SELECT t.relname, a.attname, a.attidentity, a.attgenerated,
                   pg_get_expr(d.adbin, d.adrelid), a.attcollation::oid
            FROM pg_class AS t
            JOIN pg_namespace AS n ON n.oid = t.relnamespace
            JOIN pg_attribute AS a ON a.attrelid = t.oid
            LEFT JOIN pg_attrdef AS d ON d.adrelid = t.oid AND d.adnum = a.attnum
            WHERE n.nspname = %s AND t.relkind IN ('r', 'p')
              AND a.attnum > 0 AND NOT a.attisdropped
        """,
        "constraints": """
            SELECT t.relname, c.conname, c.contype, c.convalidated,
                   c.condeferrable, c.condeferred, pg_get_constraintdef(c.oid)
            FROM pg_constraint AS c
            JOIN pg_class AS t ON t.oid = c.conrelid
            JOIN pg_namespace AS n ON n.oid = t.relnamespace
            WHERE n.nspname = %s
        """,
        "indexes": """
            SELECT t.relname, i.relname, pg_get_indexdef(i.oid)
            FROM pg_index AS x
            JOIN pg_class AS i ON i.oid = x.indexrelid
            JOIN pg_class AS t ON t.oid = x.indrelid
            JOIN pg_namespace AS n ON n.oid = t.relnamespace
            WHERE n.nspname = %s
        """,
    }
    result: dict[str, tuple[tuple[Any, ...], ...]] = {}
    for kind, query in queries.items():
        rows = connection.execute(query, (schema,)).fetchall()
        # The reference is compiled on the same PostgreSQL instance; only
        # schema qualification differs between the two catalog snapshots.
        normalized = [
            tuple(value.replace(schema + ".", "app.") if isinstance(value, str) else value
                  for value in row)
            for row in rows
        ]
        result[kind] = tuple(sorted(normalized))
    return result


def _reference_catalog(
    connection: psycopg.Connection[Any], *, include_forecast_metadata: bool
) -> dict[str, tuple[tuple[Any, ...], ...]]:
    """Build the immutable SQL baseline inside a rolled-back savepoint.

    Never stamp based on an unchecked, same-named or weakened definition.
    The comparison DDL is rolled back even if validation raises.
    """
    scratch = "flowstead_probe_" + uuid.uuid4().hex
    initial_sql = (BACKEND_ROOT.parent / "migrations" / "001_initial.sql").read_text(
        encoding="utf-8"
    )
    metadata_sql = (BACKEND_ROOT / "migrations" / "002_forecast_metadata.sql").read_text(
        encoding="utf-8"
    )
    if "CREATE SCHEMA IF NOT EXISTS app;" not in initial_sql:
        raise MigrationStateError("historical baseline SQL has an unexpected schema header")
    initial_sql = initial_sql.replace(
        "CREATE SCHEMA IF NOT EXISTS app;", f"CREATE SCHEMA {scratch};", 1
    ).replace("app.", scratch + ".")
    metadata_sql = metadata_sql.replace("app.", scratch + ".")
    connection.execute("SAVEPOINT flowstead_schema_probe")
    try:
        connection.execute(initial_sql)
        if include_forecast_metadata:
            connection.execute(metadata_sql)
        return _schema_catalog(connection, scratch)
    finally:
        connection.execute("ROLLBACK TO SAVEPOINT flowstead_schema_probe")
        connection.execute("RELEASE SAVEPOINT flowstead_schema_probe")


def _validate_schema(
    connection: psycopg.Connection[Any], *, include_forecast_metadata: bool,
    allow_extensions: bool = False,
) -> None:
    """Require historical objects, permitting only additive descendant DDL.

    Legacy stamping still requires exact equivalence. A recognized descendant
    may add objects, but must retain all original schema invariants.
    """
    if connection.execute("SELECT to_regnamespace('app')").fetchone()[0] is None:
        raise MigrationStateError("app schema is missing")

    expected_columns = {table: dict(columns) for table, columns in EXPECTED_COLUMNS.items()}
    if not include_forecast_metadata:
        expected_columns["forecast_issuances"].pop("source_revision")
        expected_columns["forecast_issuances"].pop("physical_bound_rule")

    for table, expected in expected_columns.items():
        actual = _table_columns(connection, "app", table)
        matches = (
            all(actual.get(name) == definition for name, definition in expected.items())
            if allow_extensions else actual == expected
        )
        if not matches:
            raise MigrationStateError(f"app.{table} columns do not match the approved baseline")

    actual_catalog = _schema_catalog(connection, "app")
    reference_catalog = _reference_catalog(
        connection, include_forecast_metadata=include_forecast_metadata
    )
    for kind, reference in reference_catalog.items():
        if allow_extensions:
            # Preserve the full PostgreSQL-parsed definition of every
            # historical (table, column/constraint/index name).
            actual_by_key = {(row[0], row[1]): row for row in actual_catalog[kind]}
            matches = all(
                actual_by_key.get((row[0], row[1])) == row for row in reference
            )
        else:
            matches = actual_catalog[kind] == reference
        if not matches:
            raise MigrationStateError(
                f"approved baseline {kind} definitions differ; refusing Alembic migration"
            )


def _validate_schema_migrations(connection: psycopg.Connection[Any]) -> tuple[str, ...]:
    columns = _table_columns(connection, "public", "schema_migrations")
    expected = {
        "version": ("text", None, None, None, "NO"),
        "applied_at": ("timestamp with time zone", None, None, None, "NO"),
    }
    if columns != expected:
        raise MigrationStateError("public.schema_migrations does not match its historical shape")

    # Historical marker integrity is part of the stamp boundary. Column names
    # and stored version values alone cannot establish equivalence.
    table_kind = connection.execute(
        """
        SELECT c.relkind FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = 'schema_migrations'
        """
    ).fetchone()
    if table_kind != ("r",):
        raise MigrationStateError("public.schema_migrations is not the historical table")

    column_metadata = set(connection.execute(
        """
        SELECT a.attname, pg_get_expr(d.adbin, d.adrelid),
               a.attidentity, a.attgenerated
        FROM pg_attribute AS a
        JOIN pg_class AS c ON c.oid = a.attrelid
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        LEFT JOIN pg_attrdef AS d ON d.adrelid = c.oid AND d.adnum = a.attnum
        WHERE n.nspname = 'public' AND c.relname = 'schema_migrations'
          AND a.attnum > 0 AND NOT a.attisdropped
        """
    ).fetchall())
    if column_metadata != {
        ("version", None, "", ""),
        ("applied_at", "now()", "", ""),
    }:
        raise MigrationStateError("public.schema_migrations defaults differ from historical shape")

    constraints = connection.execute(
        """
        SELECT conname, contype, convalidated, condeferrable,
               condeferred, pg_get_constraintdef(c.oid)
        FROM pg_constraint AS c
        JOIN pg_class AS t ON t.oid = c.conrelid
        JOIN pg_namespace AS n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public' AND t.relname = 'schema_migrations'
        """
    ).fetchall()
    if constraints != [
        ("schema_migrations_pkey", "p", True, False, False, "PRIMARY KEY (version)")
    ]:
        raise MigrationStateError("public.schema_migrations constraints differ from historical shape")
    return tuple(
        row[0]
        for row in connection.execute(
            "SELECT version FROM public.schema_migrations ORDER BY version"
        ).fetchall()
    )


def _alembic_revision(connection: psycopg.Connection[Any]) -> str | None:
    if connection.execute("SELECT to_regclass('public.alembic_version')").fetchone()[0] is None:
        return None

    # A recognized revision value is insufficient evidence of valid Alembic
    # history. Reject a fabricated or drifted version table before stamping or
    # upgrading a pre-existing database.
    table_kind = connection.execute(
        """
        SELECT c.relkind FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = 'alembic_version'
        """
    ).fetchone()
    expected_columns = {
        "version_num": ("character varying", 32, None, None, "NO")
    }
    if table_kind != ("r",) or _table_columns(connection, "public", "alembic_version") != expected_columns:
        raise MigrationStateError("public.alembic_version table shape is not the Alembic baseline")

    metadata = connection.execute(
        """
        SELECT pg_get_expr(d.adbin, d.adrelid), a.attidentity, a.attgenerated
        FROM pg_attribute AS a
        JOIN pg_class AS t ON t.oid = a.attrelid
        JOIN pg_namespace AS n ON n.oid = t.relnamespace
        LEFT JOIN pg_attrdef AS d ON d.adrelid = t.oid AND d.adnum = a.attnum
        WHERE n.nspname = 'public' AND t.relname = 'alembic_version'
          AND a.attname = 'version_num' AND NOT a.attisdropped
        """
    ).fetchall()
    constraints = connection.execute(
        """
        SELECT c.contype, c.convalidated, c.condeferrable,
               c.condeferred, pg_get_constraintdef(c.oid)
        FROM pg_constraint AS c
        JOIN pg_class AS t ON t.oid = c.conrelid
        JOIN pg_namespace AS n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public' AND t.relname = 'alembic_version'
        """
    ).fetchall()
    if metadata != [(None, "", "")] or constraints != [
        ("p", True, False, False, "PRIMARY KEY (version_num)")
    ]:
        raise MigrationStateError("public.alembic_version integrity constraints differ from Alembic")

    rows = connection.execute("SELECT version_num FROM public.alembic_version").fetchall()
    if len(rows) > 1:
        raise MigrationStateError("public.alembic_version contains multiple revisions")
    return rows[0][0] if rows else None


def _inspect_state(database_url: str) -> DatabaseState:
    with psycopg.connect(database_url) as connection:
        app_exists = connection.execute("SELECT to_regnamespace('app')").fetchone()[0] is not None
        marker_exists = (
            connection.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0]
            is not None
        )
        alembic_revision = _alembic_revision(connection)

        if not app_exists and not marker_exists:
            if alembic_revision is not None:
                raise MigrationStateError(
                    "Alembic revision exists without the historical marker table"
                )
            return DatabaseState(True, None, None)

        if not app_exists and marker_exists:
            markers = _validate_schema_migrations(connection)
            if markers:
                raise MigrationStateError("historical markers exist but app schema is missing")
            if alembic_revision is not None:
                raise MigrationStateError("Alembic revision exists on an empty database")
            return DatabaseState(True, None, None)

        if not marker_exists:
            raise MigrationStateError("app schema exists without historical migration markers")

        markers = _validate_schema_migrations(connection)
        known_markers = (
            "001_initial",
            "002_forecast_metadata",
            "003_jetstream_messages",
        )
        if markers != known_markers[: len(markers)] or not markers:
            raise MigrationStateError(f"unrecognized historical migration markers: {markers!r}")
        if alembic_revision is not None:
            script = _script_directory()
            try:
                known = script.get_revision(alembic_revision)
            except Exception as exc:
                raise MigrationStateError(
                    f"unknown Alembic revision: {alembic_revision}"
                ) from exc
            if known is None or not _is_descendant(script, alembic_revision, markers[-1]):
                raise MigrationStateError("Alembic revision disagrees with historical markers")
            # Version markers alone do not prove descendant schema integrity.
            # Additive local revisions are allowed; dropped/weakened historical
            # columns, constraints or indexes are not.
            if alembic_revision != markers[-1]:
                _validate_schema(
                    connection, include_forecast_metadata=True, allow_extensions=True
                )
                return DatabaseState(False, markers[-1], alembic_revision)
        if len(markers) >= 3:
            _validate_schema(
                connection, include_forecast_metadata=True, allow_extensions=True
            )
        else:
            _validate_schema(connection, include_forecast_metadata=len(markers) == 2)
        return DatabaseState(False, markers[-1], alembic_revision)


def _prepare_existing(database_url: str, state: DatabaseState) -> None:
    if state.clean or state.alembic_revision is not None:
        if state.clean:
            return
        script = _script_directory()
        try:
            script.get_revision(state.alembic_revision)  # type: ignore[arg-type]
        except Exception as exc:
            raise MigrationStateError(
                f"unknown Alembic revision: {state.alembic_revision}"
            ) from exc
        if state.marker_revision == "001_initial" and state.alembic_revision != "001_initial":
            raise MigrationStateError("Alembic revision is ahead of historical migration markers")
        if not _is_descendant(script, state.alembic_revision, state.marker_revision):  # type: ignore[arg-type]
            raise MigrationStateError("Alembic revision disagrees with historical migration markers")
        return

    assert state.marker_revision is not None
    engine = create_engine(_sqlalchemy_url(database_url))
    try:
        with engine.begin() as connection:
            command.stamp(_alembic_config(connection), state.marker_revision)
    finally:
        engine.dispose()


def _run(database_url: str, operation: str, revision: str = "head") -> None:
    engine = create_engine(_sqlalchemy_url(database_url))
    try:
        with engine.begin() as connection:
            config = _alembic_config(connection)
            if operation == "upgrade":
                command.upgrade(config, revision)
            elif operation == "downgrade":
                command.downgrade(config, revision)
            elif operation == "current":
                command.current(config, verbose=True)
            else:
                raise ValueError(f"unsupported Alembic operation: {operation}")
    finally:
        engine.dispose()


def _require_local_database_url(database_url: str) -> SplitResult:
    """Fail before local DB administration if libpq URL options can redirect it.

    For disposable/local-only actions, reject *all* URI query parameters, not
    just known host/hostaddr/dbname overrides: libpq may add new options, and
    even seemingly harmless options are unnecessary for local acceptance.
    """
    try:
        parsed = urlsplit(database_url)
        _ = parsed.port  # also reject malformed port values before connecting
    except ValueError as exc:
        raise MigrationStateError("unsafe local PostgreSQL connection URL") from exc
    if (
        parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or not parsed.path.startswith("/")
        or parsed.path.count("/") != 1
        or not parsed.path[1:]
        or parsed.query
        or parsed.fragment
    ):
        raise MigrationStateError(
            "unsafe local PostgreSQL connection URL: require an explicit "
            "loopback database without libpq query options"
        )
    return parsed


def _require_disposable_database(database_url: str, *, disposable: bool) -> None:
    if not disposable:
        raise MigrationStateError(
            "destructive rollback refused: explicitly mark a loopback "
            "flowstead_test_<32 hex> database as disposable"
        )
    try:
        parsed = _require_local_database_url(database_url)
        database_name = unquote(parsed.path[1:])
        safe = re.fullmatch(r"flowstead_test_[0-9a-f]{32}", database_name)
    except MigrationStateError:
        safe = False
    if not safe:
        raise MigrationStateError(
            "destructive rollback refused: explicitly mark a loopback "
            "flowstead_test_<32 hex> database as disposable "
            "and exclude libpq query options"
        )


def migrate(
    database_url: str, rollback: bool = False, *, disposable: bool = False
) -> None:
    """Upgrade safely; downgrade only an explicitly disposable, isolated local DB."""
    if rollback:
        _require_disposable_database(database_url, disposable=disposable)
    state = _inspect_state(database_url)
    if rollback:
        if state.clean:
            return
        _prepare_existing(database_url, state)
        _run(database_url, "downgrade", "base")
        return

    if state.clean:
        _run(database_url, "upgrade")
        return
    _prepare_existing(database_url, state)
    _run(database_url, "upgrade")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("upgrade", "current"), nargs="?", default="upgrade")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--disposable", action="store_true",
                        help="required for rollback on an isolated flowstead_test_<uuid> DB")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")
    if args.operation == "current" and args.rollback:
        parser.error("--rollback cannot be combined with current")
    if args.operation == "current":
        _run(args.database_url, "current")
    else:
        migrate(args.database_url, rollback=args.rollback, disposable=args.disposable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
