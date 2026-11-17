# T-011 — semantically correct PDF Plant report

**Status:** DRAFT — proposed approval (planning-only approval; NO implementation authorization). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
003/004/005 API policy and 008/009 UI data views approved. Owner delegated detailed PDF aesthetics but reserves normal-chat sample review for final acceptance. No public/regulatory/compliance claim.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: Backend Plant/latest/forecast services and authorized SQL data sources, final visual design requirements in `docs/design/UI_UX_BASELINE.md`. Do not use reference prototype sample values as real output.

## Observable result and scope
Add permission-bound on-demand endpoint `GET /api/v1/plants/{id}/report.pdf` (plus a bounded public-report equivalent for the same five validated fictional Plants, without account-specific content), short single-Plant PDF containing Plant identity, generated UTC/local date, four latest readings with value+quality+units, 12h forecast grid/summarized high when available, issuance/model labels, synthetic source identification once, sensible no-forecast/no-data handling. No permit/compliance/guarantee text. Content-Disposition safe, PDF output in memory capped, one authorized Plant per request; no disk/bucket persistence. One concise, polished layout with readable hierarchy and long-name/wrapping/wrong-character tests.



## Dependencies and allowed file closure
Use `reportlab>=4,<5` (after compatibility/license/security audit) in `backend/pyproject.toml` and `backend/uv.lock` via `uv add --project backend`. If alternate PDF library is required, planner approval before installation. Expose downloadable button only for a Plant currently shown with API-authorized state; never client-render PDFs from out-of-scope cached data.

Allowed create/edit paths: `backend/src/flowstead_api/**`, `backend/tests/**`, `backend/pyproject.toml`, `backend/uv.lock`, `frontend/src/**`, `frontend/tests/**`, `justfile`, `README.md`, `docs/design/UI_UX_PARITY_MATRIX.md`. New dependency installation is authorized **only** when this task itself is approved, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `IT-M11-PDF`: signed principal A can download A report from real PostgreSQL; B gets indistinguishable 404; missing/bad auth gets 401.
- `UT-M11-CONTENT`: parse PDF text, assert correct Plant/unit/value/quality/12 forecast targets or explicit unavailability; no invented data.
- `UT-M11-LIMIT`: output cap, safe filenames, long names, no stored file and failure cleanup.
- `UI-M11-PDF`: normal-chat reviewer opens a generated PDF sample, checks hierarchy/readability at 100% zoom; evidence is distinct from extraction test.

## Local verification, gates and stopping condition
Add `just test-report` and run focused backend unit + local PG authorization tests, a real PDF render+download through browser, `uv audit --project backend` after new dependency and final head receipt.

A PDF-text test does not satisfy aesthetic owner review. Record visual gate as BLOCKED until sample approved.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Normal-chat ChatGPT independently reviews; use `waiting_chat` if unavailable. After corrections, rerun checks on the exact final SHA on Mac. No 24-hour soak.
