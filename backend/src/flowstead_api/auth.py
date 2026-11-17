"""Local-only deterministic authentication fixture for T-003."""

from __future__ import annotations

import os
import re

from fastapi import Header, HTTPException

_SUBJECT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def get_current_subject(
    authorization: str | None = Header(default=None),
    x_flowstead_subject: str | None = Header(default=None),
) -> str:
    """Return a local fixture subject; production mode deliberately denies all access."""
    mode = os.environ.get("FLOWSTEAD_AUTH_MODE", "deny")
    if mode.lower() in {"deny", "production"}:
        raise _unauthorized()
    candidate = x_flowstead_subject
    if candidate is None and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            candidate = token.removeprefix("local:")
    if not candidate or not _SUBJECT.fullmatch(candidate):
        raise _unauthorized()
    return candidate


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Authentication required"})
