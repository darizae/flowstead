"""Run the app-local Alembic migrations without resetting PostgreSQL data."""

from __future__ import annotations

import argparse
import os
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
        "id": ("bigint", None, None, None, "NO"),
        "content_sha256": ("character", 64, None, None, "NO"),
        "source_sha": ("character", 40, None, None, "NO"),
        "schema_version": ("text", None, None, None, "NO"),
        "generator_version": ("text", None, None, None, "NO"),
        "seed": ("integer", None, None, None, "NO"),
        "manifest_sha256": ("character", 64, None, None, "NO"),
        "row_count": ("integer", None, None, None, "NO"),
        "content_bytes": ("integer", None, None, None, "NO"),
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
        "source_batch_id": ("bigint", None, None, None, "NO"),
    },
    "operator_plant_access": {
        "subject_id": ("text", None, None, None, "NO"),
        "plant_id": ("text", None, None, None, "NO"),
    },
    "forecast_issuances": {
        "id": ("bigint", None, None, None, "NO"),
        "plant_id": ("text", None, None, None, "NO"),
        "issued_at": ("timestamp with time zone", None, None, None, "NO"),
        "model_version": ("text", None, None, None, "NO"),
        "source_revision": ("text", None, None, None, "YES"),
        "physical_bound_rule": ("text", None, None, None, "YES"),
    },
    "forecast_hours": {
        "issuance_id": ("bigint", None, None, None, "NO"),
        "target_time": ("timestamp with time zone", None, None, None, "NO"),
        "predicted_flow": ("numeric", None, None, None, "NO"),
        "hour_number": ("smallint", None, None, None, "NO"),
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


def _validate_schema(
    connection: psycopg.Connection[Any], *, include_forecast_metadata: bool
) -> None:
    if connection.execute("SELECT to_regnamespace('app')").fetchone()[0] is None:
        raise MigrationStateError("app schema is missing")

    expected_columns = {table: dict(columns) for table, columns in EXPECTED_COLUMNS.items()}
    if not include_forecast_metadata:
        expected_columns["forecast_issuances"].pop("source_revision")
        expected_columns["forecast_issuances"].pop("physical_bound_rule")

    for table, expected in expected_columns.items():
        actual = _table_columns(connection, "app", table)
        if actual != expected:
            raise MigrationStateError(f"app.{table} columns do not match the approved baseline")

    indexes = {
        row[0]
        for row in connection.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'app'"
        ).fetchall()
    }
    missing_indexes = REQUIRED_INDEXES - indexes
    if missing_indexes:
        raise MigrationStateError(
            f"approved baseline indexes are missing: {', '.join(sorted(missing_indexes))}"
        )

    constraints = {
        row[0]
        for row in connection.execute(
            """
            SELECT conname
            FROM pg_constraint
            WHERE connamespace = 'app'::regnamespace
            """
        ).fetchall()
    }
    missing_constraints = REQUIRED_CONSTRAINTS - constraints
    if missing_constraints:
        raise MigrationStateError(
            f"approved baseline constraints are missing: {', '.join(sorted(missing_constraints))}"
        )

def _validate_schema_migrations(connection: psycopg.Connection[Any]) -> tuple[str, ...]:
    columns = _table_columns(connection, "public", "schema_migrations")
    expected = {
        "version": ("text", None, None, None, "NO"),
        "applied_at": ("timestamp with time zone", None, None, None, "NO"),
    }
    if columns != expected:
        raise MigrationStateError("public.schema_migrations does not match its historical shape")
    return tuple(
        row[0]
        for row in connection.execute(
            "SELECT version FROM public.schema_migrations ORDER BY version"
        ).fetchall()
    )


def _alembic_revision(connection: psycopg.Connection[Any]) -> str | None:
    if connection.execute("SELECT to_regclass('public.alembic_version')").fetchone()[0] is None:
        return None
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
        if markers not in (("001_initial",), ("001_initial", "002_forecast_metadata")):
            raise MigrationStateError(f"unrecognized historical migration markers: {markers!r}")
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


def migrate(database_url: str, rollback: bool = False) -> None:
    """Upgrade to Alembic head, or downgrade to base for disposable local databases."""
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
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")
    if args.operation == "current" and args.rollback:
        parser.error("--rollback cannot be combined with current")
    if args.operation == "current":
        _run(args.database_url, "current")
    else:
        migrate(args.database_url, rollback=args.rollback)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
