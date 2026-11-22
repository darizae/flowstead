"""Pure domain value objects keep source identity and immutable telemetry unchanged."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from flowstead_api.domain.models import Plant, TelemetryReading


def test_plant_is_an_immutable_location_value() -> None:
    plant = Plant(
        plant_id="plant-01",
        name="Cypress Ridge",
        city="Gainesville",
        state_code="FL",
        timezone="America/New_York",
        latitude=Decimal("29.65160"),
        longitude=Decimal("-82.32480"),
    )
    assert (plant.plant_id, plant.timezone, plant.latitude) == (
        "plant-01",
        "America/New_York",
        Decimal("29.65160"),
    )
    with pytest.raises(FrozenInstanceError):
        plant.name = "unexpected mutation"  # type: ignore[misc]


def test_telemetry_reading_is_an_immutable_measurement_value() -> None:
    issued_at = datetime(2025, 12, 31, 23, tzinfo=UTC)
    reading = TelemetryReading(
        plant_id="plant-01",
        timestamp_utc=issued_at,
        values=(Decimal("420.2"), None),
        qualities=("valid", "missing"),
    )
    assert reading.timestamp_utc == issued_at
    assert reading.values == (Decimal("420.2"), None)
    assert reading.qualities == ("valid", "missing")
    with pytest.raises(FrozenInstanceError):
        reading.qualities = ()  # type: ignore[misc]
