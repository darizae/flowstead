"""Read-repository interfaces required by application use cases.

An explicit access context is mandatory for every Plant read; concrete
PostgreSQL adapters enforce that context in SQL, not after fetching rows.
"""

from __future__ import annotations

import builtins
from datetime import datetime
from typing import Any, Protocol

from ...access import AccessScope
from ...forecast import MODEL_VERSION, FlowObservation, ForecastBuild
from ...infrastructure.persistence.records import ForecastRead, PlantRow, ReadingRow


class PlantRepository(Protocol):
    def list(self, connection: Any, *, scope: AccessScope) -> builtins.list[PlantRow]: ...

    def get(self, connection: Any, plant_id: str, *, scope: AccessScope) -> PlantRow | None: ...

    def latest(
        self, connection: Any, plant_id: str, *, scope: AccessScope
    ) -> tuple[PlantRow, ReadingRow] | None: ...

    def history(
        self,
        connection: Any,
        plant_id: str,
        from_utc: datetime,
        to_utc: datetime,
        *,
        scope: AccessScope,
    ) -> tuple[PlantRow, builtins.list[ReadingRow]] | None: ...


class ForecastRepository(Protocol):
    def build_in_transaction(
        self,
        connection: Any,
        plant_id: str,
        *,
        model_version: str = MODEL_VERSION,
    ) -> ForecastBuild: ...

    def read(
        self, connection: Any, plant_id: str, *, scope: AccessScope
    ) -> ForecastRead | None: ...

    def flow_observations(
        self, connection: Any, plant_id: str
    ) -> builtins.list[FlowObservation]: ...
