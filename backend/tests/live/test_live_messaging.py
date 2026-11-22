"""Real HTTP -> outbox -> NATS JetStream -> worker acceptance checks."""

from __future__ import annotations

import time
from uuid import uuid4

import psycopg

from .harness.stack import LiveStack


def test_queued_status_is_requester_scoped_while_worker_is_paused(
    live_stack: LiveStack,
) -> None:
    """Cases: LIVE-QUEUE-PAUSE, LIVE-QUEUE-NONLEAK — no worker means deterministic queued state."""
    with (
        live_stack.client("live-user-a") as owner,
        live_stack.client("live-user-shared") as shared,
        live_stack.client("live-user-b") as foreign,
    ):
        queued = owner.post("/api/v1/plants/plant-01/forecast-requests")
        assert queued.status_code == 202
        payload = queued.json()
        assert payload["status"] == "queued"

        correlation_id = payload["correlation_id"]
        hidden = shared.get(f"/api/v1/forecast-requests/{correlation_id}")
        unknown = shared.get(f"/api/v1/forecast-requests/{uuid4()}")
        assert hidden.status_code == unknown.status_code == 404
        assert hidden.json() == unknown.json()
        assert correlation_id not in hidden.text
        assert foreign.post("/api/v1/plants/plant-01/forecast-requests").status_code == 404

    with psycopg.connect(live_stack.database_url) as connection:
        row = connection.execute(
            "SELECT status, subject, payload->>'requested_by' FROM app.message_outbox "
            "WHERE correlation_id = %s",
            (correlation_id,),
        ).fetchone()
    assert row == ("pending", "flowstead.v1.forecast.requested", "live-user-a")


def test_real_worker_completes_a_forecast_within_a_bounded_terminal_window(
    running_worker: LiveStack,
) -> None:
    """Cases: LIVE-WORKER-SUBPROCESS, LIVE-QUEUE-COMPLETION — bounded terminal proof."""
    with running_worker.client("live-user-a") as client:
        queued = client.post("/api/v1/plants/plant-02/forecast-requests")
        assert queued.status_code == 202
        payload = queued.json()
        correlation_id = payload["correlation_id"]

        deadline = time.monotonic() + 30
        status_payload: dict[str, object] = {}
        while time.monotonic() < deadline:
            response = client.get(f"/api/v1/forecast-requests/{correlation_id}")
            assert response.status_code == 200
            status_payload = response.json()
            if status_payload["status"] in {"completed", "failed"}:
                break
            time.sleep(0.25)

    assert status_payload["status"] == "completed"
    assert status_payload["correlation_id"] == correlation_id
    with psycopg.connect(running_worker.database_url) as connection:
        assert connection.execute(
            "SELECT status FROM app.forecast_jobs WHERE correlation_id = %s",
            (correlation_id,),
        ).fetchone() == ("completed",)
        assert connection.execute(
            """
            SELECT count(*)
            FROM app.forecast_hours AS hours
            JOIN app.forecast_issuances AS issuances
              ON issuances.id = hours.issuance_id
            JOIN app.forecast_jobs AS jobs ON jobs.plant_id = issuances.plant_id
            WHERE jobs.correlation_id = %s
            """,
            (correlation_id,),
        ).fetchone() == (12,)


def test_worker_outage_keeps_committed_queue_visible_without_leaking_to_foreign_user(
    live_stack: LiveStack,
) -> None:
    """Case: LIVE-WORKER-OUTAGE — stopping the real worker preserves the queued command."""
    live_stack.start_worker()
    live_stack.stop_worker()
    with (
        live_stack.client("live-user-a") as owner,
        live_stack.client("live-user-shared") as shared,
    ):
        queued = owner.post("/api/v1/plants/plant-01/forecast-requests")
        assert queued.status_code == 202
        correlation_id = queued.json()["correlation_id"]
        assert owner.get(f"/api/v1/forecast-requests/{correlation_id}").json()["status"] == "queued"
        assert shared.get(f"/api/v1/forecast-requests/{correlation_id}").status_code == 404

    with psycopg.connect(live_stack.database_url) as connection:
        assert connection.execute(
            "SELECT status FROM app.forecast_jobs WHERE correlation_id = %s",
            (correlation_id,),
        ).fetchone() == ("queued",)
