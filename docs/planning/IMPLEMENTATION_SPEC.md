# Flowstead — application implementation contract

**Status:** Approved product scope and architectural choice D-040 (2026-11-17). Application repository is currently an initial scaffold; **no backend/UI implementation is complete**. This is the **single neutral technical contract** for Flowstead application tasks. Executable task order and readiness live in [HANDOFF_SEQUENCE.md](HANDOFF_SEQUENCE.md), not in the control-plane or private owner decision ledger.

## Ownership and execution

- **This repo `darizae/flowstead`:** React/Tailwind web app, FastAPI backend, SQL migrations, data importer, authorization, forecasts, exports, local DB harness, deployment configuration.
- **Upstream `darizae/flowstead-sim`:** independently versioned deterministic synthetic generator, schema and provenance. M0 completed; M1 proposed annual data stage uses its own task files. Pin an immutable tested upstream commit/tag/artifact before importing; never vendor its source or a mutable branch.
- **`darizae/omp-control-plane-e2e`:** owns only queue, Mac worker, dashboard, execution state, test receipts and PR lifecycle. GitHub control Issues reference the exact task file/repo/base SHA; they do not own Flowstead product specs.
- **ChatGPT normal chat in the existing Loop OMP Project:** independent PR review, bounded GitHub corrections, exact-SHA Mac re-verification request, authorized merge; not ChatGPT Work and not OMP self-review. No automatic assumption that chat remains open between jobs.
- Owner-private decisions, market/legal source research, credential/onboarding notes and private reference ZIPs remain in `darizae/software-planner-kit/projects/wastewater-saas-exploration/`. Do not copy them to this implementation repo.

## MVP scope and uniform data contracts

Five **fictional small domestic Florida** Plants are approved for synthetic M1/demo (M0 currently has three Plants × 48 hours). Identical data schema and product features for every Plant, with authorization determining which Plants each operator can access. Every Plant has hourly:
- `influent_flow` — **US gal/h**, mean rate over that hour;
- `rainfall` — **in/h** for hourly interval;
- `dissolved_oxygen` — **mg/L**, one representative hourly sample;
- `effluent_ph` — **unitless**, one representative hourly sample.

Store the unique `(plant_id, timestamp_utc)` hourly key in UTC and render charts in Plant-local IANA timezone with unambiguous DST hour labels. Missing values are **NULL** with quality `missing`, not zeros; `invalid` readings retain their flagged numeric value but are never treated as valid. Preserve synthetic origin, generator version/seed/manifest checksum and source independence; **never import or derive publishable output from DHI WaterBench data or fitted parameters**. Use real map markers with fabricated Plant locations, authorized latest/history views and four correctly labeled charts.

Forecast: for each Plant/issuance, exactly **12 future hourly influent-flow gal/h predictions** with `issued_at`, `target_time`, `predicted_flow`, `model_version`. Start with a baseline such as persistence/seasonal naive, record held-out chronological evaluation, show observed-versus-predicted boundary and meaningful unavailable states. Do not claim real-world predictive accuracy from synthetic tests.

Public demonstration: **all five** validated fictional M1 Plants are owner-approved (2026-11-17) for bounded, anonymous, read-only synthetic Plants/map/history/forecast and permitted on-demand downloads. Apply the server-side public allowlist to exactly those five verified Plant IDs, not user-supplied IDs or private account fields. This is **not** authorization to deploy publicly.

Operators: invite-only Supabase Auth identity; verify JWT and independently enforce per-Plant authorization in FastAPI on **all** Plants lists, map entries, history, forecasts and CSV/PNG/PDF exports. Avoid N+1 fetches, unbounded query windows, cross-Plant data leaks and frontend-only security. For any tables exposed through Supabase's Data API, grant minimally and enable RLS with correct ownership policies; do not use user-editable metadata as authorization. Bounded public synthetic demo is read-only.

