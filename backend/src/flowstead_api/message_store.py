"""PostgreSQL transactions for outbox, commands, and bounded status reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from .forecast import MODEL_VERSION
from .messages import (
    Event,
    ForecastRequested,
    IngestCompleted,
    encode_message,
    utc_now,
)


@dataclass(frozen=True)
class ForecastJob:
    request_event_id: UUID
    correlation_id: UUID
    plant_id: str
    status: str
    requested_at: datetime
    completed_at: datetime | None
    diagnostic: str | None


def insert_outbox(connection: psycopg.Connection[Any], message: Event) -> None:
    """Insert the already-validated canonical payload in the current transaction."""
    payload = encode_message(message)  # enforce the byte cap before SQL mutation
    connection.execute(
        """
        INSERT INTO app.message_outbox
            (event_id, subject, correlation_id, plant_id, payload, occurred_at_utc)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            message.event_id,
            message.subject,
            message.correlation_id,
            message.plant_id,
            Jsonb(message.model_dump(mode="json")),
            message.occurred_at_utc,
        ),
    )
    # The serialized representation is deliberately computed even though Jsonb
    # is passed separately, so oversize messages can never enter the outbox.
    assert payload


def emit_ingest_completed(
    connection: psycopg.Connection[Any],
    *,
    batch_id: int,
    plant_ids: list[str],
    source_sha: str,
    content_sha256: str,
    reading_count: int,
) -> tuple[UUID, ...]:
    """Emit one Plant-scoped event for a newly accepted multi-Plant import."""
    correlation_id = uuid4()
    occurred_at = utc_now()
    event_ids: list[UUID] = []
    for plant_id in sorted(plant_ids):
        event = IngestCompleted(
            event_id=uuid4(),
            correlation_id=correlation_id,
            plant_id=plant_id,
            source_sha=source_sha,
            occurred_at_utc=occurred_at,
            batch_id=batch_id,
            content_sha256=content_sha256,
            reading_count=reading_count,
        )
        insert_outbox(connection, event)
        event_ids.append(event.event_id)
    return tuple(event_ids)


def enqueue_forecast(
    database_url: str,
    *,
    plant_id: str,
    subject_id: str,
) -> ForecastJob | None:
    """Authorize and atomically persist a forecast command plus its outbox event."""
    with psycopg.connect(database_url) as connection, connection.transaction():
        provenance = connection.execute(
            """
                SELECT ib.source_sha
                FROM app.operator_plant_access AS access
                JOIN app.plants AS p ON p.plant_id = access.plant_id
                JOIN app.hourly_readings AS r ON r.plant_id = p.plant_id
                JOIN app.ingest_batches AS ib ON ib.id = r.source_batch_id
                WHERE access.subject_id = %s AND p.plant_id = %s
                ORDER BY r.timestamp_utc DESC
                LIMIT 1
                """,
            (subject_id, plant_id),
        ).fetchone()
        if provenance is None:
            return None
        occurred_at = utc_now()
        event = ForecastRequested(
            event_id=uuid4(),
            correlation_id=uuid4(),
            plant_id=plant_id,
            source_sha=provenance[0],
            occurred_at_utc=occurred_at,
            requested_by=subject_id,
            model_version=MODEL_VERSION,
        )
        connection.execute(
            """
                INSERT INTO app.forecast_jobs
                    (request_event_id, correlation_id, plant_id, requested_by,
                     source_sha, status, requested_at)
                VALUES (%s, %s, %s, %s, %s, 'queued', %s)
                """,
            (
                event.event_id,
                event.correlation_id,
                event.plant_id,
                event.requested_by,
                event.source_sha,
                event.occurred_at_utc,
            ),
        )
        insert_outbox(connection, event)
        return ForecastJob(
            event.event_id,
            event.correlation_id,
            event.plant_id,
            "queued",
            event.occurred_at_utc,
            None,
            None,
        )


def read_forecast_job(
    database_url: str,
    *,
    correlation_id: UUID,
    subject_id: str,
) -> ForecastJob | None:
    # Status is requester-scoped: same-Plant operators must not observe a
    # requester they do not match. Both requested_by and the Plant grant gate.
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT j.request_event_id, j.correlation_id, j.plant_id, j.status,
                   j.requested_at, j.completed_at, j.diagnostic
            FROM app.forecast_jobs AS j
            JOIN app.operator_plant_access AS access ON access.plant_id = j.plant_id
            WHERE j.correlation_id = %s
              AND j.requested_by = %s
              AND access.subject_id = %s
            """,
            (correlation_id, subject_id, subject_id),
        ).fetchone()
    return None if row is None else ForecastJob(*row)
