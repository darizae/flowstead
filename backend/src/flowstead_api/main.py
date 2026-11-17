"""Flowstead FastAPI read API with server-side Plant authorization."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query

from .auth import get_current_subject
from .database import Database, PlantRow, ReadingRow
from .models import (
    DissolvedOxygenMeasurement,
    EffluentPhMeasurement,
    FlowMeasurement,
    HealthResponse,
    HistoryReading,
    HistoryResponse,
    LatestReading,
    LatestResponse,
    Measurements,
    PlantLinks,
    PlantListResponse,
    PlantLocation,
    PlantSummary,
    RainfallMeasurement,
)

MAX_HISTORY_HOURS = 168
MAX_RESPONSE_BYTES = 512_000


def create_app(database_url: str | None = None) -> FastAPI:
    app = FastAPI(title="Flowstead API", version="0.1.0")
    app.state.database = Database(database_url)

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/v1/public/plants", response_model=PlantListResponse, tags=["public"])
    def public_plants() -> PlantListResponse:
        plants = app.state.database.list_plants(subject_id=None, public=True)
        return PlantListResponse(plants=[_summary(plant, public=True) for plant in plants])

    @app.get("/api/v1/public/plants/{plant_id}/latest", response_model=LatestResponse, tags=["public"])
    def public_latest(plant_id: str) -> LatestResponse:
        result = app.state.database.latest(plant_id, subject_id=None, public=True)
        if result is None:
            raise _not_found()
        plant, reading = result
        return LatestResponse(plant=_summary(plant, public=True), reading=_latest_reading(reading))

    @app.get("/api/v1/public/plants/{plant_id}/history", response_model=HistoryResponse, tags=["public"])
    def public_history(plant_id: str, window: Annotated[tuple[datetime, datetime], Depends(parse_window)]) -> HistoryResponse:
        from_utc, to_utc = window
        result = app.state.database.history(
            plant_id, from_utc, to_utc, subject_id=None, public=True
        )
        if result is None:
            raise _not_found()
        plant, readings = result
        return _history_response(plant, readings, from_utc, to_utc, public=True)

    @app.get("/api/v1/plants", response_model=PlantListResponse, tags=["private"])
    def private_plants(subject_id: Annotated[str, Depends(get_current_subject)]) -> PlantListResponse:
        plants = app.state.database.list_plants(subject_id=subject_id, public=False)
        return PlantListResponse(plants=[_summary(plant, public=False) for plant in plants])

    @app.get("/api/v1/plants/{plant_id}/latest", response_model=LatestResponse, tags=["private"])
    def private_latest(
        plant_id: str, subject_id: Annotated[str, Depends(get_current_subject)]
    ) -> LatestResponse:
        result = app.state.database.latest(plant_id, subject_id=subject_id, public=False)
        if result is None:
            raise _not_found()
        plant, reading = result
        return LatestResponse(plant=_summary(plant, public=False), reading=_latest_reading(reading))

    @app.get("/api/v1/plants/{plant_id}/history", response_model=HistoryResponse, tags=["private"])
    def private_history(
        plant_id: str,
        subject_id: Annotated[str, Depends(get_current_subject)],
        window: Annotated[tuple[datetime, datetime], Depends(parse_window)],
    ) -> HistoryResponse:
        from_utc, to_utc = window
        result = app.state.database.history(
            plant_id, from_utc, to_utc, subject_id=subject_id, public=False
        )
        if result is None:
            raise _not_found()
        plant, readings = result
        return _history_response(plant, readings, from_utc, to_utc, public=False)

    return app




def parse_window(
    from_: Annotated[str, Query(alias="from")],
    to: Annotated[str, Query(alias="to")],
) -> tuple[datetime, datetime]:
    try:
        from_utc = _parse_utc_hour(from_)
        to_utc = _parse_utc_hour(to)
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "invalid_window", "message": str(error)}) from error
    duration = to_utc - from_utc
    if duration < timedelta(hours=1) or duration > timedelta(hours=MAX_HISTORY_HOURS):
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_window", "message": "window must be between 1 and 168 hours"},
        )
    return from_utc, to_utc


def _parse_utc_hour(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamps must include UTC timezone information")
    if parsed.minute or parsed.second or parsed.microsecond:
        raise ValueError("timestamps must be aligned to UTC hours")
    return parsed.astimezone(timezone.utc)


def _summary(plant: PlantRow, *, public: bool) -> PlantSummary:
    prefix = "/api/v1/public" if public else "/api/v1"
    root = f"{prefix}/plants/{plant.plant_id}"
    return PlantSummary(
        plant_id=plant.plant_id,
        name=plant.name,
        location=PlantLocation(
            city=plant.city,
            state_code=plant.state_code,
            latitude=plant.latitude,
            longitude=plant.longitude,
        ),
        timezone=plant.timezone,
        links=PlantLinks(
            latest=f"{root}/latest",
            history=f"{root}/history",
            forecast=f"{root}/forecast",
        ),
    )


def _latest_reading(reading: ReadingRow) -> LatestReading:
    return LatestReading(
        plant_id=reading.plant_id,
        timestamp_utc=reading.timestamp_utc,
        measurements=_measurements(reading),
    )


def _history_response(
    plant: PlantRow,
    readings: list[ReadingRow],
    from_utc: datetime,
    to_utc: datetime,
    *,
    public: bool,
) -> HistoryResponse:
    result = HistoryResponse(
        plant=_summary(plant, public=public),
        from_utc=from_utc,
        to_utc=to_utc,
        readings=[
            HistoryReading(
                plant_id=reading.plant_id,
                timestamp_utc=reading.timestamp_utc,
                measurements=_measurements(reading),
            )
            for reading in readings
        ],
    )
    payload = json.dumps(result.model_dump(mode="json"), separators=(",", ":"))
    if len(payload.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise HTTPException(status_code=422, detail={"code": "response_too_large", "message": "response cap exceeded"})
    return result


def _measurements(reading: ReadingRow) -> Measurements:
    values = reading.values
    qualities = reading.qualities
    return Measurements(
        influent_flow=FlowMeasurement(value=_number(values[0]), quality=qualities[0], units="gal/h"),
        rainfall=RainfallMeasurement(value=_number(values[1]), quality=qualities[1], units="in/h"),
        dissolved_oxygen=DissolvedOxygenMeasurement(value=_number(values[2]), quality=qualities[2], units="mg/L"),
        effluent_ph=EffluentPhMeasurement(value=_number(values[3]), quality=qualities[3], units="unitless"),
    )


def _number(value: object) -> float | None:
    return None if value is None else float(value)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "plant_not_found", "message": "Plant not found"})

app = create_app()
