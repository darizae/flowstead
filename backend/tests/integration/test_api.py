from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from backend.importer import SOURCE_SHA, import_m1
from backend.tests.auth_helpers import install_test_principal, principal_headers
from fastapi.testclient import TestClient

from flowstead_api.main import create_app

DATABASE_URL = os.environ.get("DATABASE_URL")
MANIFEST = os.environ.get("FLOWSTEAD_M1_MANIFEST")
DATA = os.environ.get("FLOWSTEAD_M1_DATA")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not MANIFEST or not DATA,
    reason="set DATABASE_URL, FLOWSTEAD_M1_MANIFEST and FLOWSTEAD_M1_DATA for API integration",
)


@pytest.fixture(autouse=True)
def seed_isolated_database(
    isolated_service_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only seed the disposable per-test DB; never reset configured DATABASE_URL."""
    monkeypatch.setitem(globals(), "DATABASE_URL", isolated_service_url)
    import_m1(isolated_service_url, Path(MANIFEST), Path(DATA), SOURCE_SHA)


@pytest.fixture
def client() -> TestClient:
    return TestClient(install_test_principal(create_app(DATABASE_URL)))  # type: ignore[arg-type]


def _grant(subject_id: str, *plant_ids: str) -> None:
    with (
        psycopg.connect(DATABASE_URL) as connection,  # type: ignore[arg-type]
        connection.transaction(),
        connection.cursor() as cursor,
    ):
        cursor.executemany(
            "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s)",
            [(subject_id, plant_id) for plant_id in plant_ids],
        )


def test_disjoint_principals_receive_disjoint_private_reads(client: TestClient) -> None:
    _grant("operator-a", "plant-01")
    _grant("operator-b", "plant-02")

    headers_a = principal_headers("operator-a")
    headers_b = principal_headers("operator-b")
    assert [plant["plant_id"] for plant in client.get("/api/v1/plants", headers=headers_a).json()["plants"]] == ["plant-01"]
    assert [plant["plant_id"] for plant in client.get("/api/v1/plants", headers=headers_b).json()["plants"]] == ["plant-02"]
    assert client.get("/api/v1/plants/plant-02/latest", headers=headers_a).status_code == 404
    assert client.get("/api/v1/plants/plant-01/history?from=2025-01-01T00:00:00Z&to=2025-01-01T02:00:00Z", headers=headers_a).status_code == 200
    assert client.get("/api/v1/plants/plant-02/history?from=2025-01-01T00:00:00Z&to=2025-01-01T02:00:00Z", headers=headers_a).status_code == 404


def test_private_denials_and_bounded_windows(client: TestClient) -> None:
    """Case: SEC-M12-RATE — JWT, window and SQL-shaped Plant inputs fail closed."""
    _grant("operator-a", "plant-01")
    assert client.get("/api/v1/plants").status_code == 401
    assert client.get("/api/v1/plants/plant-01/latest").status_code == 401
    assert client.get("/api/v1/plants/plant-01/history?from=2025-01-01T00:00:00Z&to=2025-01-01T00:30:00Z", headers=principal_headers("operator-a")).status_code == 422
    assert client.get("/api/v1/plants/plant-01/history?from=2025-01-01T00:00:00-05:00&to=2025-01-01T02:00:00-05:00", headers=principal_headers("operator-a")).status_code == 422
    assert client.get("/api/v1/plants/unknown/latest", headers=principal_headers("operator-a")).status_code == 404
    malicious = "plant-01' OR '1'='1"
    assert client.get(
        f"/api/v1/plants/{malicious}/latest",
        headers=principal_headers("operator-a"),
    ).status_code == 404
    assert client.get(
        "/api/v1/plants",
        headers={"Authorization": "Bearer forged.invalid.token"},
    ).status_code == 401
    with psycopg.connect(DATABASE_URL) as connection:  # type: ignore[arg-type]
        assert connection.execute("SELECT count(*) FROM app.plants").fetchone() == (5,)


def test_public_is_exactly_the_verified_allowlist(client: TestClient) -> None:
    with psycopg.connect(DATABASE_URL) as connection, connection.transaction():  # type: ignore[arg-type]
        connection.execute("UPDATE app.plants SET public_demo = false")
    assert client.get("/api/v1/public/plants").json() == {"plants": []}
    with psycopg.connect(DATABASE_URL) as connection, connection.transaction():  # type: ignore[arg-type]
        connection.execute(
            "UPDATE app.plants SET public_demo = true WHERE plant_id = ANY(%s)",
            [["plant-01", "plant-02", "plant-03", "plant-04", "plant-05"]],
        )

    public = client.get("/api/v1/public/plants")
    assert public.status_code == 200
    assert {plant["plant_id"] for plant in public.json()["plants"]} == {
        "plant-01", "plant-02", "plant-03", "plant-04", "plant-05"
    }
    assert client.get("/api/v1/public/plants/plant-01/latest").status_code == 200
    body = client.get(
        "/api/v1/public/plants/plant-01/history?from=2025-01-01T00:00:00Z&to=2025-01-01T02:00:00Z"
    ).json()
    assert len(body["readings"]) == 2
    assert set(body["readings"][0]["measurements"]) == {
        "influent_flow", "rainfall", "dissolved_oxygen", "effluent_ph"
    }

def test_report_pdf_public_and_private_authorization(client: TestClient) -> None:
    _grant("operator-a", "plant-01")
    _grant("operator-b", "plant-02")
    public = client.get("/api/v1/public/plants/plant-01/report.pdf")
    assert public.status_code == 200
    assert public.headers["content-type"] == "application/pdf"
    assert public.content.startswith(b"%PDF-")
    assert "attachment" in public.headers["content-disposition"]
    assert client.get("/api/v1/public/plants/unknown/report.pdf").status_code == 404
    assert client.get("/api/v1/plants/plant-01/report.pdf").status_code == 401
    assert client.get("/api/v1/plants/plant-01/report.pdf", headers=principal_headers("operator-a")).status_code == 200
    assert client.get("/api/v1/plants/plant-01/report.pdf", headers=principal_headers("operator-b")).status_code == 404
