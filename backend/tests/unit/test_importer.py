from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.importer import (
    APPROVED_PLANT_IDS,
    CSV_COLUMNS,
    ImportValidationError,
    SOURCE_SHA,
    validate_source,
)


def _write_source(
    tmp_path: Path, *, quality: str = "valid", timestamp: str = "2025-01-01T00:00:00Z"
) -> tuple[Path, Path]:
    data = tmp_path / "telemetry.csv"
    rows = []
    for index, plant_id in enumerate(sorted(APPROVED_PLANT_IDS)):
        values = ["1", "0.1", "2", "7.2"]
        row_quality = quality if index == 0 else "valid"
        if row_quality == "missing":
            values[0] = ""
        rows.append(
            [plant_id, timestamp, values[0], row_quality, values[1], "valid", values[2], "valid",
             values[3], "invalid"]
        )
    data.write_text(",".join(CSV_COLUMNS) + "\n" + "\n".join(",".join(row) for row in rows) + "\n",
                    encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "m1.v1",
                "generator_version": "test-generator",
                "seed": 20250101,
                "provenance": "synthetic",
                "source_sha": SOURCE_SHA,
                "units": {
                    "influent_flow": "gal/h",
                    "rainfall": "in/h",
                    "dissolved_oxygen": "mg/L",
                    "effluent_ph": "unitless",
                },
                "plants": sorted(APPROVED_PLANT_IDS),
                "files": {
                    "telemetry.csv": {
                        "sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
                        "bytes": data.stat().st_size,
                        "rows": 5,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return manifest, data


def test_null_and_finite_invalid_values_are_kept(tmp_path: Path) -> None:
    manifest, data = _write_source(tmp_path, quality="missing")
    _, readings = validate_source(manifest, data, SOURCE_SHA)
    assert readings[0].values[0] is None
    assert readings[0].qualities[3] == "invalid"
    assert str(readings[0].values[3]) == "7.2"


def test_non_utc_timestamp_is_rejected(tmp_path: Path) -> None:
    manifest, data = _write_source(tmp_path, timestamp="2025-01-01T00:00:00-05:00")
    with pytest.raises(ImportValidationError, match="explicit UTC"):
        validate_source(manifest, data, SOURCE_SHA)


def test_unknown_quality_is_rejected(tmp_path: Path) -> None:
    manifest, data = _write_source(tmp_path, quality="unknown")
    with pytest.raises(ImportValidationError, match="unknown"):
        validate_source(manifest, data, SOURCE_SHA)


def test_manifest_path_cannot_import_unknown_plant(tmp_path: Path) -> None:
    manifest, data = _write_source(tmp_path)
    data.write_text(data.read_text(encoding="utf-8").replace("plant-01", "unknown"), encoding="utf-8")
    with pytest.raises(ImportValidationError, match="SHA-256"):
        validate_source(manifest, data, SOURCE_SHA)
