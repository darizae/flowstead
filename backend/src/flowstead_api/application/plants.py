"""Read application use cases: accessible Plants, latest, history, forecast.

Each use case opens one UnitOfWork, delegates the SQL-scoped read to the
injected repository, and returns the same projection records the HTTP mappers
already consume. Authorization is enforced by the repository SQL, never here.
"""

from __future__ import annotations

from datetime import datetime

from ..forecast import MODEL_VERSION, PHYSICAL_BOUND_RULE, ForecastBuild
from ..infrastructure.persistence.records import ForecastRead, PlantRow, ReadingRow
from ..infrastructure.persistence.unit_of_work import UnitOfWork
from .ports.repositories import ForecastRepository, PlantRepository


def list_accessible_plants(
    database_url: str,
    plants: PlantRepository,
    *,
    subject_id: str | None,
    public: bool,
) -> list[PlantRow]:
    with UnitOfWork(database_url) as uow:
        return plants.list(uow.connection, subject_id=subject_id, public=public)


def get_plant(
    database_url: str,
    plants: PlantRepository,
    plant_id: str,
    *,
    subject_id: str | None,
    public: bool,
) -> PlantRow | None:
    with UnitOfWork(database_url) as uow:
        return plants.get(uow.connection, plant_id, subject_id=subject_id, public=public)


def latest_reading(
    database_url: str,
    plants: PlantRepository,
    plant_id: str,
    *,
    subject_id: str | None,
    public: bool,
) -> tuple[PlantRow, ReadingRow] | None:
    with UnitOfWork(database_url) as uow:
        return plants.latest(uow.connection, plant_id, subject_id=subject_id, public=public)


def get_plant_history(
    database_url: str,
    plants: PlantRepository,
    plant_id: str,
    from_utc: datetime,
    to_utc: datetime,
    *,
    subject_id: str | None,
    public: bool,
) -> tuple[PlantRow, list[ReadingRow]] | None:
    with UnitOfWork(database_url) as uow:
        return plants.history(
            uow.connection,
            plant_id,
            from_utc,
            to_utc,
            subject_id=subject_id,
            public=public,
        )


def get_plant_forecast(
    database_url: str,
    plants: PlantRepository,
    forecasts: ForecastRepository,
    plant_id: str,
    *,
    subject_id: str | None,
    public: bool,
) -> ForecastRead | None:
    """Read a stored forecast, or an explicit unavailable result for a present Plant."""
    with UnitOfWork(database_url) as uow:
        forecast = forecasts.read(uow.connection, plant_id, subject_id=subject_id, public=public)
        if forecast is not None:
            return forecast
        latest = plants.latest(uow.connection, plant_id, subject_id=subject_id, public=public)
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
