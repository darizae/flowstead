#!/usr/bin/env python3
"""Dump the FastAPI OpenAPI document for the frontend contract (audit #29).

Regenerates ``frontend/openapi.json`` from the live application so the
checked-in snapshot can never silently drift from the backend routes/schemas.
Run via the backend venv (``uv run --project backend python scripts/generate_openapi.py``)
or the ``frontend`` pnpm recipe ``api:types``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from flowstead_api.main import app

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO_ROOT / "frontend" / "openapi.json"


def dump_openapi(output: Path) -> None:
    document = app.openapi()
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    # Optional explicit output path lets `api:types:check` regenerate into a
    # throwaway location and compare against the committed snapshot.
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else SNAPSHOT
    dump_openapi(output)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
