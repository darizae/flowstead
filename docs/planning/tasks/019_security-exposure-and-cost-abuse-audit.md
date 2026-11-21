# T-019 — Security exposure, abuse, and unexpected-charge audit

**Repository:** darizae/flowstead. **Status:** PARTIAL execution and remediation documented in [2026-11-21 report](../../security/2026-11-21-sec19-report.md) and [T-017 receipt](../../deployment/T017_LIVE_VERIFICATION_2026-11-21.md); complete hosted verification remains OPEN. **Created:** 2026-11-20. **Priority:** security and financial safety before any public launch.

## Goal

Determine whether a public or authenticated attacker could (a) obtain private data, tokens, credentials, or infrastructure access, (b) cause unauthorized database or application changes, (c) exhaust compute, database, storage, messaging, third-party APIs, or network quotas and thereby cause charges or service loss, or (d) persist access after sign-out or revocation. Patch proven vulnerabilities and add regression tests, while preserving the five-Plant *synthetic-only* demo, least privilege, and the existing documented authorization contract.

**Important distinction:** Reading the repository is NOT proof that a deployment exists or is secure. As of the checked-in T-016/OCI evidence, Oracle VM/DNS/Vercel deployment and live Auth/API validation were not confirmed, and OCI provisioning was blocked by a nonzero boot-volume estimate. At execution time, independently inventory actual resources; mark absent or inaccessible production checks **UNVERIFIED/BLOCKED**, never PASS.

## Instructions and guardrails

- Start implementation when assigned; consult root AGENTS.md, the current implementation contract, this task, and only security-relevant source/tests/deployment references. Follow actual code over stale task status. Existing T-012/T-017 security tests are a baseline, not a substitute for adversarial audit.
- Default to local/offline inspection and disposable PostgreSQL/NATS/Supabase-compatible test identities. Do **not** conduct intrusive active scans, traffic floods, brute-force, broad internet enumeration, permission changes, credential rotation, production backup/restore, disabling public access, or paid cloud actions without separately established authorization for the concrete target.
- Do not provision OCI/Vercel/Supabase paid resources, accept a paid trial or upgrade, incur nonzero estimated cost, or assume a budget alert prevents charging. Read-only cost inspection is preferred where available.
- Never include actual bearer tokens, signing keys, private connection strings, passwords, personal identifiers, billing information, tenant identifiers, environment dumps, or reusable presigned download URLs in commits, PRs, logs, reports, screenshots, or chat. Record only **redacted evidence** and locations of private owner-held receipts.
- If a real live credential leak or actively exploitable public-data exposure is confirmed, use a private incident channel; recommend immediate safe containment, provider-side revocation/rotation, and history/artifact cleanup as needed. Do not first publish a detailed exploit, secret, or live sensitive URL in GitHub.

## Threat model / attack surface

- **Anonymous internet client:** API health, public Plant list/latest/history/forecast/report, OpenAPI/docs, proxy edge, domain/TLS, frontend bundles/maps/downloads; bypasses and automated high-volume requests.
- **Signed-in low-privilege or revoked principal:** forged/expired JWTs, cross-Plant and cross-user IDOR, cross-user forecast status, writable endpoints, outbox/JetStream amplification, cache isolation and revocation.
- **Compromised browser or leaked bundle:** Supabase publishable key vs server-only credentials, malicious scripts/dependency supply chain, local/session/IndexedDB exposure, exported PDF/CSV/PNG metadata, insecure mixed-origin configuration.
- **Compromised API/worker/CI host:** database role privileges, outbound network, Docker mount/socket access, stored environment secrets, GitHub Actions tokens, Supabase project access, Oracle tenant and Vercel billing blast radius.
- **Operational accident:** unexpected pay-as-you-go SKU, unbounded queue/retries/uploads, deployed secrets in logs/backup/artifacts, ingress accidentally opened, missing cost alerts, resource persistence after supposed teardown.

