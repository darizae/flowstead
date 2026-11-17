# Flowstead

Private Flowstead application repository. **M0 and M1 synthetic generator work are merged in [flowstead-sim](https://github.com/darizae/flowstead-sim); this repository has the merged local PostgreSQL schema/M1 importer (task 002, PR #4) and bounded FastAPI read contracts with server-side Plant policy (task 003).** Nothing has been publicly deployed.

## Start here — one implementation source of truth

1. [**Implementation sequence**](docs/planning/HANDOFF_SEQUENCE.md) — canonical cross-repository task order, status, prerequisites, next assignment and gates.
2. [**Application implementation contract**](docs/planning/IMPLEMENTATION_SPEC.md) — binding product, API, data, Auth, UI, deployment and architecture requirements.
3. [**Numbered implementation tasks**](docs/planning/tasks/) — read only the assigned task plus its named sources; the generator has its **own** tasks in [flowstead-sim](https://github.com/darizae/flowstead-sim/blob/main/docs/planning/HANDOFF_SEQUENCE.md).

The private owner decision ledger, research and financial/account approvals remain in `darizae/software-planner-kit/projects/wastewater-saas-exploration/`. The Loop OMP control-plane repository is **an execution queue and dashboard, not another copy of project planning**.

## Approved architecture (2026-11-17, D-040)

**PostgreSQL-only for the MVP, no AWS S3.** Generator data/manifest files are local/reproducible; the FastAPI application imports validated bounded rows to one versioned SQL schema and generates authorized CSV/PNG/PDF downloads on demand. Use local Docker PostgreSQL for development, existing `flowstead-dev` Supabase PostgreSQL for separately approved private integration, and a separate future `flowstead-demo` project for the visitor-facing synthetic demonstration (not yet created). Invite-only Supabase Auth; FastAPI independently enforces per-Plant access.

**Deployment later, by separate explicit authorization:** React frontend on Vercel, FastAPI on independently selected compatible Python hosting, hosted Supabase PostgreSQL behind the backend. No public release, DNS changes, Auth user invites, cloud write/migration or paid tier is authorized merely by this architecture decision. Do not touch the existing `darizae.dev` personal website. AWS account/IAM/S3 creation is **not required**. Optional Supabase Storage may be considered later if a genuine persistent-file requirement arises.

## Local backend commands

The T-002 stack is PostgreSQL-only. Start the disposable Docker database, apply
the versioned migration, then run the bounded importer with explicit ignored
local inputs:

```text
just db-up
just migrate-local
just import-m1-local manifest=/path/to/manifest.json source_sha=ad5c94d1f46e79312a99cb9721f38700f24fdf6b data=/path/to/telemetry.csv
```

The importer validates the `m1.v1` manifest, exact telemetry checksum/size,
units, synthetic provenance, five approved Plant IDs, UTC hourly uniqueness,
and the M1 row/reading/byte caps. It is atomic and repeated identical imports
are no-ops. Generated CSV files and secrets remain local and ignored.

```text
just test-backend-unit
just test-db-integration
just check-backend
just audit-backend
just docs-check
just db-down
```

The read-only API is available locally with `just api-dev`. It exposes health,
public synthetic Plant reads, and authenticated assigned-Plant reads. Private
local requests use `X-Flowstead-Subject`; set `FLOWSTEAD_AUTH_MODE=deny` for
production default-deny behavior. API checks are `just test-api-unit` and
`just test-api-integration`.

Integration tests require `DATABASE_URL`, `FLOWSTEAD_M1_MANIFEST`, and
`FLOWSTEAD_M1_DATA` for the immutable M1 source when running the full import
receipt. No command in this task contacts Supabase, AWS, S3, or another cloud.

**Delivery:** OMP orchestrates the preapproved local backlog and implements/tests on Mac task branches. For the independent PR review it hands off to **ordinary ChatGPT chat in the existing Loop OMP Project via the owner's previously tested browser workflow**; only ChatGPT normal chat reviews, makes bounded GitHub corrections and decides acceptance. OMP/SAIA reviewer output is advisory. Required final-head Mac tests, authorized merge, status sync and source receipts remain separate. M1 Sim PR #5 and importer PR #4 have genuinely merged, but no ChatGPT review is evidenced; do not reimplement them or invent retroactive review. Task 003 is implemented here; its API remains local and public deployment remains separately gated. External/cloud/public actions require their separate approvals; no ChatGPT Work, 24-hour soak or AWS/S3.
