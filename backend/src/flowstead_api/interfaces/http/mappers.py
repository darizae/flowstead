"""Presentation mappers and shared HTTP helpers for Flowstead read routes."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import HTTPException, Query, Response

from ...database import ForecastRead, PlantRow, ReadingRow
from ...message_store import ForecastJob
from ...report import safe_report_filename
from .schemas import (
    DissolvedOxygenMeasurement,
    EffluentPhMeasurement,
    FlowMeasurement,
    ForecastHour,
    ForecastJobResponse,
    ForecastResponse,
    HistoryReading,
    HistoryResponse,
    LatestReading,
    LatestResponse,
    Measurements,
    PlantLinks,
    PlantLocation,
    PlantSummary,
    RainfallMeasurement,
)

MAX_HISTORY_HOURS = 168
MAX_RESPONSE_BYTES = 512_000


def parse_window(
    from_: Annotated[str, Query(alias="from")],
    to: Annotated[str, Query(alias="to")],
) -> tuple[datetime, datetime]:
    try:
        from_utc = _parse_utc_hour(from_)
        to_utc = _parse_utc_hour(to)
    except ValueError as error:
        # Never echo the ISO parser's internal exception text to the client.
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_window",
                "message": "window timestamps must be hour-aligned UTC ISO-8601 values",
            },
        ) from error
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
    return parsed.astimezone(UTC)


def plant_summary(plant: PlantRow, *, public: bool) -> PlantSummary:
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


def latest_response(plant: PlantRow, reading: ReadingRow, *, public: bool) -> LatestResponse:
    return LatestResponse(
        plant=plant_summary(plant, public=public),
        reading=LatestReading(
            plant_id=reading.plant_id,
            timestamp_utc=reading.timestamp_utc,
            measurements=_measurements(reading),
        ),
    )


def history_response(
    plant: PlantRow,
    readings: list[ReadingRow],
    from_utc: datetime,
    to_utc: datetime,
    *,
    public: bool,
) -> HistoryResponse:
    result = HistoryResponse(
        plant=plant_summary(plant, public=public),
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
        raise HTTPException(
            status_code=422,
            detail={"code": "response_too_large", "message": "response cap exceeded"},
        )
    return result


def forecast_response(result: ForecastRead, *, public: bool) -> ForecastResponse:
    build = result.build
    response = ForecastResponse(
        plant=plant_summary(result.plant, public=public),
        status="available" if build.available else "unavailable",
        issued_at_utc=build.issued_at_utc,
        model_version=build.model_version,
        source_revision=build.source_revision,
        physical_bound_rule=build.physical_bound_rule,
        forecasts=[
            ForecastHour(
                hour_number=point.hour_number,
                target_time_utc=point.target_time_utc,
                predicted_flow_gal_h=float(point.predicted_flow_gal_h),
                units="gal/h",
                source=point.source,
            )
            for point in build.points
        ],
        unavailable_reason=build.unavailable_reason,
    )
    payload = json.dumps(response.model_dump(mode="json"), separators=(",", ":"))
    if len(payload.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise HTTPException(
            status_code=422,
            detail={"code": "response_too_large", "message": "response cap exceeded"},
        )
    return response


def forecast_job_response(job: ForecastJob) -> ForecastJobResponse:
    return ForecastJobResponse(
        request_event_id=job.request_event_id,
        correlation_id=job.correlation_id,
        plant_id=job.plant_id,
        status=job.status,
        requested_at_utc=job.requested_at,
        completed_at_utc=job.completed_at,
        diagnostic=job.diagnostic,
    )


def _measurements(reading: ReadingRow) -> Measurements:
    values = reading.values
    qualities = reading.qualities
    return Measurements(
        influent_flow=FlowMeasurement(
            value=_number(values[0]), quality=qualities[0], units="gal/h"
        ),
        rainfall=RainfallMeasurement(value=_number(values[1]), quality=qualities[1], units="in/h"),
        dissolved_oxygen=DissolvedOxygenMeasurement(
            value=_number(values[2]), quality=qualities[2], units="mg/L"
        ),
        effluent_ph=EffluentPhMeasurement(
            value=_number(values[3]), quality=qualities[3], units="unitless"
        ),
    )


def _number(value: object) -> float | None:
    return None if value is None else float(value)


def not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"code": "plant_not_found", "message": "Plant not found"}
    )


def report_response(plant: PlantRow, content: bytes) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_report_filename(plant)}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
