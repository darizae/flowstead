"""FastAPI dependency for verified bearer identities."""

from __future__ import annotations

import re

from fastapi import Header, HTTPException, Request

from .jwt_verifier import AuthenticationError, Principal, TokenVerifier

_MAX_BEARER_BYTES = 16_384
_JWT_COMPACT = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


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


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "unauthorized", "message": "Authentication required"},
        headers={"WWW-Authenticate": "Bearer"},
    )
