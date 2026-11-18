# T-016 — provision isolated synthetic demo and deploy public services

**Execution:** Start immediately when assigned; planning-status and reviewer approvals are not prerequisites. **Repository:** `darizae/flowstead`, local `main`.

## Technical context
Implement provider configuration and deployment when assigned. Perform real writes only to concrete configured resources with usable credentials and no surprise charge; if target details are absent, finish all local config/tests rather than stop implementation.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `docs/deployment/LOCAL_AND_RECOVERY.md`, container/build, reviewed migration, env templates, live provider docs/limits and explicit owner-signed external action envelope; read-only current Vercel team/domain and Supabase project inventory first.

## Required Marisma frontend usage (binding)

Keep `@darizae/marisma@0.2.0` as the installed component library and theme for Flowstead's reusable frontend controls, as established in T-007a. If this task changes frontend code, reuse Marisma's public exports rather than introducing duplicate substitutes. During relevant frontend build/browser checks, confirm that the actual app still renders Marisma controls and follows the approved Flowstead design; do not alter the separate Marisma repository or expand this task into a UI redesign.

## Observable result and scope
With a verified concrete no-charge target project/organization/region and usable credentials, create `flowstead-demo`; migrate/reseed synthetic-only 5-Plant data from pinned checksum; configure invite-only Auth and assigned Plant grants; deploy React static to a **new** Vercel project under the configured existing team, deploy FastAPI **plus a compatible NATS/JetStream broker and bounded forecast worker** to verified compatible no-charge hosting (Render Free is an API-host candidate only; durable broker/worker suitability is separately verified), ensure API uses hosted Supabase PostgreSQL direct/pooler based on host IP support, deploy secret values only through host secret manager, safe CORS/redirect allowlists and TLS. Enable bounded anonymous read-only visibility for exactly all five manifest-verified fictional M1 Plants as approved by owner; rate limits, export caps, read-only behavior. Attach only explicitly specified `flowstead.darizae.dev`/`api.flowstead.darizae.dev` DNS records; never modify personal website/root domain. Prepare rollback and no-charge pause/teardown procedure. No paid upgrades, AWS, buckets or automatic service cloning.



## Dependencies and allowed file closure
Verify concrete provider configuration during implementation. If live provider credentials/targets are missing, deliver locally testable deployment assets without claiming hosted success. SQL migration and frontend dependencies remain pinned; provider CLI/install/config changes allowed only in task owning paths and accompanying locks/build settings. External actions beyond named resources remain forbidden.

Allowed create/edit paths: `docs/deployment/**`, `backend/**` deployment-only configuration, `frontend/**` deployment-only configuration, `.env.example`, root `justfile` only when an explicit reviewed deploy recipe is necessary, `README.md` after real state confirmed. Any necessary new dependency installation inside the task's named owning paths is included in this assignment; install compatible versions using the package manager, update the lockfile and tests and report findings. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

Hosted verification must exercise the broker/consumer and real Alembic head as well as FastAPI, auth and browser state; localhost NATS success does not authorize external service creation. Use indexed plan/data guide and exact Case IDs.

## Test-first acceptance
- `CLOUD-M16-RESOURCES`: exact owner/team/project name/tier/region/URL, no accidental paid service or root DNS override.
- `CLOUD-M16-DATA`: five synthetic Plants only, full source SHA/digest, no private research/DHI data or direct public SQL exposure.
- `SEC-M16-AUTH`: only invited demo operators on private authenticated endpoints and all five fictional Plants on anonymous read-only public endpoints, cross-Plant HTTP+export negative checks; Auth open signup disabled.
- `OPS-M16-TLS`: public/frontend/API HTTPS, correct redirects/CORS/host connection mode and health, bounded rate and cold starts.
- `OPS-M16-ROLLBACK`: previous image/seed snapshot and safe teardown documented, not automatically destructive.

## Local verification and completion
Before real writes verify resource names, durable NATS broker/worker, persistence, no-charge quotas and API compatibility; if absent, implement local config without deploying an incomplete queue. When configured, perform narrow deploy/migration and immediately run minimal hosted smoke only; do not launch broad soak. Report each external resource URL/name and redacted checks (never secrets).

Never create unexpected charges, invent DNS records or invitation recipients. If free hosting is unavailable, finish local work and report the hosted step as not performed.



## Local completion

Start coding when this task is explicitly assigned. Run focused local tests and repair real failures; never wait for reviewer certification, a READY table entry, earlier merge receipts or permission to install task dependencies. Commit a focused local task branch, **merge it into local `main`**, and report the commit/merge SHA and actual test results. **Do not push**. Real external writes require a concrete configured target and credentials, not planning-status approvals; complete all possible code/tests if a hosted environment is absent. Never invent secret values, paid service plans or successful deployment evidence.
