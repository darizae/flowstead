"""Application use case layer against a real isolated PostgreSQL database.

Covers the read workflows (ListAccessiblePlants / GetPlantHistory), the command
workflows (RequestForecast / ProcessForecastRequest), and the transaction
semantics the UnitOfWork guarantees: a failing build rolls the whole
forecast+outbox+job+inbox step back.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from backend.importer import SOURCE_SHA, import_m1

from flowstead_api.access import PUBLIC_ACCESS, OperatorAccess
from flowstead_api.application.forecasts import (
    process_forecast_request,
    request_forecast,
)
from flowstead_api.application.plants import (
    get_plant_history,
    list_accessible_plants,
)
from flowstead_api.infrastructure.persistence.forecast_repository import ForecastRepository
from flowstead_api.infrastructure.persistence.plant_repository import PlantRepository
from flowstead_api.messages import ForecastRequested, utc_now

DATABASE_URL = os.environ.get("DATABASE_URL")
MANIFEST = os.environ.get("FLOWSTEAD_M1_MANIFEST")
DATA = os.environ.get("FLOWSTEAD_M1_DATA")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not MANIFEST or not DATA,
    reason="set DATABASE_URL, FLOWSTEAD_M1_MANIFEST and FLOWSTEAD_M1_DATA for application integration",
)


@pytest.fixture(autouse=True)
def seed_isolated_database(isolated_service_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only seed the disposable per-test DB; never reset configured DATABASE_URL."""
    monkeypatch.setitem(globals(), "DATABASE_URL", isolated_service_url)
    import_m1(isolated_service_url, Path(MANIFEST), Path(DATA), SOURCE_SHA)


def _grant(subject_id: str, *plant_ids: str) -> None:
    with (
        psycopg.connect(DATABASE_URL) as connection,
        connection.transaction(),
        connection.cursor() as cursor,
    ):
        cursor.executemany(
            "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s)",
            [(subject_id, plant_id) for plant_id in plant_ids],
        )


def _request(plant_id: str) -> ForecastRequested:
    return ForecastRequested(
        event_id=uuid4(),
        correlation_id=uuid4(),
        plant_id=plant_id,
        source_sha=SOURCE_SHA,
        occurred_at_utc=utc_now(),
        requested_by="operator-a",
        model_version="seasonal_naive_24h_v1",
    )


def test_list_accessible_plants_respects_public_and_operator_scope() -> None:
    _grant("operator-a", "plant-01", "plant-02")
    plants = PlantRepository()

    public_ids = {
        p.plant_id for p in list_accessible_plants(DATABASE_URL, plants, scope=PUBLIC_ACCESS)
    }
    assert public_ids == {"plant-01", "plant-02", "plant-03", "plant-04", "plant-05"}

    operator_ids = {
        p.plant_id
        for p in list_accessible_plants(DATABASE_URL, plants, scope=OperatorAccess("operator-a"))
    }
    assert operator_ids == {"plant-01", "plant-02"}


def test_get_plant_history_returns_bounded_readings_under_scope() -> None:
    _grant("operator-a", "plant-01")
    plants = PlantRepository()
    with psycopg.connect(DATABASE_URL) as connection:
        latest_timestamp = connection.execute(
            "SELECT MAX(timestamp_utc) FROM app.hourly_readings WHERE plant_id = %s",
            ("plant-01",),
        ).fetchone()[0]
    assert latest_timestamp is not None
    from_utc = latest_timestamp - timedelta(hours=167)
    to_utc = latest_timestamp + timedelta(hours=1)

    visible = get_plant_history(
        DATABASE_URL,
        plants,
        "plant-01",
        from_utc,
        to_utc,
        scope=OperatorAccess("operator-a"),
    )
    assert visible is not None and len(visible[1]) == 168

    assert (
        get_plant_history(
            DATABASE_URL,
            plants,
            "plant-02",
            from_utc,
            to_utc,
            scope=OperatorAccess("operator-a"),
        )
        is None
    )


def test_request_forecast_persists_job_and_outbox_atomically() -> None:
    _grant("operator-a", "plant-01")
    job = request_forecast(DATABASE_URL, plant_id="plant-01", subject_id="operator-a")

    assert job is not None and job.status == "queued"
    with psycopg.connect(DATABASE_URL) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM app.forecast_jobs WHERE request_event_id = %s",
                (job.request_event_id,),
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM app.message_outbox WHERE event_id = %s",
                (job.request_event_id,),
            ).fetchone()[0]
            == 1
        )
    assert request_forecast(DATABASE_URL, plant_id="plant-02", subject_id="operator-a") is None


def test_process_forecast_request_commits_forecast_job_outbox_and_receipt() -> None:
    _grant("operator-a", "plant-01")
    job = request_forecast(DATABASE_URL, plant_id="plant-01", subject_id="operator-a")
    assert job is not None
    request = _request("plant-01")
    # align an authorized database command to the incoming event
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "UPDATE app.forecast_jobs "
            "SET request_event_id = %s, correlation_id = %s, requested_by = %s, source_sha = %s "
            "WHERE request_event_id = %s",
            (
                request.event_id,
                request.correlation_id,
                "operator-a",
                request.source_sha,
                job.request_event_id,
            ),
        )

    result = process_forecast_request(DATABASE_URL, request, ForecastRepository(), delivery_count=1)

    assert result.state == "completed"
    with psycopg.connect(DATABASE_URL) as connection:
        assert connection.execute("SELECT count(*) FROM app.forecast_hours").fetchone()[0] == 12
        assert (
            connection.execute(
                "SELECT status FROM app.forecast_jobs WHERE request_event_id = %s",
                (request.event_id,),
            ).fetchone()[0]
            == "completed"
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM app.message_inbox WHERE event_id = %s",
                (request.event_id,),
            ).fetchone()[0]
            == 1
        )


def test_process_forecast_request_rolls_back_on_build_failure() -> None:
    """Case: IT-M4-ATOMIC — build failure rolls back job, outbox and forecast."""
    _grant("operator-a", "plant-01")
    job = request_forecast(DATABASE_URL, plant_id="plant-01", subject_id="operator-a")
    assert job is not None
    request = _request("plant-01")
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "UPDATE app.forecast_jobs "
            "SET request_event_id = %s, correlation_id = %s, requested_by = %s, source_sha = %s "
            "WHERE request_event_id = %s",
            (
                request.event_id,
                request.correlation_id,
                "operator-a",
                request.source_sha,
                job.request_event_id,
            ),
        )

    class _ExplodingForecasts(ForecastRepository):
        def build_in_transaction(self, connection, plant_id, *, model_version="x"):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        process_forecast_request(DATABASE_URL, request, _ExplodingForecasts(), delivery_count=1)

    with psycopg.connect(DATABASE_URL) as connection:
        # job untouched, forecast and inbox empty: whole transaction rolled back
        assert (
            connection.execute(
                "SELECT status FROM app.forecast_jobs WHERE request_event_id = %s",
                (request.event_id,),
            ).fetchone()[0]
            == "queued"
        )
        assert connection.execute("SELECT count(*) FROM app.forecast_hours").fetchone()[0] == 0
        assert (
            connection.execute(
                "SELECT count(*) FROM app.message_inbox WHERE event_id = %s",
                (request.event_id,),
            ).fetchone()[0]
            == 0
        )
