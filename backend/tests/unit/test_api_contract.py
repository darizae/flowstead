from __future__ import annotations

from datetime import timedelta, timezone

import pytest
from pydantic import ValidationError

from flowstead_api.main import _parse_utc_hour, parse_window
from flowstead_api.models import Measurements


def test_four_channels_require_canonical_units_and_preserve_flags() -> None:
    measurements = Measurements.model_validate(
        {
            "influent_flow": {"value": None, "quality": "missing", "units": "gal/h"},
            "rainfall": {"value": 0.25, "quality": "valid", "units": "in/h"},
            "dissolved_oxygen": {"value": 1.5, "quality": "invalid", "units": "mg/L"},
            "effluent_ph": {"value": 7.2, "quality": "invalid", "units": "unitless"},
        }
    )
    assert measurements.influent_flow.value is None
    assert measurements.influent_flow.quality == "missing"
    assert measurements.dissolved_oxygen.quality == "invalid"

    with pytest.raises(ValidationError):
        Measurements.model_validate(
            {
                "influent_flow": {"value": 1, "quality": "valid", "units": "liters"},
                "rainfall": {"value": 0, "quality": "valid", "units": "in/h"},
                "dissolved_oxygen": {"value": 1, "quality": "valid", "units": "mg/L"},
                "effluent_ph": {"value": 7, "quality": "valid", "units": "unitless"},
            }
        )


def test_history_window_is_utc_aligned_and_half_open() -> None:
    from_utc, to_utc = parse_window(
        "2025-01-01T00:00:00Z", "2025-01-08T00:00:00+00:00"
    )
    assert to_utc - from_utc == timedelta(hours=168)
    assert from_utc.tzinfo == timezone.utc

    with pytest.raises(ValueError):
        _parse_utc_hour("2025-01-01T00:00:00-05:00")
    with pytest.raises(ValueError):
        _parse_utc_hour("2025-01-01T00:30:00Z")
    with pytest.raises(ValueError):
        _parse_utc_hour("not-a-timestamp")
