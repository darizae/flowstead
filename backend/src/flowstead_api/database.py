"""Thin database facade delegating to application use cases.

The application layer (``application.plants``, ``application.forecasts``) owns
the read and command workflows and their transactions; this facade keeps the
historical ``flowstead_api.database.Database`` API for the routes and test
suite while delegating every operation to a real application use case.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg

from .access import PUBLIC_ACCESS, OperatorAccess
from .application.forecasts import (
    build_forecast_for_plant,
    read_forecast_status,
    request_forecast,
)
from .application.plants import (
    get_plant,
    get_plant_forecast,
    get_plant_history,
    latest_reading,
    list_accessible_plants,
)
from .forecast import MODEL_VERSION, ForecastBuild
from .infrastructure.persistence.forecast_repository import ForecastRepository
from .infrastructure.persistence.plant_repository import PlantRepository
from .infrastructure.persistence.records import (
    PUBLIC_PLANT_IDS,
    ForecastRead,
    PlantRow,
    ReadingRow,
)
from .message_store import ForecastJob

__all__ = [
    "PUBLIC_PLANT_IDS",
    "Database",
    "ForecastRead",
    "PlantRow",
    "ReadingRow",
]


class Database:
    """Adapter exposing the historical facade API over application use cases."""

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
        return request_forecast(self.resolved_url(), plant_id=plant_id, subject_id=subject_id)

    def forecast_job(self, correlation_id: UUID, *, subject_id: str) -> ForecastJob | None:
        return read_forecast_status(
            self.resolved_url(), correlation_id=correlation_id, subject_id=subject_id
        )

    def plant(self, plant_id: str, *, subject_id: str | None, public: bool) -> PlantRow | None:
        return get_plant(
            self.resolved_url(),
            self._plants,
            plant_id,
            scope=PUBLIC_ACCESS if public else OperatorAccess(subject_id or ""),
        )

    def list_plants(self, *, subject_id: str | None, public: bool) -> list[PlantRow]:
        return list_accessible_plants(
            self.resolved_url(),
            self._plants,
            scope=PUBLIC_ACCESS if public else OperatorAccess(subject_id or ""),
        )

    def latest(
        self, plant_id: str, *, subject_id: str | None, public: bool
    ) -> tuple[PlantRow, ReadingRow] | None:
        return latest_reading(
            self.resolved_url(),
            self._plants,
            plant_id,
            scope=PUBLIC_ACCESS if public else OperatorAccess(subject_id or ""),
        )

    def history(
        self,
        plant_id: str,
        from_utc: datetime,
        to_utc: datetime,
        *,
        subject_id: str | None,
        public: bool,
    ) -> tuple[PlantRow, list[ReadingRow]] | None:
        return get_plant_history(
            self.resolved_url(),
            self._plants,
            plant_id,
            from_utc,
            to_utc,
            scope=PUBLIC_ACCESS if public else OperatorAccess(subject_id or ""),
        )

    def build_forecast(
        self,
        plant_id: str,
        *,
        model_version: str = MODEL_VERSION,
    ) -> ForecastBuild:
        """Build and atomically persist the latest forecast for one Plant."""
        return build_forecast_for_plant(
            self.resolved_url(), self._forecasts, plant_id, model_version=model_version
        )

    def forecast(
        self,
        plant_id: str,
        *,
        subject_id: str | None,
        public: bool,
    ) -> ForecastRead | None:
        """Read a stored forecast or an explicit unavailable result."""
        return get_plant_forecast(
            self.resolved_url(),
            self._plants,
            self._forecasts,
            plant_id,
            scope=PUBLIC_ACCESS if public else OperatorAccess(subject_id or ""),
        )

    def flow_observations(self, plant_id: str) -> list[Any]:
        """Return the source channel for a local chronological receipt."""
        with self.connect() as connection:
            return self._forecasts.flow_observations(connection, plant_id)
