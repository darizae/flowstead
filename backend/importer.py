"""Validate and atomically import the accepted Flowstead M1 CSV into PostgreSQL."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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


class ImportValidationError(ValueError):
    """Raised before any database mutation for invalid source input."""


@dataclass(frozen=True)
class Manifest:
    path: Path
    digest: str
    schema_version: str
    generator_version: str
    seed: int
    plants: frozenset[str]
    data_name: str
    expected_sha256: str
    expected_bytes: int
    expected_rows: int


@dataclass(frozen=True)
class Reading:
    plant_id: str
    timestamp_utc: datetime
    values: tuple[Decimal | None, ...]
    qualities: tuple[str, ...]


def _fail(message: str) -> ImportValidationError:
    return ImportValidationError(message)


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _fail(f"{label} must be an object")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise _fail(f"{label} must be a non-empty string")
    return value


def _manifest_plants(raw: dict[str, Any]) -> frozenset[str]:
    parameters = raw.get("parameters")
    if not isinstance(parameters, dict):
        parameters = {}
    raw_plants = raw.get("plants") or parameters.get("plants") or raw.get("plant_ids")
    if not isinstance(raw_plants, list) or not raw_plants:
        raise _fail("manifest must declare plants")
    ids: list[str] = []
    for item in raw_plants:
        plant_id = item.get("plant_id") if isinstance(item, dict) else item
        plant_id = _nonempty_string(plant_id, "plant_id")
        if plant_id not in APPROVED_PLANT_IDS:
            raise _fail("manifest contains an unapproved Plant ID")
        ids.append(plant_id)
    result = frozenset(ids)
    if len(ids) != 5 or len(result) != 5 or result != APPROVED_PLANT_IDS:
        raise _fail("manifest must contain exactly the five approved Plant IDs")
    metadata = raw.get("plant_metadata")
    if isinstance(metadata, list):
        if len(metadata) != len(ids):
            raise _fail("manifest Plant metadata count does not match Plant IDs")
        for item in metadata:
            if not isinstance(item, dict):
                raise _fail("manifest Plant metadata must be objects")
            plant_id = _nonempty_string(item.get("plant_id"), "plant_id")
            if plant_id not in result:
                raise _fail("manifest Plant metadata contains an unknown Plant ID")
            expected = APPROVED_PLANTS[plant_id]
            if item.get("timezone") != expected["timezone"]:
                raise _fail(f"manifest timezone does not match app-owned {plant_id} metadata")
            try:
                capacity = Decimal(str(item["capacity_gal_per_h"]))
            except (KeyError, InvalidOperation) as exc:
                raise _fail(f"manifest capacity is missing for {plant_id}") from exc
            if capacity != expected["hydraulic_capacity_gal_h"]:
                raise _fail(f"manifest capacity does not match app-owned {plant_id} metadata")
    return result


def _validate_manifest_units(raw: dict[str, Any]) -> None:
    schema = raw.get("schema")
    channels = schema.get("channels") if isinstance(schema, dict) else None
    if isinstance(channels, dict):
        if set(channels) != set(EXPECTED_UNITS):
            raise _fail("manifest channels do not exactly match the M1 contract")
        for channel, expected_unit in EXPECTED_UNITS.items():
            entry = channels.get(channel)
            if not isinstance(entry, dict) or entry.get("unit") != expected_unit:
                raise _fail("manifest units do not exactly match the M1 contract")
            if entry.get("value_column") != channel or entry.get("quality_column") != f"{channel}_quality":
                raise _fail("manifest channel columns do not exactly match the M1 contract")
        return
    units = raw.get("units")
    if units is None and isinstance(schema, dict):
        units = schema.get("units")
    if units is None and isinstance(raw.get("columns"), list):
        units = {
            item.get("name"): item.get("unit")
            for item in raw["columns"]
            if isinstance(item, dict)
        }
    if units != EXPECTED_UNITS:
        raise _fail("manifest units do not exactly match the M1 contract")


def _provenance_is_synthetic(raw: dict[str, Any]) -> bool:
    provenance = raw.get("provenance")
    if provenance == "synthetic":
        return True
    if isinstance(provenance, dict):
        return provenance.get("kind", provenance.get("type")) == "synthetic" and (
            provenance.get("observed_data") is not True
        )
    return False


def _file_entry(raw: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    files = _mapping(raw.get("files"), "manifest files")
    if set(files) != {"telemetry.csv"}:
        raise _fail("manifest files must contain only telemetry.csv")
    entry = _mapping(files["telemetry.csv"], "telemetry.csv manifest entry")
    digest = entry.get("sha256", entry.get("sha"))
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise _fail("manifest telemetry.csv sha256 is invalid")
    size = entry.get("bytes", entry.get("size"))
    counts = raw.get("counts")
    rows = entry.get("rows", entry.get("row_count"))
    if rows is None and isinstance(counts, dict):
        rows = counts.get("rows")
    if not isinstance(size, int) or not isinstance(rows, int):
        raise _fail("manifest telemetry.csv size and row count are required")
    if not 0 < size <= MAX_BYTES or not 0 < rows <= MAX_ROWS:
        raise _fail("manifest telemetry.csv exceeds the M1 bounds")
    return "telemetry.csv", {"sha256": digest, "bytes": size, "rows": rows}




def load_manifest(path: Path, source_sha: str) -> Manifest:
    _validate_source_sha(source_sha)
    try:
        resolved = path.resolve(strict=True)
        raw_bytes = resolved.read_bytes()
        raw = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise _fail(f"cannot read manifest: {exc}") from exc
    schema_version = raw.get("schema_version")
    if schema_version is None:
        schema = raw.get("schema")
        schema_version = schema.get("version") if isinstance(schema, dict) else schema
    if schema_version != SCHEMA_VERSION:
        raise _fail("manifest schema version must be m1.v1")
    if not _provenance_is_synthetic(raw):
        raise _fail("manifest provenance must be synthetic")
    if raw.get("observed_source") is True or raw.get("source_type") == "observed":
        raise _fail("observed source is not importable")
    seed = raw.get("seed")
    if seed != SEED:
        raise _fail("manifest seed is not the accepted M1 seed")
    generator_version = raw.get("generator_version")
    if generator_version is None and isinstance(raw.get("generator"), dict):
        generator_version = raw["generator"].get("version")
    generator_version = _nonempty_string(generator_version, "generator_version")
    declared_source = raw.get("source_sha", raw.get("source_commit"))
    if declared_source is not None and declared_source != source_sha:
        raise _fail("manifest source SHA does not match the explicit source SHA")
    _validate_manifest_units(raw)
    plants = _manifest_plants(raw)
    data_name, entry = _file_entry(raw)
    return Manifest(
        path=resolved,
        digest=hashlib.sha256(raw_bytes).hexdigest(),
        schema_version=SCHEMA_VERSION,
        generator_version=generator_version,
        seed=seed,
        plants=plants,
        data_name=data_name,
        expected_sha256=entry["sha256"],
        expected_bytes=entry["bytes"],
        expected_rows=entry["rows"],
    )


def _validate_source_sha(source_sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise _fail("source SHA must be a 40-character lowercase immutable SHA")
    if source_sha != SOURCE_SHA:
        raise _fail("source SHA is not the accepted immutable M1 source")


def _safe_data_path(manifest: Manifest, data_path: Path) -> Path:
    try:
        data = data_path.resolve(strict=True)
    except OSError as exc:
        raise _fail(f"cannot read telemetry.csv: {exc}") from exc
    try:
        data.relative_to(manifest.path.parent)
    except ValueError as exc:
        raise _fail("data path must remain below the manifest directory") from exc
    if data.name != manifest.data_name:
        raise _fail("data path does not match the manifest file name")
    return data


def _file_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise _fail("telemetry.csv exceeds the byte limit")
                digest.update(chunk)
    except OSError as exc:
        raise _fail(f"cannot hash telemetry.csv: {exc}") from exc
    return digest.hexdigest(), size


def _parse_timestamp(value: str, row_number: int) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise _fail(f"row {row_number}: invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise _fail(f"row {row_number}: timestamp must have an explicit UTC offset")
    if any((parsed.minute, parsed.second, parsed.microsecond)):
        raise _fail(f"row {row_number}: timestamp must be aligned to an hour")
    return parsed.astimezone(UTC)


def _parse_decimal(value: str, row_number: int, channel: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise _fail(f"row {row_number}: {channel} is not numeric") from exc
    if not number.is_finite() or not math.isfinite(float(number)):
        raise _fail(f"row {row_number}: {channel} must be finite")
    return number


def _parse_reading(row: dict[str, str], row_number: int) -> Reading:
    plant_id = row["plant_id"]
    if plant_id not in APPROVED_PLANT_IDS:
        raise _fail(f"row {row_number}: unknown Plant ID")
    timestamp = _parse_timestamp(row["timestamp_utc"], row_number)
    values: list[Decimal | None] = []
    qualities: list[str] = []
    for channel in CHANNELS:
        quality = row[f"{channel}_quality"]
        if quality not in QUALITY_VALUES:
            raise _fail(f"row {row_number}: unknown {channel} quality")
        raw_value = row[channel].strip()
        if quality == "missing":
            if raw_value not in {"", "NULL", "null"}:
                raise _fail(f"row {row_number}: missing {channel} must be NULL")
            values.append(None)
        else:
            if raw_value == "":
                raise _fail(f"row {row_number}: {quality} {channel} needs a finite value")
            values.append(_parse_decimal(raw_value, row_number, channel))
        qualities.append(quality)
    return Reading(plant_id, timestamp, tuple(values), tuple(qualities))


def _iter_readings(path: Path) -> Iterator[Reading]:
    csv.field_size_limit(1024 * 1024)
    try:
        handle = path.open("r", encoding="utf-8", newline="")
    except OSError as exc:
        raise _fail(f"cannot open telemetry.csv: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise _fail("telemetry.csv columns do not exactly match the M1 contract")
        seen: set[tuple[str, datetime]] = set()
        for row_number, row in enumerate(reader, start=2):
            if row_number - 1 > MAX_ROWS:
                raise _fail("telemetry.csv exceeds the row limit")
            if None in row:
                raise _fail(f"row {row_number}: too many columns")
            reading = _parse_reading(row, row_number)
            key = (reading.plant_id, reading.timestamp_utc)
            if key in seen:
                raise _fail(f"row {row_number}: duplicate Plant/timestamp key")
            seen.add(key)
            yield reading


def validate_source(manifest_path: Path, data_path: Path, source_sha: str) -> tuple[Manifest, list[Reading]]:
    manifest = load_manifest(manifest_path, source_sha)
    data = _safe_data_path(manifest, data_path)
    actual_sha, actual_bytes = _file_digest(data)
    if actual_sha != manifest.expected_sha256:
        raise _fail("telemetry.csv SHA-256 does not match the manifest")
    if actual_bytes != manifest.expected_bytes:
        raise _fail("telemetry.csv byte size does not match the manifest")
    readings = list(_iter_readings(data))
    if len(readings) != manifest.expected_rows:
        raise _fail("telemetry.csv row count does not match the manifest")
    if len(readings) * len(CHANNELS) > MAX_READINGS:
        raise _fail("telemetry.csv reading count exceeds the M1 limit")
    if {reading.plant_id for reading in readings} != manifest.plants:
        raise _fail("telemetry.csv does not contain exactly the five approved Plant IDs")
    return manifest, readings


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
    with psycopg.connect(database_url) as connection, connection.transaction():
        with connection.cursor() as cursor:
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
            if cursor.execute(
                "SELECT to_regclass('app.message_outbox')"
            ).fetchone()[0] is not None:
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
