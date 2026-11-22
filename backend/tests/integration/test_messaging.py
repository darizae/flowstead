"""Real PostgreSQL, HTTP, and JetStream acceptance for T-004b."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from backend.importer import (
    APPROVED_PLANT_IDS,
    APPROVED_PLANTS,
    CSV_COLUMNS,
    SOURCE_SHA,
    ImportValidationError,
    import_m1,
)
from backend.tests.auth_helpers import install_test_principal, principal_headers
from fastapi.testclient import TestClient
from nats.errors import NoServersError
from nats.js.errors import NotFoundError

from flowstead_api.forecast import MODEL_VERSION
from flowstead_api.main import create_app
from flowstead_api.message_store import insert_outbox
from flowstead_api.messages import FORECAST_REQUESTED, ForecastRequested
from flowstead_api.messaging import (
    FORECAST_DURABLE,
    MAX_DELIVERIES,
    STREAM_NAME,
    connect,
    dispatch_once,
    ensure_topology,
    worker_once,
)

NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:42229")
REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def seeded_url(isolated_service_url: str, monkeypatch: pytest.MonkeyPatch) -> str:
    with psycopg.connect(isolated_service_url) as connection, connection.transaction():
        batch_id = connection.execute(
            """
            INSERT INTO app.ingest_batches
                (content_sha256, source_sha, schema_version, generator_version,
                 seed, manifest_sha256, row_count, content_bytes)
            VALUES (%s, %s, 'm1.v1', 'integration-fixture', 20250101,
                    %s, 50, 1000)
            RETURNING id
            """,
            ("a" * 64, SOURCE_SHA, "b" * 64),
        ).fetchone()[0]
        for plant_id in ("plant-01", "plant-02"):
            plant = APPROVED_PLANTS[plant_id]
            connection.execute(
                """
                INSERT INTO app.plants
                    (plant_id, name, city, state_code, timezone, latitude,
                     longitude, hydraulic_capacity_gal_h, public_demo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)
                """,
                (
                    plant_id,
                    plant["name"],
                    plant["city"],
                    plant["state_code"],
                    plant["timezone"],
                    plant["latitude"],
                    plant["longitude"],
                    plant["hydraulic_capacity_gal_h"],
                ),
            )
            start = datetime(2026, 11, 16, tzinfo=UTC)
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO app.hourly_readings
                        (plant_id, timestamp_utc, influent_flow, influent_flow_quality,
                         rainfall, rainfall_quality, dissolved_oxygen,
                         dissolved_oxygen_quality, effluent_ph, effluent_ph_quality,
                         source_batch_id)
                    VALUES (%s, %s, %s, 'valid', 0, 'valid', 2, 'valid',
                            7, 'valid', %s)
                    """,
                    [
                        (
                            plant_id,
                            start + timedelta(hours=hour),
                            Decimal(100) + hour,
                            batch_id,
                        )
                        for hour in range(25)
                    ],
                )
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s)",
                [("operator-a", "plant-01"), ("operator-a", "plant-02")],
            )
    return isolated_service_url


def _client(url: str) -> TestClient:
    return TestClient(install_test_principal(create_app(url)))


def _headers() -> dict[str, str]:
    return principal_headers("operator-a")


