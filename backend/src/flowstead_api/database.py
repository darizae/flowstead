"""Small, parameterized PostgreSQL access layer for bounded API reads."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg
from backend.importer import APPROVED_PLANT_IDS

from .forecast import (
    MODEL_VERSION,
    PHYSICAL_BOUND_RULE,
    FlowObservation,
    ForecastBuild,
    forecast_for_issuance,
)
from .message_store import ForecastJob, enqueue_forecast, read_forecast_job

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


class Database:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url

    @property
    def public_plant_ids(self) -> tuple[str, ...]:
        return PUBLIC_PLANT_IDS

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(self.resolved_url()) as connection:
            yield connection

    def resolved_url(self) -> str:
        database_url = self.database_url or os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is required for API access")
        return database_url

    def enqueue_forecast(self, plant_id: str, *, subject_id: str) -> ForecastJob | None:
        return enqueue_forecast(self.resolved_url(), plant_id=plant_id, subject_id=subject_id)

    def forecast_job(self, correlation_id: UUID, *, subject_id: str) -> ForecastJob | None:
        return read_forecast_job(
            self.resolved_url(), correlation_id=correlation_id, subject_id=subject_id
        )

    def plant(
        self, plant_id: str, *, subject_id: str | None, public: bool
    ) -> PlantRow | None:
        """Read one Plant through the same public/private access predicate."""
        access_clause, params = _access_clause(plant_id, subject_id=subject_id, public=public)
        query = f"""
            SELECT p.plant_id, p.name, p.city, p.state_code, p.timezone,
                   p.latitude, p.longitude
            FROM app.plants AS p
            {access_clause}
            LIMIT 1
        """
        with self.connect() as connection:
            row = connection.execute(query, params).fetchone()
        return None if row is None else _plant_row(row)

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

    def latest(
        self, plant_id: str, *, subject_id: str | None, public: bool
    ) -> tuple[PlantRow, ReadingRow] | None:
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

    def build_forecast(
        self,
        plant_id: str,
        *,
        model_version: str = MODEL_VERSION,
    ) -> ForecastBuild:
        """Build and atomically persist the latest forecast for one Plant."""
        with self.connect() as connection, connection.transaction():
            return self.build_forecast_in_transaction(
                connection, plant_id, model_version=model_version
            )

    def build_forecast_in_transaction(
        self,
        connection: psycopg.Connection[Any],
        plant_id: str,
        *,
        model_version: str = MODEL_VERSION,
    ) -> ForecastBuild:
        """Persist a forecast inside a caller-owned transaction."""
        latest = connection.execute(
            """
                    SELECT max(r.timestamp_utc)
                    FROM app.plants AS p
                    JOIN app.hourly_readings AS r ON r.plant_id = p.plant_id
                    WHERE p.plant_id = %s
                    """,
            (plant_id,),
        ).fetchone()[0]
        if latest is None:
            return ForecastBuild(
                issued_at_utc=None,
                model_version=model_version,
                source_revision=None,
                physical_bound_rule=PHYSICAL_BOUND_RULE,
                points=(),
                unavailable_reason="no_observations",
            )
        input_rows = connection.execute(
            """
                    SELECT r.timestamp_utc, r.influent_flow, r.influent_flow_quality,
                           ib.content_sha256
                    FROM app.hourly_readings AS r
                    LEFT JOIN app.ingest_batches AS ib ON ib.id = r.source_batch_id
                    WHERE r.plant_id = %s
                      AND r.timestamp_utc >= %s
                      AND r.timestamp_utc <= %s
                    ORDER BY r.timestamp_utc
                    """,
            (plant_id, latest - timedelta(hours=24), latest),
        ).fetchall()
        observations = [
            FlowObservation(timestamp, value, quality)
            for timestamp, value, quality, _source_revision in input_rows
        ]
        revisions = sorted(
            {
                source_revision
                for _timestamp, _value, _quality, source_revision in input_rows
                if source_revision
            }
        )
        source_revision = ",".join(revisions) or None
        build = forecast_for_issuance(
            observations,
            latest,
            source_revision=source_revision,
            model_version=model_version,
        )
        if not build.available:
            return build

        existing = connection.execute(
            """
                    SELECT id, issued_at, model_version, source_revision,
                           physical_bound_rule
                    FROM app.forecast_issuances
                    WHERE plant_id = %s AND issued_at = %s AND model_version = %s
                    """,
            (plant_id, build.issued_at_utc, model_version),
        ).fetchone()
        if existing is not None:
            stored = connection.execute(
                """
                        SELECT hour_number, target_time, predicted_flow
                        FROM app.forecast_hours
                        WHERE issuance_id = %s
                        ORDER BY hour_number
                        """,
                (existing[0],),
            ).fetchall()
            if len(stored) != 12:
                raise RuntimeError("stored forecast is not exactly twelve rows")
            return _stored_forecast(existing, stored)

        inserted = connection.execute(
            """
                    INSERT INTO app.forecast_issuances
                        (plant_id, issued_at, model_version, source_revision,
                         physical_bound_rule)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (plant_id, issued_at) DO NOTHING
                    RETURNING id
                    """,
            (
                plant_id,
                build.issued_at_utc,
                model_version,
                build.source_revision,
                build.physical_bound_rule,
            ),
        ).fetchone()
        if inserted is None:
            existing = connection.execute(
                """
                        SELECT id, issued_at, model_version, source_revision,
                               physical_bound_rule
                        FROM app.forecast_issuances
                        WHERE plant_id = %s AND issued_at = %s
                        """,
                (plant_id, build.issued_at_utc),
            ).fetchone()
            if existing is None:
                raise RuntimeError("forecast issuance disappeared during idempotent insert")
            stored = connection.execute(
                """
                        SELECT hour_number, target_time, predicted_flow
                        FROM app.forecast_hours
                        WHERE issuance_id = %s
                        ORDER BY hour_number
                        """,
                (existing[0],),
            ).fetchall()
            if len(stored) != 12:
                raise RuntimeError("stored forecast is not exactly twelve rows")
            return _stored_forecast(existing, stored)

        with connection.cursor() as cursor:
            cursor.executemany(
                """
                        INSERT INTO app.forecast_hours
                            (issuance_id, target_time, predicted_flow, hour_number)
                        VALUES (%s, %s, %s, %s)
                        """,
                [
                    (
                        inserted[0],
                        point.target_time_utc,
                        point.predicted_flow_gal_h,
                        point.hour_number,
                    )
                    for point in build.points
                ],
            )
        count = connection.execute(
            "SELECT count(*) FROM app.forecast_hours WHERE issuance_id = %s",
            (inserted[0],),
        ).fetchone()[0]
        if count != 12:
            raise RuntimeError("forecast transaction did not create exactly twelve rows")
        return build

    def forecast(
        self,
        plant_id: str,
        *,
        subject_id: str | None,
        public: bool,
    ) -> ForecastRead | None:
        """Read a stored forecast or an explicit unavailable result."""
        access_clause, params = _access_clause(plant_id, subject_id=subject_id, public=public)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT p.plant_id, p.name, p.city, p.state_code, p.timezone,
                       p.latitude, p.longitude,
                       i.id, i.issued_at, i.model_version, i.source_revision,
                       i.physical_bound_rule,
                       h.hour_number, h.target_time, h.predicted_flow
                FROM app.plants AS p
                JOIN app.forecast_issuances AS i ON i.plant_id = p.plant_id
                JOIN app.forecast_hours AS h ON h.issuance_id = i.id
                {access_clause}
                ORDER BY i.issued_at DESC, h.hour_number
                LIMIT 12
                """,
                params,
            ).fetchall()
        if rows and len({row[7] for row in rows}) == 1 and len(rows) == 12:
            first = rows[0]
            build = ForecastBuild(
                issued_at_utc=first[8],
                model_version=first[9],
                source_revision=first[10],
                physical_bound_rule=first[11] or PHYSICAL_BOUND_RULE,
                points=tuple(_stored_point(row[12], row[13], row[14]) for row in rows),
            )
            return ForecastRead(_plant_row(first[:7]), build)

        latest = self.latest(plant_id, subject_id=subject_id, public=public)
        if latest is None:
            return None
        plant, latest_reading = latest
        return ForecastRead(
            plant,
            ForecastBuild(
                issued_at_utc=latest_reading.timestamp_utc,
                model_version=MODEL_VERSION,
                source_revision=None,
                physical_bound_rule=PHYSICAL_BOUND_RULE,
                points=(),
                unavailable_reason="not_issued",
            ),
        )

    def flow_observations(self, plant_id: str) -> list[FlowObservation]:
        """Return the source channel for a local chronological receipt."""
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT timestamp_utc, influent_flow, influent_flow_quality
                FROM app.hourly_readings
                WHERE plant_id = %s
                ORDER BY timestamp_utc
                """,
                (plant_id,),
            ).fetchall()
        return [FlowObservation(timestamp, value, quality) for timestamp, value, quality in rows]


def _stored_point(hour_number: int, target_time: datetime, predicted_flow: Decimal) -> Any:
    from .forecast import ForecastPoint

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
