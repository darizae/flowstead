# T-016 — provision isolated synthetic demo and deploy public services

**Status:** DRAFT — the hosted-release gate/external approvals REQUIRED (planning-only approval; NO implementation authorization). **Repository:** `darizae/flowstead`, private `main`. **Source planning baseline checked:** `43df18c5b88aba189a9b794872a1d6f8aeb60549` on 2026-11-17; verify fresh `main` at dispatch. No task may run solely because this file exists.

## Preconditions and order
015 local deploy evidence accepted and 014 hosted Auth/data security evidence reviewed; owner must explicitly approve all hosted resources: actual Python API/worker and **durable NATS/JetStream broker** host and Free plan/eligibility, Vercel project/team, exact `flowstead-demo` project creation region/Free quota, Auth settings/invite count, synthetic M1 digest, both subdomains and DNS edits, permitted traffic/cost limit and deploy/release. `flowstead-demo` is **not yet created**. Confirm owner has 2-project Free quota when executing; no hidden spend or payment method work.

## Initial read set
Root `AGENTS.md`, `docs/planning/HANDOFF_SEQUENCE.md`, this one task, `docs/planning/IMPLEMENTATION_SPEC.md`, root `justfile` when commands are used, `.agents/skills/engineering-quality/SKILL.md`; then only the owning paths and tests named below. No other task files or private planner records.

Owning context: `docs/deployment/LOCAL_AND_RECOVERY.md`, container/build, reviewed migration, env templates, live provider docs/limits and explicit owner-signed external action envelope; read-only current Vercel team/domain and Supabase project inventory first.

## Observable result and scope
With separate exact authorization, create `flowstead-demo` in approved Supabase org/region; migrate/reseed synthetic-only 5-Plant data from pinned checksum; configure invite-only Auth and assigned Plant grants; deploy React static to a **new** Vercel project under approved existing team, deploy FastAPI **plus a compatible NATS/JetStream broker and bounded forecast worker** to explicitly approved, cost-compatible hosting (Render Free is an API-host candidate only; durable broker/worker suitability is separately verified), ensure API uses hosted Supabase PostgreSQL direct/pooler based on host IP support, deploy secret values only through host secret manager, safe CORS/redirect allowlists and TLS. Enable bounded anonymous read-only visibility for exactly all five manifest-verified fictional M1 Plants as approved by owner; rate limits, export caps, read-only behavior. Attach only approved `flowstead.darizae.dev`/`api.flowstead.darizae.dev` after direct owner consent; never modify personal website/root domain. Prepare rollback and no-charge pause/teardown procedure. No paid upgrades, AWS, buckets or automatic service cloning.



## Dependencies and allowed file closure
Provider-specific config/pin is selected by ChatGPT/owner **before dispatch** and inserted into this task, not invented by worker. A missing exact provider/cost/visibility approval makes this BLOCKED. SQL migration and frontend dependencies remain pinned; provider CLI/install/config changes allowed only in task owning paths and accompanying locks/build settings. External actions beyond named resources remain forbidden.

Allowed create/edit paths: `docs/deployment/**`, `backend/**` deployment-only configuration, `frontend/**` deployment-only configuration, `.env.example`, root `justfile` only when an explicit reviewed deploy recipe is necessary, `README.md` after real state confirmed. New dependency installation is authorized **only** when this task itself is approved, using the declared owning manifest and package manager to produce the lockfile. Do not make unrelated repository or service changes. Recheck real manifests/lockfiles and tool availability in the checked-out revision immediately before dispatch.

Hosted verification must exercise the broker/consumer and real Alembic head as well as FastAPI, auth and browser state; localhost NATS success does not authorize external service creation. Use indexed plan/data guide and exact Case IDs.

## Test-first acceptance
- `CLOUD-M16-RESOURCES`: exact owner/team/project name/tier/region/URL, no accidental paid service or root DNS override.
- `CLOUD-M16-DATA`: five synthetic Plants only, full source SHA/digest, no private research/DHI data or direct public SQL exposure.
- `SEC-M16-AUTH`: only invited demo operators on private authenticated endpoints and all five fictional Plants on anonymous read-only public endpoints, cross-Plant HTTP+export negative checks; Auth open signup disabled.
- `OPS-M16-TLS`: public/frontend/API HTTPS, correct redirects/CORS/host connection mode and health, bounded rate and cold starts.
- `OPS-M16-ROLLBACK`: previous image/seed snapshot and safe teardown documented, not automatically destructive.

## Local verification, gates and stopping condition
Before first write show owner exact resource inventory including the **durable NATS broker and worker**, free-tier terms, restart/persistence constraints, cost exposure and approved action list; if no suitable provider is authorized, remain local rather than deploy a broken partial queue. After approval, perform narrow deploy/migration and immediately run minimal hosted smoke only; do not launch broad soak. Report each external resource URL/name and redacted checks (never secrets).

Stop without cost/spend, DNS, Supabase project creation, invitations or public exposure consent. If free hosting is unavailable, BLOCK and return choice to ChatGPT; never silently switch to paid.



## Git / review receipt
Work only on a short-lived branch from the verified current `main` HEAD and one draft PR. Record changed files, current base/head SHAs, exact local command output, receipt and unresolved gates. Do not push secrets, force-push protected history, merge, tag, spend or alter cloud state without specific approval. Normal-chat ChatGPT independently reviews; use `waiting_chat` if unavailable. After corrections, rerun checks on the exact final SHA on Mac. No 24-hour soak.
