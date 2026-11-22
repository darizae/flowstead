"""FastAPI application assembly: middleware, state, and route registration."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...auth import (
    AuthConfigurationError,
    TokenVerifier,
    UnavailableVerifier,
    verifier_from_env,
)
from ...database import Database
from ...security import ClientRateLimiter, HttpSecurityMiddleware, SecurityConfig
from .routers.forecasts import router as forecasts_router
from .routers.health import router as health_router
from .routers.plants import router as plants_router


def create_app(
    database_url: str | None = None,
    *,
    auth_verifier: TokenVerifier | None = None,
    security_config: SecurityConfig | None = None,
) -> FastAPI:
    app = FastAPI(title="Flowstead API", version="0.1.0")
    security = security_config or SecurityConfig.from_env()
    if security.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(security.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Accept", "Authorization", "Content-Type"],
            expose_headers=[
                "Content-Disposition",
                "Retry-After",
                "X-RateLimit-Remaining",
            ],
            max_age=600,
        )
    app.add_middleware(HttpSecurityMiddleware, config=security)
    app.state.database = Database(database_url)
    # Per-principal+Plant bound on forecast-request submission, independent of
    # the shared per-IP HTTP limiter: an authenticated operator cannot amplify
    # DB/outbox/JetStream work beyond this rate per Plant (SEC19-03).
    forecast_limiter_config = SecurityConfig(
        requests_per_window=security.forecast_requests_per_window,
        window_seconds=security.forecast_window_seconds,
        max_clients=security.max_clients,
        max_body_bytes=security.max_body_bytes,
        max_target_bytes=security.max_target_bytes,
        trusted_proxies=security.trusted_proxies,
        cors_origins=security.cors_origins,
        forecast_requests_per_window=security.forecast_requests_per_window,
        forecast_window_seconds=security.forecast_window_seconds,
    )
    app.state.forecast_limiter = ClientRateLimiter(forecast_limiter_config)
    if auth_verifier is not None:
        app.state.auth_verifier = auth_verifier
        app.state.auth_configuration_error = None
    else:
        try:
            app.state.auth_verifier = verifier_from_env()
            app.state.auth_configuration_error = None
        except AuthConfigurationError as error:
            app.state.auth_verifier = UnavailableVerifier()
            app.state.auth_configuration_error = str(error)

    app.include_router(health_router)
    app.include_router(plants_router)
    app.include_router(forecasts_router)
    return app


app = create_app()
