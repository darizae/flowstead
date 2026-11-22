#!/usr/bin/env python3
"""Safely materialize the version-pinned synthetic M1 fixture for CI.

The tracked source is compressed only to avoid a large CSV in Git. The importer
still validates the immutable M1 schema, source revision and content digest.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "backend" / "tests" / "fixtures" / "m1"
MAX_BYTES = 20_000_000
PINNED_SOURCE_SHA = "ad5c94d1f46e79312a99cb9721f38700f24fdf6b"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    expected = manifest["files"]["telemetry.csv"]
    if (
        manifest["source_sha"] != PINNED_SOURCE_SHA
        or manifest["schema_version"] != "m1.v1"
    ):
        raise ValueError("M1 source contract changed")
    output = args.output.resolve()
    if output.name != "telemetry.csv":
        raise ValueError("M1 fixture must be named telemetry.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    output_manifest = output.parent / "manifest.json"
    if output.exists() or output_manifest.exists():
        raise FileExistsError("refusing to overwrite existing M1 fixture files")
    digest = hashlib.sha256()
    size = 0
    try:
        # Importer deliberately rejects telemetry files outside the manifest
        # directory. Materialize the immutable contract alongside its CSV.
        with output_manifest.open("xb") as target_manifest:
            target_manifest.write((FIXTURES / "manifest.json").read_bytes())
        with (
            gzip.open(FIXTURES / "telemetry.csv.gz", "rb") as source,
            output.open("xb") as target,
        ):
            while chunk := source.read(65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("decompressed fixture exceeds M1 maximum")
                digest.update(chunk)
                target.write(chunk)
        if size != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
            raise ValueError("M1 fixture digest or size mismatch")
    except BaseException:
        output.unlink(missing_ok=True)
        output_manifest.unlink(missing_ok=True)
        raise
    print(f"verified synthetic M1 fixture: {size} bytes, sha256 {digest.hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
