"""Bounded PostgreSQL outbox dispatcher and durable JetStream forecast worker."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import nats
import psycopg
from nats.aio.msg import Msg
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js.api import (
    AckPolicy,
    ConsumerConfig,
    DeliverPolicy,
    RetentionPolicy,
    StorageType,
    StreamConfig,
)
from nats.js.errors import NotFoundError

from .database import Database
from .message_store import insert_outbox
from .messages import (
    FORECAST_REQUESTED,
    SUBJECTS,
    ForecastCompleted,
    ForecastFailed,
    ForecastRequested,
    MessageError,
    decode_message,
    utc_now,
)

STREAM_NAME = "FLOWSTEAD_V1"
FORECAST_DURABLE = "flowstead-forecast-v1"
ACK_WAIT_SECONDS = 30.0
MAX_DELIVERIES = 5
MAX_EVENT_AGE_SECONDS = 7 * 24 * 60 * 60
PUBLISH_TIMEOUT_SECONDS = 5.0
FETCH_TIMEOUT_SECONDS = 2.0
DISPATCH_BATCH_SIZE = 25
RETRY_DELAYS_SECONDS = (0.25, 0.5, 1.0, 1.0, 1.0)


@dataclass(frozen=True)
class ProcessResult:
    state: str
    diagnostic: str | None = None


async def connect(nats_url: str) -> Any:
    return await nats.connect(
        servers=[nats_url],
        connect_timeout=PUBLISH_TIMEOUT_SECONDS,
        reconnect_time_wait=1,
        max_reconnect_attempts=3,
    )


async def ensure_topology(js: Any) -> None:
    stream = StreamConfig(
        name=STREAM_NAME,
        description="Flowstead v1 application events",
        subjects=list(SUBJECTS),
        retention=RetentionPolicy.LIMITS,
        storage=StorageType.FILE,
        max_age=MAX_EVENT_AGE_SECONDS,
        max_msgs=100_000,
        max_bytes=256 * 1024 * 1024,
        max_msg_size=16_384,
        duplicate_window=120.0,
        num_replicas=1,
        deny_delete=True,
    )
    try:
        await js.stream_info(STREAM_NAME)
    except NotFoundError:
        await js.add_stream(config=stream)
    else:
        await js.update_stream(config=stream)

    consumer = ConsumerConfig(
        durable_name=FORECAST_DURABLE,
        description="Flowstead deterministic forecast request worker",
        deliver_policy=DeliverPolicy.ALL,
        ack_policy=AckPolicy.EXPLICIT,
        ack_wait=ACK_WAIT_SECONDS,
        max_deliver=MAX_DELIVERIES,
        backoff=list(RETRY_DELAYS_SECONDS),
        filter_subject=FORECAST_REQUESTED,
        max_ack_pending=1,
    )
    try:
        await js.consumer_info(STREAM_NAME, FORECAST_DURABLE)
    except NotFoundError:
        await js.add_consumer(STREAM_NAME, config=consumer)


def _database_url(explicit: str | None = None) -> str:
    value = explicit or os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required for messaging")
    return value


def _nats_url(explicit: str | None = None) -> str:
    return explicit or os.environ.get("NATS_URL", "nats://127.0.0.1:42229")


async def dispatch_once(database_url: str, js: Any, *, limit: int = DISPATCH_BATCH_SIZE) -> int:
    """Publish a bounded locked batch, confirming each JetStream acknowledgement."""
    published = 0
    with psycopg.connect(database_url) as connection, connection.transaction():
        rows = connection.execute(
            """
            SELECT event_id, subject, payload
            FROM app.message_outbox
            WHERE status = 'pending' AND available_at <= now()
            ORDER BY created_at, event_id
            FOR UPDATE SKIP LOCKED
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
        for event_id, subject, payload in rows:
            data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            try:
                acknowledgement = await js.publish(
                    subject,
                    data,
                    timeout=PUBLISH_TIMEOUT_SECONDS,
                    headers={"Nats-Msg-Id": str(event_id)},
                )
            except (TimeoutError, nats.errors.Error) as error:
                connection.execute(
                    """
                    UPDATE app.message_outbox
                    SET publish_attempts = LEAST(publish_attempts + 1, 100),
                        available_at = now() + interval '1 second',
                        last_error = %s
                    WHERE event_id = %s
                    """,
                    (_diagnostic(error), event_id),
                )
                continue
            connection.execute(
                """
                UPDATE app.message_outbox
                SET status = 'published', published_at = now(),
                    publish_attempts = LEAST(publish_attempts + 1, 100),
                    jetstream_sequence = %s, last_error = NULL
                WHERE event_id = %s
                """,
                (acknowledgement.seq, event_id),
            )
            published += 1
    return published