## Initial source-backed leads (investigate; NOT verified incidents)

| ID | Source observation | Risk to prove or disprove | Initial priority |
| --- | --- | --- | --- |
| SEC19-01 | deploy/oci/env.hosted.example describes certificate verification but example DATABASE_URL uses sslmode=require. | Verify actual libpq certificate and hostname validation; require verified TLS (typically verify-full with trusted CA), not merely encryption. Inspect actual runtime setting privately. | P1 |
| SEC19-02 | deploy/oci/Caddyfile comments say only public demo reads should be reachable, yet the site has unrestricted reverse_proxy api:8000; backend/main.py also defines private GETs and POST forecast-requests. | Decide intended exposure: public-only proxy allowlist vs intentional authenticated paths. Test denied anonymous/private access, OpenAPI/docs and method/path bypasses. Do not treat existing authenticated routes as a confirmed auth bypass. | P1 |
| SEC19-03 | message_store.enqueue_forecast creates a new forecast_jobs row/outbox event per authorized POST; security.py defaults to 600 requests/60s per client and uses a per-process limiter. | Repeated permitted requests may grow DB/outbox/JetStream/work and exhaust free-tier quotas; measure only in bounded tests and add per-principal/Plant quotas, idempotency/coalescing, retention/cleanup and queue backpressure as warranted. | P1 |
| SEC19-04 | compose.hosted.yml injects DATABASE_URL into API **and worker** through the same host env file; hosted docs describe use of an app-schema database-owner connection. | Prove least-privilege runtime roles, restricted schema operations and separate migration-only credentials; assess compromise blast radius. Do not reveal the connection string. | P1 |
| SEC19-05 | backend/Dockerfile notes base-image tags are not digest-pinned. | Verify image provenance, scan locked dependencies/base layers and decide digest pinning + update cadence before live deployment. | P2 |
| SEC19-06 | The repo includes numerous docs/design/evidence binary ZIP/PDF/PNG artifacts; only current-tree targeted code searches were done. | Perform owner-approved recursive *local* secret/PII scan of text, binaries, Git history, CI artifacts and built frontend output; any match requires private triage, not publication. | P1 review |
| SEC19-07 | security.py checks Content-Length / Transfer-Encoding and forwarded-client IP, but tests must establish behavior behind real Caddy and on streaming/no-Length or malformed requests. | Look for request-bound or rate-limit bypass, spoofed client identity, header trust and multi-instance limiter limitations; do not infer an exploit from code inspection alone. | P2 |
| SEC19-08 | OCI_ALWAYS_FREE.md and HOSTED_DEPLOYMENT.md record a nonzero estimated boot-volume charge and no verified deployed VM, budget or host. | Reconcile today's actual external inventory/billing, domain ownership and live ingress before declaring security or cost posture. Do not conflate old written evidence with current live state. | P0 gating |

**Positive controls to preserve and verify:** asymmetric/JWKS or validated legacy auth, fail-closed private routes, SQL Plant-scoped checks, parameterized queries, public synthetic-only data, restrictive CORS/headers, non-root Docker process, bounded per-client rate limiting, and Compose networking without direct API/NATS host ports. These controls are design/code observations, not a completed penetration test.

## Audit work packages (implement sequentially; produce evidence)

### A. Inventory, architecture, and sensitive assets

1. Establish exact branch/commit SHA, build identifiers and whether a real production host, Supabase project, OCI resource, frontend deployment, DNS record or Caddy endpoint exists. Map public hostname -> TLS proxy -> API -> runtime DB -> NATS/worker -> Auth, and all CI/deploy workflows. Record environment status separately: local, development, demo, production.
2. Inventory secrets and privileges by **name/role only**: DATABASE_URL, Supabase Auth/JWKS/anon vs service-role access, GitHub Actions permissions, SSH keys, Oracle API credentials, Vercel tokens, external map providers, logs, backups and environment files. Confirm no high-privilege key in VITE_ variables or public bundles, public repository history, container images or telemetry.
3. Run bounded local credential scanners (e.g., gitleaks/trufflehog where available), scan entire reachable Git history and generated evidence/build outputs (including embedded archives), with zero secret content written to audit output. Document scanner version, scope, exclusions, redacted match count and private remediation disposition. GitHub code search alone is insufficient.

