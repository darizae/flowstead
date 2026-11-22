"""Authentication infrastructure: configuration, verification, and HTTP dependency."""

from .config import AuthConfig, AuthConfigurationError
from .dependency import get_current_principal
from .jwt_verifier import (
    AuthenticationError,
    JWKSVerifier,
    LegacyAuthEndpointVerifier,
    Principal,
    TokenVerifier,
    UnavailableVerifier,
    verifier_from_config,
    verifier_from_env,
)

__all__ = [
    "AuthConfig",
    "AuthConfigurationError",
    "AuthenticationError",
    "JWKSVerifier",
    "LegacyAuthEndpointVerifier",
    "Principal",
    "TokenVerifier",
    "UnavailableVerifier",
    "get_current_principal",
    "verifier_from_config",
    "verifier_from_env",
]
