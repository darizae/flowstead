# T-002 — local PostgreSQL schema and pinned synthetic-data importer

**Repository:** `darizae/flowstead` (application). **Status:** PREPARED, NOT QUEUED. Local-only M2 task to release after the approved generator version/commit from `flowstead-sim` is available and its interface is pinned. **Preferred implementation model:** `openai-codex/gpt-5.6-luna` at High; approved SAIA assistance allowed for coding/testing but not PR review.

## Preconditions and initial read set

Inspect this repository's `AGENTS.md`, `docs/planning/IMPLEMENTATION_SPEC.md`, `docs/planning/HANDOFF_SEQUENCE.md`, root `justfile`, existing manifests and checked-in source tree. Read the **exact immutable** `flowstead-sim` schema, manifest and version/commit supplied in the task. Verify Docker/Compose and Python/Postgres tools and current stable security-supported dependency versions; do not guess installed packages. This task does not create a hosted Supabase project, access `flowstead-dev` with write credentials, implement frontend/Auth, or deploy.

## Implementable outcome

Build a minimal locally runnable PostgreSQL schema (versioned migrations), deterministic importer for only validated pinned independent synthetic generator CSV/manifest, bounded read model/query API foundation and local integration tests. Canonical tables/keys: fictional Plants, UTC hour readings for all four defined units and `valid|missing|invalid` quality, generator/source provenance, optional Plant assignment structures reserved for future real auth, and forecast issuance+12 hourly values (if included now, only as schema, not a forecast model). Unique Plant/hour key; foreign keys and sensible indexes for latest/history; no duplication of unbounded archives or cloud object-store adapters.

Importer rejects unknown schema version, broken SHA-256, duplicate Plant/hour, malformed timezone/units, invalid quality vocabulary, ambiguous missing-value treatment and any non-synthetic/DHI-derived source. Repeating import is idempotent and transaction-safe; test a failed import leaves SQL unchanged. Seed/rebuild operations must be explicit local commands with safe row/size limits, not automatic remote writes.

Use an app-owned schema/migration/seed directory and root `justfile` recipes for actual local start, test and import actions; document minimal `.env.example` **names only**. Keep `DATABASE_URL` server-only; no production creds, new AWS/S3 adapter, Supabase bucket, cloud migration, Auth account or public endpoint. Maintain a simple provider-swappable Postgres connection boundary so the **same SQL migrations** can later be applied to `flowstead-dev` and separately approved `flowstead-demo` when specific cloud-write tasks are approved.

## Dependency closure and allowed edits

Allowed when actually required: application `backend/` or `src/`, `migrations/`, `tests/`, `integration_tests/`, `docker-compose.yml` or `compose.yml`, `pyproject.toml` and lockfile, root `justfile`, `.env.example`, `.gitignore`, `README.md`. The dispatch must enumerate the precise paths chosen and approve all new dependency/lockfile edits; verify no leftover agent/MCP-executable integrations or unapproved shell commands. No changes to `flowstead-sim` from this task.

## Test-first acceptance

- Deterministic up/down migration on isolated local Docker PostgreSQL and repeatable fixture import from pinned upstream, with schema/row/unit/quality/UTC/provenance fidelity.
- Unique `plant_id,timestamp_utc` and indexed bounded history/latest reads; no arbitrary all-Plant data reads and no N+1 query loops.
- Null missing vs explicitly invalid numeric values preserved; malicious/invalid manifest, checksum and data rejected; rollback and idempotent reimport verified.
- SQL connection, credentials and local logs not exposed to browser or committed Git. No external cloud calls in the default `just check`.
- Fixed unit+real Postgres integration commands run on the Mac, actual model receipts, exact-HEAD test evidence and scope-limited single draft PR.

## GitHub/ChatGPT handoff

OMP implements and executes local gates. ChatGPT **normal chat in existing Loop OMP Project** alone reviews PR code and commits bounded corrections through GitHub. Every changed head gets pinned Mac re-verification; only an owner-authorized final merge closes the task and cleans owned artifacts. If ChatGPT is inactive, mark `waiting_chat` and let unrelated work continue. No 24-hour soak.
