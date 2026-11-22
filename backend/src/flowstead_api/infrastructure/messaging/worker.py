"""Durable forecast worker: request processing, SQL writes, retry and failures.

This is the persistence/application half of the messaging boundary. The NATS
transport (connection, topology, outbox dispatch) lives in ``transport``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

import psycopg
from nats.aio.msg import Msg
from nats.errors import TimeoutError as NatsTimeoutError

from ...application.forecasts import ProcessResult, process_forecast_request
from ...message_store import insert_outbox
from ...messages import (
    ForecastFailed,
    ForecastRequested,
    MessageError,
    decode_message,
    utc_now,
)
from ..persistence.forecast_repository import ForecastRepository
from .transport import (
    FORECAST_DURABLE,
    FORECAST_REQUESTED,
    MAX_DELIVERIES,
    RETRY_DELAYS_SECONDS,
    STREAM_NAME,
    _diagnostic,
)

# ``process_forecast_request`` now lives in the application layer and owns the
# transactional workflow; this module exports it through the messaging boundary.

_FORECASTS = ForecastRepository()


def record_failure(
    database_url: str,
    *,
    subject: str,
    payload: bytes,
    delivery_count: int,
    stream_sequence: int | None,
    diagnostic: str,
    terminal: bool,
) -> None:
    event_id = _untrusted_event_id(payload)
    digest = hashlib.sha256(payload).hexdigest()
    with psycopg.connect(database_url) as connection, connection.transaction():
        connection.execute(
            """
            INSERT INTO app.message_failures
                (stream_sequence, subject, event_id, payload_sha256,
                 delivery_count, diagnostic, terminal)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stream_sequence, payload_sha256) DO UPDATE
            SET delivery_count = GREATEST(
                    app.message_failures.delivery_count, EXCLUDED.delivery_count
                ),
                diagnostic = EXCLUDED.diagnostic,
                terminal = app.message_failures.terminal OR EXCLUDED.terminal,
                recorded_at = now()
            """,
            (
                stream_sequence,
                subject[:256],
                event_id,
                digest,
                min(max(delivery_count, 1), 100),
                diagnostic[:512],
                terminal,
            ),
        )


def record_terminal_request_failure(
    database_url: str,
    request: ForecastRequested,
    *,
    delivery_count: int,
    diagnostic: str,
) -> None:
    """Make retry exhaustion a visible terminal job and inbox receipt."""
    occurred_at = utc_now()
    result_event = ForecastFailed(
        event_id=uuid4(),
        correlation_id=request.correlation_id,
        plant_id=request.plant_id,
        source_sha=request.source_sha,
        occurred_at_utc=occurred_at,
        request_event_id=request.event_id,
        error_code="max_deliveries_exceeded",
        diagnostic=diagnostic[:512],
    )
    with psycopg.connect(database_url) as connection, connection.transaction():
        job = connection.execute(
            """
            SELECT 1 FROM app.forecast_jobs
            WHERE request_event_id = %s AND correlation_id = %s
              AND plant_id = %s AND requested_by = %s AND source_sha = %s
            FOR UPDATE
            """,
            (
                request.event_id,
                request.correlation_id,
                request.plant_id,
                request.requested_by,
                request.source_sha,
            ),
        ).fetchone()
        if job is None:
            return
        existing = connection.execute(
            "SELECT 1 FROM app.message_inbox WHERE event_id = %s",
            (request.event_id,),
        ).fetchone()
        if existing is not None:
            return
        insert_outbox(connection, result_event)
        connection.execute(
            """
            UPDATE app.forecast_jobs
            SET status = 'failed', completed_at = %s, result_event_id = %s,
                diagnostic = %s
            WHERE request_event_id = %s
            """,
            (occurred_at, result_event.event_id, _public_diagnostic(diagnostic), request.event_id),
        )
        connection.execute(
            """
            INSERT INTO app.message_inbox
                (event_id, subject, correlation_id, plant_id, delivery_count,
                 status, diagnostic)
            VALUES (%s, %s, %s, %s, %s, 'failed', %s)
            """,
            (
                request.event_id,
                request.subject,
                request.correlation_id,
                request.plant_id,
                min(delivery_count, 100),
                diagnostic[:512],
            ),
        )


async def consume_one(database_url: str, message: Msg) -> ProcessResult:
    metadata = message.metadata
    delivery_count = metadata.num_delivered if metadata is not None else 1
    stream_sequence = metadata.sequence.stream if metadata is not None else None
    try:
        decoded = decode_message(message.subject, message.data)
        if not isinstance(decoded, ForecastRequested):
            raise MessageError("forecast consumer received the wrong message action")
    except MessageError as error:
        record_failure(
            database_url,
            subject=message.subject,
            payload=message.data,
            delivery_count=delivery_count,
            stream_sequence=stream_sequence,
            diagnostic=str(error),
            terminal=True,
        )
        await message.term()
        return ProcessResult("dead_lettered", str(error))

    try:
        result = process_forecast_request(
            database_url, decoded, _FORECASTS, delivery_count=delivery_count
        )
        if result.state == "rejected":
            record_failure(
                database_url,
                subject=message.subject,
                payload=message.data,
                delivery_count=delivery_count,
                stream_sequence=stream_sequence,
                diagnostic=result.diagnostic or "unauthorized request",
                terminal=True,
            )
            await message.term()
            return result
    except (psycopg.Error, RuntimeError, ValueError, AssertionError) as error:
        terminal = delivery_count >= MAX_DELIVERIES
        if terminal:
            record_terminal_request_failure(
                database_url,
                decoded,
                delivery_count=delivery_count,
                diagnostic=_diagnostic(error),
            )
        record_failure(
            database_url,
            subject=message.subject,
            payload=message.data,
            delivery_count=delivery_count,
            stream_sequence=stream_sequence,
            diagnostic=_diagnostic(error),
            terminal=terminal,
        )
        if terminal:
            await message.term()
            return ProcessResult("dead_lettered", _diagnostic(error))
        await message.nak(delay=RETRY_DELAYS_SECONDS[min(delivery_count - 1, 4)])
        return ProcessResult("retrying", _diagnostic(error))

    # The database transaction above has committed before this acknowledgement.
    await message.ack()
    return result


async def worker_once(database_url: str, js: Any, *, timeout: float = 2.0) -> int:
    subscription = await js.pull_subscribe(
        FORECAST_REQUESTED,
        durable=FORECAST_DURABLE,
        stream=STREAM_NAME,
    )
    try:
        messages = await subscription.fetch(1, timeout=timeout)
    except NatsTimeoutError:
        return 0
    await consume_one(database_url, messages[0])
    return 1


def _public_diagnostic(raw: str) -> str:
    """Keep a terminal-failure marker for the read API, never raw exception text.

    The full diagnostic (which may embed DSN, host, schema or path detail) is
    stored for operations in message_failures; only the exception class is safe
    to surface through forecast_jobs.diagnostic to the requesting operator.
    """
    return (raw.split(":", 1)[0] or "failure")[:512]


def _untrusted_event_id(payload: bytes) -> UUID | None:
    try:
        value = json.loads(payload).get("event_id")
        return UUID(value) if isinstance(value, str) else None
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        return None


__all__ = [
    "ProcessResult",
    "consume_one",
    "process_forecast_request",
    "record_failure",
    "record_terminal_request_failure",
    "worker_once",
]
