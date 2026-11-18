# Flowstead — indexed test plan and traceability contract

**Source of truth for stable case IDs.** This catalog indexes the concrete acceptance cases owned by the numbered task files under docs/planning/tasks/. Case meanings below are excerpted from the actual task specifications; an index is **not proof that a test was implemented or passed**. Preserve every existing case ID. New code/UI tests must reference these IDs; do not renumber or equate a grep match with behavioral coverage.

## How to use this plan

- **Before implementation:** read the assigned task and the matching cases here plus [TEST_DATA_GUIDE.md](TEST_DATA_GUIDE.md). Search actual tests for each exact ID. Classify **COVERED** only after inspecting its asserting test and observed results; otherwise INDEXED/UNCOVERED or BLOCKED with reason. Record specific missing cases, not generic quality gates.
- **Test-first:** write the minimal assertion that fails for missing intended behavior (RED where practical), implement to GREEN, refactor and run focused regressions. Do not fabricate chronology for tasks already merged.
- **Identity:** a pytest asserting test has an exact short docstring **Case: ID** or **Cases: ID1, ID2**; a Vitest/Playwright test has the exact ID in its test title. IDs in helper/comments/fixtures alone do not count. Group cases by shared setup/invariant; one assertion group may cover several IDs when all outcomes are actually asserted.
- **Real boundaries:** PostgreSQL DDL/SQL, NATS JetStream events and durable consumer, FastAPI HTTP security, React browser/IndexedDB lifecycle, export/PDF decoding and visual MapLibre checks must use real local services when the case requires them. A mock-only result is not a PASS for a real integration case.
- **Visible coverage:** each task's receipt maps **case ID → exact asserting test path/title/docstring → outcomes asserted → real/mock boundary → command → result → exact SHA**. Generate a readable Markdown/JSON matrix and **locally inspectable Playwright HTML report** for browser tests. Store only redacted synthetic screenshots; don't commit user tokens, auth states or raw private archives. All indexed but unproved cases remain UNVERIFIED.
- **Test data:** [TEST_DATA_GUIDE.md](TEST_DATA_GUIDE.md) defines own/foreign/absent Plants, public/private, different dataset identities, quality, cache and queue lifecycle dimensions. Keep case IDs stable and test concrete integration boundaries with the smallest deterministic fixtures.

## Indexed task acceptance cases (case definitions, not pass status)

### T-002 — [task source](../planning/tasks/002_local-postgres-schema-import__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `IT-M2-MIGRATE` | migrate up on empty local PG, verify tables/indexes/FKs, rollback or reversible rebuild only in disposable local DB; migrations repeat safely. | UNVERIFIED until asserting test+run checked |
| `IT-M2-IMPORT` | full immutable M1 source at SHA matches manifest row counts/Plant IDs/units/hourly UTC; source commit, seed and exact data checksum saved. | UNVERIFIED until asserting test+run checked |
| `IT-M2-REJECT` | tampered SHA, duplicate hour, unknown quality, non-UTC, wrong units/version, row cap, non-synthetic origin and unsafe paths are rejected; snapshot row counts/digest unchanged after each failure. | UNVERIFIED until asserting test+run checked |
| `IT-M2-IDEMP` | second identical import creates zero duplicates; conflicting same timestamp rejected, not overwritten. | UNVERIFIED until asserting test+run checked |
| `UT-M2-QUALITY` | NULL versus finite flagged invalid survives SQL roundtrip; DST conversion does not alter stored UTC key. | UNVERIFIED until asserting test+run checked |

### T-003 — [task source](../planning/tasks/003_fastapi-read-and-plant-policy__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `UT-M3-CONTRACT` | OpenAPI models validate canonical four channels/units and preserve flagged NULL/invalid. | UNVERIFIED until asserting test+run checked |
| `IT-M3-PLANT` | two local principals with disjoint assigned Plants get disjoint list/map/latest/history results against real PG, never other Plant IDs. | UNVERIFIED until asserting test+run checked |
| `IT-M3-DENY` | missing/bad auth=401 for private routes; forbidden and missing Plant both 404; invalid window/cap=422; malformed SQL-resistant input has no side effect. | UNVERIFIED until asserting test+run checked |
| `IT-M3-BOUND` | SQL query count/index and payload/window caps checked; no unbounded all-Plant query. | UNVERIFIED until asserting test+run checked |
| `IT-M3-PUBLIC` | public list empty until enabled; public handler cannot enumerate operator-restricted Plants. | UNVERIFIED until asserting test+run checked |

