"""Transport schemas (backward-compatible re-export).

The canonical schema definitions now live in ``interfaces.http.schemas``.
This module keeps the historical ``flowstead_api.models`` import path working.
"""

from __future__ import annotations

from .interfaces.http.schemas import (
    DissolvedOxygenMeasurement,
    EffluentPhMeasurement,
    FlowMeasurement,
    ForecastHour,
    ForecastJobResponse,
    ForecastResponse,
    HealthResponse,
    HistoryReading,
    HistoryResponse,
    LatestReading,
    LatestResponse,
    Measurements,
    PlantLinks,
    PlantListResponse,
    PlantLocation,
    PlantSummary,
    Quality,
    RainfallMeasurement,
)

__all__ = [
    "DissolvedOxygenMeasurement",
    "EffluentPhMeasurement",
    "FlowMeasurement",
    "ForecastHour",
    "ForecastJobResponse",
    "ForecastResponse",
    "HealthResponse",
    "HistoryReading",
    "HistoryResponse",
    "LatestReading",
    "LatestResponse",
    "Measurements",
    "PlantLinks",
    "PlantListResponse",
    "PlantLocation",
    "PlantSummary",
    "Quality",
    "RainfallMeasurement",
]
