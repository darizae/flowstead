from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flowstead_api.forecast import FlowObservation, backtest, forecast_for_issuance

UTC = timezone.utc
ISSUED = datetime(2025, 1, 2, 12, tzinfo=UTC)


def observation(timestamp: datetime, value: object, quality: str = "valid") -> FlowObservation:
    return FlowObservation(timestamp, value, quality)


def test_horizon_is_exactly_twelve_ordered_utc_hours() -> None:
    source = [
        observation(ISSUED - timedelta(hours=23 - offset), Decimal(100 + offset))
        for offset in range(12)
    ]

    result = forecast_for_issuance(source, ISSUED, source_revision="source-a")

    assert result.available
    assert result.model_version == "seasonal_naive_24h_v1"
    assert result.source_revision == "source-a"
    assert len(result.points) == 12
    assert [point.hour_number for point in result.points] == list(range(1, 13))
    assert [point.target_time_utc for point in result.points] == [
        ISSUED + timedelta(hours=hour) for hour in range(1, 13)
    ]
    assert len({point.target_time_utc for point in result.points}) == 12
    assert all(point.target_time_utc.tzinfo == UTC for point in result.points)


def test_valid_seasonal_source_is_preferred_over_persistence() -> None:
    source = [observation(ISSUED, 999)]
    source.extend(
        observation(ISSUED - timedelta(hours=23 - offset), 200 + offset)
        for offset in range(12)
    )

    result = forecast_for_issuance(source, ISSUED)

    assert [point.source for point in result.points] == ["seasonal_naive_24h"] * 12
    assert [point.predicted_flow_gal_h for point in result.points] == [
        Decimal(200 + offset) for offset in range(12)
    ]


def test_missing_or_invalid_seasonal_source_uses_latest_six_hour_persistence() -> None:
    source = [
        observation(ISSUED - timedelta(hours=1), 75),
        observation(ISSUED - timedelta(hours=2), 50, "invalid"),
        observation(ISSUED - timedelta(hours=12), 10, "missing"),
    ]

    result = forecast_for_issuance(source, ISSUED)

    assert result.available
    assert [point.source for point in result.points] == ["persistence_6h"] * 12
    assert all(point.predicted_flow_gal_h == Decimal(75) for point in result.points)


def test_forecast_is_explicitly_unavailable_without_valid_source() -> None:
    result = forecast_for_issuance(
        [observation(ISSUED, 1, "invalid"), observation(ISSUED - timedelta(hours=1), None, "missing")],
        ISSUED,
    )
    assert not result.available
    assert result.unavailable_reason == "no_valid_source"
    assert result.points == ()



def test_backtest_excludes_invalid_truth_and_uses_no_future_features() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    source = [
        observation(start + timedelta(hours=hour), hour)
        for hour in range(48)
    ]
    source[-2] = observation(source[-2].timestamp_utc, source[-2].value, "invalid")

    receipt = backtest(source, holdout_hours=8)

    assert receipt.model_eligible_count == 7
    assert receipt.persistence_eligible_count == 7
    assert receipt.notice.startswith("Synthetic backtests do not validate")
