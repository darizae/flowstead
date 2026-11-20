"""Flowstead FastAPI read API with server-side Plant authorization."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .auth import (
    AuthConfigurationError,
    Principal,
    TokenVerifier,
    UnavailableVerifier,
    get_current_principal,
    verifier_from_env,
)
from .database import Database, ForecastRead, PlantRow, ReadingRow
from .message_store import ForecastJob
from .models import (
    DissolvedOxygenMeasurement,
    EffluentPhMeasurement,
    FlowMeasurement,
    ForecastHour,
    ForecastJobResponse,
    ForecastResponse,
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
from .report import render_report, safe_report_filename
from .security import HttpSecurityMiddleware, SecurityConfig

MAX_HISTORY_HOURS = 168
MAX_RESPONSE_BYTES = 512_000


def create_app(
    database_url: str | None = None,
    *,
    auth_verifier: TokenVerifier | None = None,
    security_config: SecurityConfig | None = None,
) -> FastAPI:
    app = FastAPI(title="Flowstead API", version="0.1.0")
    security = security_config or SecurityConfig.from_env()
    if security.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(security.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Accept", "Authorization", "Content-Type"],
            expose_headers=[
                "Content-Disposition",
                "Retry-After",
                "X-RateLimit-Remaining",
            ],
            max_age=600,
        )
    app.add_middleware(HttpSecurityMiddleware, config=security)
    app.state.database = Database(database_url)
    if auth_verifier is not None:
        app.state.auth_verifier = auth_verifier
        app.state.auth_configuration_error = None
    else:
        try:
            app.state.auth_verifier = verifier_from_env()
            app.state.auth_configuration_error = None
        except AuthConfigurationError as error:
            app.state.auth_verifier = UnavailableVerifier()
            app.state.auth_configuration_error = str(error)

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
    @app.get(
        "/api/v1/public/plants/{plant_id}/forecast",
        response_model=ForecastResponse,
        tags=["public"],
    )
    def public_forecast(plant_id: str) -> ForecastResponse:
        result = app.state.database.forecast(plant_id, subject_id=None, public=True)
        if result is None:
            raise _not_found()
        return _forecast_response(result, public=True)

    @app.get("/api/v1/public/plants/{plant_id}/report.pdf", tags=["public"])
    def public_report(plant_id: str) -> Response:
        plant = app.state.database.plant(plant_id, subject_id=None, public=True)
        if plant is None:
            raise _not_found()
        latest_result = app.state.database.latest(plant_id, subject_id=None, public=True)
        reading = latest_result[1] if latest_result is not None else None
        forecast = app.state.database.forecast(plant_id, subject_id=None, public=True)
        content = render_report(plant, reading, forecast, generated_at_utc=datetime.now(UTC))
        return _report_response(plant, content)

    @app.get("/api/v1/plants", response_model=PlantListResponse, tags=["private"])
    def private_plants(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> PlantListResponse:
        plants = app.state.database.list_plants(subject_id=principal.sub, public=False)
        return PlantListResponse(plants=[_summary(plant, public=False) for plant in plants])

    @app.get("/api/v1/plants/{plant_id}/latest", response_model=LatestResponse, tags=["private"])
    def private_latest(
        plant_id: str,
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> LatestResponse:
        result = app.state.database.latest(plant_id, subject_id=principal.sub, public=False)
        if result is None:
            raise _not_found()
        plant, reading = result
        return LatestResponse(plant=_summary(plant, public=False), reading=_latest_reading(reading))

    @app.get("/api/v1/plants/{plant_id}/history", response_model=HistoryResponse, tags=["private"])
    def private_history(
        plant_id: str,
        principal: Annotated[Principal, Depends(get_current_principal)],
        window: Annotated[tuple[datetime, datetime], Depends(parse_window)],
    ) -> HistoryResponse:
        from_utc, to_utc = window
        result = app.state.database.history(
            plant_id, from_utc, to_utc, subject_id=principal.sub, public=False
        )
        if result is None:
            raise _not_found()
        plant, readings = result
        return _history_response(plant, readings, from_utc, to_utc, public=False)
    @app.get(
        "/api/v1/plants/{plant_id}/forecast",
        response_model=ForecastResponse,
        tags=["private"],
    )
    def private_forecast(
        plant_id: str,
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> ForecastResponse:
        result = app.state.database.forecast(plant_id, subject_id=principal.sub, public=False)
        if result is None:
            raise _not_found()
        return _forecast_response(result, public=False)
    @app.get("/api/v1/plants/{plant_id}/report.pdf", tags=["private"])
    def private_report(
        plant_id: str,
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Response:
        plant = app.state.database.plant(plant_id, subject_id=principal.sub, public=False)
        if plant is None:
            raise _not_found()
        latest_result = app.state.database.latest(plant_id, subject_id=principal.sub, public=False)
        reading = latest_result[1] if latest_result is not None else None
        forecast = app.state.database.forecast(plant_id, subject_id=principal.sub, public=False)
        content = render_report(plant, reading, forecast, generated_at_utc=datetime.now(UTC))
        return _report_response(plant, content)


    @app.post(
        "/api/v1/plants/{plant_id}/forecast-requests",
        response_model=ForecastJobResponse,
        status_code=202,
        tags=["private"],
    )
    def request_private_forecast(
        plant_id: str,
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> ForecastJobResponse:
        job = app.state.database.enqueue_forecast(plant_id, subject_id=principal.sub)
        if job is None:
            raise _not_found()
        return _forecast_job_response(job)

    @app.get(
        "/api/v1/forecast-requests/{correlation_id}",
        response_model=ForecastJobResponse,
        tags=["private"],
    )
    def private_forecast_status(
        correlation_id: UUID,
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> ForecastJobResponse:
        job = app.state.database.forecast_job(
            correlation_id, subject_id=principal.sub
        )
        if job is None:
            raise _not_found()
        return _forecast_job_response(job)


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
    return parsed.astimezone(UTC)


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


def _forecast_response(result: ForecastRead, *, public: bool) -> ForecastResponse:
    build = result.build
    response = ForecastResponse(
        plant=_summary(result.plant, public=public),
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
        raise HTTPException(status_code=422, detail={"code": "response_too_large", "message": "response cap exceeded"})
    return response


def _forecast_job_response(job: ForecastJob) -> ForecastJobResponse:
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
        influent_flow=FlowMeasurement(value=_number(values[0]), quality=qualities[0], units="gal/h"),
        rainfall=RainfallMeasurement(value=_number(values[1]), quality=qualities[1], units="in/h"),
        dissolved_oxygen=DissolvedOxygenMeasurement(value=_number(values[2]), quality=qualities[2], units="mg/L"),
        effluent_ph=EffluentPhMeasurement(value=_number(values[3]), quality=qualities[3], units="unitless"),
    )


def _number(value: object) -> float | None:
    return None if value is None else float(value)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "plant_not_found", "message": "Plant not found"})
def _report_response(plant: PlantRow, content: bytes) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_report_filename(plant)}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


app = create_app()
