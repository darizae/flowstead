from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from backend.importer import SOURCE_SHA, import_m1
from backend.tests.auth_helpers import install_test_principal, principal_headers
from fastapi.testclient import TestClient

from flowstead_api.database import Database
from flowstead_api.main import create_app

DATABASE_URL = os.environ.get("DATABASE_URL")
MANIFEST = os.environ.get("FLOWSTEAD_M1_MANIFEST")
DATA = os.environ.get("FLOWSTEAD_M1_DATA")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not MANIFEST or not DATA,
    reason="set DATABASE_URL, FLOWSTEAD_M1_MANIFEST and FLOWSTEAD_M1_DATA for forecast integration",
)


@pytest.fixture(autouse=True)
def seed_isolated_database(isolated_service_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only seed the disposable per-test DB; never reset configured DATABASE_URL."""
    monkeypatch.setitem(globals(), "DATABASE_URL", isolated_service_url)
    import_m1(isolated_service_url, Path(MANIFEST), Path(DATA), SOURCE_SHA)


@pytest.fixture
def client() -> TestClient:
    return TestClient(install_test_principal(create_app(DATABASE_URL)))  # type: ignore[arg-type]


def _grant(subject_id: str, *plant_ids: str) -> None:
    with (
        psycopg.connect(DATABASE_URL) as connection,
        connection.transaction(),
        connection.cursor() as cursor,
    ):
        cursor.executemany(
            "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s)",
            [(subject_id, plant_id) for plant_id in plant_ids],
        )


def test_forecast_persists_twelve_rows_and_rerun_is_idempotent() -> None:
    """Case: IT-M4-ATOMIC — repeat forecast builds do not duplicate rows."""
    database = Database(DATABASE_URL)

    first = database.build_forecast("plant-01")
    second = database.build_forecast("plant-01")

    assert first.available
    assert [
        (point.hour_number, point.target_time_utc, point.predicted_flow_gal_h)
        for point in second.points
    ] == [
        (point.hour_number, point.target_time_utc, point.predicted_flow_gal_h)
        for point in first.points
    ]
    with psycopg.connect(DATABASE_URL) as connection:
        assert connection.execute("SELECT count(*) FROM app.forecast_issuances").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM app.forecast_hours").fetchone()[0] == 12


def test_private_forecast_authorization_and_default_public_denial(client: TestClient) -> None:
    """Case: IT-M4-CROSSPLANT — private read cannot cross Plant ownership."""
    _grant("operator-a", "plant-01")
    with psycopg.connect(DATABASE_URL) as connection, connection.transaction():
        connection.execute("UPDATE app.plants SET public_demo = false")
    database = Database(DATABASE_URL)
    assert database.build_forecast("plant-01").available

    headers = principal_headers("operator-a")
    private = client.get("/api/v1/plants/plant-01/forecast", headers=headers)
    assert private.status_code == 200
    assert private.json()["status"] == "available"
    assert len(private.json()["forecasts"]) == 12
    assert client.get("/api/v1/plants/plant-02/forecast", headers=headers).status_code == 404
    assert client.get("/api/v1/public/plants/plant-01/forecast").status_code == 404


def test_public_forecast_uses_verified_allowlist_only(client: TestClient) -> None:
    database = Database(DATABASE_URL)
    assert database.build_forecast("plant-01").available
    with psycopg.connect(DATABASE_URL) as connection, connection.transaction():
        connection.execute("UPDATE app.plants SET public_demo = false")
        connection.execute("UPDATE app.plants SET public_demo = true WHERE plant_id = 'plant-01'")

    response = client.get("/api/v1/public/plants/plant-01/forecast")

    assert response.status_code == 200
    assert len(response.json()["forecasts"]) == 12
    assert client.get("/api/v1/public/plants/plant-02/forecast").status_code == 404
