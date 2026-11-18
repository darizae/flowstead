from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from backend.importer import SOURCE_SHA

from flowstead_api.messages import (
    FORECAST_REQUESTED,
    ForecastRequested,
    MessageError,
    decode_message,
    encode_message,
)


def _request() -> ForecastRequested:
    return ForecastRequested(
        event_id=uuid4(),
        correlation_id=uuid4(),
        plant_id="plant-01",
        source_sha=SOURCE_SHA,
        occurred_at_utc=datetime(2026, 11, 18, tzinfo=UTC),
        requested_by="operator-a",
        model_version="seasonal_naive_24h_v1",
    )


def test_message_round_trip_is_canonical_and_typed() -> None:
    request = _request()

    payload = encode_message(request)
    decoded = decode_message(FORECAST_REQUESTED, payload)

    assert decoded == request
    assert json.loads(payload)["schema_version"] == 1
    assert UUID(json.loads(payload)["event_id"]) == request.event_id


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"plant_id": "plant-99"},
        {"source_sha": "0" * 39},
        {"occurred_at_utc": "2026-11-18T00:00:00-05:00"},
        {"requested_by": "../../operator"},
    ],
)
def test_poison_messages_are_rejected(change: dict[str, object]) -> None:
    raw = _request().model_dump(mode="json")
    raw.update(change)

    with pytest.raises(MessageError, match="validation failed"):
        decode_message(FORECAST_REQUESTED, json.dumps(raw).encode())


def test_subject_and_payload_are_bounded() -> None:
    with pytest.raises(MessageError, match="subject"):
        decode_message("flowstead.v2.forecast.requested", encode_message(_request()))
    with pytest.raises(MessageError, match="size"):
        decode_message(FORECAST_REQUESTED, b"{" + b"x" * 20_000)
