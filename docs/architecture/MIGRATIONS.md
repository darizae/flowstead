# Flowstead Migrations

**Version:** 1.0
**Date:** 2026-11-22
**Owner:** Backend

This document defines the migration ownership and artifact policy.

## 1. Active Migration System

**Source of truth:** `backend/migrations/alembic/`

- **Directory:** `backend/migrations/alembic/`
- **Command:** `just db-upgrade` / `just db-current`
- **Entry point:** `backend/migrate.py`
- **Ownership:** Backend

Alembic manages all forward migrations. Revision files live in `versions/`. The `env.py` configures connection and autogenerate behavior.

## 2. Historical SQL Artifacts

**Preserved for provenance:** both `migrations/` at repository root and `backend/migrations/` (legacy SQL snapshots)

| File | Purpose | Status |
|------|---------|--------|
| `001_initial.sql` | Original schema (M0) | Immutable evidence |
| `001_initial_down.sql` | Original down migration | Immutable evidence |
| `backend/migrations/002_forecast_metadata.sql` | Forecast metadata (M1) | Historical evidence |
| `backend/migrations/002_forecast_metadata_down.sql` | Forecast metadata down | Historical evidence |

**Policy:** Do not modify, rename, or delete. These are historical proof that the M1 schema aligns with the current Alembic baseline. The importer validates the **pinned manifest and CSV**, not historical migration SQL files.

## 3. Immutable M1 Contract

**Pinned source:** Commit `ad5c94d1f46e79312a99cb9721f38700f24fdf6b`
**Manifest:** `m1.v1`
**Seed:** `20250101`
**Canonical telemetry SHA-256:** `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`

The importer validates CSV checksum, size, and row count against the supplied manifest before an atomic import. The caller must independently confirm that the manifest's telemetry checksum matches the canonical digest above; the importer does not pin it.

## 4. Migrations and Architecture

- **Domain:** The schema (tables, constraints, indexes) is owned by the domain layer.
- **Application:** The `backend/migrate.py` wrapper and CLI recipes are owned by the application layer.
- **Infrastructure:** The actual PostgreSQL connection and Alembic execution are infrastructure.

Alembic revisions are schema-only operations; schema inspection is in `flowstead_api.infrastructure.migrations.safety`, and upgrade/rollback execution is in `flowstead_api.infrastructure.migrations.executor`. The `backend.migrate` module preserves the historical CLI and test entry points.
