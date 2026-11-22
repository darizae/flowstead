from __future__ import annotations

import ipaddress
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from backend.tests.auth_helpers import install_test_principal, principal_headers
from fastapi.testclient import TestClient

from flowstead_api.main import create_app
from flowstead_api.message_store import ForecastJob
from flowstead_api.security import SecurityConfig, SecurityConfigurationError


def _config(**updates: object) -> SecurityConfig:
    values: dict[str, object] = {
        "requests_per_window": 20,
        "window_seconds": 60,
        "max_clients": 20,
        "max_body_bytes": 64,
        "max_target_bytes": 512,
        "trusted_proxies": (),
        "cors_origins": ("http://127.0.0.1:5173",),
        "forecast_requests_per_window": 30,
        "forecast_window_seconds": 60,
    }
    values.update(updates)
    return SecurityConfig(**values)  # type: ignore[arg-type]


def test_security_headers_exact_cors_and_request_caps() -> None:
    """Case: SEC-M12-RATE."""
    client = TestClient(create_app(security_config=_config()))

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.headers["cache-control"] == "no-store"
    assert (
        health.headers["content-security-policy"]
        == "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    assert health.headers["referrer-policy"] == "no-referrer"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"

    allowed = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    denied = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers

    oversized = client.post(
        "/api/v1/plants/plant-01/forecast-requests",
        content=b"x" * 65,
    )
    assert oversized.status_code == 413
    assert oversized.json()["detail"]["code"] == "request_denied"


def test_rate_limit_is_bounded_and_ignores_untrusted_forwarding() -> None:
    """Case: SEC-M12-RATE."""
    client = TestClient(
        create_app(security_config=_config(requests_per_window=2, max_clients=1)),
        client=("203.0.113.10", 50000),
    )
    assert (
        client.get("/api/v1/health", headers={"X-Forwarded-For": "198.51.100.1"}).status_code == 200
    )
    assert (
        client.get("/api/v1/health", headers={"X-Forwarded-For": "198.51.100.2"}).status_code == 200
    )
    denied = client.get("/api/v1/health", headers={"X-Forwarded-For": "198.51.100.3"})
    assert denied.status_code == 429
    assert denied.headers["retry-after"] == "60"
    assert denied.headers["x-ratelimit-remaining"] == "0"
    assert denied.json() == {
        "detail": {"code": "request_denied", "message": "Request rate limit exceeded"}
    }


def test_trusted_proxy_uses_closest_untrusted_forwarded_address() -> None:
    """Case: SEC-M12-RATE."""
    trusted = (ipaddress.ip_network("10.0.0.0/8"),)
    client = TestClient(
        create_app(security_config=_config(requests_per_window=1, trusted_proxies=trusted)),
        client=("10.0.0.2", 50000),
    )
    headers = {"X-Forwarded-For": "198.51.100.7, 10.0.0.3"}
    assert client.get("/api/v1/health", headers=headers).status_code == 200
    assert client.get("/api/v1/health", headers=headers).status_code == 429
    assert (
        client.get(
            "/api/v1/health",
            headers={"X-Forwarded-For": "198.51.100.8, 10.0.0.3"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/health", headers={"X-Forwarded-For": "not-an-ip"}).status_code == 400


def test_malformed_window_leaks_no_parser_internals() -> None:
    """Case: SEC-AUD-ERRLEAK — invalid windows return a fixed message, not parser internals."""
    client = TestClient(create_app(security_config=_config()))
    for query in (
        "from=not-a-time&to=also-bad",
        "from=2026-11-18T00:00:00+14:00&to=2026-11-18T03:00:00+14:00",
        "from=2026-99-99T00:00:00Z&to=2026-99-99T03:00:00Z",
    ):
        response = client.get(f"/api/v1/public/plants/plant-01/history?{query}")
        assert response.status_code == 422
        body = response.json()["detail"]
        assert body["code"] == "invalid_window"
        assert body["message"] == "window timestamps must be hour-aligned UTC ISO-8601 values"
        serialized = str(body)
        assert "isoformat" not in serialized.lower()
        assert "not-a-time" not in serialized
        assert "month must be" not in serialized


def test_security_configuration_rejects_open_or_ambiguous_origins() -> None:
    """Case: SEC-M12-RATE."""
    with pytest.raises(SecurityConfigurationError):
        SecurityConfig.from_env({"FLOWSTEAD_CORS_ORIGINS": "*"})
    with pytest.raises(SecurityConfigurationError):
        SecurityConfig.from_env({"FLOWSTEAD_CORS_ORIGINS": "http://example.com"})
    with pytest.raises(SecurityConfigurationError):
        SecurityConfig.from_env({"FLOWSTEAD_RATE_LIMIT_REQUESTS": "0"})
    with pytest.raises(SecurityConfigurationError):
        SecurityConfig.from_env({"FLOWSTEAD_FORECAST_RATE_LIMIT_REQUESTS": "0"})


def test_forecast_requests_rate_limited_per_principal_and_plant() -> None:
    """Case: SEC19-03 — bounded per-principal+Plant forecast submission."""

    def fake_enqueue(plant_id: str, *, subject_id: str) -> ForecastJob:
        return ForecastJob(uuid4(), uuid4(), plant_id, "queued", datetime.now(UTC), None, None)

    app = create_app(security_config=_config(forecast_requests_per_window=1))
    install_test_principal(app)
    app.state.database.enqueue_forecast = fake_enqueue  # type: ignore[method-assign]
    client = TestClient(app)

    ok = client.post("/api/v1/plants/plant-01/forecast-requests", headers=principal_headers("op-a"))
    assert ok.status_code == 202
    denied = client.post(
        "/api/v1/plants/plant-01/forecast-requests", headers=principal_headers("op-a")
    )
    assert denied.status_code == 429
    assert denied.headers["retry-after"] == "60"
    assert denied.json() == {
        "detail": {
            "code": "request_denied",
            "message": "Forecast request rate limit exceeded",
        }
    }
    # A different principal on the same Plant is not throttled by op-a's slot.
    assert (
        client.post(
            "/api/v1/plants/plant-01/forecast-requests", headers=principal_headers("op-b")
        ).status_code
        == 202
    )
    # A different Plant for the same principal is not throttled either.
    assert (
        client.post(
            "/api/v1/plants/plant-02/forecast-requests", headers=principal_headers("op-a")
        ).status_code
        == 202
    )
