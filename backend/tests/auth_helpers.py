"""Test-only FastAPI dependency injection; this module is not packaged for deployment."""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException

from flowstead_api.auth import Principal, get_current_principal

TEST_SUBJECT_HEADER = "X-Flowstead-Test-Subject"


def install_test_principal(app: FastAPI) -> FastAPI:
    """Install an explicit pytest fixture dependency with no environment switch."""

    def test_principal(
        x_flowstead_test_subject: str | None = Header(default=None),
    ) -> Principal:
        if not x_flowstead_test_subject:
            raise HTTPException(
                status_code=401,
                detail={"code": "unauthorized", "message": "Authentication required"},
            )
        return Principal(sub=x_flowstead_test_subject)

    app.dependency_overrides[get_current_principal] = test_principal
    return app


def principal_headers(subject: str) -> dict[str, str]:
    return {TEST_SUBJECT_HEADER: subject}
