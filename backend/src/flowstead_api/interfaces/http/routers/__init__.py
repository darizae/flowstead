"""FastAPI route modules: health, plants, and forecast commands."""

from .forecasts import router as forecasts
from .health import router as health
from .plants import router as plants

__all__ = ["forecasts", "health", "plants"]
