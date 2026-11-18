from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import jwt
import psycopg
import pytest
from backend.importer import APPROVED_PLANTS, SOURCE_SHA
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from flowstead_api.auth import AuthConfig, JWKSVerifier
from flowstead_api.database import Database
from flowstead_api.main import create_app

ISSUER = "https://local-auth-fixture.supabase.co/auth/v1"


@pytest.fixture
def seeded_auth_url(isolated_service_url: str) -> str:
    """Seed the five approved fictional IDs and enough bounded data for auth reads."""
    with psycopg.connect(isolated_service_url) as connection, connection.transaction():
        batch_id = connection.execute(
            """
            INSERT INTO app.ingest_batches
                (content_sha256, source_sha, schema_version, generator_version,
                 seed, manifest_sha256, row_count, content_bytes)
            VALUES (%s, %s, 'm1.v1', 'auth-integration-fixture', 20250101,
                    %s, 50, 1000)
            RETURNING id
            """,
            ("a" * 64, SOURCE_SHA, "b" * 64),
        ).fetchone()[0]
        for plant_id in sorted(APPROVED_PLANTS):
            plant = APPROVED_PLANTS[plant_id]
            connection.execute(
                """
                INSERT INTO app.plants
                    (plant_id, name, city, state_code, timezone, latitude,
                     longitude, hydraulic_capacity_gal_h, public_demo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)
                """,
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
        start = datetime(2026, 1, 1, tzinfo=UTC)
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO app.hourly_readings
                    (plant_id, timestamp_utc, influent_flow, influent_flow_quality,
                     rainfall, rainfall_quality, dissolved_oxygen,
                     dissolved_oxygen_quality, effluent_ph, effluent_ph_quality,
                     source_batch_id)
                VALUES (%s, %s, %s, 'valid', 0, 'valid', 2, 'valid',
                        7, 'valid', %s)
                """,
                [
                    (
                        plant_id,
                        start + timedelta(hours=hour),
                        Decimal(100) + hour,
                        batch_id,
                    )
                    for plant_id in ("plant-01", "plant-02")
                    for hour in range(25)
                ],
            )
            cursor.executemany(
                """
                INSERT INTO app.operator_plant_access (subject_id, plant_id)
                VALUES (%s, %s)
                """,
                [("operator-a", "plant-01"), ("operator-b", "plant-02")],
            )

    database = Database(isolated_service_url)
    assert database.build_forecast("plant-01").available
    assert database.build_forecast("plant-02").available
    return isolated_service_url


@pytest.fixture
def signed_client(seeded_auth_url: str) -> tuple[TestClient, rsa.RSAPrivateKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": "integration-key", "alg": "RS256", "use": "sig"})

    def serve_jwks(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{ISSUER}/.well-known/jwks.json"
        return httpx.Response(200, json={"keys": [jwk]})

    config = AuthConfig(
        auth_url=ISSUER,
        issuer=ISSUER,
        audience="authenticated",
        algorithms=("RS256",),
    )
    verifier = JWKSVerifier(
        config,
        client=httpx.Client(transport=httpx.MockTransport(serve_jwks)),
    )
    return TestClient(create_app(seeded_auth_url, auth_verifier=verifier)), private_key


def _headers(
    private_key: rsa.RSAPrivateKey,
    subject: str,
    *,
    asserted_plant: str | None = None,
) -> dict[str, str]:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": subject,
        "iss": ISSUER,
        "aud": "authenticated",
        "iat": int((now - timedelta(seconds=1)).timestamp()),
        "nbf": int((now - timedelta(seconds=1)).timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    if asserted_plant:
        claims["app_metadata"] = {"plant_ids": [asserted_plant]}
    token = jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "integration-key", "typ": "JWT"},
    )
    headers = {"Authorization": f"Bearer {token}"}
    if asserted_plant:
        headers["X-Flowstead-Plant-Ids"] = asserted_plant
    return headers


def test_signed_disjoint_principals_are_sql_scoped_across_private_reads(
    signed_client: tuple[TestClient, rsa.RSAPrivateKey],
) -> None:
    """Case: IT-M5-AUTHZ."""
    client, private_key = signed_client
    headers_a = _headers(private_key, "operator-a", asserted_plant="plant-02")
    headers_b = _headers(private_key, "operator-b")

    assert [
        plant["plant_id"]
        for plant in client.get("/api/v1/plants", headers=headers_a).json()["plants"]
    ] == ["plant-01"]
    assert [
        plant["plant_id"]
        for plant in client.get("/api/v1/plants", headers=headers_b).json()["plants"]
    ] == ["plant-02"]

    assert client.get("/api/v1/plants/plant-01/latest", headers=headers_a).status_code == 200
    denied_latest = client.get("/api/v1/plants/plant-02/latest", headers=headers_a)
    assert denied_latest.status_code == 404
    absent_latest = client.get("/api/v1/plants/absent/latest", headers=headers_a)
    assert absent_latest.status_code == 404
    assert denied_latest.json() == absent_latest.json()

    history = "/api/v1/plants/{}/history?from=2026-01-01T00:00:00Z&to=2026-01-01T02:00:00Z"
    assert client.get(history.format("plant-01"), headers=headers_a).status_code == 200
    assert client.get(history.format("plant-02"), headers=headers_a).status_code == 404

    forecast_a = client.get("/api/v1/plants/plant-01/forecast", headers=headers_a)
    assert forecast_a.status_code == 200
    assert len(forecast_a.json()["forecasts"]) == 12
    assert client.get("/api/v1/plants/plant-02/forecast", headers=headers_a).status_code == 404
    assert client.get("/api/v1/plants/plant-02/forecast", headers=headers_b).status_code == 200
