"""Immutable synthetic M1 identifiers and provenance policy."""

from __future__ import annotations

from decimal import Decimal
from typing import Final

SOURCE_SHA: Final = "ad5c94d1f46e79312a99cb9721f38700f24fdf6b"
SCHEMA_VERSION: Final = "m1.v1"
SEED: Final = 20250101
MAX_ROWS: Final = 43_800
MAX_READINGS: Final = 175_200
MAX_BYTES: Final = 4_247_080
EXPECTED_UNITS: Final = {
    "influent_flow": "gal/h",
    "rainfall": "in/h",
    "dissolved_oxygen": "mg/L",
    "effluent_ph": "unitless",
}
CHANNELS: Final = tuple(EXPECTED_UNITS)
CSV_COLUMNS: Final = (
    "plant_id",
    "timestamp_utc",
    "influent_flow",
    "influent_flow_quality",
    "rainfall",
    "rainfall_quality",
    "dissolved_oxygen",
    "dissolved_oxygen_quality",
    "effluent_ph",
    "effluent_ph_quality",
)
QUALITY_VALUES: Final = frozenset({"valid", "invalid", "missing"})

# These values are part of the accepted M1 fixture, not geocoded runtime data.
# In particular, plant-04 (Miami) keeps the historical America/Chicago timezone
# from the immutable M1 fixture. Correcting it to America/New_York would reject
# the accepted manifest/data contract (audit #71 decision: unchanged).
APPROVED_PLANTS: Final = {
    "plant-01": {
        "name": "Cypress Ridge Water Reclamation",
        "city": "Gainesville",
        "state_code": "FL",
        "timezone": "America/New_York",
        "latitude": Decimal("29.6516"),
        "longitude": Decimal("-82.3248"),
        "hydraulic_capacity_gal_h": Decimal("620.00"),
    },
    "plant-02": {
        "name": "Gulf Palms Water Reclamation",
        "city": "Tampa",
        "state_code": "FL",
        "timezone": "America/New_York",
        "latitude": Decimal("27.9506"),
        "longitude": Decimal("-82.4572"),
        "hydraulic_capacity_gal_h": Decimal("710.00"),
    },
    "plant-03": {
        "name": "Lake Osprey Water Reclamation",
        "city": "Orlando",
        "state_code": "FL",
        "timezone": "America/New_York",
        "latitude": Decimal("28.5383"),
        "longitude": Decimal("-81.3792"),
        "hydraulic_capacity_gal_h": Decimal("780.00"),
    },
    "plant-04": {
        "name": "Orange Hammock Water Reclamation",
        "city": "Miami",
        "state_code": "FL",
        "timezone": "America/Chicago",
        "latitude": Decimal("25.7617"),
        "longitude": Decimal("-80.1918"),
        "hydraulic_capacity_gal_h": Decimal("665.00"),
    },
    "plant-05": {
        "name": "Pine Harbor Water Reclamation",
        "city": "Pensacola",
        "state_code": "FL",
        "timezone": "America/Chicago",
        "latitude": Decimal("30.4213"),
        "longitude": Decimal("-87.2169"),
        "hydraulic_capacity_gal_h": Decimal("745.00"),
    },
}
APPROVED_PLANT_IDS: Final = frozenset(APPROVED_PLANTS)