UI: React + Tailwind, consider actual compatible released `darizae/marisma` package after validation; use the approved private HTML v2 design as a reference, not as a public source artifact. Real MapLibre/OpenFreeMap map; explicit time and measurement unit axis labels preserved in chart PNGs; downloadable raw CSV and a polished, semantically correct PDF Plant report; invite/expired-session/unauthorized/logged-out states. **H-10 status:** owner approved v2 session-state design direction (invite/sign-in, signed-out, no assigned Plants, forbidden direct URL, expired session, logout) on 2026-11-17. Actual connected-browser map tiles/markers, an openable PDF sample and owner-reviewed repo-accessible reference screenshots remain blocked before local UI implementation task 007; do not infer test success. Active screen/state contract: `docs/design/UI_UX_BASELINE.md`; local UI workers update `docs/design/UI_UX_PARITY_MATRIX.md` with real evidence.

## Storage and environments — approved D-040

**MVP uses PostgreSQL only; no AWS S3, AWS account/IAM, object bucket, cloud archive, storage adapter or persistent PDF/PNG/CSV file store is required.** `flowstead-sim` generates local, reproducible CSV/Parquet + manifests and the app imports validated bounded rows to SQL. The API generates authorized CSV/PNG/PDF **on demand**. Only if an actual large-file persistence requirement emerges should a separately approved task consider **private Supabase Storage**, without making it an MVP prerequisite.

**One versioned SQL schema/migration and deterministic importer**, tested across three isolated environments:
1. **Local:** PostgreSQL in Docker on the Mac for fast/repeatable development and integration tests; no cloud required.
2. **Private development:** verified existing `flowstead-dev` Supabase PostgreSQL project, ref `jryvzjwsrxctjeawnkqo`, `eu-west-1`, `ACTIVE_HEALTHY` on 2026-11-17. Apply migrations / connect writable only under an **explicit task-scoped cloud write authorization**; do not assume Mac OMP's OAuth is active without an actual read-only `list_tables` test.
3. **Public-facing future demo:** a **separate not-yet-created** `flowstead-demo` Supabase project for reproducible synthetic data and limited demo Auth identities, isolated from the unattended worker's development writes. Architecture choice is approved; project creation, schema writes, invitations, hosting, DNS, paid services and public exposure are **separate external-action gates**.

For future deployment: React static frontend on Vercel, FastAPI on a separately selected compatible Python hosting service, and the deployed API connects to **hosted Supabase PostgreSQL** (never the Mac). Choose direct IPv6 connection or IPv4 session pooler from the verified host configuration; use server-only secret `DATABASE_URL`, appropriate connection limits and no privileged credentials in browser output. Do not repoint `darizae.dev` or change existing personal-site DNS. Free/best-effort startup/pauses are accepted; make the data reconstructible with migrations, synthetic seeds, backup/export and re-seed steps.

## Test-first implementation and gates

- Each task must specify the exact upstream SHA/contract, target branch, files/prefixes it may change, dependency/lockfile closure, new required `justfile` recipes, acceptance tests and expected artifact/receipt.
- Local unit tests first; repeatable PostgreSQL integration/negative cross-Plant tests; then local browser/Playwright and export-appearance checks at the appropriate milestone. Security/dependency checks and docs/routing hygiene before a milestone release.
- Never mistake local Git worktrees for OS sandboxing. No arbitrary OMP Issue-supplied shell commands, secret dumps, broad cloud MCP permissions, self-reviewed PRs, unbounded loops, forced history rewrites or cloud deployment from a local coding task.
- Keep the root `justfile` runnable and add only real commands when their dependencies exist. Check current stable runtime/library versions at task dispatch rather than assuming earlier estimates remain current.

## Source-of-truth and approval rule

Read [HANDOFF_SEQUENCE.md](HANDOFF_SEQUENCE.md), then **only the assigned numbered task file**, then this shared contract plus named source files. A row marked PLANNED is not a queued implementation authorization; before dispatch it needs a concrete scoped task, current dependency/runtime preflight and necessary owner approval. **M0 is completed, not to be requeued.** Cloud/write, public deployment, account creation and H-10 visual gate remain explicit. The owner-approved eight-part high-level plan is not itself an executable OMP issue. No 24-hour soak is required.
