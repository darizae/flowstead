"""Narrow persistence contracts consumed by application use cases.

These Protocols are structural: each method signature matches the concrete
repository in ``infrastructure.persistence`` that the application passes in
(a layered monolith wires real adapters directly, no DI container). SQL-scoped
authorization stays in the repository; every read takes the same
``subject_id``/``public`` access scope the routes receive.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from ...forecast import MODEL_VERSION, FlowObservation, ForecastBuild
from ...infrastructure.persistence.records import (
    ForecastRead,
    PlantRow,
    ReadingRow,
)


class PlantRepository(Protocol):
    def list(
        self,
        connection: Any,
        *,
        subject_id: str | None,
        public: bool,
    ) -> list[PlantRow]: ...
    def get(
        self,
        connection: Any,
        plant_id: str,
        *,
        subject_id: str | None,
        public: bool,
    ) -> PlantRow | None: ...
    def latest(
        self,
        connection: Any,
        plant_id: str,
        *,
        subject_id: str | None,
        public: bool,
    ) -> tuple[PlantRow, ReadingRow] | None: ...
    def history(
        self,
        connection: Any,
        plant_id: str,
        from_utc: datetime,
        to_utc: datetime,
        *,
        subject_id: str | None,
        public: bool,
    ) -> tuple[PlantRow, list[ReadingRow]] | None: ...


class ForecastRepository(Protocol):
    def build_in_transaction(
        self,
        connection: Any,
        plant_id: str,
        *,
        model_version: str = MODEL_VERSION,
    ) -> ForecastBuild: ...
    def read(
        self,
        connection: Any,
        plant_id: str,
        *,
        subject_id: str | None,
        public: bool,
    ) -> ForecastRead | None: ...
    def flow_observations(self, connection: Any, plant_id: str) -> list[FlowObservation]: ...