def _write_bounded_import(tmp_path: Path) -> tuple[Path, Path]:
    data = tmp_path / "telemetry.csv"
    rows = [
        [plant_id, "2026-11-18T00:00:00Z", "100", "valid", "0", "valid", "2", "valid", "7", "valid"]
        for plant_id in sorted(APPROVED_PLANT_IDS)
    ]
    data.write_text(
        ",".join(CSV_COLUMNS) + "\n" + "\n".join(",".join(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "m1.v1",
                "generator_version": "message-integration-fixture",
                "seed": 20250101,
                "provenance": "synthetic",
                "source_sha": SOURCE_SHA,
                "units": {
                    "influent_flow": "gal/h",
                    "rainfall": "in/h",
                    "dissolved_oxygen": "mg/L",
                    "effluent_ph": "unitless",
                },
                "plants": sorted(APPROVED_PLANT_IDS),
                "files": {
                    "telemetry.csv": {
                        "sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
                        "bytes": data.stat().st_size,
                        "rows": 5,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return manifest, data


def test_command_is_authorized_transactional_and_observably_queued(
    seeded_url: str,
) -> None:
    """Cases: MSG-M4B-PUBLISH, MSG-M4B-PAUSE, MSG-M4B-AUTH"""
    client = _client(seeded_url)

    queued = client.post("/api/v1/plants/plant-01/forecast-requests", headers=_headers())

    assert queued.status_code == 202
    assert queued.json()["status"] == "queued"
    correlation_id = queued.json()["correlation_id"]
    status = client.get(f"/api/v1/forecast-requests/{correlation_id}", headers=_headers())
    assert status.status_code == 200 and status.json()["status"] == "queued"
    assert (
        client.post(
            "/api/v1/plants/plant-01/forecast-requests",
            headers=principal_headers("operator-b"),
        ).status_code
        == 404
    )
    assert client.post("/api/v1/public/plants/plant-01/forecast-requests").status_code == 404
    assert client.get("/api/v1/public/plants/plant-01/latest").status_code == 200

    with psycopg.connect(seeded_url) as connection:
        row = connection.execute(
            """
            SELECT subject, event_id::text, correlation_id::text, plant_id,
                   payload->>'event_id', payload->>'source_sha', status
            FROM app.message_outbox
            """
        ).fetchone()
        assert row == (
            FORECAST_REQUESTED,
            queued.json()["request_event_id"],
            correlation_id,
            "plant-01",
            queued.json()["request_event_id"],
            SOURCE_SHA,
            "pending",
        )
        event = ForecastRequested(
            event_id=uuid4(),
            correlation_id=uuid4(),
            plant_id="plant-01",
            source_sha=SOURCE_SHA,
            occurred_at_utc=datetime.now(UTC),
            requested_by="operator-a",
            model_version=MODEL_VERSION,
        )
        with pytest.raises(RuntimeError, match="rollback proof"), connection.transaction():
            insert_outbox(connection, event)
            raise RuntimeError("rollback proof")
        assert connection.execute(
            "SELECT count(*) FROM app.message_outbox WHERE event_id = %s",
            (event.event_id,),
        ).fetchone() == (0,)


def test_forecast_status_is_requester_scoped_across_shared_plant_reads(
    seeded_url: str,
) -> None:
    """Case: SEC-M19-AUTHZ — same-Plant, different requester must not read a job."""
    with psycopg.connect(seeded_url) as connection, connection.transaction():
        connection.execute(
            "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s)",
            ("operator-shared", "plant-01"),
        )
    client = _client(seeded_url)

    owner = client.post("/api/v1/plants/plant-01/forecast-requests", headers=_headers())
    assert owner.status_code == 202
    owner_correlation = owner.json()["correlation_id"]

    # Shared-Plant but non-requester: uniform 404, identical to an unknown ID.
    leaked = client.get(
        f"/api/v1/forecast-requests/{owner_correlation}",
        headers=principal_headers("operator-shared"),
    )
    unknown = client.get(
        f"/api/v1/forecast-requests/{uuid4()}",
        headers=principal_headers("operator-shared"),
    )
    assert leaked.status_code == 404
    assert leaked.json() == unknown.json()
    assert "operator" not in json.dumps(leaked.json())

    # The requester still reads their own job; the shared user reads their own.
    assert (
        client.get(f"/api/v1/forecast-requests/{owner_correlation}", headers=_headers()).status_code
        == 200
    )
    own = client.post(
        "/api/v1/plants/plant-01/forecast-requests",
        headers=principal_headers("operator-shared"),
    ).json()
    assert (
        client.get(
            f"/api/v1/forecast-requests/{own['correlation_id']}",
            headers=principal_headers("operator-shared"),
        ).status_code
        == 200
    )


async def _reset_isolated_broker() -> None:
    assert os.environ.get("FLOWSTEAD_ISOLATED_NATS_TEST") == "1"
    client = await connect(NATS_URL)
    try:
        js = client.jetstream()
        try:
            await js.purge_stream(STREAM_NAME)
        except NotFoundError:
            pass
        try:
            await js.delete_consumer(STREAM_NAME, FORECAST_DURABLE)
        except NotFoundError:
            pass
        await ensure_topology(js)
    finally:
        await client.drain()


async def _dispatch(url: str) -> int:
    client = await connect(NATS_URL)
    try:
        js = client.jetstream()
        await ensure_topology(js)
        return await dispatch_once(url, js)
    finally:
        await client.drain()


async def _work(url: str, count: int = 1) -> list[int]:
    client = await connect(NATS_URL)
    try:
        js = client.jetstream()
        await ensure_topology(js)
        return [await worker_once(url, js, timeout=3.0) for _ in range(count)]
    finally:
        await client.drain()


@pytest.mark.skipif(
    os.environ.get("FLOWSTEAD_ISOLATED_NATS_TEST") != "1",
    reason="set by the isolated local JetStream acceptance recipe",
)
def test_import_events_commit_atomically_and_publish_to_real_jetstream(
    isolated_service_url: str, tmp_path: Path
) -> None:
    """Case: MSG-M4B-PUBLISH"""
    asyncio.run(_reset_isolated_broker())
    manifest, data = _write_bounded_import(tmp_path)

    assert import_m1(isolated_service_url, manifest, data, SOURCE_SHA)

    with psycopg.connect(isolated_service_url) as connection:
        rows = connection.execute(
            """
            SELECT subject, plant_id, payload->>'event_id', event_id::text,
                   payload->>'source_sha', payload->>'content_sha256', status
            FROM app.message_outbox
            ORDER BY plant_id
            """
        ).fetchall()
        assert len(rows) == 5
        assert [row[1] for row in rows] == sorted(APPROVED_PLANT_IDS)
        assert all(
            row[0] == "flowstead.v1.ingest.completed"
            and row[2] == row[3]
            and row[4] == SOURCE_SHA
            and row[5] == hashlib.sha256(data.read_bytes()).hexdigest()
            and row[6] == "pending"
            for row in rows
        )

    assert asyncio.run(_dispatch(isolated_service_url)) == 5
    with psycopg.connect(isolated_service_url) as connection:
        assert connection.execute(
            """
            SELECT count(*) FROM app.message_outbox
            WHERE status = 'published' AND jetstream_sequence IS NOT NULL
            """
        ).fetchone() == (5,)
        before = connection.execute("SELECT count(*) FROM app.message_outbox").fetchone()
    data.write_text(data.read_text().replace(",100,", ",101,", 1))
    with pytest.raises(ImportValidationError, match="SHA-256"):
        import_m1(isolated_service_url, manifest, data, SOURCE_SHA)
    with psycopg.connect(isolated_service_url) as connection:
        assert connection.execute("SELECT count(*) FROM app.message_outbox").fetchone() == before


@pytest.mark.skipif(
    os.environ.get("FLOWSTEAD_ISOLATED_NATS_TEST") != "1",
    reason="set by the isolated local JetStream acceptance recipe",
)
def test_real_jetstream_flow_duplicate_outage_poison_and_retry_exhaustion(
    seeded_url: str,
) -> None:
    """Cases: MSG-M4B-FLOW, MSG-M4B-DUP, MSG-M4B-OUTAGE, MSG-M4B-PAUSE, MSG-M4B-POISON"""
    asyncio.run(_reset_isolated_broker())
    client = _client(seeded_url)
    queued = client.post("/api/v1/plants/plant-01/forecast-requests", headers=_headers()).json()

    # A real controlled broker stop cannot change the committed queue or break
    # ordinary reads; restarting the same JetStream volume resumes delivery.
    subprocess.run(["docker", "compose", "stop", "nats"], cwd=REPO_ROOT, check=True)
    try:
        with pytest.raises(NoServersError):
            asyncio.run(connect(NATS_URL))
        assert client.get("/api/v1/public/plants/plant-01/latest").status_code == 200
        assert (
            client.get(
                f"/api/v1/forecast-requests/{queued['correlation_id']}",
                headers=_headers(),
            ).json()["status"]
            == "queued"
        )
        with psycopg.connect(seeded_url) as connection:
            assert connection.execute(
                "SELECT status FROM app.message_outbox WHERE event_id = %s",
                (queued["request_event_id"],),
            ).fetchone() == ("pending",)
    finally:
        subprocess.run(
            ["docker", "compose", "up", "-d", "--wait", "nats"],
            cwd=REPO_ROOT,
            check=True,
        )

    assert asyncio.run(_dispatch(seeded_url)) == 1
    with psycopg.connect(seeded_url) as connection:
        stream_event = connection.execute(
            "SELECT subject, payload FROM app.message_outbox WHERE event_id = %s",
            (queued["request_event_id"],),
        ).fetchone()
        # Simulate publish acknowledgement followed by a dispatcher crash: the
        # same Nats-Msg-Id is safely accepted as a JetStream duplicate.
        connection.execute(
            """
            UPDATE app.message_outbox
            SET status = 'pending', published_at = NULL, jetstream_sequence = NULL
            WHERE event_id = %s
            """,
            (queued["request_event_id"],),
        )
    assert asyncio.run(_dispatch(seeded_url)) == 1
    assert asyncio.run(_work(seeded_url)) == [1]

    with psycopg.connect(seeded_url) as connection:
        assert connection.execute(
            "SELECT count(*) FROM app.forecast_issuances WHERE plant_id = 'plant-01'"
        ).fetchone() == (1,)
        assert connection.execute(
            """
            SELECT count(*) FROM app.forecast_hours AS h
            JOIN app.forecast_issuances AS i ON i.id = h.issuance_id
            WHERE i.plant_id = 'plant-01'
            """
        ).fetchone() == (12,)
        assert connection.execute(
            "SELECT count(*) FROM app.message_inbox WHERE event_id = %s",
            (queued["request_event_id"],),
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT status FROM app.forecast_jobs WHERE request_event_id = %s",
            (queued["request_event_id"],),
        ).fetchone() == ("completed",)

    # A new stream sequence containing the identical request is acknowledged
    # from the inbox receipt and cannot create a second issuance or result event.
    async def redeliver() -> None:
        nc = await connect(NATS_URL)
        try:
            js = nc.jetstream()
            data = json.dumps(stream_event[1], sort_keys=True, separators=(",", ":")).encode()
            await js.publish(stream_event[0], data)
        finally:
            await nc.drain()

    asyncio.run(redeliver())
    assert asyncio.run(_work(seeded_url)) == [1]
    with psycopg.connect(seeded_url) as connection:
        assert connection.execute(
            "SELECT count(*) FROM app.forecast_issuances WHERE plant_id = 'plant-01'"
        ).fetchone() == (1,)
        completed_count = connection.execute(
            """
            SELECT count(*) FROM app.message_outbox
            WHERE subject = 'flowstead.v1.forecast.completed'
              AND correlation_id = %s
            """,
            (queued["correlation_id"],),
        ).fetchone()
        assert completed_count == (1,)

    # Two distinct authorized requests delivered in reverse creation order
    # both terminate without duplicating the deterministic issuance.
    reordered = [
        client.post("/api/v1/plants/plant-01/forecast-requests", headers=_headers()).json()
        for _ in range(2)
    ]
    with psycopg.connect(seeded_url) as connection:
        pending = connection.execute(
            """
            SELECT event_id, subject, payload
            FROM app.message_outbox
            WHERE event_id = ANY(%s)
            ORDER BY created_at
            """,
            ([job["request_event_id"] for job in reordered],),
        ).fetchall()

    async def publish_reversed() -> list[tuple[int, str]]:
        nc = await connect(NATS_URL)
        published: list[tuple[int, str]] = []
        try:
            js = nc.jetstream()
            for event_id, subject, payload in reversed(pending):
                acknowledgement = await js.publish(
                    subject,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
                    headers={"Nats-Msg-Id": str(event_id)},
                )
                published.append((acknowledgement.seq, str(event_id)))
            return published
        finally:
            await nc.drain()

    published_reversed = asyncio.run(publish_reversed())
    with (
        psycopg.connect(seeded_url) as connection,
        connection.transaction(),
        connection.cursor() as cursor,
    ):
        cursor.executemany(
            """
            UPDATE app.message_outbox
            SET status = 'published', published_at = now(), jetstream_sequence = %s
            WHERE event_id = %s
            """,
            published_reversed,
        )
    assert asyncio.run(_work(seeded_url, 2)) == [1, 1]
    with psycopg.connect(seeded_url) as connection:
        assert connection.execute(
            "SELECT count(*) FROM app.forecast_issuances WHERE plant_id = 'plant-01'"
        ).fetchone() == (1,)
        assert connection.execute(
            """
            SELECT count(*) FROM app.forecast_jobs
            WHERE request_event_id = ANY(%s) AND status = 'completed'
            """,
            ([job["request_event_id"] for job in reordered],),
        ).fetchone() == (2,)

    async def publish_poison() -> None:
        nc = await connect(NATS_URL)
        try:
            js = nc.jetstream()
            poison = dict(stream_event[1])
            poison["event_id"] = str(uuid4())
            poison["schema_version"] = 99
            await js.publish(FORECAST_REQUESTED, json.dumps(poison).encode())
        finally:
            await nc.drain()

    asyncio.run(publish_poison())
    assert asyncio.run(_work(seeded_url)) == [1]
    with psycopg.connect(seeded_url) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM app.message_failures WHERE terminal = true"
            ).fetchone()[0]
            >= 1
        )
        assert connection.execute(
            "SELECT count(*) FROM app.forecast_issuances WHERE plant_id = 'plant-02'"
        ).fetchone() == (0,)

    # A malformed pre-existing issuance forces deterministic processing to
    # fail while PostgreSQL remains writable; the fifth real delivery becomes
    # a visible failed job, inbox receipt, and forecast.failed outbox event.
    latest = datetime(2026, 11, 17, tzinfo=UTC)
    with psycopg.connect(seeded_url) as connection, connection.transaction():
        issuance_id = connection.execute(
            """
            INSERT INTO app.forecast_issuances
                (plant_id, issued_at, model_version, source_revision,
                 physical_bound_rule)
            VALUES ('plant-02', %s, %s, 'fixture', 'nonnegative_influent_flow')
            RETURNING id
            """,
            (latest, MODEL_VERSION),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO app.forecast_hours
                (issuance_id, target_time, predicted_flow, hour_number)
            VALUES (%s, %s, 1, 1)
            """,
            (issuance_id, latest + timedelta(hours=1)),
        )
    failed = client.post("/api/v1/plants/plant-02/forecast-requests", headers=_headers()).json()
    assert asyncio.run(_dispatch(seeded_url)) >= 1
    deliveries = asyncio.run(_work(seeded_url, MAX_DELIVERIES))
    assert deliveries == [1] * MAX_DELIVERIES
    with psycopg.connect(seeded_url) as connection:
        assert connection.execute(
            "SELECT status FROM app.forecast_jobs WHERE request_event_id = %s",
            (failed["request_event_id"],),
        ).fetchone() == ("failed",)
        assert connection.execute(
            "SELECT delivery_count, status FROM app.message_inbox WHERE event_id = %s",
            (failed["request_event_id"],),
        ).fetchone() == (MAX_DELIVERIES, "failed")
        assert connection.execute(
            """
            SELECT count(*) FROM app.message_outbox
            WHERE correlation_id = %s
              AND subject = 'flowstead.v1.forecast.failed'
            """,
            (failed["correlation_id"],),
        ).fetchone() == (1,)
