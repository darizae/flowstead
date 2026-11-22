"""Validate and atomically import the accepted Flowstead M1 CSV into PostgreSQL."""

from __future__ import annotations

import argparse
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import psycopg

# Immutable M1 contract and app-owned Plant metadata are domain-owned
# (flowstead_api.domain.m1). This module re-exports them so the long-standing
# `from backend.importer import APPROVED_PLANT_IDS, ...` contract keeps working
# while `flowstead_api` no longer depends on the repository root on PYTHONPATH.
from flowstead_api.domain.m1 import (
    APPROVED_PLANT_IDS,
    APPROVED_PLANTS,
    CHANNELS,
    CSV_COLUMNS,
    EXPECTED_UNITS,
    MAX_BYTES,
    MAX_READINGS,
    MAX_ROWS,
    QUALITY_VALUES,
    SCHEMA_VERSION,
    SEED,
    SOURCE_SHA,
)
from flowstead_api.infrastructure.importing.validation import (
    ImportValidationError,
    Manifest,
    Reading,
    _fail,
    load_manifest,
    validate_source,
)

__all__ = [
    "APPROVED_PLANTS",
    "APPROVED_PLANT_IDS",
    "CHANNELS",
    "CSV_COLUMNS",
    "EXPECTED_UNITS",
    "MAX_BYTES",
    "MAX_READINGS",
    "MAX_ROWS",
    "QUALITY_VALUES",
    "SCHEMA_VERSION",
    "SEED",
    "SOURCE_SHA",
    "ImportValidationError",
    "Manifest",
    "Reading",
    "import_m1",
    "load_manifest",
    "main",
    "validate_source",
]


def _reading_values(reading: Reading) -> tuple[Any, ...]:
    return (
        reading.plant_id,
        reading.timestamp_utc,
        reading.values[0],
        reading.qualities[0],
        reading.values[1],
        reading.qualities[1],
        reading.values[2],
        reading.qualities[2],
        reading.values[3],
        reading.qualities[3],
    )


def import_m1(database_url: str, manifest_path: Path, data_path: Path, source_sha: str) -> bool:
    manifest, readings = validate_source(manifest_path, data_path, source_sha)
    content_sha = manifest.expected_sha256
    with (
        psycopg.connect(database_url) as connection,
        connection.transaction(),
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "SELECT id, source_sha, schema_version, generator_version, seed, "
            "manifest_sha256, row_count FROM app.ingest_batches "
            "WHERE content_sha256 = %s",
            (content_sha,),
        )
        existing = cursor.fetchone()
        if existing is not None:
            if tuple(existing[1:]) != (
                source_sha,
                manifest.schema_version,
                manifest.generator_version,
                manifest.seed,
                manifest.digest,
                len(readings),
            ):
                raise _fail("existing content digest has incompatible provenance")
            cursor.execute(
                "SELECT count(*) FROM app.hourly_readings WHERE source_batch_id = %s",
                (existing[0],),
            )
            if cursor.fetchone()[0] != len(readings):
                raise _fail("existing ingest batch is incomplete")
            return False
        cursor.execute("SELECT count(*) FROM app.ingest_batches")
        if cursor.fetchone()[0]:
            raise _fail("a different M1 content digest is already imported")
        for plant_id in sorted(APPROVED_PLANT_IDS):
            plant = APPROVED_PLANTS[plant_id]
            cursor.execute(
                """INSERT INTO app.plants
                        (plant_id, name, city, state_code, timezone, latitude, longitude,
                         hydraulic_capacity_gal_h, public_demo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)""",
                (
                    plant_id,
                    plant["name"],
                    plant["city"],
                    plant["state_code"],
                    plant["timezone"],
                    plant["latitude"],
                    plant["longitude"],
                    plant["hydraulic_capacity_gal_h"],
                ),
            )
        cursor.execute(
            """INSERT INTO app.ingest_batches
                    (content_sha256, source_sha, schema_version, generator_version, seed,
                     manifest_sha256, row_count, content_bytes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id""",
            (
                content_sha,
                source_sha,
                manifest.schema_version,
                manifest.generator_version,
                manifest.seed,
                manifest.digest,
                len(readings),
                manifest.expected_bytes,
            ),
        )
        batch_id = cursor.fetchone()[0]
        cursor.executemany(
            """INSERT INTO app.hourly_readings
                    (plant_id, timestamp_utc, influent_flow, influent_flow_quality,
                     rainfall, rainfall_quality, dissolved_oxygen, dissolved_oxygen_quality,
                     effluent_ph, effluent_ph_quality, source_batch_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            ((*_reading_values(reading), batch_id) for reading in readings),
        )
        # Import locally to keep the source validator independent from
        # the runtime messaging package while sharing this transaction.
        from flowstead_api.message_store import emit_ingest_completed

        # Historical 001/002 databases remain stampable without
        # fabricating events for imports that predate the outbox.
        if cursor.execute("SELECT to_regclass('app.message_outbox')").fetchone()[0] is not None:
            emit_ingest_completed(
                connection,
                batch_id=batch_id,
                plant_ids=list(manifest.plants),
                source_sha=source_sha,
                content_sha256=content_sha,
                reading_count=len(readings),
            )
    return True


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args(argv)
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")
    try:
        changed = import_m1(args.database_url, args.manifest, args.data, args.source_sha)
    except (ImportValidationError, psycopg.Error) as exc:
        parser.error(str(exc))
    print("imported" if changed else "already imported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
