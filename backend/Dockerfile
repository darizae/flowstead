# Flowstead backend+worker production image.
#
# One image serves both runtime processes, overridden by the Compose command:
#   - API:     uvicorn flowstead_api.main:app --host 0.0.0.0 --port 8000
#   - worker:  python -m flowstead_api.messaging run
# Non-root, no secrets baked in (secret env is injected at runtime only).
#
# shortcut: base images are tagged, not digest-pinned, so rebuild tooling can
#   pick up security patches; pin digests before any public deployment.
# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.9.13 AS uv
FROM python:3.12-slim AS builder
COPY --from=uv /uv /bin/uv
WORKDIR /build
COPY pyproject.toml uv.lock ./
# Pin the venv to the final /opt/venv path so console-script shebangs (uvicorn,
# alembic) keep resolving after the layer is copied into the runtime image.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/backend/src \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# backend.importer / backend.migrate are imported at runtime (flowstead_api
# references backend.importer), so the backend package must be importable.
COPY __init__.py ./backend/__init__.py
COPY importer.py migrate.py ./backend/
COPY src/flowstead_api ./backend/src/flowstead_api/

# Runtime starts as an unprivileged user; no writes to root-owned paths.
RUN addgroup --system --gid 10001 app && \
    adduser --system --uid 10001 --ingroup app --no-create-home app
USER 10001:10001

EXPOSE 8000
# Default = forecast worker; the API service overrides command with uvicorn.
CMD ["python", "-m", "flowstead_api.messaging", "run"]