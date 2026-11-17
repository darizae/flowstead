# T-002 — local PostgreSQL schema, reproducible M1 importer

**Status:** WAITING — M1 receipt and local preflight; M1 release gate open (bounded local task may run when ordered prerequisites and OMP readiness are verified; external operations remain separately gated). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
M1 `darizae/flowstead-sim` task 003 must be independently reviewed, merged and local generator/schema contract recorded by immutable full SHA plus manifest checksum; **no tag/public package is presumed**. This is an explicitly proposed source-at-SHA/local-data integration method, not an app package dependency. Owner must approve local M2 scope; Docker/Compose must pass on the Mac. Check `flowstead-sim` M0 tests have not regressed. Never execute against Supabase here.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `flowstead-sim/src/flowstead_sim/generator.py`, `__main__.py`, `tests/test_generator.py` **at the recorded immutable M1 commit**; actual M1 `manifest.json` and `telemetry.csv` in a Git-ignored local directory; approved schema and units in the app contract.

## Observable result and scope
Provide local Docker PostgreSQL, versioned migration/rollback path, validated CSV+manifest import, pinned source provenance, and repeatable isolated database tests. All five fictional Plants approved for future anonymous read-only synthetic visibility, but never activate public deployment from this importer. Five fictional Plants × 8,760 UTC hours, up to 43,800 wide rows (175,200 values) for M1. Do not ship generated CSV in Git. Use one SQL schema that can later run unchanged on the hosted PostgreSQL project.

Define in non-exposed `app` schema: `plants` (`plant_id` text PK, name, city/state, IANA timezone, fabricated latitude/longitude, hydraulic capacity **gal/h**, `public_demo` boolean default false, explicitly set true only for the five manifest-verified fictional M1 Plants during approved local import; never for arbitrary IDs); `hourly_readings` (PK `(plant_id, timestamp_utc timestamptz)`, one numeric/quality pair for each four canonical channels, source batch FK); `ingest_batches` (unique content SHA-256, schema/generator versions, source SHA, seed, manifest digest, time); `operator_plant_access` (subject id text + plant FK PK; never populated from editable user metadata); `forecast_issuances` and `forecast_hours` (issued UTC and unique target UTC, 12 values later). Set sensible bounded time/plant indexes and strict constraints: `missing` implies SQL NULL; valid/invalid imply finite numeric, quality vocabulary only; `invalid` numeric is never automatically corrected. Plant display names/coordinates/timezone are deterministic fictional app-owned seed metadata keyed by generator `plant_id`, cross-validated with any M1 Plant metadata. Verify `America/New_York` and `America/Chicago` as required by each fictional location.

`import-m1 --manifest <path> --source-sha <40-char SHA>` must validate schema version and manifest file SHA/size, exact column names/units, provenance `synthetic`/not observed, allowed IDs, UTC aligned hourly timestamps, no duplicate keys, strictly bounded file/rows/bytes and no cross-file path traversal; stream/parse defensively. First import atomic, repeated identical digest no-op, incompatible re-import rejected unless an explicitly authorized local reset is invoked. A failed row rolls back the transaction. **Never** infer the version from mutable `main` or publish a library. The operator supplies immutable SHA and generated data path via ignored local inputs.

## Dependencies and allowed file closure
Introduce `backend/pyproject.toml` and `backend/uv.lock` with supported patched FastAPI-ready Python baseline (Python `>=3.11,<3.14` unless demonstrated compatible with newer), `SQLAlchemy>=2,<3`, `alembic>=1,<2`, `psycopg[binary]>=3,<4`, `pydantic>=2,<3`, `pytest>=8,<10`, `ruff>=0.14,<1`, plus required build/test tools, using `uv add --project backend` / `uv lock --project backend`. Keep schema migration and import logic application-owned; no DHI, AWS, object storage, network services or new Git repositories. Do a real registry-backed local dependency audit via available supported `uv audit` (check CLI version) or `pip-audit` on exported locked deps; missing registry means UNVERIFIED.

Allowed create/edit paths: `backend/**`, `migrations/**` (if used instead of backend migrations), `tests/**` local DB tests, `compose.yml`, `justfile`, `README.md`, `.env.example`, `.gitignore`, and **only** the task-specific route/docs if required by changed commands. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `IT-M2-MIGRATE`: migrate up on empty local PG, verify tables/indexes/FKs, rollback or reversible rebuild only in disposable local DB; migrations repeat safely.
- `IT-M2-IMPORT`: full immutable M1 source at SHA matches manifest row counts/Plant IDs/units/hourly UTC; source commit, seed and exact data checksum saved.
- `IT-M2-REJECT`: tampered SHA, duplicate hour, unknown quality, non-UTC, wrong units/version, row cap, non-synthetic origin and unsafe paths are rejected; snapshot row counts/digest unchanged after each failure.
- `IT-M2-IDEMP`: second identical import creates zero duplicates; conflicting same timestamp rejected, not overwritten.
- `UT-M2-QUALITY`: NULL versus finite flagged invalid survives SQL roundtrip; DST conversion does not alter stored UTC key.

## Local verification, gates and stopping condition
Implement `just db-up`, `just db-down` (only local compose), `just migrate-local`, `just import-m1-local` (explicit input and SHA; never a default), `just check-backend`, `just test-backend-unit`, `just test-db-integration`, `just audit-backend` and `just docs-check` only when each underlying command exists. Fast loop: `uv run --project backend pytest -q backend/tests/unit`; integration: `docker compose up -d db && uv run --project backend pytest -q backend/tests/integration`; audit: `uv audit --project backend` after checking supported syntax. No cloud requests from `just check`.

Completion requires real local PostgreSQL tests, exact M1 source SHA/digest receipt, dependency audit status, and accepted ChatGPT review. If M1 row/schema/metadata layout is incompatible, stop for planner rather than guessing/copying generator source.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Independent distinct-agent review at exact PR head is required; until OMP unattended-review acceptance passes, leave `review_ready` blocked. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
