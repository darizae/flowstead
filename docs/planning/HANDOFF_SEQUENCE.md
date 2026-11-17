# Flowstead — canonical implementation sequence

**Current OMP handoff policy (owner-directed simplification, 2026-11-17):** The reviewed, numbered local implementation tasks in this sequence form the bounded scope for unattended execution **once their predecessors, actual checkout/command preflight and executor capabilities pass**. Do not request a new owner confirmation for each routine local source/test/docs task. Keep one active implementation task per dependent repository, preserve all technical acceptance criteria, and use the existing OMP queue rather than a second planner queue. M0 is COMPLETE and must never be rerun. Public deployment, hosted writes/migrations, invitations, new resources, DNS, expenses, changes to product scope and destructive operations **still require explicit owner authorization**. Use the current OMP execution behavior, and assign unattended review/status automation to OMP as a follow-up responsibility rather than making it an M1 startup prerequisite. No AWS/S3, object store or 24-hour soak.

## Cross-repository stage and application tasks

| Order | Task / precise file | State (at drafting) | Dependency / stop gate |
| --- | --- | --- | --- |
| 001 | [`flowstead` repository initialization](tasks/001_repository-initialization__omp-glm-5-3-flash__default.md) | COMPLETE — previously verified | existing private main; never rerun |
| S-003 | [`flowstead-sim` M1 annual generator](https://github.com/darizae/flowstead-sim/blob/main/docs/planning/tasks/003_m1-annual-synthetic-generator__codex-luna-5-6__high.md) | NEXT — dispatch via current OMP worker | M0 accepted; M1 exact PR/review/test receipt |
| 002 | [PostgreSQL + pinned M1 import](tasks/002_local-postgres-schema-import__codex-luna-5-6__high.md) | WAITING — M1 accepted; next local importer | S-003 exact reviewed M1 SHA/digest + Mac Docker |
| 003 | [FastAPI read/API Plant policy](tasks/003_fastapi-read-and-plant-policy__codex-luna-5-6__high.md) | WAITING — predecessor acceptance | 002 reviewed and accepted |
| 004 | [12-hour forecast baseline](tasks/004_deterministic-twelve-hour-forecast__codex-luna-5-6__high.md) | WAITING — predecessor acceptance | 003 reviewed + observed SQL |
| 005 | [Local JWT/Auth verifier](tasks/005_supabase-auth-verifier-local__codex-luna-5-6__high.md) | WAITING — predecessor acceptance | 003 real Plant policy |
| 006 | [Backend docs and route hygiene](tasks/006_backend-contract-docs-hygiene__omp-glm-5-3-flash__default.md) | WAITING — prerequisite acceptance | 002–005 merged and checked |
| 007 | [Frontend foundation and Plants](tasks/007_frontend-foundation-and-plants__codex-luna-5-6__high.md) | WAITING — 006; OMP implements H-10 evidence | 006; approved v2 design reference, build missing visual proof during UI work |
| 008 | [Real map + four charts](tasks/008_map-and-history-visualizations__codex-luna-5-6__high.md) | WAITING — frontend; OMP tests map/visuals | 007; verify map/style in task 008 |
| 009 | [Forecast + Auth-state UX](tasks/009_forecast-and-session-ux__codex-luna-5-6__high.md) | WAITING — 005 and 008; real browser acceptance | 008 + 005; approved session storyboard |
| 010 | [CSV/PNG exports](tasks/010_bounded-csv-and-png-exports__codex-luna-5-6__high.md) | WAITING — prior UI/API acceptance | 009 + 005 |
| 011 | [PDF Plant report](tasks/011_authorized-pdf-plant-report__codex-luna-5-6__high.md) | WAITING — prior exports/API acceptance | 010 + 005 + PDF sample review |
| 012 | [Local MVP security and parity](tasks/012_local-mvp-security-and-parity__codex-luna-5-6__high.md) | WAITING — integrated code | 011 + actual browser/security tests; outstanding H-10 evidence is tested here |
| 013 | [MVP Markdown/routing hygiene](tasks/013_mvp-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md) | WAITING — milestone acceptance | 012 acceptance receipts |
| 014 | [`flowstead-dev` hosted migration/Auth smoke](tasks/014_dev-supabase-integration__codex-luna-5-6__high.md) | BLOCKED — exact cloud migration/invitation consent | 013 + exact `flowstead-dev` cloud-write/invite consent |
| 015 | [Local deployment build and recovery](tasks/015_local-deployment-build-and-recovery__codex-luna-5-6__high.md) | WAITING — local MVP acceptance | 013 local acceptance; can precede 014 |
| 016 | [Public-demo provisioning and deployment](tasks/016_public-demo-provision-and-deploy__codex-luna-5-6__high.md) | BLOCKED — H-14/host/Supabase/demo/DNS/cost consent | 014 + 015; owner provider/resource/DNS/cost approval |
| 017 | [Hosted verification and rollback](tasks/017_public-demo-verification__codex-luna-5-6__high.md) | BLOCKED — 016 deployed and owner review | 016 exact deployed version/identities |
| 018 | [Release docs and routing hygiene](tasks/018_release-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md) | WAITING — hosted verification receipt | 017 acceptance |

## Non-executable owner/approval checkpoints

- **G-SIM:** After upstream M1 PR independent review and accepted exact-head Mac tests, record 40-character SHA, generator schema version, seed, manifest/data SHA-256 and a reproducible local `flowstead-sim` invocation. This is a **source-at-immutable-SHA** data integration, **not** a published wheel/tag. An actual release/tag is a separate permission if later desired.
- **H-10 (PARTIAL):** Owner approved the v2-derived invite/signed-out/no-Plants/forbidden/expired/logout session-state storyboard on 2026-11-17. Real connected-browser Florida tiles/marker interaction, openable sample PDF and owner-reviewed repo-accessible visual references remain unverified. The v2 direction is approved. **Do not block local UI coding on missing visual evidence**: assign OMP to produce actual map/PDF/browser artifacts within tasks 007–012, compare them with approved direction, and preserve owner acceptance for final public presentation only. Agents cannot self-declare untested UI parity.
- **G-PUBLIC (DECIDED):** Owner approved **all five fictional M1 Plants** for bounded anonymous read-only synthetic APIs/UI/exports on 2026-11-17. The application can retain database default-deny until verified M1 import; seed only the five validated generator Plant IDs as public. Public release remains H-14 BLOCKED. Private assigned-Plant endpoints, account data and private session caches still require independent per-account server authorization.
- **G-DEV:** A separate exact approval for any writes in existing `flowstead-dev` ref `jryvzjwsrxctjeawnkqo`, and optional actual invitation to owner-named demo users. Mac OAuth reported but not proven. No credentials in Markdown.
- **H-14:** Separate exact owner approvals for creating `flowstead-demo`, chosen Free Python host (Render Free only a candidate), new Vercel project and optional approved subdomains, Auth settings/invites, DNS, cost and public exposure. Local task 015 does not require these.
- **G-REVIEW:** OMP owns the end-to-end review and status follow-up. The executor must implement independent source review, bounded correction, exact-final-SHA tests, policy-authorized merge and source-of-truth status updates as part of its own follow-up task. **Do not make completing that improvement a prerequisite for dispatching M1 or other eligible local coding tasks**: start through the existing working queue now; the current review step may remain pending while the control-plane improvement is implemented. No agent may mark an unreviewed PR as merged.

## Completion rules

An existing bounded **local** task is eligible when its actual predecessor is accepted. **OMP owns** the ordinary checkout/tool/test setup and remediation inside that task; do not send it back to the owner for predictable implementation work. Dispatch the next eligible local task through the existing queue with its exact file path and current base commit. A static task filename/status or a free-form Issue is not evidence of completion. Keep review, exact-final-SHA tests, merge and approved status reconciliation as distinct gates. For hosted, public, secret, cost or architecture-changing tasks, obtain the separate explicit owner approval named above. Milestone Markdown/routing hygiene remains required (006, 013, 018). No shadow planning queue; this sequence and [`IMPLEMENTATION_SPEC.md`](IMPLEMENTATION_SPEC.md) remain authoritative.

## Accepted Flowstead Sim source receipt

<!-- flowstead-status-sync source-ad5c94d1f46e79312a99cb9721f38700f24fdf6b -->
- Source commit: `ad5c94d1f46e79312a99cb9721f38700f24fdf6b`
- Schema: `m1.v1`
- Seed: `20250101`
- Manifest file checksums: `{"telemetry.csv":"e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e"}`
- Reproduction: `PYTHONPATH=src python3 -m flowstead_sim --profile m1 --seed 20250101 --output-dir generated-m1-12`
- Provenance: bounded local synthetic data; no cloud, AWS/S3 or observed-facility source.
