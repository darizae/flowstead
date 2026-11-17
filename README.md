# Flowstead

Private application scaffold for the approved Flowstead exploration. This repository contains no application implementation yet. Synthetic M0 telemetry is owned by the separate private `darizae/flowstead-sim` repository and is not vendored here.

## Local commands

- `just --list` — show the currently available scaffold commands.

## Future Supabase integration — not yet approved for execution

Owner setup and technical boundaries for a later explicitly approved Supabase development project are described in [Supabase development access](docs/setup/SUPABASE_DEVELOPMENT_ACCESS.md). **No Supabase project, API keys or hosted Auth are required for the current scaffold.** Configure project-scoped agent access only after owner approval; never commit credentials.

## External service readiness (no provisioning permission)

The nonsecret [Vercel, DNS and AWS readiness guide](docs/setup/EXTERNAL_SERVICE_READINESS.md) records the already verified Vercel team/domain, the protected existing personal website, and the restricted S3 integration requirements for a later authorized development task. No AWS account, S3 bucket, hostname record, paid tier or public deployment is created or authorized by this document.
