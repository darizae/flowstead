# Flowstead backend+worker production image.
#
# One image serves both runtime processes, overridden by the Compose command:
#   - API:     uvicorn flowstead_api.main:app --host 0.0.0.0 --port 8000
#   - worker:  python -m flowstead_api.messaging run
# Non-root, no secrets baked in (secret env is injected at runtime only).
#
# Base image index digests are pinned to those verified from the official
# registries on 2026-11-21. Update these intentionally after scanning and
# rerunning the build/worker integration tests (do not float production tags).
# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.9.13@sha256:f07d1bf7b1fb4b983eed2b31320e25a2a76625bdf83d5ff0208fe105d4d8d2f5 AS uv
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS builder
COPY --from=uv /uv /bin/uv
WORKDIR /build
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY importer.py migrate.py __init__.py ./
# Pin the venv to the final /opt/venv path so console-script shebangs (uvicorn,
# alembic) keep resolving after the layer is copied into the runtime image.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLOWSTEAD_BACKEND_ROOT=/app/backend \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# flowstead_api is installed into /opt/venv as a regular Python package.
# Keep the historical backend.* CLIs importable without injecting source
# checkout paths into PYTHONPATH. Alembic revisions must remain available.
COPY __init__.py ./backend/__init__.py
COPY importer.py migrate.py ./backend/
COPY migrations ./backend/migrations/

# Runtime starts as an unprivileged user; no writes to root-owned paths.
RUN addgroup --system --gid 10001 app && \
    adduser --system --uid 10001 --ingroup app --no-create-home app
USER 10001:10001

EXPOSE 8000
# Default = forecast worker; the API service overrides command with uvicorn.
CMD ["python", "-m", "flowstead_api.messaging", "run"]