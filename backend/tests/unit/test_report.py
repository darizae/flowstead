from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from flowstead_api.database import ForecastRead, PlantRow, ReadingRow
from flowstead_api.forecast import ForecastBuild, ForecastPoint
from flowstead_api.report import MAX_REPORT_BYTES, render_report, safe_report_filename


@pytest.fixture
def plant() -> PlantRow:
    return PlantRow(
        "plant-01",
        "Márisma North / Very Long Demonstration Plant",
        "Miami",
        "FL",
        "America/New_York",
        Decimal(25),
        Decimal(-80),
    )


def _forecast(plant: PlantRow) -> ForecastRead:
    issued = datetime(2025, 1, 1, tzinfo=UTC)
    build = ForecastBuild(
        issued_at_utc=issued,
        model_version="seasonal_naive_24h_v1",
        source_revision="synthetic-revision",
        physical_bound_rule="nonnegative_influent_flow",
        points=tuple(
            ForecastPoint(i, issued + timedelta(hours=i), Decimal(100 + i), "stored")
            for i in range(1, 13)
        ),
    )
    return ForecastRead(plant, build)


def test_report_is_pdf_bounded_and_safe_filename(plant: PlantRow) -> None:
    reading = ReadingRow(
        plant.plant_id,
        datetime(2025, 1, 1, tzinfo=UTC),
        (Decimal("12.5"), None, Decimal("2.1"), Decimal("7.2")),
        ("valid", "missing", "invalid", "valid"),
    )
    content = render_report(
        plant, reading, _forecast(plant), generated_at_utc=datetime(2025, 1, 2, tzinfo=UTC)
    )
    assert content.startswith(b"%PDF-")
    assert len(content) <= MAX_REPORT_BYTES
    assert (
        safe_report_filename(plant)
        == "flowstead-marisma-north-very-long-demonstration-plant-plant-01.pdf"
    )
    assert b"/" not in safe_report_filename(plant).encode()


def test_report_handles_no_data_and_unavailable_forecast(plant: PlantRow) -> None:
    content = render_report(
        plant,
        None,
        ForecastRead(
            plant,
            ForecastBuild(
                issued_at_utc=None,
                model_version="seasonal_naive_24h_v1",
                source_revision=None,
                physical_bound_rule="nonnegative_influent_flow",
                points=(),
                unavailable_reason="no_observations",
            ),
        ),
    )
    assert content.startswith(b"%PDF-")


def test_report_rejects_tiny_output_cap(plant: PlantRow) -> None:
    with pytest.raises(ValueError, match="exceeds"):
        render_report(plant, None, None, max_bytes=128)
