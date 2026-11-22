"""Persistence-independent report projection consumed by the PDF renderer.

The HTTP boundary maps authorized query results here. Domain-oriented report
data never needs to know PostgreSQL row classes or HTTP serialization.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from ..forecast import ForecastBuild


class PlantSource(Protocol):
    plant_id: str
    name: str
    city: str
    state_code: str
    timezone: str


class ReadingSource(Protocol):
    values: tuple[Decimal | None, ...]
    qualities: tuple[str, ...]


class ForecastSource(Protocol):
    build: ForecastBuild


@dataclass(frozen=True, slots=True)
class ReportPlant:
    plant_id: str
    name: str
    city: str
    state_code: str
    timezone: str


@dataclass(frozen=True, slots=True)
class ReportReading:
    values: tuple[Decimal | None, ...]
    qualities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReportForecast:
    build: ForecastBuild


@dataclass(frozen=True, slots=True)
class ReportData:
    plant: ReportPlant
    reading: ReportReading | None
    forecast: ReportForecast | None


def report_data(
    plant: PlantSource, reading: ReadingSource | None, forecast: ForecastSource | None
) -> ReportData:
    return ReportData(
        plant=ReportPlant(
            plant_id=plant.plant_id,
            name=plant.name,
            city=plant.city,
            state_code=plant.state_code,
            timezone=plant.timezone,
        ),
        reading=None if reading is None else ReportReading(reading.values, reading.qualities),
        forecast=None if forecast is None else ReportForecast(forecast.build),
    )
