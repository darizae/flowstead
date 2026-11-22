"""System health routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/api/v1/health/live", response_model=HealthResponse)
def health_live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/api/v1/health/ready", response_model=HealthResponse)
def health_ready(request: Request) -> HealthResponse:
    try:
        with request.app.state.database.connect() as connection:
            connection.execute("SELECT 1")
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "not_ready", "message": "database is not reachable"},
        ) from error
    return HealthResponse(status="ok")


@router.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