def process_forecast_request(
    database_url: str,
    request: ForecastRequested,
    *,
    delivery_count: int,
) -> ProcessResult:
    """Commit forecast, dedupe receipt, job state, and result event atomically."""
    database = Database(database_url)
    with psycopg.connect(database_url) as connection, connection.transaction():
        receipt = connection.execute(
            "SELECT status, diagnostic FROM app.message_inbox WHERE event_id = %s",
            (request.event_id,),
        ).fetchone()
        if receipt is not None:
            return ProcessResult("duplicate", receipt[1])

        job = connection.execute(
            """
            SELECT status
            FROM app.forecast_jobs
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
            return ProcessResult("rejected", "request has no authorized database command")

        connection.execute(
            """
            UPDATE app.forecast_jobs
            SET status = 'processing', started_at = COALESCE(started_at, now())
            WHERE request_event_id = %s
            """,
            (request.event_id,),
        )
        build = database.build_forecast_in_transaction(
            connection, request.plant_id, model_version=request.model_version
        )
        occurred_at = utc_now()
        if build.available:
            assert build.issued_at_utc is not None and len(build.points) == 12
            result_event = ForecastCompleted(
                event_id=uuid4(),
                correlation_id=request.correlation_id,
                plant_id=request.plant_id,
                source_sha=request.source_sha,
                occurred_at_utc=occurred_at,
                request_event_id=request.event_id,
                issued_at_utc=build.issued_at_utc,
                model_version=build.model_version,
            )
            state = "completed"
            diagnostic = None
        else:
            diagnostic = (build.unavailable_reason or "forecast unavailable")[:512]
            result_event = ForecastFailed(
                event_id=uuid4(),
                correlation_id=request.correlation_id,
                plant_id=request.plant_id,
                source_sha=request.source_sha,
                occurred_at_utc=occurred_at,
                request_event_id=request.event_id,
                error_code="forecast_unavailable",
                diagnostic=diagnostic,
            )
            state = "failed"
        insert_outbox(connection, result_event)
        connection.execute(
            """
            UPDATE app.forecast_jobs
            SET status = %s, completed_at = %s, result_event_id = %s, diagnostic = %s
            WHERE request_event_id = %s
            """,
            (state, occurred_at, result_event.event_id, diagnostic, request.event_id),
        )
        connection.execute(
            """
            INSERT INTO app.message_inbox
                (event_id, subject, correlation_id, plant_id, delivery_count,
                 status, diagnostic)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                request.event_id,
                request.subject,
                request.correlation_id,
                request.plant_id,
                min(delivery_count, 100),
                state,
                diagnostic,
            ),
        )
        return ProcessResult(state, diagnostic)


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
            (occurred_at, result_event.event_id, diagnostic[:512], request.event_id),
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
            database_url, decoded, delivery_count=delivery_count
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


async def worker_once(database_url: str, js: Any, *, timeout: float = FETCH_TIMEOUT_SECONDS) -> int:
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


async def run_once(
    database_url: str,
    nats_url: str,
    *,
    dispatch: bool,
    consume: bool,
) -> tuple[int, int]:
    client = await connect(nats_url)
    try:
        js = client.jetstream()
        await ensure_topology(js)
        published = await dispatch_once(database_url, js) if dispatch else 0
        consumed = await worker_once(database_url, js) if consume else 0
        return published, consumed
    finally:
        await client.drain()


async def run_service(database_url: str, nats_url: str) -> None:
    client = await connect(nats_url)
    try:
        js = client.jetstream()
        await ensure_topology(js)
        while True:
            await dispatch_once(database_url, js)
            await worker_once(database_url, js, timeout=1.0)
            await asyncio.sleep(0.25)
    finally:
        await client.drain()


def _diagnostic(error: Exception) -> str:
    text = f"{type(error).__name__}: {error}".replace("\x00", "")
    return text[:512]


def _untrusted_event_id(payload: bytes) -> UUID | None:
    try:
        value = json.loads(payload).get("event_id")
        return UUID(value) if isinstance(value, str) else None
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("init", "dispatch", "worker", "run"))
    parser.add_argument("--database-url")
    parser.add_argument("--nats-url")
    args = parser.parse_args(argv)
    database_url = _database_url(args.database_url)
    nats_url = _nats_url(args.nats_url)
    if args.mode == "run":
        asyncio.run(run_service(database_url, nats_url))
        return 0
    published, consumed = asyncio.run(
        run_once(
            database_url,
            nats_url,
            dispatch=args.mode == "dispatch",
            consume=args.mode == "worker",
        )
    )
    print(f"published={published} consumed={consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
