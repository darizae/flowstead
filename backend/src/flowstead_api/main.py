"""Flowstead FastAPI application entry point.

The FastAPI app is assembled in ``interfaces.http.app``; this module is the
stable import surface for the running server and the test suite.
"""

from __future__ import annotations

from .interfaces.http.app import app, create_app
from .interfaces.http.mappers import _parse_utc_hour, parse_window

__all__ = ["_parse_utc_hour", "app", "create_app", "parse_window"]
