"""JWT and Supabase Auth endpoint verification adapters."""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

import httpx
import jwt

from .config import AuthConfig, AuthConfigurationError

_LOGGER = logging.getLogger(__name__)
_SUBJECT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_MAX_RESPONSE_BYTES = 65_536
_MAX_JWKS_KEYS = 16


class AuthenticationError(Exception):
    """An intentionally detail-free authentication failure."""


@dataclass(frozen=True, slots=True)
class Principal:
    """Verified application identity; Plant access remains a separate SQL decision."""

    sub: str


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
