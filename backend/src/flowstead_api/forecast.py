"""Deterministic, bounded influent-flow forecast calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

HORIZON_HOURS = 12
SEASONAL_LAG = timedelta(hours=24)
PERSISTENCE_LOOKBACK = timedelta(hours=5)
MODEL_VERSION = "seasonal_naive_24h_v1"
PHYSICAL_BOUND_RULE = "nonnegative_influent_flow"
SYNTHETIC_BACKTEST_NOTICE = (
    "Synthetic backtests do not validate real-world performance and are not an accuracy claim."
)


@dataclass(frozen=True)
class FlowObservation:
    timestamp_utc: datetime
    value: Decimal | float | int | None
    quality: str


@dataclass(frozen=True)
class ForecastPoint:
    hour_number: int
    target_time_utc: datetime
    predicted_flow_gal_h: Decimal
    source: str


@dataclass(frozen=True)
class ForecastBuild:
    issued_at_utc: datetime | None
    model_version: str
    source_revision: str | None
    physical_bound_rule: str
    points: tuple[ForecastPoint, ...]
    unavailable_reason: str | None = None

    @property
    def available(self) -> bool:
        return not self.unavailable_reason



@dataclass(frozen=True)
class BacktestReceipt:
    holdout_start_utc: datetime | None
    holdout_end_utc: datetime | None
    model_mae_gal_h: float | None
    model_eligible_count: int
    persistence_mae_gal_h: float | None
    persistence_eligible_count: int
    notice: str = SYNTHETIC_BACKTEST_NOTICE


def _utc_hour(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("forecast timestamps must include UTC timezone information")
    normalized = value.astimezone(timezone.utc)
    if normalized.minute or normalized.second or normalized.microsecond:
        raise ValueError("forecast timestamps must be aligned to UTC hours")
    return normalized


def _valid_value(observation: FlowObservation | None) -> Decimal | None:
    if observation is None or observation.quality != "valid" or observation.value is None:
        return None
    try:
        value = Decimal(str(observation.value))
    except Exception:
        return None
    if not value.is_finite():
        return None
    return value


def _observation_map(
    observations: Iterable[FlowObservation],
    issued_at_utc: datetime,
) -> dict[datetime, FlowObservation]:
    result: dict[datetime, FlowObservation] = {}
    for observation in observations:
        timestamp = _utc_hour(observation.timestamp_utc)
        if timestamp <= issued_at_utc:
            result[timestamp] = FlowObservation(timestamp, observation.value, observation.quality)
    return result


def _latest_valid(
    observations: dict[datetime, FlowObservation],
    start_utc: datetime,
    end_utc: datetime,
) -> tuple[datetime, Decimal] | None:
    candidates = [
        (timestamp, _valid_value(observation))
        for timestamp, observation in observations.items()
        if start_utc <= timestamp <= end_utc
    ]
    valid = [(timestamp, value) for timestamp, value in candidates if value is not None]
    if not valid:
        return None
    return max(valid, key=lambda item: item[0])


def _bounded(value: Decimal) -> Decimal:
    return max(value, Decimal("0"))


def forecast_for_issuance(
    observations: Iterable[FlowObservation],
    issued_at_utc: datetime,
    *,
    source_revision: str | None = None,
    model_version: str = MODEL_VERSION,
) -> ForecastBuild:
    """Build exactly twelve forecasts using only observations at or before issuance."""
    issued_at_utc = _utc_hour(issued_at_utc)
    observed = _observation_map(observations, issued_at_utc)
    persistence = _latest_valid(
        observed,
        issued_at_utc - PERSISTENCE_LOOKBACK,
        issued_at_utc,
    )
    points: list[ForecastPoint] = []
    for hour_number in range(1, HORIZON_HOURS + 1):
        target = issued_at_utc + timedelta(hours=hour_number)
        seasonal = _valid_value(observed.get(target - SEASONAL_LAG))
        if seasonal is not None:
            value = seasonal
            source = "seasonal_naive_24h"
        elif persistence is not None:
            value = persistence[1]
            source = "persistence_6h"
        else:
            return ForecastBuild(
                issued_at_utc=issued_at_utc,
                model_version=model_version,
                source_revision=source_revision,
                physical_bound_rule=PHYSICAL_BOUND_RULE,
                points=(),
                unavailable_reason="no_valid_source",
            )
        points.append(
            ForecastPoint(
                hour_number=hour_number,
                target_time_utc=target,
                predicted_flow_gal_h=_bounded(value),
                source=source,
            )
        )
    return ForecastBuild(
        issued_at_utc=issued_at_utc,
        model_version=model_version,
        source_revision=source_revision,
        physical_bound_rule=PHYSICAL_BOUND_RULE,
        points=tuple(points),
    )


def _one_step_prediction(
    observations: dict[datetime, FlowObservation],
    target_time_utc: datetime,
) -> Decimal | None:
    issuance = target_time_utc - timedelta(hours=1)
    seasonal = _valid_value(observations.get(target_time_utc - SEASONAL_LAG))
    if seasonal is not None:
        return _bounded(seasonal)
    persistence = _latest_valid(observations, issuance - PERSISTENCE_LOOKBACK, issuance)
    return None if persistence is None else _bounded(persistence[1])


def backtest(
    observations: Iterable[FlowObservation],
    *,
    holdout_hours: int = 30 * 24,
) -> BacktestReceipt:
    """Walk a chronological holdout; feature rows are truncated at each issuance."""
    if holdout_hours < 1:
        raise ValueError("holdout_hours must be positive")
    ordered = sorted(
        {
            _utc_hour(observation.timestamp_utc): observation
            for observation in observations
        }.values(),
        key=lambda observation: observation.timestamp_utc,
    )
    if not ordered:
        return BacktestReceipt(None, None, None, 0, None, 0)
    holdout = ordered[-holdout_hours:]
    errors: list[Decimal] = []
    persistence_errors: list[Decimal] = []
    for truth in holdout:
        truth_value = _valid_value(truth)
        if truth_value is None:
            continue
        target = _utc_hour(truth.timestamp_utc)
        issuance = target - timedelta(hours=1)
        history = {
            _utc_hour(observation.timestamp_utc): observation
            for observation in ordered
            if _utc_hour(observation.timestamp_utc) <= issuance
        }
        prediction = _one_step_prediction(history, target)
        if prediction is not None:
            errors.append(abs(prediction - truth_value))
        persistence = _latest_valid(history, issuance - PERSISTENCE_LOOKBACK, issuance)
        if persistence is not None:
            persistence_errors.append(abs(_bounded(persistence[1]) - truth_value))
    return BacktestReceipt(
        holdout_start_utc=_utc_hour(holdout[0].timestamp_utc),
        holdout_end_utc=_utc_hour(holdout[-1].timestamp_utc),
        model_mae_gal_h=(float(sum(errors) / len(errors)) if errors else None),
        model_eligible_count=len(errors),
        persistence_mae_gal_h=(
            float(sum(persistence_errors) / len(persistence_errors))
            if persistence_errors
            else None
        ),
        persistence_eligible_count=len(persistence_errors),
    )


def main() -> int:
    """Run the local build for every approved Plant; no network or scheduler is used."""
    from .database import Database

    database = Database()
    print(f"backtest_notice={SYNTHETIC_BACKTEST_NOTICE}")
    for plant_id in sorted(database.public_plant_ids):
        result = database.build_forecast(plant_id)
        state = "available" if result.available else f"unavailable:{result.unavailable_reason}"
        issued_at = (
            result.issued_at_utc.isoformat()
            if result.issued_at_utc is not None
            else "none"
        )
        receipt = backtest(database.flow_observations(plant_id))
        print(
            f"{plant_id} {state} issued_at={issued_at} "
            f"mae_gal_h={receipt.model_mae_gal_h} "
            f"eligible={receipt.model_eligible_count} "
            f"persistence_mae_gal_h={receipt.persistence_mae_gal_h} "
            f"persistence_eligible={receipt.persistence_eligible_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
