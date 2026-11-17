"""Stable JSON contracts for Flowstead read endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

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


class PlantListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plants: list[PlantSummary]


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
