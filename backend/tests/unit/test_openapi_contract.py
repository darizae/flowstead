"""OpenAPI contract-tracking test (audit #29).

The checked-in ``frontend/openapi.json`` snapshot feeds the frontend type
generation. If backend routes or Pydantic schemas change without regenerating
the snapshot, this test fails and surfaces the drift. Structural equality keeps
the check robust to JSON whitespace/ordering, which the generator normalises.
"""

from __future__ import annotations

import json
from pathlib import Path

from flowstead_api.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = REPO_ROOT / "frontend" / "openapi.json"


def test_checked_in_openapi_contract_matches_live_app() -> None:
    assert SNAPSHOT.is_file(), "frontend/openapi.json missing; run `npm run api:types`"
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert snapshot == app.openapi()


def test_openapi_document_is_valid_contract() -> None:
    document = app.openapi()
    assert document["openapi"].startswith("3.1")
    assert document["info"]["title"] == "Flowstead API"
    schemas = document["components"]["schemas"]
    for name in ("PlantSummary", "LatestResponse", "HistoryResponse", "ForecastResponse"):
        assert name in schemas, f"missing contract schema {name!r}"
