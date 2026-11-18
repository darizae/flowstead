# T-015 — local production build, host-neutral deployment config and recovery

**Execution:** Start immediately when assigned; planning-status and reviewer approvals are not prerequisites. **Repository:** `darizae/flowstead`, local `main`.

## Technical context
Build and verify the backend/worker/frontend deployment and recovery configuration locally. A public hosting selection is not necessary for this engineering work.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: Actual frontend Vite build, FastAPI requirements/lock, Docker Compose and database migration files, existing Vercel team/domain read-only facts from approved shared contract.

## Required Marisma frontend usage (binding)

Keep `@darizae/marisma@0.2.0` as the installed component library and theme for Flowstead's reusable frontend controls, as established in T-007a. If this task changes frontend code, reuse Marisma's public exports rather than introducing duplicate substitutes. During relevant frontend build/browser checks, confirm that the actual app still renders Marisma controls and follows the approved Flowstead design; do not alter the separate Marisma repository or expand this task into a UI redesign.

## Observable result and scope
Prepare reproducible production-grade **FastAPI and bounded NATS forecast worker/dispatcher** container/builds (non-root, no secrets baked in, separate liveness/readiness, graceful SIGTERM), frontend static build configured for an explicit HTTPS API URL, safe environment variable templates, default-deny CORS/auth, local staging-like container test with **real PostgreSQL, NATS/JetStream, Alembic upgrade-to-head, outbox replay and worker restart**. Document infrastructure interface `DATABASE_URL` server-only, Supabase issuer/JWKS URLs, browser-only publishable key, frontend/backend host separation, exact rollback to previous image/commit, synthetic seed/backup/reseed and cold-start/unavailability messaging. Public DNS aliases proposed `flowstead.darizae.dev` frontend and `api.flowstead.darizae.dev` API, not assigned. No external host is required for this local build task. Prohibit automatic deploy from a PR and paid upgrades.



## Dependencies and allowed file closure
Prefer standard Python containers and existing backend `uv.lock`/frontend npm lock; the already approved **JetStream broker + bounded worker/dispatcher are required runtime processes**, not optional speculative app microservices. Add smallest required Dockerfile, `.dockerignore`, host-config templates; choose digest-pinned base image only after checking current supported security release at task time. Dependency audits re-run if build artifacts add packages.

Allowed create/edit paths: `backend/Dockerfile`, `backend/.dockerignore`, `frontend/**` build/env templates, `compose.yml` staging profile if needed, `docs/deployment/LOCAL_AND_RECOVERY.md`, `justfile`, `.env.example`, `README.md`, current Docker configuration. Necessary package/manifest/lockfile, test and command updates within the task's named owning paths are included in this assignment. Choose compatible maintained dependencies, use the real package manager to update locks, audit and test. Do not request separate approval for routine setup. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

Use actual indexed plan/data guide with exact asserting Case IDs. Test broker/worker readiness and local restart recovery; a green HTTP health alone does not prove async pipeline.

## Test-first acceptance
- `OPS-M15-BUILD`: production image and static frontend build locally from locks, no secret in image or bundle.
- `IT-M15-START`: local containers can reach isolated local PostgreSQL and JetStream with scripted config, run **real Alembic** upgrade, boot API and forecast consumer, serve bounded requests, process/replay one message and shut down gracefully.
- `SEC-M15-CONFIG`: missing secret/auth config fails closed, CORS restricts reviewed origin, no open signup or accidental public SQL endpoint.
- `OPS-M15-RECOVER`: documented local restore/reseed/rollback is actually exercised on disposable DB copy, with known data checksums.

## Local verification and completion
Add `just build-backend-image`, `just build`, `just test-deploy-local` as real scripts; execute local image/build/smoke and selective audit. No Vercel CLI deploy, DNS, provider signup, cloud Supabase write or remote smoke in this task.

No hosting provider is required to implement and test this local task.



## Local completion

Start coding when this task is explicitly assigned. Run focused local tests and repair real failures; never wait for reviewer certification, a READY table entry, earlier merge receipts or permission to install task dependencies. Commit a focused local task branch, **merge it into local `main`**, and report the commit/merge SHA and actual test results. **Do not push**. Real external writes require a concrete configured target and credentials, not planning-status approvals; complete all possible code/tests if a hosted environment is absent. Never invent secret values, paid service plans or successful deployment evidence.
