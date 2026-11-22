"""Real HTTP and identity-boundary checks against the live stack."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import httpx

from .harness.stack import LiveStack


def _plant_ids(response: httpx.Response) -> set[str]:
    return {plant["plant_id"] for plant in response.json()["plants"]}


def test_health_and_readiness_are_served_by_real_uvicorn_http(live_stack: LiveStack) -> None:
    """Cases: LIVE-HEALTH, LIVE-READINESS — live Uvicorn and migrated PostgreSQL."""
    with live_stack.anonymous_client() as client:
        assert client.get("/api/v1/health/live").json() == {"status": "ok"}
        assert client.get("/api/v1/health/ready").json() == {"status": "ok"}
        assert client.get("/api/v1/health").status_code == 200


def test_rs256_jwks_tokens_and_private_plant_scopes_are_distinct(
    live_stack: LiveStack,
) -> None:
    """Cases: LIVE-AUTH-RS256, LIVE-IDENTITY, LIVE-AUTHZ — users use genuine signed tokens."""
    with (
        live_stack.client("live-user-a") as user_a,
        live_stack.client("live-user-b") as user_b,
        live_stack.anonymous_client() as anonymous,
    ):
        assert _plant_ids(user_a.get("/api/v1/plants")) == {"plant-01", "plant-02"}
        assert _plant_ids(user_b.get("/api/v1/plants")) == {"plant-03"}
        assert user_a.get("/api/v1/plants/plant-03/latest").status_code == 404
        assert anonymous.get("/api/v1/plants").status_code == 401


def test_concurrent_multi_principal_requests_do_not_cross_private_boundaries(
    live_stack: LiveStack,
) -> None:
    """Case: LIVE-CONCURRENT-AUTHZ — parallel real requests retain principal scope."""
    requests = [
        ("live-user-a", "/api/v1/plants/plant-01/latest", 200),
        ("live-user-a", "/api/v1/plants/plant-03/latest", 404),
        ("live-user-b", "/api/v1/plants/plant-03/latest", 200),
        ("live-user-b", "/api/v1/plants/plant-01/latest", 404),
    ] * 5

    def request(item: tuple[str, str, int]) -> int:
        subject, path, expected = item
        with live_stack.client(subject) as client:
            response = client.get(path)
            assert response.status_code == expected, response.text
            if expected == 404:
                assert "plant-01" not in response.text or path.endswith("plant-03/latest")
            return response.status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(request, requests))
    assert statuses.count(200) == 10
    assert statuses.count(404) == 10
