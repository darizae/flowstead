# T-011 — semantically correct PDF Plant report

**Execution:** Start when explicitly assigned; no WAITING/READY/approval prerequisite. **Repository:** `darizae/flowstead`, local `main` checkout.

## Existing implementation and technical context
Use the existing FastAPI/SQL models and frontend export controls. Build and inspect the local PDF behavior as assigned rather than waiting for another task's merge receipt.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: **existing** backend Plant/latest/forecast typed models and parameterized SQL, actual `flowstead_api` service boundaries, v2 `downloadReport` button/detail hierarchy, `docs/design/UI_UX_BASELINE.md` and matrix. Do not use reference prototype sample values as real output or copy private reference PDF code.

## Observable result and scope
Add permission-bound on-demand endpoint `GET /api/v1/plants/{id}/report.pdf` (plus a bounded public-report equivalent for the same five validated fictional Plants, without account-specific content), short single-Plant PDF containing Plant identity, generated UTC/local date, four latest readings with value+quality+units, 12h forecast grid/summarized high when available, issuance/model labels, synthetic source identification once, sensible no-forecast/no-data handling. No permit/compliance/guarantee text. Content-Disposition safe, PDF output in memory capped, one authorized Plant per request; no disk/bucket persistence. One concise, polished layout with readable hierarchy and long-name/wrapping/wrong-character tests.



## Dependencies and allowed file closure
Use `reportlab>=4,<5` (after compatibility/license/security audit) in `backend/pyproject.toml` and `backend/uv.lock` via `uv add --project backend`. If alternate PDF library is required, planner approval before installation. Expose downloadable button only for a Plant currently shown with API-authorized state; never client-render PDFs from out-of-scope cached data.

Allowed create/edit paths: `backend/src/flowstead_api/**`, `backend/tests/**`, `backend/pyproject.toml`, `backend/uv.lock`, `frontend/src/**`, `frontend/tests/**`, `frontend/e2e/**`, `frontend/playwright.config.ts` if changed, `justfile`, `README.md`, `docs/design/UI_UX_PARITY_MATRIX.md`, `docs/design/evidence/**` scrubbed synthetic PDF/browser evidence. Necessary package, manifest, lockfile, fixture, command and test updates in the named owning paths are in scope when this task is assigned. Choose supported compatible versions, generate lockfiles with the package manager, audit dependencies and verify locally. Do not request separate permission for predictable dependency setup; keep changes related to this task. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Prototype and Python service-boundary fidelity (binding)

- Keep the PDF action beside the selected Plant heading as in the approved v2 `downloadReport` control. Implement a **thin FastAPI HTTP report route** reusing the **same server-side authorized Plant lookup** and actual typed schemas as latest/history/forecast; a focused `report` rendering/service function owns capped ReportLab layout, exact data formatting and error behavior. Do not bypass the existing access query, create a second PDF-data repository, copy `analysis_b` file-store service or add NATS/async processing. Public report uses only validated five-Plant read-only public scope and no account fields.
- Test-first (where practical) the true `IT-M11-PDF` DB/HTTP authorization for principal A, denied B, absent JWT/public scope, plus `UT-M11-CONTENT/LIMIT` text extraction and size/filename/quality/unavailable cases. Then run actual Playwright **browser download**, **open/render** the generated synthetic PDF at 100% zoom, and inspect Plant name/long-name wrapping, four units, quality flags, 12h horizon and report hierarchy on desktop/mobile. No source-v2 mocked values may appear in the real file.
- Save a scrubbed synthetic example PDF/screenshot and final-SHA verified steps under `docs/design/evidence/` (no private credentials); update the parity matrix's PDF row with **functional PASS vs visual PASS separately**. Real render+readability cannot be replaced by PDF-text assertions or a guessed filename. Owner final public-presentation acceptance remains separate from local developer review.

## Test-first acceptance
- `IT-M11-PDF`: signed principal A can download A report from real PostgreSQL; B gets indistinguishable 404; missing/bad auth gets 401.
- `UT-M11-CONTENT`: parse PDF text, assert correct Plant/unit/value/quality/12 forecast targets or explicit unavailability; no invented data.
- `UT-M11-LIMIT`: output cap, safe filenames, long names, no stored file and failure cleanup.
- `UI-M11-PDF`: independent reviewer opens a generated PDF sample, checks hierarchy/readability at 100% zoom; evidence is distinct from extraction test.

## Local verification and completion
Add `just test-report` and run focused backend unit + local PG authorization tests, **`just test-e2e-local` for actual PDF request/download/open at 1330px and 390px**, `uv audit --project backend` after new dependency and final head receipt.

A PDF-text test does not satisfy visual acceptance. Keep **local PDF visual review PENDING/UNVERIFIED** until an actual generated/opened sample is inspected by independent normal ChatGPT chat in the Loop OMP review, with source and image/PDF evidence. Visual inspection is part of local completion; do not wait for a separate owner message.



## Local completion

Implement immediately when this file is explicitly assigned. Run the stated targeted local tests and fix failures in task-owned source and tests; record observed checks and any environment limitations. Make a focused local task-branch commit and **merge into local `main`** after resolving code/test failures and Git conflicts. Record the resulting SHA and changes. **Do not push**. Independent ChatGPT review, PR receipts, predecessor acceptance, task index statuses and extra owner authorization are **not prerequisites** to starting, committing or locally merging this task. If a real external resource is absent, finish all feasible local work and report what could not be exercised without inventing hosted results.
