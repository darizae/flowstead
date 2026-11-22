"""Validated configuration for the Supabase-compatible authentication adapter."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

_SUPPORTED_ASYMMETRIC_ALGORITHMS = frozenset({"ES256", "RS256"})


class AuthConfigurationError(ValueError):
    """Raised when server-side authentication configuration is unsafe or incomplete."""


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
