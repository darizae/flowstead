"""Public/private forecast reads and private forecast-request commands."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from ....infrastructure.auth import Principal, get_current_principal
from ..mappers import forecast_job_response, forecast_response, not_found
from ..schemas import ForecastJobResponse, ForecastResponse

router = APIRouter()


@router.get(
    "/api/v1/public/plants/{plant_id}/forecast",
    response_model=ForecastResponse,
    tags=["public"],
)
def public_forecast(request: Request, plant_id: str) -> ForecastResponse:
    result = request.app.state.database.forecast(plant_id, subject_id=None, public=True)
    if result is None:
        raise not_found()
    return forecast_response(result, public=True)


@router.get(
    "/api/v1/plants/{plant_id}/forecast",
    response_model=ForecastResponse,
    tags=["private"],
)
def private_forecast(
    request: Request,
    plant_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ForecastResponse:
    result = request.app.state.database.forecast(plant_id, subject_id=principal.sub, public=False)
    if result is None:
        raise not_found()
    return forecast_response(result, public=False)


@router.post(
    "/api/v1/plants/{plant_id}/forecast-requests",
    response_model=ForecastJobResponse,
    status_code=202,
    tags=["private"],
)
def request_private_forecast(
    request: Request,
    plant_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ForecastJobResponse:
    allowed, _, retry_after = request.app.state.forecast_limiter.check(
        f"{principal.sub}:{plant_id}"
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"code": "request_denied", "message": "Forecast request rate limit exceeded"},
            headers={"Retry-After": str(retry_after)},
        )
    job = request.app.state.database.enqueue_forecast(plant_id, subject_id=principal.sub)
    if job is None:
        raise not_found()
    return forecast_job_response(job)


@router.get(
    "/api/v1/forecast-requests/{correlation_id}",
    response_model=ForecastJobResponse,
    tags=["private"],
)
def private_forecast_status(
    request: Request,
    correlation_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ForecastJobResponse:
    job = request.app.state.database.forecast_job(correlation_id, subject_id=principal.sub)
    if job is None:
        raise not_found()
    return forecast_job_response(job)
