# ADR 0003 — SQL-enforced Plant scope and immutable M1 data provenance

**Status:** Accepted (pre-existing invariants retained during refactor)

## Context

Flowstead exposes both public synthetic demonstrations and operator-scoped reads. The telemetry fixture originates from a pinned synthetic generator. Refactoring imports, auth or persistence must not change which measurements are authorized or how provenance is verified.

## Decision

Verified identity is established at the HTTP/auth boundary, and private reads are filtered by principal-to-Plant access in SQL. Public demo reads use the approved allowlist intersected with the database's public flag. Treat unauthorized Plant access as not found where the API contract requires it.

Retain M1 source commit `ad5c94d1f46e79312a99cb9721f38700f24fdf6b`, manifest `m1.v1`, seed `20250101`, and canonical telemetry digest `e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e`. Validate source/manifest data before atomic import. Do not silently correct fixture timezones without verifying the pinned source contract.

## Consequences

Authorization and importer changes require explicit regression tests. Browser cache records use principal scope and must be purged/isolated on identity changes. Provenance discrepancies are resolved against the original contract, not geographic intuition.
