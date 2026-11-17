# T-015 — local production build, host-neutral deployment config and recovery

**Status:** WAITING — local-only (bounded local scope approved; OMP handles ordinary execution setup). **Repository:** `darizae/flowstead`, private `main`. OMP resolves the current base commit at dispatch. No task may run solely because this file exists.

## Preconditions and order
012–013 accepted, and current backend/frontend runtime/tooling verified. Can run independently of 014 hosted Auth actions. No actual Vercel/Render/Supabase service creation or DNS writes.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: Actual frontend Vite build, FastAPI requirements/lock, Docker Compose and database migration files, existing Vercel team/domain read-only facts from approved shared contract.

## Observable result and scope
Prepare a reproducible production-grade FastAPI container/build (non-root, no secrets baked in, health and readiness, port from environment, graceful SIGTERM), frontend static build configured for an explicit HTTPS API URL, safe environment variable templates, default-deny CORS/auth, local staging-like container test. Document infrastructure interface `DATABASE_URL` server-only, Supabase issuer/JWKS URLs, browser-only publishable key, frontend/backend host separation, exact rollback to previous image/commit, synthetic seed/backup/reseed and cold-start/unavailability messaging. Public DNS aliases proposed `flowstead.darizae.dev` frontend and `api.flowstead.darizae.dev` API, not assigned. Keep Vercel project creation and external Python host undecided until owner reviews provider/cost. Prohibit automatic deploy from a PR and paid upgrades.



## Dependencies and allowed file closure
Prefer standard Python container and existing `uv.lock`/frontend npm lock, no new app service. Add smallest required Dockerfile, `.dockerignore`, host-config templates; choose digest-pinned base image only after checking current supported security release at task time. Dependency audits re-run if build artifacts add packages.

Allowed create/edit paths: `backend/Dockerfile`, `backend/.dockerignore`, `frontend/**` build/env templates, `compose.yml` staging profile if needed, `docs/deployment/LOCAL_AND_RECOVERY.md`, `justfile`, `.env.example`, `README.md`, current Docker configuration. Named task dependencies and their owning lockfiles are within the local task scope once it becomes READY under `HANDOFF_SEQUENCE.md`; unexpected dependencies require explicit planner review, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

## Test-first acceptance
- `OPS-M15-BUILD`: production image and static frontend build locally from locks, no secret in image or bundle.
- `IT-M15-START`: local container can reach isolated local Postgres with scripted config, run migration, boot API/health, serve bounded requests and shut down.
- `SEC-M15-CONFIG`: missing secret/auth config fails closed, CORS restricts reviewed origin, no open signup or accidental public SQL endpoint.
- `OPS-M15-RECOVER`: documented local restore/reseed/rollback is actually exercised on disposable DB copy, with known data checksums.

## Local verification, gates and stopping condition
Add `just build-backend-image`, `just build`, `just test-deploy-local` as real scripts; execute local image/build/smoke and selective audit. No Vercel CLI deploy, DNS, provider signup, cloud Supabase write or remote smoke in this task.

Missing hosting provider approval is **not** a blocker to this local task, only the later 016 public provisioning.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. OMP owns independent PR review and acceptance synchronization as a control-plane follow-up; do not delay this task's implementation waiting for that upgrade. After any correction, rerun required checks on the exact final SHA on Mac. Never auto-merge without a verified independent review and explicit repository policy. No 24-hour soak.
