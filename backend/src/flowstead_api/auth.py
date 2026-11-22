"""Supabase-compatible bearer authentication with fail-closed verification."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

import httpx
import jwt
from fastapi import Header, HTTPException, Request

_LOGGER = logging.getLogger(__name__)
_SUBJECT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SUPPORTED_ASYMMETRIC_ALGORITHMS = frozenset({"ES256", "RS256"})
_MAX_RESPONSE_BYTES = 65_536
_MAX_JWKS_KEYS = 16
_MAX_BEARER_BYTES = 16_384
_JWT_COMPACT = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


class AuthConfigurationError(ValueError):
    """Raised when server-side authentication configuration is unsafe or incomplete."""


class AuthenticationError(Exception):
    """An intentionally detail-free authentication failure."""


@dataclass(frozen=True, slots=True)
class Principal:
    """Verified application identity; Plant access remains a separate SQL decision."""

    sub: str


@dataclass(frozen=True, slots=True)
class AuthConfig:
    """Validated server-only configuration for one Supabase Auth authority."""

    auth_url: str
    issuer: str
    audience: str
    algorithms: tuple[str, ...]
    verification_mode: str = "jwks"
    publishable_key: str | None = None
    jwks_ttl_seconds: float = 600.0
    unknown_kid_refresh_seconds: float = 5.0
    http_timeout_seconds: float = 3.0

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AuthConfig:
        values = os.environ if environ is None else environ
        auth_mode = values.get("FLOWSTEAD_AUTH_MODE", "supabase").strip().lower()
        if auth_mode != "supabase":
            raise AuthConfigurationError(
                "FLOWSTEAD_AUTH_MODE must be 'supabase'; local/test principal modes are forbidden"
            )

        auth_url = _required(values, "SUPABASE_AUTH_URL").rstrip("/")
        issuer = _required(values, "SUPABASE_JWT_ISSUER").rstrip("/")
        _require_https_url(auth_url, "SUPABASE_AUTH_URL")
        _require_https_url(issuer, "SUPABASE_JWT_ISSUER")
        if auth_url != issuer:
            raise AuthConfigurationError(
                "SUPABASE_AUTH_URL and SUPABASE_JWT_ISSUER must name the same Auth authority"
            )

        audience = _required(values, "SUPABASE_JWT_AUDIENCE")
        raw_algorithms = values.get("SUPABASE_JWT_ALGORITHMS", "ES256,RS256")
        algorithms = tuple(
            dict.fromkeys(part.strip() for part in raw_algorithms.split(",") if part.strip())
        )
        if not algorithms or not set(algorithms) <= _SUPPORTED_ASYMMETRIC_ALGORITHMS:
            raise AuthConfigurationError(
                "SUPABASE_JWT_ALGORITHMS must contain only supported asymmetric algorithms"
            )

        verification_mode = values.get("SUPABASE_AUTH_VERIFICATION_MODE", "jwks").strip().lower()
        if verification_mode not in {"jwks", "legacy-auth-endpoint"}:
            raise AuthConfigurationError(
                "SUPABASE_AUTH_VERIFICATION_MODE must be 'jwks' or 'legacy-auth-endpoint'"
            )
        publishable_key = values.get("SUPABASE_PUBLISHABLE_KEY")
        if verification_mode == "legacy-auth-endpoint" and not publishable_key:
            raise AuthConfigurationError(
                "SUPABASE_PUBLISHABLE_KEY is required for legacy Auth endpoint verification"
            )

        return cls(
            auth_url=auth_url,
            issuer=issuer,
            audience=audience,
            algorithms=algorithms,
            verification_mode=verification_mode,
            publishable_key=publishable_key,
        )

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"

    @property
    def user_url(self) -> str:
        return f"{self.auth_url}/user"


class TokenVerifier(Protocol):
    def verify(self, token: str) -> Principal: ...


class JWKSVerifier:
    """Verify asymmetric JWTs against a bounded, rotation-aware JWKS cache."""

    def __init__(
        self,
        config: AuthConfig,
        *,
        client: httpx.Client | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if config.verification_mode != "jwks":
            raise AuthConfigurationError("JWKSVerifier requires jwks verification mode")
        self.config = config
        self._client = client or httpx.Client(
            timeout=config.http_timeout_seconds,
            follow_redirects=False,
        )
        self._clock = clock
        self._keys: dict[tuple[str, str], jwt.PyJWK] = {}
        self._expires_at = 0.0
        self._last_refresh_at = float("-inf")
        self._lock = threading.RLock()

    def verify(self, token: str) -> Principal:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            algorithm = header.get("alg")
            if not isinstance(kid, str) or not kid or len(kid) > 256:
                raise AuthenticationError()
            if algorithm not in self.config.algorithms:
                raise AuthenticationError()
            key = self._key_for(kid, algorithm)
            claims = jwt.decode(
                token,
                key=key,
                algorithms=list(self.config.algorithms),
                audience=self.config.audience,
                issuer=self.config.issuer,
                options={
                    "require": ["sub", "iss", "aud", "exp", "iat"],
                    # Supabase ES256 Auth tokens do not necessarily include nbf.
                    # verify_nbf=True below still rejects future nbf when sent.
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )
            subject = claims.get("sub")
            if not isinstance(subject, str) or not _SUBJECT.fullmatch(subject):
                raise AuthenticationError()
            return Principal(sub=subject)
        except AuthenticationError:
            raise
        except jwt.PyJWTError as error:
            raise AuthenticationError() from error

    def _key_for(self, kid: str, algorithm: str) -> jwt.PyJWK:
        now = self._clock()
        with self._lock:
            cache_expired = now >= self._expires_at
            key = self._keys.get((kid, algorithm))
            unknown_refresh_due = (
                key is None
                and now - self._last_refresh_at >= self.config.unknown_kid_refresh_seconds
            )
            if cache_expired or not self._keys or unknown_refresh_due:
                self._refresh(now)
                key = self._keys.get((kid, algorithm))
            if key is None:
                raise AuthenticationError()
            return key

    def _refresh(self, now: float) -> None:
        try:
            response = self._client.get(
                self.config.jwks_url,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            if len(response.content) > _MAX_RESPONSE_BYTES:
                raise ValueError("JWKS response exceeds size limit")
            document = response.json()
            raw_keys = document.get("keys") if isinstance(document, dict) else None
            if not isinstance(raw_keys, list) or not 1 <= len(raw_keys) <= _MAX_JWKS_KEYS:
                raise ValueError("JWKS key count is invalid")
            parsed: dict[tuple[str, str], jwt.PyJWK] = {}
            for raw_key in raw_keys:
                if not isinstance(raw_key, dict):
                    raise TypeError("JWKS key is invalid")
                kid = raw_key.get("kid")
                algorithm = raw_key.get("alg")
                use = raw_key.get("use")
                key_ops = raw_key.get("key_ops")
                if (
                    not isinstance(kid, str)
                    or not kid
                    or algorithm not in self.config.algorithms
                    or use not in {None, "sig"}
                    or (key_ops is not None and "verify" not in key_ops)
                ):
                    continue
                cache_key = (kid, algorithm)
                if cache_key in parsed:
                    raise ValueError("JWKS contains a duplicate key identifier")
                pyjwk = jwt.PyJWK.from_dict(raw_key, algorithm=algorithm)
                if pyjwk.algorithm_name != algorithm:
                    raise ValueError("JWKS algorithm mismatch")
                parsed[cache_key] = pyjwk
            if not parsed:
                raise ValueError("JWKS contains no supported verification key")
        except (httpx.HTTPError, jwt.PyJWTError, ValueError, TypeError, KeyError) as error:
            _LOGGER.warning("authentication key refresh failed")
            raise AuthenticationError() from error

        self._keys = parsed
        self._last_refresh_at = now
        self._expires_at = now + self.config.jwks_ttl_seconds


class LegacyAuthEndpointVerifier:
    """Validate legacy symmetric tokens through the configured Supabase Auth server."""

    def __init__(self, config: AuthConfig, *, client: httpx.Client | None = None) -> None:
        if config.verification_mode != "legacy-auth-endpoint" or not config.publishable_key:
            raise AuthConfigurationError(
                "LegacyAuthEndpointVerifier requires legacy mode and a publishable key"
            )
        self.config = config
        self._client = client or httpx.Client(
            timeout=config.http_timeout_seconds,
            follow_redirects=False,
        )

    def verify(self, token: str) -> Principal:
        try:
            response = self._client.get(
                self.config.user_url,
                headers={
                    "Accept": "application/json",
                    "apikey": self.config.publishable_key or "",
                    "Authorization": f"Bearer {token}",
                },
            )
            response.raise_for_status()
            if len(response.content) > _MAX_RESPONSE_BYTES:
                raise ValueError("Auth response exceeds size limit")
            body = response.json()
            subject = body.get("id") if isinstance(body, dict) else None
            audience = body.get("aud") if isinstance(body, dict) else None
            if (
                not isinstance(subject, str)
                or not _SUBJECT.fullmatch(subject)
                or audience != self.config.audience
            ):
                raise ValueError("Auth response identity is invalid")
            return Principal(sub=subject)
        except (httpx.HTTPError, ValueError, TypeError) as error:
            _LOGGER.warning("legacy authentication endpoint verification failed")
            raise AuthenticationError() from error


class UnavailableVerifier:
    """Fail closed while leaving the public health endpoint operational."""

    def verify(self, token: str) -> Principal:
        raise AuthenticationError()


def verifier_from_config(
    config: AuthConfig,
    *,
    client: httpx.Client | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> TokenVerifier:
    if config.verification_mode == "jwks":
        return JWKSVerifier(config, client=client, clock=clock)
    return LegacyAuthEndpointVerifier(config, client=client)


def verifier_from_env(environ: Mapping[str, str] | None = None) -> TokenVerifier:
    return verifier_from_config(AuthConfig.from_env(environ))


def get_current_principal(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Principal:
    """Return only a verified subject; never accept caller-supplied Plant access."""
    token = _bearer_token(authorization)
    verifier: TokenVerifier = request.app.state.auth_verifier
    try:
        return verifier.verify(token)
    except AuthenticationError as error:
        raise _unauthorized() from error


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.isascii() or len(authorization) > _MAX_BEARER_BYTES:
        raise _unauthorized()
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not _JWT_COMPACT.fullmatch(parts[1]):
        raise _unauthorized()
    return parts[1]


def _required(values: Mapping[str, str], name: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise AuthConfigurationError(f"{name} is required")
    return value


def _require_https_url(value: str, name: str) -> None:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise AuthConfigurationError(f"{name} must be an HTTPS URL without credentials or query")


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "unauthorized", "message": "Authentication required"},
        headers={"WWW-Authenticate": "Bearer"},
    )
