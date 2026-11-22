"""Pinned M1 manifest and telemetry verification (immutable provenance)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .proc import RunnerError

SOURCE_SHA = "ad5c94d1f46e79312a99cb9721f38700f24fdf6b"
TELEMETRY_SHA256 = "e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e"
DB_PREFIX = "flowstead_test_"


def verify_m1(manifest_path: Path, data_path: Path) -> None:
    """Verify the pinned M1 manifest and telemetry digest before any provisioning."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"cannot read M1 manifest: {error}") from error
    schema_version = manifest.get("schema_version") or (
        manifest.get("schema", {}).get("version")
        if isinstance(manifest.get("schema"), dict)
        else None
    )
    if schema_version != "m1.v1" or manifest.get("seed") != 20250101:
        raise RunnerError("M1 manifest must declare schema m1.v1 and seed 20250101")
    provenance = manifest.get("provenance")
    if provenance != "synthetic" and not (
        isinstance(provenance, dict)
        and provenance.get("kind", provenance.get("type")) == "synthetic"
    ):
        raise RunnerError("M1 manifest must declare synthetic provenance")
    # The generator may or may not embed a source SHA; when one is declared it
    # must match the pinned source. The authoritative source is passed to the
    # importer via --source-sha (importer.py does not require a manifest field).
    declared_sources = [
        manifest.get(name)
        for name in ("source_sha", "source_commit")
        if name in manifest
    ]
    if any(source != SOURCE_SHA for source in declared_sources):
        raise RunnerError(
            "M1 manifest must not declare a source SHA/commit other than the pinned source"
        )
    files = manifest.get("files")
    entry = files.get("telemetry.csv") if isinstance(files, dict) else None
    expected = (
        entry.get("sha256", entry.get("sha")) if isinstance(entry, dict) else None
    )
    if expected != TELEMETRY_SHA256:
        raise RunnerError(
            "M1 manifest telemetry SHA does not match the canonical digest"
        )
    if (
        data_path.name != "telemetry.csv"
        or data_path.parent.resolve() != manifest_path.parent.resolve()
    ):
        raise RunnerError("M1 telemetry.csv must be next to the manifest")
    digest = hashlib.sha256()
    try:
        with data_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise RunnerError(f"cannot read M1 telemetry: {error}") from error
    if digest.hexdigest() != TELEMETRY_SHA256:
        raise RunnerError("M1 telemetry SHA does not match the canonical digest")