### B. Authorization, authentication, data isolation

1. Create a direct-request matrix for anonymous, authorized principal A, authorized principal B (disjoint and shared Plant), revoked principal, expired/forged JWT, wrong aud/iss/alg/kid and absent/malformed bearer token. Cover public/private list/latest/history/forecast/PDF, forecast POST and job status with unknown IDs.
2. Confirm every private DB read/write is authorized **server-side** and correct for both Plant and requester. Specifically evaluate whether forecast_job status should be restricted by requested_by in addition to Plant membership. Return uniform non-enumerating errors.
3. Test CORS from unapproved origins, OPTIONS behavior, cross-origin bearer exposure, Supabase sign-in invite policy, token persistence/logging, IndexedDB/user switching, logout/expiry/revocation cleanup, downloadable file caching and CSP against the actual frontend build.
4. Restrict public endpoints to explicitly approved synthetic fields. Compare generated OpenAPI/docs and Caddy routing to the intended public-only/authorized route policy; fail closed on paths and methods not intentionally exposed.

### C. Cost, abuse, denial-of-service and backpressure

1. For each endpoint calculate worst-case work per request: history window, forecast computation, PDF render, DB connections/query time, public download size and forecast job creation. Verify request body size enforcement across Content-Length, chunked/proxy transformations and malformed/slow requests using **small, non-disruptive** cases.
2. Measure a bounded test sequence against a disposable environment to show: per-IP AND per-principal enforcement (prefer shared limiter if scaled), trusted-proxy X-Forwarded-For behavior, effective 429/Retry-After, job dedupe/idempotency, maximum outstanding jobs, FIFO/backpressure, cleanup/retention and JetStream max_msgs/max_bytes/max_deliver.
3. Specify and implement hard resource ceilings: short DB statement/connect timeouts and connection limits, max job count per identity/Plant/time, concurrency controls, bounded outbox/failure growth, report generation limits, storage budgets, and safe failure modes when providers reach free quotas.
4. Model how an attacker might incur costs: OCI shape/storage/egress and public IP, Supabase DB/storage/auth/logs/egress, Vercel function/bandwidth/build usage, external APIs and CI runner minutes. Identify which providers offer real *hard* spend caps; distinguish alerts from automatic spending prevention. No load test on billable services.

### D. Infrastructure, transport, and supply chain

1. Validate TLS certificate name/chain, HSTS placement, DNS records, proxy behavior, restricted SSH, firewall/OCI NSG and host port publication from **authorized vantage points**. Require no public NATS 4222/8222, PostgreSQL 5432/6543, Docker socket or app port 8000; Docker network isolation must match actual Compose project/network.
2. Verify database TLS *hostname validation* and minimum privileges; use one migration/admin role offline and restricted API/worker runtime roles where feasible. Review Supabase RLS/exposed schemas, app role access, backups and restore scope. Never execute destructive migration/restore against demo without explicit approval.
3. Audit Dockerfile image pinning, container capabilities/read-only mounts, host env-file modes, secret redaction, resource limits and outbound egress. Review pinned Python/JS lockfiles with current vulnerability databases (pip-audit, npm audit), Vite sourcemaps, npm scripts and GitHub Actions permissions/dependency trust.
4. Review logs, traces, errors, request/response headers and build artifacts for private tokens/URLs. Add safe alerts for authentication anomalies, 429 spikes, forecast backlog, connection saturation, provider quota thresholds and failed/billable resource creation.

### E. Patch, prove, and operate

