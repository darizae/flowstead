"""Plant read repository with SQL-enforced public/operator scoping."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...access import AccessScope, PublicAccess
from .records import (
    PUBLIC_PLANT_IDS,
    PlantRow,
    ReadingRow,
    _access_clause,
    _plant_row,
    _reading_row,
)


class PlantRepository:
    """Read Plants through the same public/private access predicates as the API.

    Authorization stays in SQL: the caller supplies an explicit access scope and
    the repository never widens it.
    """

    def list(self, connection: Any, *, scope: AccessScope) -> list[PlantRow]:
        if isinstance(scope, PublicAccess):
            query = """
                SELECT p.plant_id, p.name, p.city, p.state_code, p.timezone,
                       p.latitude, p.longitude
                FROM app.plants AS p
                WHERE p.public_demo = true AND p.plant_id = ANY(%s)
                ORDER BY p.plant_id
                LIMIT 5
            """
            params: tuple[Any, ...] = (list(PUBLIC_PLANT_IDS),)
        else:
            query = """
                SELECT p.plant_id, p.name, p.city, p.state_code, p.timezone,
                       p.latitude, p.longitude
                FROM app.plants AS p
                JOIN app.operator_plant_access AS access ON access.plant_id = p.plant_id
                WHERE access.subject_id = %s
                ORDER BY p.plant_id
                LIMIT 5
            """
            params = (scope.subject_id,)
        rows = connection.execute(query, params).fetchall()
        return [_plant_row(row) for row in rows]

    def get(self, connection: Any, plant_id: str, *, scope: AccessScope) -> PlantRow | None:
        access_clause, params = _access_clause(plant_id, scope=scope)
        query = f"""
            SELECT p.plant_id, p.name, p.city, p.state_code, p.timezone,
                   p.latitude, p.longitude
            FROM app.plants AS p
            {access_clause}
            LIMIT 1
        """
        row = connection.execute(query, params).fetchone()
        return None if row is None else _plant_row(row)

    def latest(
        self, connection: Any, plant_id: str, *, scope: AccessScope
    ) -> tuple[PlantRow, ReadingRow] | None:
        access_clause, params = _access_clause(plant_id, scope=scope)
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
        row = connection.execute(query, params).fetchone()
        if row is None:
            return None
        return _plant_row(row[:7]), _reading_row(row[7:], row[0])

    def history(
        self,
        connection: Any,
        plant_id: str,
        from_utc: datetime,
        to_utc: datetime,
        *,
        scope: AccessScope,
    ) -> tuple[PlantRow, list[ReadingRow]] | None:
        access_clause, params = _access_clause(plant_id, scope=scope)
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
        rows = connection.execute(query, (from_utc, to_utc, *params)).fetchall()
        if not rows:
            return None
        plant = _plant_row(rows[0][:7])
        if rows[0][7] is None:
            return plant, []
        return plant, [_reading_row(row[7:], row[0]) for row in rows]
