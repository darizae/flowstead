"""Validated runtime settings shared by API, worker, and maintenance CLIs."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from .infrastructure.auth import AuthConfig
from .security import SecurityConfig

_DEFAULT_NATS_URL = "nats://127.0.0.1:42229"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    url: str

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> DatabaseSettings:
        value = (os.environ if environ is None else environ).get("DATABASE_URL", "").strip()
        if not value:
            raise RuntimeError("DATABASE_URL is required")
        return cls(value)


@dataclass(frozen=True, slots=True)
class MessagingSettings:
    database_url: str
    nats_url: str = _DEFAULT_NATS_URL

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> MessagingSettings:
        values = os.environ if environ is None else environ
        database_url = values.get("DATABASE_URL", "").strip()
        if not database_url:
            raise RuntimeError("DATABASE_URL is required")
        return cls(
            database_url, values.get("NATS_URL", _DEFAULT_NATS_URL).strip() or _DEFAULT_NATS_URL
        )


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """API settings; database remains lazy when no URL was supplied."""

    database_url: str | None
    auth: AuthConfig | None
    security: SecurityConfig

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        database_url: str | None = None,
        auth_required: bool = True,
        security_config: SecurityConfig | None = None,
    ) -> ApiSettings:
        values = dict(os.environ if environ is None else environ)
        configured_database_url = (
            database_url.strip()
            if database_url is not None
            else values.get("DATABASE_URL", "").strip()
        )
        return cls(
            database_url=configured_database_url or None,
            auth=AuthConfig.from_env(values) if auth_required else None,
            security=security_config or SecurityConfig.from_env(values),
        )


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    """Required database and bounded NATS settings for the worker process."""

    database_url: str
    nats_url: str = _DEFAULT_NATS_URL

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        database_url: str | None = None,
        nats_url: str | None = None,
    ) -> WorkerSettings:
        values = os.environ if environ is None else environ
        resolved_database_url = (
            database_url.strip()
            if database_url is not None
            else values.get("DATABASE_URL", "").strip()
        )
        if not resolved_database_url:
            raise RuntimeError("DATABASE_URL is required")
        resolved_nats_url = (
            nats_url if nats_url is not None else values.get("NATS_URL", _DEFAULT_NATS_URL)
        )
        return cls(resolved_database_url, resolved_nats_url.strip() or _DEFAULT_NATS_URL)


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    database: DatabaseSettings
    messaging: MessagingSettings
    auth: AuthConfig
    security: SecurityConfig

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> ApplicationSettings:
        values = os.environ if environ is None else environ
        database = DatabaseSettings.from_env(values)
        return cls(
            database=database,
            messaging=MessagingSettings.from_env(values),
            auth=AuthConfig.from_env(values),
            security=SecurityConfig.from_env(values),
        )
