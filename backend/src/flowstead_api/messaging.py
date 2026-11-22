"""Flowstead messaging entry point: CLI, run loop, and public transport/worker API.

Transport adapters live in ``infrastructure.messaging.transport`` and the durable
forecast worker in ``infrastructure.messaging.worker``. This module preserves the
historical ``flowstead_api.messaging`` import surface and owns process wiring.
"""

from __future__ import annotations

import argparse
import asyncio
import signal

from .infrastructure.messaging.transport import (
    ACK_WAIT_SECONDS,
    DISPATCH_BATCH_SIZE,
    FETCH_TIMEOUT_SECONDS,
    FORECAST_DURABLE,
    MAX_DELIVERIES,
    MAX_EVENT_AGE_SECONDS,
    PUBLISH_TIMEOUT_SECONDS,
    RETRY_DELAYS_SECONDS,
    STREAM_NAME,
    _database_url,
    _nats_url,
    connect,
    dispatch_once,
    ensure_topology,
)
from .infrastructure.messaging.worker import (
    ProcessResult,
    _public_diagnostic,
    consume_one,
    process_forecast_request,
    record_failure,
    record_terminal_request_failure,
    worker_once,
)

__all__ = [
    "ACK_WAIT_SECONDS",
    "DISPATCH_BATCH_SIZE",
    "FETCH_TIMEOUT_SECONDS",
    "FORECAST_DURABLE",
    "MAX_DELIVERIES",
    "MAX_EVENT_AGE_SECONDS",
    "PUBLISH_TIMEOUT_SECONDS",
    "RETRY_DELAYS_SECONDS",
    "STREAM_NAME",
    "ProcessResult",
    "_public_diagnostic",
    "connect",
    "consume_one",
    "dispatch_once",
    "ensure_topology",
    "process_forecast_request",
    "record_failure",
    "record_terminal_request_failure",
    "worker_once",
]


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
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:  # e.g. Windows; fall back to default handling
            pass
    client = await connect(nats_url)
    try:
        js = client.jetstream()
        await ensure_topology(js)
        while not stop_event.is_set():
            await dispatch_once(database_url, js)
            await worker_once(database_url, js, timeout=1.0)
            # Graceful-SIGTERM window: sleep so a pending stop_event is observed.
            await asyncio.sleep(0.25)
    finally:
        await client.drain()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flowstead JetStream dispatcher and worker")
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
