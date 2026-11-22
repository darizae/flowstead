"""Command application use cases: forecast requests and the worker workflow.

``process_forecast_request`` is the transactional forecast workflow: within one
UnitOfWork it deduplicates the receipt, claims the queued job, persists the
deterministic forecast and its outbox result event, updates job state, and
records the inbox receipt — all atomic, so a failure rolls the whole step back.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from ..forecast import MODEL_VERSION, ForecastBuild
from ..infrastructure.persistence.unit_of_work import UnitOfWork
from ..message_store import ForecastJob, enqueue_forecast, insert_outbox, read_forecast_job
from ..messages import (
    ForecastCompleted,
    ForecastFailed,
    ForecastRequested,
    utc_now,
)
from .ports.repositories import ForecastRepository
from .ports.unit_of_work import UnitOfWork as UnitOfWorkPort


@dataclass(frozen=True)
class ProcessResult:
    state: str
    diagnostic: str | None = None


def request_forecast(
    database_url: str,
    *,
    plant_id: str,
    subject_id: str,
) -> ForecastJob | None:
    """Authorize and atomically persist a forecast command plus its outbox event."""
    return enqueue_forecast(database_url, plant_id=plant_id, subject_id=subject_id)


def build_forecast_for_plant(
    database_url: str,
    forecasts: ForecastRepository,
    plant_id: str,
    *,
    model_version: str = MODEL_VERSION,
) -> ForecastBuild:
    """Build and atomically persist the latest forecast for one Plant."""
    with UnitOfWork(database_url) as uow:
        return forecasts.build_in_transaction(uow.connection, plant_id, model_version=model_version)


def read_forecast_status(
    database_url: str,
    *,
    correlation_id: UUID,
    subject_id: str,
) -> ForecastJob | None:
    """Read one requester-scoped forecast job status."""
    return read_forecast_job(database_url, correlation_id=correlation_id, subject_id=subject_id)


def process_forecast_request(
    database_url: str,
    request: ForecastRequested,
    forecasts: ForecastRepository,
    *,
    delivery_count: int,
) -> ProcessResult:
    """Commit forecast, dedupe receipt, job state, and result event atomically."""
    uow: UnitOfWorkPort = UnitOfWork(database_url)
    with uow:
        receipt = uow.connection.execute(
            "SELECT status, diagnostic FROM app.message_inbox WHERE event_id = %s",
            (request.event_id,),
        ).fetchone()
        if receipt is not None:
            return ProcessResult("duplicate", receipt[1])

        job = uow.connection.execute(
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

        uow.connection.execute(
            """
            UPDATE app.forecast_jobs
            SET status = 'processing', started_at = COALESCE(started_at, now())
            WHERE request_event_id = %s
            """,
            (request.event_id,),
        )
        build = forecasts.build_in_transaction(
            uow.connection, request.plant_id, model_version=request.model_version
        )
        occurred_at = utc_now()
        if build.available:
            assert build.issued_at_utc is not None and len(build.points) == 12
            result_event: ForecastCompleted | ForecastFailed = ForecastCompleted(
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
            diagnostic: str | None = None
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
        insert_outbox(uow.connection, result_event)
        uow.connection.execute(
            """
            UPDATE app.forecast_jobs
            SET status = %s, completed_at = %s, result_event_id = %s, diagnostic = %s
            WHERE request_event_id = %s
            """,
            (state, occurred_at, result_event.event_id, diagnostic, request.event_id),
        )
        uow.connection.execute(
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
