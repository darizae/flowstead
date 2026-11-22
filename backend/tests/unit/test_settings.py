from __future__ import annotations

import pytest

from flowstead_api.auth import AuthConfig
from flowstead_api.settings import ApiSettings, ApplicationSettings, WorkerSettings

_AUTH_ENV = {
    "SUPABASE_AUTH_URL": "https://project-ref.supabase.co/auth/v1",
    "SUPABASE_JWT_ISSUER": "https://project-ref.supabase.co/auth/v1",
    "SUPABASE_JWT_AUDIENCE": "authenticated",
}


def test_api_settings_validate_auth_and_keep_database_lazy() -> None:
    settings = ApiSettings.from_env(_AUTH_ENV)

    assert settings.database_url is None
    assert isinstance(settings.auth, AuthConfig)
    assert settings.security.cors_origins == (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )


def test_worker_settings_apply_cli_overrides_and_preserve_defaults() -> None:
    settings = WorkerSettings.from_env(
        {"DATABASE_URL": "postgresql://env", "NATS_URL": "nats://env"},
        database_url=" postgresql://cli ",
        nats_url=" nats://cli ",
    )

    assert settings.database_url == "postgresql://cli"
    assert settings.nats_url == "nats://cli"


def test_application_settings_validate_all_runtime_boundaries() -> None:
    settings = ApplicationSettings.from_env(
        {
            **_AUTH_ENV,
            "DATABASE_URL": "postgresql://runtime",
        }
    )

    assert settings.database.url == settings.messaging.database_url == "postgresql://runtime"
    assert settings.auth.issuer == _AUTH_ENV["SUPABASE_JWT_ISSUER"]


def test_worker_settings_keep_required_database_error() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        WorkerSettings.from_env({})
