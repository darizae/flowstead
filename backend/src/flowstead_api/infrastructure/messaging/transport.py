"""NATS/JetStream transport: client connection, topology, and outbox dispatch."""

from __future__ import annotations

import json
import os
from typing import Any

import nats
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

from ...messages import FORECAST_REQUESTED, SUBJECTS

STREAM_NAME = "FLOWSTEAD_V1"
FORECAST_DURABLE = "flowstead-forecast-v1"
ACK_WAIT_SECONDS = 30.0
MAX_DELIVERIES = 5
MAX_EVENT_AGE_SECONDS = 7 * 24 * 60 * 60
PUBLISH_TIMEOUT_SECONDS = 5.0
FETCH_TIMEOUT_SECONDS = 2.0
DISPATCH_BATCH_SIZE = 25
RETRY_DELAYS_SECONDS = (0.25, 0.5, 1.0, 1.0, 1.0)


def _database_url(explicit: str | None = None) -> str:
    value = explicit or os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required for messaging")
    return value


def _nats_url(explicit: str | None = None) -> str:
    return explicit or os.environ.get("NATS_URL", "nats://127.0.0.1:42229")


def _diagnostic(error: Exception) -> str:
    text = f"{type(error).__name__}: {error}".replace("\x00", "")
    return text[:512]


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


async def dispatch_once(database_url: str, js: Any, *, limit: int = DISPATCH_BATCH_SIZE) -> int:
    """Publish a bounded locked batch, confirming each JetStream acknowledgement."""
    import psycopg

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
            except (NatsTimeoutError, nats.errors.Error) as error:
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
