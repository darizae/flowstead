"""Forecast build (transaction-scoped) and read repository."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from ...access import AccessScope
from ...forecast import (
    MODEL_VERSION,
    PHYSICAL_BOUND_RULE,
    FlowObservation,
    ForecastBuild,
    forecast_for_issuance,
)
from .records import (
    ForecastRead,
    _access_clause,
    _plant_row,
    _stored_forecast,
    _stored_point,
)


class ForecastRepository:
    """Persist deterministic forecasts and read stored/fallback results."""

    def build_in_transaction(
        self,
        connection: Any,
        plant_id: str,
        *,
        model_version: str = MODEL_VERSION,
    ) -> ForecastBuild:
        """Build and persist a forecast inside the caller-owned transaction."""
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

    def read(
        self,
        connection: Any,
        plant_id: str,
        *,
        scope: AccessScope,
    ) -> ForecastRead | None:
        """Return a stored twelve-row forecast, or None to trigger the fallback path."""
        access_clause, params = _access_clause(plant_id, scope=scope)
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
        return None

    def flow_observations(self, connection: Any, plant_id: str) -> list[FlowObservation]:
        """Return the source channel for a local chronological receipt."""
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