For each validated issue, open a focused remediation change with a regression test and reproduction that uses no real secrets or destructive live traffic. Patch highest-risk credential/public-data/charge-amplification problems before unrelated polish. Re-run existing backend auth/security/messaging/integration, hosted-network tests, frontend/unit/e2e and docs checks relevant to changed paths. Require an explicit decision for any breaking public API or deployment change. Provide a recovery/rollback and key-rotation playbook with verified permission boundaries.

## Deliverables

- A redacted dated audit report under docs/security/ containing observed commit, environment inventory, attack surface, method/commands, tool versions, **PASS / FAIL / UNVERIFIED / BLOCKED** results and a prioritized findings register (P0 immediate leak/charge, P1 urgent, P2 normal, P3 hygiene). Include file:line / test evidence, exploit preconditions, impact, verified vs hypothetical status, fix owner and closure criteria.
- A dedicated cost-threat table: each potentially billable product/resource, billing plan, current usage, quotas, threshold/alerts, actual hard caps, cleanup owner and whether $0 eligibility is confirmed. Do not commit billing identifiers.
- Minimal reproducible tests and code/config fixes for verified issues, plus dependency/audit scan outputs that contain no credentials or sensitive personal details.
- A no-leak incident checklist: contain public exposure, rotate/revoke in provider and dependent services, check logs/history/artifacts, invalidate sessions as required, redeploy, verify absence, and notify the owner privately.
- A final security/readiness decision distinguishing **local verified** from **live verified**; list any outstanding acceptance blocker. A plan or mock-only test cannot close a live acceptance gate.

## Required acceptance cases

- **SEC-M19-SECRETS:** full repo/history/build/artifact scan completed without disclosing values; known test keys are clearly identified; verified leaks rotated/remediated privately.
- **SEC-M19-AUTHZ:** anonymous/forged/revoked/cross-Plant/cross-requester direct API tests deny unauthorized data and writes; public result contains only approved synthetic content.
- **SEC-M19-EDGE:** explicit edge allowlist, headers, TLS and DNS, CORS, proxy identity, request-size handling and non-published service ports tested locally and, if actual live target exists and is authorized, verified externally.
- **SEC-M19-JOBS:** repeated forecast submissions are bounded by identity/Plant/time and storage with backpressure/idempotency or documented hard limits; no unbounded DB/outbox growth at normal allowed rates.
- **SEC-M19-RUNTIME:** server secrets never enter frontend artifacts/logs; DB/CI/runtime roles are least privilege; external network and container capabilities are constrained.
- **SEC-M19-SUPPLY:** locked dependency and base-image scan findings triaged; high/critical exploitable items patched or explicitly blocked with rationale.
- **OPS-M19-BILLING:** all real-provider costs/quotas/alerts/free eligibility *observed*, provider by provider; no paid provisioning or tests, and alert-only safeguards are not claimed to be hard caps.
- **OPS-M19-INCIDENT:** reversible remediation/rotation/backup/rollback instructions tested in disposable environments; no production destructive steps.
- **DOC-M19-TRUTH:** findings cite exact actual evidence, pass/fail/unknown status and tested SHA. No declaration of no leaks, zero risk, or $0 costs based solely on source code.

## Allowed changes when task is implemented

Owning paths: backend/src/flowstead_api auth/security/main/database/messaging/message_store and focused tests; frontend/src/lib auth/api/cache and relevant tests; deploy/oci, compose.hosted.yml, backend/Dockerfile, lockfiles, GitHub workflows (if present), scoped deployment/security docs, justfile scripts and new redacted docs/security reports. Preserve synthetic M1 provenance, immutable generator inputs, migrations and Marisma UI contract. Changes outside these paths require an explicit technical dependency. Use existing test recipes where available; install tools only in approved local scope and never publish scan results containing secrets.

**Completion rule:** This task file is only the specification. Audit, fixes, cloud checks and test results remain **NOT RUN** until separately executed. A GitHub documentation commit does not deploy or patch anything.
