from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from backend.importer import SOURCE_SHA, import_m1
from backend.migrate import migrate
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
def clean_database() -> None:
    migrate(DATABASE_URL)  # type: ignore[arg-type]
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        with connection.transaction():
            connection.execute(
                "TRUNCATE app.hourly_readings, app.forecast_hours, app.forecast_issuances, "
                "app.operator_plant_access, app.plants, app.ingest_batches RESTART IDENTITY"
            )
    import_m1(DATABASE_URL, Path(MANIFEST), Path(DATA), SOURCE_SHA)  # type: ignore[arg-type]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FLOWSTEAD_AUTH_MODE", "local")
    return TestClient(create_app(DATABASE_URL))  # type: ignore[arg-type]


def _grant(subject_id: str, *plant_ids: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s)",
                    [(subject_id, plant_id) for plant_id in plant_ids],
                )


def test_forecast_persists_twelve_rows_and_rerun_is_idempotent() -> None:
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
    _grant("operator-a", "plant-01")
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.transaction():
            connection.execute("UPDATE app.plants SET public_demo = false")
    database = Database(DATABASE_URL)
    assert database.build_forecast("plant-01").available

    headers = {"X-Flowstead-Subject": "operator-a"}
    private = client.get("/api/v1/plants/plant-01/forecast", headers=headers)
    assert private.status_code == 200
    assert private.json()["status"] == "available"
    assert len(private.json()["forecasts"]) == 12
    assert client.get("/api/v1/plants/plant-02/forecast", headers=headers).status_code == 404
    assert client.get("/api/v1/public/plants/plant-01/forecast").status_code == 404


def test_public_forecast_uses_verified_allowlist_only(client: TestClient) -> None:
    database = Database(DATABASE_URL)
    assert database.build_forecast("plant-01").available
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.transaction():
            connection.execute("UPDATE app.plants SET public_demo = false")
            connection.execute("UPDATE app.plants SET public_demo = true WHERE plant_id = 'plant-01'")

    response = client.get("/api/v1/public/plants/plant-01/forecast")

    assert response.status_code == 200
    assert len(response.json()["forecasts"]) == 12
    assert client.get("/api/v1/public/plants/plant-02/forecast").status_code == 404
