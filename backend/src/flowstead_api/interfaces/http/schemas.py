"""Stable JSON contracts for Flowstead read endpoints (transport schemas)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

Quality = Literal["valid", "invalid", "missing"]


class FlowMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None
    quality: Quality
    units: Literal["gal/h"]


class RainfallMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None
    quality: Quality
    units: Literal["in/h"]


class DissolvedOxygenMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None
    quality: Quality
    units: Literal["mg/L"]


class EffluentPhMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None
    quality: Quality
    units: Literal["unitless"]


class Measurements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    influent_flow: FlowMeasurement
    rainfall: RainfallMeasurement
    dissolved_oxygen: DissolvedOxygenMeasurement
    effluent_ph: EffluentPhMeasurement


class PlantLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city: str
    state_code: Literal["FL"]
    latitude: float
    longitude: float


class PlantLinks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latest: str
    history: str
    forecast: str


class PlantSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: str
    name: str
    location: PlantLocation
    timezone: str
    links: PlantLinks

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except Exception as error:
            raise ValueError("timezone must be an IANA timezone") from error
        return value


class LatestReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: str
    timestamp_utc: datetime
    latest: Literal[True] = True
    measurements: Measurements

    @field_serializer("timestamp_utc")
    def serialize_timestamp(self, value: datetime) -> str:
        return _utc_iso(value)


class LatestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latest: Literal[True] = True
    plant: PlantSummary
    reading: LatestReading


class HistoryReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: str
    timestamp_utc: datetime
    latest: Literal[False] = False
    measurements: Measurements

    @field_serializer("timestamp_utc")
    def serialize_timestamp(self, value: datetime) -> str:
        return _utc_iso(value)


class HistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant: PlantSummary
    from_utc: datetime
    to_utc: datetime
    readings: list[HistoryReading] = Field(default_factory=list)

    @field_serializer("from_utc", "to_utc")
    def serialize_window(self, value: datetime) -> str:
        return _utc_iso(value)


class ForecastHour(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hour_number: int = Field(ge=1, le=12)
    target_time_utc: datetime
    predicted_flow_gal_h: float
    units: Literal["gal/h"] = "gal/h"
    source: Literal["seasonal_naive_24h", "persistence_6h", "stored"]

    @field_serializer("target_time_utc")
    def serialize_target(self, value: datetime) -> str:
        return _utc_iso(value)


class ForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant: PlantSummary
    status: Literal["available", "unavailable"]
    issued_at_utc: datetime | None
    model_version: str
    source_revision: str | None
    physical_bound_rule: str
    forecasts: list[ForecastHour] = Field(default_factory=list)
    unavailable_reason: str | None = None

    @field_serializer("issued_at_utc")
    def serialize_issued_at(self, value: datetime | None) -> str | None:
        return None if value is None else _utc_iso(value)


class ForecastJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_event_id: UUID
    correlation_id: UUID
    plant_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    requested_at_utc: datetime
    completed_at_utc: datetime | None = None
    diagnostic: str | None = None

    @field_serializer("requested_at_utc", "completed_at_utc")
    def serialize_job_time(self, value: datetime | None) -> str | None:
        return None if value is None else _utc_iso(value)


class PlantListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plants: list[PlantSummary]


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
