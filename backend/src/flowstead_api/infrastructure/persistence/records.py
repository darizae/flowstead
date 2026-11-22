"""Persistence mapping records and shared row helpers.

These are database row projections (not domain types). Domain values live in
``domain.models``; transport schemas live in ``interfaces.http.schemas``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from ...domain.m1 import APPROVED_PLANT_IDS
from ...forecast import PHYSICAL_BOUND_RULE, ForecastBuild

PUBLIC_PLANT_IDS = tuple(sorted(APPROVED_PLANT_IDS))


@dataclass(frozen=True)
class PlantRow:
    plant_id: str
    name: str
    city: str
    state_code: str
    timezone: str
    latitude: Decimal
    longitude: Decimal


@dataclass(frozen=True)
class ReadingRow:
    plant_id: str
    timestamp_utc: datetime
    values: tuple[Decimal | None, ...]
    qualities: tuple[str, ...]


@dataclass(frozen=True)
class ForecastRead:
    plant: PlantRow
    build: ForecastBuild


def _access_clause(
    plant_id: str, *, subject_id: str | None, public: bool
) -> tuple[str, tuple[Any, ...]]:
    if public:
        return "WHERE p.plant_id = %s AND p.public_demo = true AND p.plant_id = ANY(%s)", (
            plant_id,
            list(PUBLIC_PLANT_IDS),
        )
    return (
        (
            "JOIN app.operator_plant_access AS access ON access.plant_id = p.plant_id "
            "WHERE p.plant_id = %s AND access.subject_id = %s"
        ),
        (plant_id, subject_id),
    )


def _plant_row(row: tuple[Any, ...]) -> PlantRow:
    return PlantRow(
        plant_id=row[0],
        name=row[1],
        city=row[2],
        state_code=row[3],
        timezone=row[4],
        latitude=row[5],
        longitude=row[6],
    )


def _reading_row(row: tuple[Any, ...], plant_id: str) -> ReadingRow:
    return ReadingRow(
        plant_id=plant_id,
        timestamp_utc=row[0],
        values=(row[1], row[3], row[5], row[7]),
        qualities=(row[2], row[4], row[6], row[8]),
    )


def _stored_point(hour_number: int, target_time: datetime, predicted_flow: Decimal) -> Any:
    from ...forecast import ForecastPoint

    return ForecastPoint(
        hour_number=hour_number,
        target_time_utc=target_time,
        predicted_flow_gal_h=predicted_flow,
        source="stored",
    )


def _stored_forecast(
    issuance: tuple[Any, ...],
    rows: list[tuple[Any, ...]],
) -> ForecastBuild:
    return ForecastBuild(
        issued_at_utc=issuance[1],
        model_version=issuance[2],
        source_revision=issuance[3],
        physical_bound_rule=issuance[4] or PHYSICAL_BOUND_RULE,
        points=tuple(_stored_point(row[0], row[1], row[2]) for row in rows),
    )
