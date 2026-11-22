"""Validated runtime settings shared by API, worker, and maintenance CLIs."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    url: str

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> DatabaseSettings:
        value = (environ or os.environ).get("DATABASE_URL", "").strip()
        if not value:
            raise RuntimeError("DATABASE_URL is required")
        return cls(value)


@dataclass(frozen=True, slots=True)
class MessagingSettings:
    database_url: str
    nats_url: str = "nats://127.0.0.1:42229"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> MessagingSettings:
        values = environ or os.environ
        database_url = values.get("DATABASE_URL", "").strip()
        if not database_url:
            raise RuntimeError("DATABASE_URL is required")
        return cls(database_url, values.get("NATS_URL", cls.nats_url).strip() or cls.nats_url)


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    database: DatabaseSettings
    messaging: MessagingSettings

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> ApplicationSettings:
        values = environ or os.environ
        database = DatabaseSettings.from_env(values)
        return cls(
            database,
            MessagingSettings(database.url, values.get("NATS_URL", "nats://127.0.0.1:42229")),
        )
