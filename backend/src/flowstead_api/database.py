"""Thin database facade coordinating persistence repositories.

SQL lives in ``infrastructure.persistence`` repositories; this facade keeps the
historical ``flowstead_api.database.Database`` API for the routes, worker, and
test suite while delegating reads and forecast builds to focused repositories.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg

from .forecast import MODEL_VERSION, PHYSICAL_BOUND_RULE, ForecastBuild
from .infrastructure.persistence.forecast_repository import ForecastRepository
from .infrastructure.persistence.plant_repository import PlantRepository
from .infrastructure.persistence.records import (
    PUBLIC_PLANT_IDS,
    ForecastRead,
    PlantRow,
    ReadingRow,
)
from .message_store import ForecastJob, enqueue_forecast, read_forecast_job

__all__ = [
    "PUBLIC_PLANT_IDS",
    "Database",
    "ForecastRead",
    "PlantRow",
    "ReadingRow",
]


class Database:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url
        self._plants = PlantRepository()
        self._forecasts = ForecastRepository()

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

    def plant(self, plant_id: str, *, subject_id: str | None, public: bool) -> PlantRow | None:
        """Read one Plant through the same public/private access predicate."""
        with self.connect() as connection:
            return self._plants.get(connection, plant_id, subject_id=subject_id, public=public)

    def list_plants(self, *, subject_id: str | None, public: bool) -> list[PlantRow]:
        with self.connect() as connection:
            return self._plants.list(connection, subject_id=subject_id, public=public)

    def latest(
        self, plant_id: str, *, subject_id: str | None, public: bool
    ) -> tuple[PlantRow, ReadingRow] | None:
        with self.connect() as connection:
            return self._plants.latest(connection, plant_id, subject_id=subject_id, public=public)

    def history(
        self,
        plant_id: str,
        from_utc: datetime,
        to_utc: datetime,
        *,
        subject_id: str | None,
        public: bool,
    ) -> tuple[PlantRow, list[ReadingRow]] | None:
        with self.connect() as connection:
            return self._plants.history(
                connection, plant_id, from_utc, to_utc, subject_id=subject_id, public=public
            )

    def build_forecast(
        self,
        plant_id: str,
        *,
        model_version: str = MODEL_VERSION,
    ) -> ForecastBuild:
        """Build and atomically persist the latest forecast for one Plant."""
        with self.connect() as connection, connection.transaction():
            return self._forecasts.build_in_transaction(
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
        return self._forecasts.build_in_transaction(
            connection, plant_id, model_version=model_version
        )

    def forecast(
        self,
        plant_id: str,
        *,
        subject_id: str | None,
        public: bool,
    ) -> ForecastRead | None:
        """Read a stored forecast or an explicit unavailable result."""
        with self.connect() as connection:
            forecast = self._forecasts.read(
                connection, plant_id, subject_id=subject_id, public=public
            )
            if forecast is not None:
                return forecast
            latest = self._plants.latest(connection, plant_id, subject_id=subject_id, public=public)
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

    def flow_observations(self, plant_id: str) -> list[Any]:
        """Return the source channel for a local chronological receipt."""
        with self.connect() as connection:
            return self._forecasts.flow_observations(connection, plant_id)
