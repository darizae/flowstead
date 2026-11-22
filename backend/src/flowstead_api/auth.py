"""Backward-compatible authentication imports."""

from .infrastructure.auth import (
    AuthConfig,
    AuthConfigurationError,
    AuthenticationError,
    JWKSVerifier,
    LegacyAuthEndpointVerifier,
    Principal,
    TokenVerifier,
    UnavailableVerifier,
    get_current_principal,
    verifier_from_config,
    verifier_from_env,
)
from .infrastructure.auth.dependency import _bearer_token

__all__ = [
    "AuthConfig",
    "AuthConfigurationError",
    "AuthenticationError",
    "JWKSVerifier",
    "LegacyAuthEndpointVerifier",
    "Principal",
    "TokenVerifier",
    "UnavailableVerifier",
    "_bearer_token",
    "get_current_principal",
    "verifier_from_config",
    "verifier_from_env",
]
