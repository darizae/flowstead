"""Report application data types and persistence-to-report mapping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..domain.models import Plant, TelemetryReading
from ..forecast import ForecastBuild


@dataclass(frozen=True, slots=True)
class ReportPlant:
    plant_id: str
    name: str
    city: str
    state_code: str
    timezone: str
    latitude: Decimal
    longitude: Decimal


@dataclass(frozen=True, slots=True)
class ReportReading:
    plant_id: str
    timestamp_utc: datetime
    values: tuple[Decimal | None, ...]
    qualities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReportForecast:
    plant: ReportPlant
    build: ForecastBuild


@dataclass(frozen=True, slots=True)
class ReportData:
    plant: ReportPlant
    latest: ReportReading | None
    forecast: ReportForecast | None


def report_data(
    plant: Plant, reading: TelemetryReading | None, forecast: tuple[Plant, ForecastBuild] | None
) -> ReportData:
    report_plant = (
        ReportPlant(**plant.__dict__)
        if hasattr(plant, "__dict__")
        else ReportPlant(
            plant.plant_id,
            plant.name,
            plant.city,
            plant.state_code,
            plant.timezone,
            plant.latitude,
            plant.longitude,
        )
    )
    report_reading = (
        None
        if reading is None
        else ReportReading(
            reading.plant_id, reading.timestamp_utc, reading.values, reading.qualities
        )
    )
    report_forecast = None if forecast is None else ReportForecast(report_plant, forecast[1])
    return ReportData(report_plant, report_reading, report_forecast)
