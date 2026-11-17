# Flowstead

Private Flowstead application repository. **M0 synthetic generator is completed in [flowstead-sim](https://github.com/darizae/flowstead-sim); this application repository is still a scaffold**, not a deployed or coded app.

## Start here — one implementation source of truth

1. [**Implementation sequence**](docs/planning/HANDOFF_SEQUENCE.md) — canonical cross-repository task order, status, prerequisites, next assignment and gates.
2. [**Application implementation contract**](docs/planning/IMPLEMENTATION_SPEC.md) — binding product, API, data, Auth, UI, deployment and architecture requirements.
3. [**Numbered implementation tasks**](docs/planning/tasks/) — read only the assigned task plus its named sources; the generator has its **own** tasks in [flowstead-sim](https://github.com/darizae/flowstead-sim/blob/main/docs/planning/HANDOFF_SEQUENCE.md).

The private owner decision ledger, research and financial/account approvals remain in `darizae/software-planner-kit/projects/wastewater-saas-exploration/`. The Loop OMP control-plane repository is **an execution queue and dashboard, not another copy of project planning**.

## Approved architecture (2026-11-17, D-040)

**PostgreSQL-only for the MVP, no AWS S3.** Generator data/manifest files are local/reproducible; the FastAPI application imports validated bounded rows to one versioned SQL schema and generates authorized CSV/PNG/PDF downloads on demand. Use local Docker PostgreSQL for development, existing `flowstead-dev` Supabase PostgreSQL for separately approved private integration, and a separate future `flowstead-demo` project for the visitor-facing synthetic demonstration (not yet created). Invite-only Supabase Auth; FastAPI independently enforces per-Plant access.

**Deployment later, by separate explicit authorization:** React frontend on Vercel, FastAPI on independently selected compatible Python hosting, hosted Supabase PostgreSQL behind the backend. No public release, DNS changes, Auth user invites, cloud write/migration or paid tier is authorized merely by this architecture decision. Do not touch the existing `darizae.dev` personal website. AWS account/IAM/S3 creation is **not required**. Optional Supabase Storage may be considered later if a genuine persistent-file requirement arises.

## Local commands

`just --list` shows available recipes. Do not assume there is working application code, a database, Docker stack or a real `just test` recipe until an approved task adds those files. See [Supabase development access](docs/setup/SUPABASE_DEVELOPMENT_ACCESS.md) and [external service readiness](docs/setup/EXTERNAL_SERVICE_READINESS.md) for nonsecret prerequisites.

**Delivery:** The existing ordered local task backlog can be dispatched to OMP as prerequisites pass, without repeated per-task approval. OMP implements and tests on local task branches. A separate independent review and exact-final-SHA Mac verification are required before any policy-authorized merge and automatic status reconciliation. OMP owns unattended review/status synchronization as a follow-up; this improvement does **not** delay starting the next bounded local coding task. Existing review-ready PRs remain pending until legitimately reviewed. External/cloud/public changes remain separate owner approvals. No ChatGPT Work, 24-hour soak or general cloud deployment is implied.
