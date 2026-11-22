"""Narrow persistence contracts for application workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ...domain.models import Plant, TelemetryReading
from ...forecast import FlowObservation, ForecastBuild
from ...message_store import ForecastJob
from .access import AccessScope


class PlantRepository(Protocol):
    def list(self, scope: AccessScope) -> list[Plant]: ...
    def get(self, plant_id: str, scope: AccessScope) -> Plant | None: ...
    def latest(
        self, plant_id: str, scope: AccessScope
    ) -> tuple[Plant, TelemetryReading] | None: ...
    def history(
        self, plant_id: str, from_utc: datetime, to_utc: datetime, scope: AccessScope
    ) -> tuple[Plant, list[TelemetryReading]] | None: ...


class TelemetryRepository(Protocol):
    def flow_observations(self, plant_id: str) -> list[FlowObservation]: ...


class ForecastRepository(Protocol):
    def build(self, plant_id: str, *, model_version: str) -> ForecastBuild: ...
    def build_in_transaction(
        self, connection: object, plant_id: str, *, model_version: str
    ) -> ForecastBuild: ...
    def get(self, plant_id: str, scope: AccessScope) -> tuple[Plant, ForecastBuild] | None: ...


class JobRepository(Protocol):
    def enqueue(self, plant_id: str, *, subject_id: str) -> ForecastJob | None: ...
    def read(self, correlation_id: UUID, *, subject_id: str) -> ForecastJob | None: ...
