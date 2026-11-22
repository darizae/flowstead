"""Public and private Plant read routes (list, latest, history, report)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ....auth import Principal, get_current_principal
from ....report import render_report
from ..mappers import (
    history_response,
    latest_response,
    not_found,
    parse_window,
    plant_summary,
    report_response,
)
from ..schemas import HistoryResponse, LatestResponse, PlantListResponse

router = APIRouter()


@router.get("/api/v1/public/plants", response_model=PlantListResponse, tags=["public"])
def public_plants(request: Request) -> PlantListResponse:
    plants = request.app.state.database.list_plants(subject_id=None, public=True)
    return PlantListResponse(plants=[plant_summary(plant, public=True) for plant in plants])


@router.get(
    "/api/v1/public/plants/{plant_id}/latest", response_model=LatestResponse, tags=["public"]
)
def public_latest(request: Request, plant_id: str) -> LatestResponse:
    result = request.app.state.database.latest(plant_id, subject_id=None, public=True)
    if result is None:
        raise not_found()
    plant, reading = result
    return latest_response(plant, reading, public=True)


@router.get(
    "/api/v1/public/plants/{plant_id}/history", response_model=HistoryResponse, tags=["public"]
)
def public_history(
    request: Request,
    plant_id: str,
    window: Annotated[tuple[datetime, datetime], Depends(parse_window)],
) -> HistoryResponse:
    from_utc, to_utc = window
    result = request.app.state.database.history(
        plant_id, from_utc, to_utc, subject_id=None, public=True
    )
    if result is None:
        raise not_found()
    plant, readings = result
    return history_response(plant, readings, from_utc, to_utc, public=True)


@router.get("/api/v1/public/plants/{plant_id}/report.pdf", tags=["public"])
def public_report(request: Request, plant_id: str) -> Response:
    plant = request.app.state.database.plant(plant_id, subject_id=None, public=True)
    if plant is None:
        raise not_found()
    latest_result = request.app.state.database.latest(plant_id, subject_id=None, public=True)
    reading = latest_result[1] if latest_result is not None else None
    forecast = request.app.state.database.forecast(plant_id, subject_id=None, public=True)
    content = render_report(plant, reading, forecast, generated_at_utc=datetime.now(UTC))
    return report_response(plant, content)


@router.get("/api/v1/plants", response_model=PlantListResponse, tags=["private"])
def private_plants(
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> PlantListResponse:
    plants = request.app.state.database.list_plants(subject_id=principal.sub, public=False)
    return PlantListResponse(plants=[plant_summary(plant, public=False) for plant in plants])


@router.get("/api/v1/plants/{plant_id}/latest", response_model=LatestResponse, tags=["private"])
def private_latest(
    request: Request,
    plant_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> LatestResponse:
    result = request.app.state.database.latest(plant_id, subject_id=principal.sub, public=False)
    if result is None:
        raise not_found()
    plant, reading = result
    return latest_response(plant, reading, public=False)


@router.get("/api/v1/plants/{plant_id}/history", response_model=HistoryResponse, tags=["private"])
def private_history(
    request: Request,
    plant_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    window: Annotated[tuple[datetime, datetime], Depends(parse_window)],
) -> HistoryResponse:
    from_utc, to_utc = window
    result = request.app.state.database.history(
        plant_id, from_utc, to_utc, subject_id=principal.sub, public=False
    )
    if result is None:
        raise not_found()
    plant, readings = result
    return history_response(plant, readings, from_utc, to_utc, public=False)


@router.get("/api/v1/plants/{plant_id}/report.pdf", tags=["private"])
def private_report(
    request: Request,
    plant_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Response:
    plant = request.app.state.database.plant(plant_id, subject_id=principal.sub, public=False)
    if plant is None:
        raise not_found()
    latest_result = request.app.state.database.latest(
        plant_id, subject_id=principal.sub, public=False
    )
    reading = latest_result[1] if latest_result is not None else None
    forecast = request.app.state.database.forecast(plant_id, subject_id=principal.sub, public=False)
    content = render_report(plant, reading, forecast, generated_at_utc=datetime.now(UTC))
    return report_response(plant, content)
