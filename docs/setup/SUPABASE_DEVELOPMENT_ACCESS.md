# Supabase development access — future application integration

**Current read-only verified status (2026-11-17):** Disposable development project `flowstead-dev` EXISTS, project ref `jryvzjwsrxctjeawnkqo`, Free organization, region `eu-west-1`, `ACTIVE_HEALTHY`, no public schema tables yet. **Owner reports** local OMP OAuth/MCP authentication complete; OMP connection is **not independently verified from this repository**. Run OMP `/mcp list` and actual project-scoped `list_tables` with read-only access before claiming setup passes. Do not recreate the project or write migrations without separate task permission.


Status: PLANNED, not authorized for project creation, schema write, hosted Auth or deployment. The application scaffold has no provisioned schema/Auth configuration yet; the development project itself exists and is verified. No cloud service is needed for local M0 synthetic-data work.

## Ownership

This repository owns the FastAPI + React application, PostgreSQL migrations, provider-adapted invite-only Supabase Auth and independently enforced Plant permissions. The independent generator repository (darizae/flowstead-sim) MUST remain free of Supabase dependencies.

The owner-private planner (darizae/software-planner-kit/projects/wastewater-saas-exploration/) retains project-creation and cost decisions, owner browser OAuth/MFA instructions and external-operation approvals; do not duplicate those records here.

## Required agent preflight for a future approved Supabase development task

1. Confirm an owner-approved, disposable Supabase **development** project exists on the Free plan. Obtain its actual project ref/URL/region as nonsecret configuration; do not create projects or paid resources based on this document alone.
2. Verify authenticated **project-scoped MCP** or approved Supabase CLI connectivity. For general inspection, use read-only project-scoped MCP with features limited to database and docs, or equivalent access:
   - Endpoint pattern: https://mcp.supabase.com/mcp?project_ref=ACTUAL_PROJECT_REF&read_only=true&features=database,docs
   - Client OAuth is performed interactively by the owner in their local agent session; do not embed auth tokens, PATs, private keys or database passwords in checked-in MCP configuration.
   - If an MCP config file is kept under .omp/mcp.json, it is ignored by Git. Verify actual active profile and working directory.
3. Verify connection using a real read-only list_tables request; mark it UNVERIFIED if only the configuration file exists. Do not call migration/write tools as part of read-only setup.
4. For an explicitly approved DB schema/migration task, temporarily use a **project-scoped write-enabled** connection or appropriate CLI credentials. Commit migration source to this application repository; verify actual migration state, negative access cases and security advisors; remove/disable write privileges after the task.
5. Treat the Supabase Auth identity as identity only: FastAPI independently validates JWT issuer/audience/signature/expiry and server-side Plant authorizations for every list, history, forecast and export. Public access is synthetic-only and read-only, with bounded query/export/rate/cost caps. No open signup; no operator account invites without specific owner approval.
6. For any table exposed through the Supabase Data API, configure safe GRANTs and RLS on exposed schemas; do not assume auth alone enforces tenant boundaries. Do not base authorization on user-editable user_metadata. Keep application data behind FastAPI unless explicitly approved otherwise.

## Credentials and versioned configuration

- Safe nonsecret: project ref, URL, region, publishable browser API key (only when needed).
- Secret: DB password/connection URI, Supabase secret administrative key if actually required, server-only runtime values and MCP OAuth tokens. Store in approved owner-managed runtime secrets / ignored local priv/, never in tasks, repositories or chat.
- Maintain a typed .env.example with **variable names but no credential values** only in a future approved application task. Project ID/ref is known; no project keys or database password are currently required for the local M0 work.
- Review actual official Supabase API/Auth and release docs before modifying integrations. Test real database boundaries; mocks do not prove permissions.

References:
- https://supabase.com/docs/guides/ai-tools/mcp
- https://supabase.com/docs/guides/getting-started/api-keys
- https://supabase.com/docs/guides/auth/general-configuration
- https://supabase.com/docs/guides/api/securing-your-api

**Stop conditions:** no project, missing owner OAuth/MFA, non-Free quoted cost, account-wide access, production/real data, lack of explicit migration approval, or unsafely configured authorization/secret handling. Escalate to the owner/planner rather than broadening permissions.
