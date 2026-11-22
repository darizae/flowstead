from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from flowstead_api.auth import (
    AuthConfig,
    AuthConfigurationError,
    AuthenticationError,
    JWKSVerifier,
    LegacyAuthEndpointVerifier,
    Principal,
    _bearer_token,
)
from flowstead_api.main import create_app

ISSUER = "https://project-ref.supabase.co/auth/v1"
AUDIENCE = "authenticated"


def _key(kid: str) -> tuple[rsa.RSAPrivateKey, dict[str, object]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig", "key_ops": ["verify"]})
    return private_key, jwk


def _claims(subject: str = "operator-a", **updates: object) -> dict[str, object]:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": subject,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": int((now - timedelta(seconds=1)).timestamp()),
        "nbf": int((now - timedelta(seconds=1)).timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    claims.update(updates)
    return claims


def _token(
    private_key: rsa.RSAPrivateKey,
    kid: str,
    *,
    subject: str = "operator-a",
    **claim_updates: object,
) -> str:
    return jwt.encode(
        _claims(subject, **claim_updates),
        private_key,
        algorithm="RS256",
        headers={"kid": kid, "typ": "JWT"},
    )


def _config(**updates: object) -> AuthConfig:
    values: dict[str, object] = {
        "auth_url": ISSUER,
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "algorithms": ("RS256",),
    }
    values.update(updates)
    return AuthConfig(**values)  # type: ignore[arg-type]


def _rejected(verifier: JWKSVerifier, token: str) -> None:
    with pytest.raises(AuthenticationError):
        verifier.verify(token)


def test_signed_jwt_claims_rotation_and_bounded_cache() -> None:
    """Case: UT-M5-JWT."""
    key_a, jwk_a = _key("key-a")
    key_b, jwk_b = _key("key-b")
    forged_key, _ = _key("forged")
    state: dict[str, object] = {"keys": [jwk_a], "calls": 0}
    clock = [100.0]

    def serve_jwks(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{ISSUER}/.well-known/jwks.json"
        state["calls"] = int(state["calls"]) + 1
        return httpx.Response(200, json={"keys": state["keys"]})

    verifier = JWKSVerifier(
        _config(jwks_ttl_seconds=600.0, unknown_kid_refresh_seconds=5.0),
        client=httpx.Client(transport=httpx.MockTransport(serve_jwks)),
        clock=lambda: clock[0],
    )
    valid_a = _token(key_a, "key-a")
    assert verifier.verify(valid_a) == Principal(sub="operator-a")
    assert verifier.verify(valid_a) == Principal(sub="operator-a")
    assert state["calls"] == 1

    now = datetime.now(UTC)
    _rejected(verifier, _token(key_a, "key-a", iss="https://attacker.invalid/auth/v1"))
    _rejected(verifier, _token(key_a, "key-a", aud="another-audience"))
    _rejected(
        verifier,
        _token(
            key_a,
            "key-a",
            iat=int((now - timedelta(minutes=10)).timestamp()),
            nbf=int((now - timedelta(minutes=10)).timestamp()),
            exp=int((now - timedelta(minutes=5)).timestamp()),
        ),
    )
    _rejected(
        verifier,
        _token(
            key_a,
            "key-a",
            iat=int((now + timedelta(minutes=5)).timestamp()),
            nbf=int((now + timedelta(minutes=5)).timestamp()),
        ),
    )
    _rejected(verifier, _token(forged_key, "key-a"))
    unsigned = jwt.encode(_claims(), key="", algorithm="none", headers={"kid": "key-a"})
    _rejected(verifier, unsigned)
    valid_b = _token(key_b, "key-b", subject="operator-b")
    _rejected(verifier, valid_b)

    state["keys"] = [jwk_a, jwk_b]
    clock[0] += 5.0
    assert verifier.verify(valid_b) == Principal(sub="operator-b")
    assert state["calls"] == 2

    state["keys"] = [jwk_b]
    clock[0] += 601.0
    _rejected(verifier, valid_a)
    assert verifier.verify(valid_b) == Principal(sub="operator-b")
    assert state["calls"] == 3


def test_remote_verification_failures_are_closed_and_token_safe(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Case: UT-M5-FAIL."""
    private_key, _ = _key("key-a")
    secret_token = _token(private_key, "key-a", subject="secret-bearing-subject")

    def unavailable(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    caplog.set_level(logging.WARNING)
    jwks_verifier = JWKSVerifier(
        _config(),
        client=httpx.Client(transport=httpx.MockTransport(unavailable)),
    )
    _rejected(jwks_verifier, secret_token)

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    legacy_config = _config(
        verification_mode="legacy-auth-endpoint",
        publishable_key="publishable-test-key",
    )
    legacy_verifier = LegacyAuthEndpointVerifier(
        legacy_config,
        client=httpx.Client(transport=httpx.MockTransport(timeout)),
    )
    with pytest.raises(AuthenticationError):
        legacy_verifier.verify(secret_token)

    assert secret_token not in caplog.text
    assert "secret-bearing-subject" not in caplog.text
    assert "publishable-test-key" not in caplog.text


def test_legacy_auth_endpoint_accepts_only_verified_user_response() -> None:
    config = _config(
        verification_mode="legacy-auth-endpoint",
        publishable_key="publishable-test-key",
    )

    def auth_user(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{ISSUER}/user"
        assert request.headers["apikey"] == "publishable-test-key"
        assert request.headers["authorization"] == "Bearer legacy-token"
        return httpx.Response(200, json={"id": "operator-a", "aud": AUDIENCE})

    verifier = LegacyAuthEndpointVerifier(
        config,
        client=httpx.Client(transport=httpx.MockTransport(auth_user)),
    )
    assert verifier.verify("legacy-token") == Principal(sub="operator-a")


def test_production_configuration_rejects_bypasses_and_missing_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case: UT-M5-MODE."""
    with pytest.raises(AuthConfigurationError, match="SUPABASE_AUTH_URL"):
        AuthConfig.from_env({})
    with pytest.raises(AuthConfigurationError, match="local/test principal modes"):
        AuthConfig.from_env({"FLOWSTEAD_AUTH_MODE": "local"})
    with pytest.raises(AuthConfigurationError, match="asymmetric algorithms"):
        AuthConfig.from_env(
            {
                "FLOWSTEAD_AUTH_MODE": "supabase",
                "SUPABASE_AUTH_URL": ISSUER,
                "SUPABASE_JWT_ISSUER": ISSUER,
                "SUPABASE_JWT_AUDIENCE": AUDIENCE,
                "SUPABASE_JWT_ALGORITHMS": "HS256",
            }
        )

    for name in (
        "SUPABASE_AUTH_URL",
        "SUPABASE_JWT_ISSUER",
        "SUPABASE_JWT_AUDIENCE",
        "SUPABASE_JWT_ALGORITHMS",
        "SUPABASE_AUTH_VERIFICATION_MODE",
        "SUPABASE_PUBLISHABLE_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("FLOWSTEAD_AUTH_MODE", "supabase")
    client = TestClient(create_app())
    assert client.get("/api/v1/health").status_code == 200
    response = client.get(
        "/api/v1/plants",
        headers={
            "Authorization": "Bearer local:operator-a",
            "X-Flowstead-Subject": "operator-a",
        },
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_malformed_jwks_key_type_fails_closed() -> None:
    """Case: UT-M5-FAIL — an invalid remote JWK must never produce a server error."""
    private_key, _ = _key("key-a")

    def malformed_key(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "keys": [
                    {
                        "kid": "key-a",
                        "alg": "RS256",
                        "kty": "oct",
                        "k": "Zm9v",
                        "use": "sig",
                    }
                ]
            },
        )

    verifier = JWKSVerifier(
        _config(),
        client=httpx.Client(transport=httpx.MockTransport(malformed_key)),
    )
    _rejected(verifier, _token(private_key, "key-a"))


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer not-a-jwt",
        "Bearer é.jwt.token",
        "Bearer a.b.c\n",
        "Bearer\ta.b.c",
        "Bearer header.payload.signature\\nextra",
        "Basic a.b.c",
    ],
)
def test_invalid_bearer_values_are_rejected_before_http_header_forwarding(
    authorization: str,
) -> None:
    """Case: UT-M5-FAIL — invalid HTTP bearer values return 401, not a server error."""
    with pytest.raises(HTTPException) as caught:
        _bearer_token(authorization)
    assert caught.value.status_code == 401


def test_es256_signed_jwt_is_accepted_from_configured_jwks() -> None:
    """Case: UT-M5-JWT — supported ES256 signing keys verify like RS256."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_jwk = json.loads(ECAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "ec-key", "alg": "ES256", "use": "sig", "key_ops": ["verify"]})

    def serve_jwks(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"keys": [public_jwk]})

    verifier = JWKSVerifier(
        _config(algorithms=("ES256",)),
        client=httpx.Client(transport=httpx.MockTransport(serve_jwks)),
    )
    token = jwt.encode(
        _claims(),
        private_key,
        algorithm="ES256",
        headers={"kid": "ec-key", "typ": "JWT"},
    )
    assert verifier.verify(token) == Principal(sub="operator-a")

    # The real flowstead-demo Supabase ES256 token omits the optional nbf claim.
    # Signature, issuer, audience, issued-at and expiry are still mandatory.
    without_nbf = _claims()
    without_nbf.pop("nbf")
    token_without_nbf = jwt.encode(
        without_nbf, private_key, algorithm="ES256", headers={"kid": "ec-key"}
    )
    assert verifier.verify(token_without_nbf) == Principal(sub="operator-a")

    future_nbf = _claims(nbf=int((datetime.now(UTC) + timedelta(minutes=10)).timestamp()))
    future_token = jwt.encode(future_nbf, private_key, algorithm="ES256", headers={"kid": "ec-key"})
    _rejected(verifier, future_token)

    without_exp = dict(without_nbf)
    without_exp.pop("exp")
    bad_exp_token = jwt.encode(
        without_exp, private_key, algorithm="ES256", headers={"kid": "ec-key"}
    )
    _rejected(verifier, bad_exp_token)
