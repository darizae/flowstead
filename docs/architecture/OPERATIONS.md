# Flowstead Operations

**Version:** 1.0
**Date:** 2026-11-22

This document describes operational procedures and local development setup.

## 1. Local Development Stack

### Start stack

```bash
just dev
```

This starts PostgreSQL, NATS/JetStream, and the Vite frontend in development mode.

### Stop stack

```bash
just dev-down
```

### Upgrade database

```bash
just db-upgrade
```

### Check current migration version

```bash
just db-current
```

### Import M1 data

```bash
just import-m1-local <manifest> <source_sha> <data>
```

## 2. Backend

### Run API server

```bash
just api-dev
```

### Run forecast CLI

```bash
just forecast-local
```

### Run message worker

```bash
just message-worker
```

### Run unit tests

```bash
just test-backend-unit
```

### Run integration tests

```bash
just test-db-integration
```

### Check backend

```bash
just check-backend
```

### Lint backend

```bash
just lint
```

### Format backend

```bash
just format-backend
```

### Typecheck backend

```bash
just typecheck-backend
```

### Run coverage

```bash
just coverage
```

### Build backend image

```bash
just build-backend-image
```

## 3. Frontend

### Run dev server

```bash
just frontend-dev
```

### Run unit tests

```bash
just test-frontend-unit
```

### Typecheck frontend

```bash
just frontend-typecheck
```

### Build frontend

```bash
just build
```

### Audit frontend

```bash
just audit-frontend
```

## 4. End-to-End

### Run E2E tests (local)

```bash
just test-e2e-local
```

### Build smoke

```bash
just build-smoke
```

### Deploy local

```bash
just test-deploy-local
```

## 5. Hosted

### Build hosted image

```bash
just build-backend-image-host
```

### Verify hosted host

```bash
just verify-hosted-host
```

### Hosted config validate

```bash
just hosted-config-validate
```

### Deploy hosted

```bash
just test-deploy-hosted
```

## 6. Diagnostics

### OCI diagnose

```bash
just oci-diagnose
```

### OCI recover

```bash
just oci-recover
```

## 7. CI Evidence

### Pre-commit hooks

Run `pre-commit install` to enable local checks.

Current hooks:
- Backend Ruff lint
- Backend Ruff formatting
- Frontend lint and formatting
- Documentation links

### Local pre-commit run

```bash
pre-commit run --all-files
```

## 8. References

- `docs/architecture/OPERATIONAL_SETTINGS.md` — configuration contract
- `docs/architecture/MIGRATIONS.md` — migration ownership
- `docs/architecture/PACKAGE_OWNERSHIP.md` — module ownership
- `.pre-commit-config.yaml` — pre-commit configuration
- `.env.example` — configuration template
