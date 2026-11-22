"""Domain values independent of PostgreSQL rows and HTTP schemas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Plant:
    plant_id: str
    name: str
    city: str
    state_code: str
    timezone: str
    latitude: Decimal
    longitude: Decimal


@dataclass(frozen=True, slots=True)
class TelemetryReading:
    plant_id: str
    timestamp_utc: datetime
    values: tuple[Decimal | None, ...]
    qualities: tuple[str, ...]
