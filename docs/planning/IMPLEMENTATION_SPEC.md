# Flowstead application scaffold contract

This private repository is the application-side scaffold authorized by D-033/H-11. It is not an M0 implementation target. Keep the application separate from `darizae/flowstead-sim`, which owns the deterministic synthetic generator and its schema. No M1+ product behavior, UI, hosted infrastructure, cloud service, DHI data, credentials, package publication or deployment is approved in this scaffold.

The initial repository must remain secret-free, use `main`, and expose only a harmless local `just --list` command until a later owner-approved task defines an application contract. Cross-repository integration requires an explicit upstream commit/artifact and a later approved task; an unpushed source commit is not a release.

## Future Supabase access and authentication gate (NOT an M0 task)

The application, not the synthetic generator, will integrate invite-only Supabase Auth and PostgreSQL through a modular provider adapter. The local agent's required project-scoped, read-only OAuth/MCP preflight and server-only secret boundaries are defined at [Supabase development access](../setup/SUPABASE_DEVELOPMENT_ACCESS.md). A real disposable development project, Auth configuration, migration rights or public hosting requires separate owner action authorization; no project exists as of the 2026-11-17 verified connected account check. Do not generate credentials, enable paid services, run migrations or begin Auth/UI implementation under this scaffold contract. Future approved work must enforce per-Plant authorization independently in FastAPI and test forbidden cross-Plant requests and exports.
