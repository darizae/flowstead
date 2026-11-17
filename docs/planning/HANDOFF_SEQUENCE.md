# Flowstead — proposed implementation sequence (planning-only PR)

**Owner approved publication of this planning-only PR on 2026-11-17; NO executable task or local implementation has been authorized by that approval.** Existing `main` remains authoritative until this PR is separately reviewed and merged. One assigned task at a time per repository. The control plane may queue only an owner-released task with exact commit and preflight, then pauses for normal-chat ChatGPT PR review (`waiting_chat`) before dependent merges. M0 is DONE; never requeue it. No AWS, S3, object store, 24-hour soak or independently created planning queue.

## Cross-repository stage and application tasks

| Order | Task / precise file | State (at drafting) | Dependency / stop gate |
| --- | --- | --- | --- |
| 001 | [`flowstead` repository initialization](tasks/001_repository-initialization__omp-glm-5-3-flash__default.md) | COMPLETE — previously verified | existing private main; never rerun |
| S-003 | [`flowstead-sim` M1 annual generator](https://github.com/darizae/flowstead-sim/blob/main/docs/planning/tasks/003_m1-annual-synthetic-generator__codex-luna-5-6__high.md) | PREPARED — owner local launch authorization pending | M0 accepted; M1 exact PR/review/test receipt |
| 002 | [PostgreSQL + pinned M1 import](tasks/002_local-postgres-schema-import__codex-luna-5-6__high.md) | PREPARED — M1 and local approval gates | S-003 exact reviewed M1 SHA/digest + Mac Docker |
| 003 | [FastAPI read/API Plant policy](tasks/003_fastapi-read-and-plant-policy__codex-luna-5-6__high.md) | PLANNED — local task launch unapproved | 002 reviewed and accepted |
| 004 | [12-hour forecast baseline](tasks/004_deterministic-twelve-hour-forecast__codex-luna-5-6__high.md) | PLANNED — local task launch unapproved | 003 reviewed + observed SQL |
| 005 | [Local JWT/Auth verifier](tasks/005_supabase-auth-verifier-local__codex-luna-5-6__high.md) | PLANNED — local task launch unapproved | 003 real Plant policy |
| 006 | [Backend docs and route hygiene](tasks/006_backend-contract-docs-hygiene__omp-glm-5-3-flash__default.md) | DRAFT — milestone gate | 002–005 merged and checked |
| 007 | [Frontend foundation and Plants](tasks/007_frontend-foundation-and-plants__codex-luna-5-6__high.md) | BLOCKED — H-10 UI owner acceptance | 006 and H-10 prototype/visual references |
| 008 | [Real map + four charts](tasks/008_map-and-history-visualizations__codex-luna-5-6__high.md) | BLOCKED — H-10 and frontend | 007 + map/style real UI check |
| 009 | [Forecast + Auth-state UX](tasks/009_forecast-and-session-ux__codex-luna-5-6__high.md) | BLOCKED — H-10 real-browser/visual gate and frontend | 008 + 005; session storyboard approved 2026-11-17 |
| 010 | [CSV/PNG exports](tasks/010_bounded-csv-and-png-exports__codex-luna-5-6__high.md) | DRAFT — prior UI/API tasks | 009 + 005 |
| 011 | [PDF Plant report](tasks/011_authorized-pdf-plant-report__codex-luna-5-6__high.md) | DRAFT — prior exports/API tasks | 010 + 005 + PDF sample review |
| 012 | [Local MVP security and parity](tasks/012_local-mvp-security-and-parity__codex-luna-5-6__high.md) | DRAFT — local integrated code and H-10 | 011 + actual browser/security tests |
| 013 | [MVP Markdown/routing hygiene](tasks/013_mvp-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md) | DRAFT — milestone gate | 012 acceptance receipts |
| 014 | [`flowstead-dev` hosted migration/Auth smoke](tasks/014_dev-supabase-integration__codex-luna-5-6__high.md) | BLOCKED — exact cloud migration/invitation consent | 013 + exact `flowstead-dev` cloud-write/invite consent |
| 015 | [Local deployment build and recovery](tasks/015_local-deployment-build-and-recovery__codex-luna-5-6__high.md) | DRAFT — local-only after MVP | 013 local acceptance; can precede 014 |
| 016 | [Public-demo provisioning and deployment](tasks/016_public-demo-provision-and-deploy__codex-luna-5-6__high.md) | BLOCKED — H-14/host/Supabase/demo/DNS/cost consent | 014 + 015; owner provider/resource/DNS/cost approval |
| 017 | [Hosted verification and rollback](tasks/017_public-demo-verification__codex-luna-5-6__high.md) | BLOCKED — 016 deployed and owner review | 016 exact deployed version/identities |
| 018 | [Release docs and routing hygiene](tasks/018_release-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md) | DRAFT — final evidence gate | 017 acceptance |

## Non-executable owner/approval checkpoints

- **G-SIM:** After upstream M1 PR ChatGPT review and accepted exact-head Mac tests, record 40-character SHA, generator schema version, seed, manifest/data SHA-256 and a reproducible local `flowstead-sim` invocation. This is a **source-at-immutable-SHA** data integration, **not** a published wheel/tag. An actual release/tag is a separate permission if later desired.
- **H-10 (PARTIAL):** Owner approved the v2-derived invite/signed-out/no-Plants/forbidden/expired/logout session-state storyboard on 2026-11-17. Real connected-browser Florida tiles/marker interaction, openable sample PDF and owner-reviewed repo-accessible visual references remain unverified. Local UI tasks 007–009 stay BLOCKED until those gates close; do not ask implementers to accept their own design.
- **G-PUBLIC (DECIDED):** Owner approved **all five fictional M1 Plants** for bounded anonymous read-only synthetic APIs/UI/exports on 2026-11-17. The application can retain database default-deny until verified M1 import; seed only the five validated generator Plant IDs as public. Public release remains H-14 BLOCKED. Private assigned-Plant endpoints, account data and private session caches still require independent per-account server authorization.
- **G-DEV:** A separate exact approval for any writes in existing `flowstead-dev` ref `jryvzjwsrxctjeawnkqo`, and optional actual invitation to owner-named demo users. Mac OAuth reported but not proven. No credentials in Markdown.
- **H-14:** Separate exact owner approvals for creating `flowstead-demo`, chosen Free Python host (Render Free only a candidate), new Vercel project and optional approved subdomains, Auth settings/invites, DNS, cost and public exposure. Local task 015 does not require these.
- **G-REVIEW:** Each PR requires normal-chat ChatGPT independent review and exact SHA Mac retest; the controller must show `waiting_chat` rather than self-approve. Authorized merge/cleanup, only then next dependency dispatch.

## Completion rules

The owner-approved planning-only PR is **NOT** approval to queue any task. Before promotion to READY, verify current repo manifests/locks and the named paths, matching model/effort runner config, allowed dependency/manifest/justfile closure, actual local commands, owner gate and exact current base SHA. Status changes follow evidence, not task creation. Each meaningful milestone ends with explicit Markdown/routing hygiene (006, 013, 018). Original approved product scope remains [`IMPLEMENTATION_SPEC.md`](IMPLEMENTATION_SPEC.md); this is the detailed downstream implementation order.