### T-004 — [task source](../planning/tasks/004_deterministic-twelve-hour-forecast__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `UT-M4-HORIZON` | exactly 12 ordered hour-aligned UTC targets with no duplicate and correct units/version. | UNVERIFIED until asserting test+run checked |
| `UT-M4-FALLBACK` | 24h valid seasonal input preferred; fallback to last six hours; invalid/missing source rejected; total unavailable is explicit. | UNVERIFIED until asserting test+run checked |
| `IT-M4-ATOMIC` | partial insertion fails atomically; same-key rerun idempotent. | UNVERIFIED until asserting test+run checked |
| `IT-M4-CROSSPLANT` | user assigned Plant A cannot see Plant B forecast; public absent by default. | UNVERIFIED until asserting test+run checked |
| `UT-M4-BACKTEST` | feature inputs always ≤ issuance, held-out observations not accessed as features; metrics count correctly, and no fabricated empirical claim. | UNVERIFIED until asserting test+run checked |

### T-004a — [Alembic baseline task](../planning/tasks/004a_alembic-baseline-adoption__codex-luna-5-6__high.md)

**Reconciled 2026-11-18:** [local T-004a acceptance receipt](evidence/T004A_ACCEPTANCE_2026-11-18.md), on top of merged [PR #7](https://github.com/darizae/flowstead/pull/7) (`78b109c598a7e2a8441ee6cc5ced1ca1525068cb`) and post-merge acceptance commit `3b40ce5f368033dd73f4efc3012923e4a25c99d4`. Outcomes below are reported local results, not tests rerun for this documentation edit. The dependency security audit remains **UNVERIFIED**.

| ID | Intended observable assertion (from approved task) | Evidence status |
|---|---|---|
| `DB-M4A-FRESH` | Disposable PostgreSQL Alembic head has exact historical columns, defaults, identities, parsed index/FK/CHECK definitions and both markers; importer/API regressions run against the real database. | PASS — recorded local acceptance receipt |
| `DB-M4A-STAMP` | Historical SQL-migrated populated database is stamped without rerunning DDL; full immutable M1 rows and forecast receipt hashes, including markers, unchanged. | PASS — recorded local full-M1/forecast preservation |
| `DB-M4A-MISMATCH` | Partial schema, unknown Alembic version, malformed legacy CHECK/index, and a recognized descendant with missing historical table/column or altered same-named constraint/index are rejected without further data or revision changes. | PASS — recorded local acceptance receipt |
| `DB-M4A-REPEAT` | Repeat upgrade no-op; temporary disposable-only new Alembic descendant upgrades, repeats, downgrades and preserves existing data. | PASS — recorded local acceptance receipt |
| `IT-M2-MIGRATE` | Existing migration/import invariant remains; rollback is allowed only against an isolated explicitly disposable local database. | PASS — recorded local acceptance receipt |
| `UT-M4A-DB-LIFECYCLE` | PostgreSQL preflight requires exact configured Compose project/service and canonical checkout/config paths; owned healthy is reused, stopped started, unhealthy restarted once, and foreign/lookalike project/checkouts/ports rejected without mutation. | PASS (suite-level) — asserting unit tests present; unit suite reported passing, not individually enumerated |

### T-005 — [task source](../planning/tasks/005_supabase-auth-verifier-local__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `UT-M5-JWT` | signed valid local JWKS passes; forged/wrong issuer/wrong audience/expired/unsigned/unknown `kid` rejected; rotations and cache expiry proven. | UNVERIFIED until asserting test+run checked |
| `UT-M5-FAIL` | JWKS/unavailable Auth endpoint/timeout fails closed; no secret-bearing logs. | UNVERIFIED until asserting test+run checked |
| `IT-M5-AUTHZ` | real SQL disjoint-Plant tests across list/latest/history/forecast; caller cannot assert Plant assignment. | UNVERIFIED until asserting test+run checked |
| `UT-M5-MODE` | production config rejects test-principal bypass and missing Auth URL/issuer. | UNVERIFIED until asserting test+run checked |

### T-006 — [task source](../planning/tasks/006_backend-contract-docs-hygiene__omp-glm-5-3-flash__default.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `DOC-M2-LINKS` | active Markdown links to files/skills/routes resolve; tracked docs do not point to missing files. | UNVERIFIED until asserting test+run checked |
| `DOC-M2-COMMANDS` | every advertised `just` command exists and its referenced script exists; no fake pass claims. | UNVERIFIED until asserting test+run checked |
| `DOC-M2-STATUS` | sequence status matches accepted PR/commit evidence; historical AWS is not an active requirement. | UNVERIFIED until asserting test+run checked |
| `DOC-M2-DUP` | one current API spec/route per concern; no extra planner docs. | UNVERIFIED until asserting test+run checked |

### T-007 — [task source](../planning/tasks/007_frontend-foundation-and-plants__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `UT-M7-NAV` | list renders only API-returned Plants; click/back and inaccessible direct link handle state correctly. | UNVERIFIED until asserting test+run checked |
| `UT-M7-FAIL` | empty/unauthorized/loading/offline/API error show useful, non-leaking copy and retry; no hardcoded demo data in shipped build. | UNVERIFIED until asserting test+run checked |
| `UI-M7-PARITY` | owner-approved v2 hierarchy/colors/type, 390px + desktop no overflow; keyboard/focus/accessible navigation checked in real browser. | UNVERIFIED until asserting test+run checked |
| `SEC-M7-CLIENT` | server-only keys not in bundle; API URL config is explicit; isolated principal transitions clear in-memory cache. | UNVERIFIED until asserting test+run checked |

### T-008 — [task source](../planning/tasks/008_map-and-history-visualizations__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `UI-M8-MAP` | real tile render and marker selection from API list; forbidden Plant marker absent; attribution visible; internet/WebGL failure renders list fallback. | UNVERIFIED until asserting test+run checked |
| `UT-M8-CHART` | all four charts preserve proper unit, quality flags, 24/72/168h and axis labels; no line joining across missing segments. | UNVERIFIED until asserting test+run checked |
| `UT-M8-DST` | UTC fall-back repeated hours have explicit timezone offset/abbreviation; spring-forward gap not invented; Central/Eastern chosen per Plant. | UNVERIFIED until asserting test+run checked |
| `UI-M8-PARITY` | desktop 1330px and mobile 390px real browser snapshots/actions, keyboard and zoom; matrix evidence PASS/FAIL/UNVERIFIED. | UNVERIFIED until asserting test+run checked |

### T-009 — [task source](../planning/tasks/009_forecast-and-session-ux__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `UT-M9-FORECAST` | exactly 12 future points from API, visible observed/predicted boundary, local/DST axis/gal/h; outage/unavailable/empty handling. | UNVERIFIED until asserting test+run checked |
| `UT-M9-SESSIONS` | logged-out mode, valid invite/login, expiry, logout, forbidden/zero-Plant states; no open-signup flow. | UNVERIFIED until asserting test+run checked |
| `SEC-M9-CACHE` | auth switch clears all private rows/tokens from in-memory stores; unauthorized URL never renders stale previous Plant. | UNVERIFIED until asserting test+run checked |
| `UI-M9-PARITY` | real browser invitation/login/expired/forbidden/logout evidence including keyboard/mobile and owner-approved copy. | UNVERIFIED until asserting test+run checked |

### T-010 — [task source](../planning/tasks/010_bounded-csv-and-png-exports__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `UT-M10-CSV` | header/order/quoting/null quality/source/UTC correct; no formula execution, bounded rows, 12 forecast entries. | UNVERIFIED until asserting test+run checked |
| `UI-M10-PNG` | downloaded real PNG decodes, has both axes labels/units/time meaning at readable resolution for each chart in desktop and mobile sources. | UNVERIFIED until asserting test+run checked |
| `SEC-M10-EXPORT` | denied/logout/expired states disable export and no private stale data persists; if server route is added, foreign Plant returns 404. | UNVERIFIED until asserting test+run checked |
| `UI-M10-PARITY` | actions directly visible as approved, no filler/explanatory audit copy. | UNVERIFIED until asserting test+run checked |

### T-011 — [task source](../planning/tasks/011_authorized-pdf-plant-report__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `IT-M11-PDF` | signed principal A can download A report from real PostgreSQL; B gets indistinguishable 404; missing/bad auth gets 401. | UNVERIFIED until asserting test+run checked |
| `UT-M11-CONTENT` | parse PDF text, assert correct Plant/unit/value/quality/12 forecast targets or explicit unavailability; no invented data. | UNVERIFIED until asserting test+run checked |
| `UT-M11-LIMIT` | output cap, safe filenames, long names, no stored file and failure cleanup. | UNVERIFIED until asserting test+run checked |
| `UI-M11-PDF` | independent reviewer opens a generated PDF sample, checks hierarchy/readability at 100% zoom; evidence is distinct from extraction test. | UNVERIFIED until asserting test+run checked |

### T-012 — [task source](../planning/tasks/012_local-mvp-security-and-parity__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `E2E-M12-PATH` | public view/list/map; user A list/history/12h/download; user B denied A; 401/404 states; logout cache clear and no JS leaks. | UNVERIFIED until asserting test+run checked |
| `E2E-M12-MAP` | real tile/marker/attribution and controlled offline fallback. | UNVERIFIED until asserting test+run checked |
| `E2E-M12-FILES` | PNG axes and PDF visual quality, CSV columns, inspected downloaded file contents. | UNVERIFIED until asserting test+run checked |
| `SEC-M12-RATE` | bounded windows/rows/files, rate limit/timeout/cors constraints, SQL+JWT adversarial tests. | UNVERIFIED until asserting test+run checked |
| `SEC-M12-AUDIT` | `npm audit` and Python locked dependency audit with remediations and unresolved advisory inventory. | UNVERIFIED until asserting test+run checked |
| `UI-M12-ALL` | matrix row evidence for responsive desktop + mobile, zoom, keyboard, loading/missing/expired, intentional deviations owner-signed. | UNVERIFIED until asserting test+run checked |

### T-013 — [task source](../planning/tasks/013_mvp-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `DOC-M13-ACTIVE` | relative links, skill read-set paths, current task links, no historical active instructions. | UNVERIFIED until asserting test+run checked |
| `DOC-M13-CLAIMS` | README reports actual implemented stages and tested commands, no invented public deployment. | UNVERIFIED until asserting test+run checked |
| `DOC-M13-VERSIONS` | exact pinned M1 source/manifest and runtime versions agree with actual lockfiles. | UNVERIFIED until asserting test+run checked |
| `DOC-M13-PARITY` | matrix statuses supported by actual real-browser evidence. | UNVERIFIED until asserting test+run checked |

### T-014 — [task source](../planning/tasks/014_dev-supabase-integration__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `CLOUD-M14-SCOPE` | project ref verified and only authorized app schema objects/data touched; pre-change schema snapshot/backup recorded. | UNVERIFIED until asserting test+run checked |
| `CLOUD-M14-IMPORT` | same M1 digest/row count as local; no real/DHI data. | UNVERIFIED until asserting test+run checked |
| `SEC-M14-AUTH` | actual Supabase signed login token verified; user A/B disjoint Plant policies; public no private data. | UNVERIFIED until asserting test+run checked |
| `SEC-M14-DATAAPI` | no unauthorized Supabase Data API access; grants and RLS or nonexposed schema verified. | UNVERIFIED until asserting test+run checked |
| `OPS-M14-RESTORE` | bounded documented re-seed/rollback/backup procedure tested on disposable local clone, not destructive remote reset. | UNVERIFIED until asserting test+run checked |

### T-015 — [task source](../planning/tasks/015_local-deployment-build-and-recovery__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `OPS-M15-BUILD` | production image and static frontend build locally from locks, no secret in image or bundle. | UNVERIFIED until asserting test+run checked |
| `IT-M15-START` | local container can reach isolated local Postgres with scripted config, run migration, boot API/health, serve bounded requests and shut down. | UNVERIFIED until asserting test+run checked |
| `SEC-M15-CONFIG` | missing secret/auth config fails closed, CORS restricts reviewed origin, no open signup or accidental public SQL endpoint. | UNVERIFIED until asserting test+run checked |
| `OPS-M15-RECOVER` | documented local restore/reseed/rollback is actually exercised on disposable DB copy, with known data checksums. | UNVERIFIED until asserting test+run checked |

### T-016 — [task source](../planning/tasks/016_public-demo-provision-and-deploy__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `CLOUD-M16-RESOURCES` | exact owner/team/project name/tier/region/URL, no accidental paid service or root DNS override. | UNVERIFIED until asserting test+run checked |
| `CLOUD-M16-DATA` | five synthetic Plants only, full source SHA/digest, no private research/DHI data or direct public SQL exposure. | UNVERIFIED until asserting test+run checked |
| `SEC-M16-AUTH` | only invited demo operators on private authenticated endpoints and all five fictional Plants on anonymous read-only public endpoints, cross-Plant HTTP+export negative checks; Auth open signup disabled. | UNVERIFIED until asserting test+run checked |
| `OPS-M16-TLS` | public/frontend/API HTTPS, correct redirects/CORS/host connection mode and health, bounded rate and cold starts. | UNVERIFIED until asserting test+run checked |
| `OPS-M16-ROLLBACK` | previous image/seed snapshot and safe teardown documented, not automatically destructive. | UNVERIFIED until asserting test+run checked |

### T-017 — [task source](../planning/tasks/017_public-demo-verification__codex-luna-5-6__high.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `E2E-M17-PUBLIC` | anonymous sees exactly approved synthetic subset and no private IDs; list/map/history/chart/exports work. | UNVERIFIED until asserting test+run checked |
| `E2E-M17-AUTH` | invite operator restricted to assigned Plants through direct crafted API/CSV/PDF requests; expired/revoked tokens fail. | UNVERIFIED until asserting test+run checked |
| `UI-M17-LIVE` | actual 390px and desktop map/PDF/PNG/axis/keyboard parity; visible attribution and fail states. | UNVERIFIED until asserting test+run checked |
| `OPS-M17-RECOVER` | documented reproducible seed and authorized backup/rollback drill with exact SHAs, no blind destructive DB reset. | UNVERIFIED until asserting test+run checked |
| `OPS-M17-COST` | verified free tier/usage alerts and no unexpected paid service, with owner decision for any exception. | UNVERIFIED until asserting test+run checked |

### T-018 — [task source](../planning/tasks/018_release-docs-and-routing-hygiene__omp-glm-5-3-flash__default.md)

| ID | Intended observable assertion (from task) | Evidence status |
|---|---|---|
| `DOC-M18-RELEASE` | current remote URLs, CLI commands, tested SHA/version correct and all links resolve. | UNVERIFIED until asserting test+run checked |
| `DOC-M18-NOCLAIM` | no unsupported test/deployment/security/compliance claims; README written for actual operator/developer. | UNVERIFIED until asserting test+run checked |
| `DOC-M18-PRIVATE` | no secret/private planner DHI material in repo/docs/output. | UNVERIFIED until asserting test+run checked |
| `DOC-M18-GATE` | active milestone statuses match independent approvals and receipts. | UNVERIFIED until asserting test+run checked |

### T-004a — [Alembic baseline](../planning/tasks/004a_alembic-baseline-adoption__codex-luna-5-6__high.md)

| ID | Intended observable assertion | Evidence status |
|---|---|---|
| `DB-M4A-FRESH` | Clean PostgreSQL Alembic upgrade reproduces approved schema, constraints/indexes and importer/API behavior | UNVERIFIED until tested |
| `DB-M4A-STAMP` | Previously SQL-migrated populated database validates/stamps without replaying old DDL or changing M1+forecast records | UNVERIFIED until tested |
| `DB-M4A-MISMATCH` | Unknown/partially migrated schema safely fails without destructive repair | UNVERIFIED until tested |
| `DB-M4A-REPEAT` | Repeated upgrade is no-op; new local revision safely up/down without data loss | UNVERIFIED until tested |

### T-004b — [JetStream messaging](../planning/tasks/004b_nats-jetstream-message-flow__codex-luna-5-6__high.md)

**Local implementation evidence (2026-11-18, base `f9503c1` plus uncommitted T-004b worktree):** `backend/tests/integration/test_messaging.py` ran against loopback PostgreSQL 16, FastAPI HTTP and the pinned NATS 2.12.15 JetStream image with `DATABASE_URL=postgresql://flowstead:flowstead_local@127.0.0.1:54329/flowstead NATS_URL=nats://127.0.0.1:42229 FLOWSTEAD_ISOLATED_NATS_TEST=1 uv run --project backend pytest -q backend/tests/integration/test_messaging.py`: **3 passed**. The test stopped and restarted the isolated Compose broker, exercised real publication/acknowledgement, duplicate delivery, durable retries and poison termination, and polled exact PostgreSQL state. `uv run --project backend pytest -q backend/tests/unit` reported **62 passed**; the full configured integration directory reported **20 passed, 10 skipped** after this task (skips require the external full-M1 files and are not counted as messaging evidence). `backend/tests/integration/test_migrations.py` reported **16 passed, 1 skipped**, including a fresh 003 schema. `just audit-backend` used pinned `pip-audit 2.10.1` with strict collection against a hash-verified `uv export --locked` of all runtime and development packages in `backend/uv.lock` and reported **No known vulnerabilities found**, including for `nats-py 2.17.0`. Exact-final-SHA review/Mac receipts remain a merge-stage gate.

| ID | Intended observable assertion | Evidence status |
|---|---|---|
| `MSG-M4B-PUBLISH` | Outbox transaction and real JetStream publication retain exact typed event identity; rollback produces no event | PASS — `test_import_events_commit_atomically_and_publish_to_real_jetstream`; command rollback assertion in `test_command_is_authorized_transactional_and_observably_queued` |
| `MSG-M4B-FLOW` | Real worker persists exactly 12 forecast targets and completion event before acknowledging | PASS — `test_real_jetstream_flow_duplicate_outage_poison_and_retry_exhaustion` |
| `MSG-M4B-DUP` | Replay/redelivery/reordering/crash restart do not duplicate issuance or side effects | PASS — same real JetStream test; message-ID republish and post-commit duplicate delivery asserted |
| `MSG-M4B-OUTAGE` | Broker unavailable does not break read API or lose committed outbox; recovery replays safely | PASS — same test; real Compose NATS stop/start with pending SQL and live HTTP read asserted |
| `MSG-M4B-PAUSE` | Controlled worker pause proves queued distinct from completed and bounded resumption | PASS — queued HTTP status asserted before worker; bounded real worker reached terminal state |
| `MSG-M4B-POISON` | Invalid version, Plant or payload dead-lettered/failed safely with no business mutation | PASS — unit schema variants plus real unknown-version termination and five-delivery terminal receipt |
| `MSG-M4B-AUTH` | Private cross-Plant command denied; public read-only cannot queue arbitrary Plant work | PASS — real HTTP/SQL assertion in `test_command_is_authorized_transactional_and_observably_queued` |

### T-007 — [IndexedDB foundation](../planning/tasks/007_frontend-foundation-and-plants__codex-luna-5-6__high.md)

| ID | Intended observable assertion | Evidence status |
|---|---|---|
| `IDB-M7-PREF` | Anonymous/public and per-principal selection preferences survive reload without permission leakage | UNVERIFIED until tested |

### T-009 — [IndexedDB principal isolation](../planning/tasks/009_forecast-and-session-ux__codex-luna-5-6__high.md)

| ID | Intended observable assertion | Evidence status |
|---|---|---|
| `IDB-M9-ISOLATE` | IndexedDB private namespaces clear on signout, expiry, switch and revocation; other principal cannot render stale data | UNVERIFIED until tested |
| `IDB-M9-BOUNDS` | TTL/quota/schema-corruption/eviction and offline behavior are bounded, deterministic and fail safely | UNVERIFIED until tested |

### T-012 — [Indexed test visibility](../planning/tasks/012_local-mvp-security-and-parity__codex-luna-5-6__high.md)

| ID | Intended observable assertion | Evidence status |
|---|---|---|
| `E2E-M12-INDEX` | Local Playwright HTML report and indexed Markdown/JSON catalog match exact UI test IDs and real browser outcomes | UNVERIFIED until tested |

**Inventory:** 91 distinct indexed cases. Initial evidence status is intentionally **UNVERIFIED**: no Mac case-by-case test scan was run in this document-authoring step. Any claimed pass must be substantiated in the actual test implementation and execution report.
