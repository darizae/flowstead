"""Small, parameterized PostgreSQL access layer for bounded API reads."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import psycopg

from backend.importer import APPROVED_PLANT_IDS

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


class Database:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection[Any]]:
        database_url = self.database_url or os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is required for API reads")
        with psycopg.connect(database_url) as connection:
            yield connection

    def list_plants(self, *, subject_id: str | None, public: bool) -> list[PlantRow]:
        if public:
            query = """
                SELECT p.plant_id, p.name, p.city, p.state_code, p.timezone,
                       p.latitude, p.longitude
                FROM app.plants AS p
                WHERE p.public_demo = true
                  AND p.plant_id = ANY(%s)
                ORDER BY p.plant_id
                LIMIT 5
            """
            params: tuple[Any, ...] = (list(PUBLIC_PLANT_IDS),)
        else:
            query = """
                SELECT p.plant_id, p.name, p.city, p.state_code, p.timezone,
                       p.latitude, p.longitude
                FROM app.plants AS p
                JOIN app.operator_plant_access AS access
                  ON access.plant_id = p.plant_id
                WHERE access.subject_id = %s
                ORDER BY p.plant_id
                LIMIT 5
            """
            params = (subject_id,)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_plant_row(row) for row in rows]

    def latest(self, plant_id: str, *, subject_id: str | None, public: bool) -> tuple[PlantRow, ReadingRow] | None:
        access_clause, params = _access_clause(plant_id, subject_id=subject_id, public=public)
        query = f"""
            SELECT p.plant_id, p.name, p.city, p.state_code, p.timezone,
                   p.latitude, p.longitude,
                   r.timestamp_utc, r.influent_flow, r.influent_flow_quality,
                   r.rainfall, r.rainfall_quality,
                   r.dissolved_oxygen, r.dissolved_oxygen_quality,
                   r.effluent_ph, r.effluent_ph_quality
            FROM app.plants AS p
            JOIN app.hourly_readings AS r ON r.plant_id = p.plant_id
            {access_clause}
            ORDER BY r.timestamp_utc DESC
            LIMIT 1
        """
        with self.connect() as connection:
            row = connection.execute(query, params).fetchone()
        if row is None:
            return None
        return _plant_row(row[:7]), _reading_row(row[7:], row[0])

    def history(
        self,
        plant_id: str,
        from_utc: datetime,
        to_utc: datetime,
        *,
        subject_id: str | None,
        public: bool,
    ) -> tuple[PlantRow, list[ReadingRow]] | None:
        access_clause, params = _access_clause(plant_id, subject_id=subject_id, public=public)
        query = f"""
            SELECT p.plant_id, p.name, p.city, p.state_code, p.timezone,
                   p.latitude, p.longitude,
                   r.timestamp_utc, r.influent_flow, r.influent_flow_quality,
                   r.rainfall, r.rainfall_quality,
                   r.dissolved_oxygen, r.dissolved_oxygen_quality,
                   r.effluent_ph, r.effluent_ph_quality
            FROM app.plants AS p
            LEFT JOIN app.hourly_readings AS r
              ON r.plant_id = p.plant_id
             AND r.timestamp_utc >= %s
             AND r.timestamp_utc < %s
            {access_clause}
            ORDER BY r.timestamp_utc ASC
            LIMIT 168
        """
        with self.connect() as connection:
            rows = connection.execute(query, (from_utc, to_utc, *params)).fetchall()
        if not rows:
            return None
        plant = _plant_row(rows[0][:7])
        if rows[0][7] is None:
            return plant, []
        return plant, [_reading_row(row[7:], row[0]) for row in rows]


def _access_clause(plant_id: str, *, subject_id: str | None, public: bool) -> tuple[str, tuple[Any, ...]]:
    if public:
        return "WHERE p.plant_id = %s AND p.public_demo = true AND p.plant_id = ANY(%s)", (
            plant_id,
            list(PUBLIC_PLANT_IDS),
        )
    return (
        "JOIN app.operator_plant_access AS access ON access.plant_id = p.plant_id "
        "WHERE p.plant_id = %s AND access.subject_id = %s",
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
