"""Strict, versioned JSON contracts for the Flowstead JetStream boundary."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, ClassVar, Literal
from uuid import UUID

from backend.importer import APPROVED_PLANT_IDS
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

INGEST_COMPLETED = "flowstead.v1.ingest.completed"
FORECAST_REQUESTED = "flowstead.v1.forecast.requested"
FORECAST_COMPLETED = "flowstead.v1.forecast.completed"
FORECAST_FAILED = "flowstead.v1.forecast.failed"
SUBJECTS = (INGEST_COMPLETED, FORECAST_REQUESTED, FORECAST_COMPLETED, FORECAST_FAILED)
MAX_MESSAGE_BYTES = 16_384
MAX_DIAGNOSTIC_CHARS = 512

SourceSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
ContentSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class MessageError(ValueError):
    """A message is not safe to publish or process."""


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: ClassVar[str]
    schema_version: Literal[1] = 1
    event_id: UUID
    correlation_id: UUID
    plant_id: str
    source_sha: SourceSha
    occurred_at_utc: datetime

    @field_validator("event_id", "correlation_id")
    @classmethod
    def non_nil_uuid(cls, value: UUID) -> UUID:
        if value.int == 0:
            raise ValueError("message UUIDs must not be nil")
        return value

    @field_validator("plant_id")
    @classmethod
    def approved_plant(cls, value: str) -> str:
        if value not in APPROVED_PLANT_IDS:
            raise ValueError("message Plant ID is not approved")
        return value

    @field_validator("occurred_at_utc")
    @classmethod
    def explicit_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("message timestamp must have an explicit UTC offset")
        return value.astimezone(UTC)


class IngestCompleted(Event):
    subject: ClassVar[str] = INGEST_COMPLETED
    batch_id: int = Field(gt=0)
    content_sha256: ContentSha
    reading_count: int = Field(gt=0, le=43_800)


class ForecastRequested(Event):
    subject: ClassVar[str] = FORECAST_REQUESTED
    requested_by: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    model_version: str = Field(min_length=1, max_length=128)


class ForecastCompleted(Event):
    subject: ClassVar[str] = FORECAST_COMPLETED
    request_event_id: UUID
    issued_at_utc: datetime
    forecast_count: Literal[12] = 12
    model_version: str = Field(min_length=1, max_length=128)

    _issued_at_is_utc = field_validator("issued_at_utc")(Event.explicit_utc.__func__)


class ForecastFailed(Event):
    subject: ClassVar[str] = FORECAST_FAILED
    request_event_id: UUID
    error_code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    diagnostic: str = Field(min_length=1, max_length=MAX_DIAGNOSTIC_CHARS)


Message = IngestCompleted | ForecastRequested | ForecastCompleted | ForecastFailed
_BY_SUBJECT: dict[str, type[Event]] = {
    message_type.subject: message_type
    for message_type in (IngestCompleted, ForecastRequested, ForecastCompleted, ForecastFailed)
}


def encode_message(message: Message) -> bytes:
    payload = json.dumps(
        message.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(payload) > MAX_MESSAGE_BYTES:
        raise MessageError("message exceeds the byte limit")
    return payload


def decode_message(subject: str, payload: bytes) -> Message:
    if subject not in _BY_SUBJECT:
        raise MessageError("message subject is not recognized")
    if not payload or len(payload) > MAX_MESSAGE_BYTES:
        raise MessageError("message payload size is invalid")
    try:
        decoded = _BY_SUBJECT[subject].model_validate_json(payload)
    except Exception as error:
        raise MessageError(f"message validation failed: {error}") from error
    return decoded  # type: ignore[return-value]


def utc_now() -> datetime:
    return datetime.now(UTC)
