# Flowstead Operational Settings Contract

**Version:** 1.0
**Date:** 2026-11-22
**Scope:** Local/staging runtime configuration contract

This document is the canonical source for operational settings. Environment variable names and semantics are defined here; all configuration files, compose specs, and deployment manifests must align.

## 1. Servers

### PostgreSQL

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql://flowstead:flowstead_local@127.0.0.1:54329/flowstead` | Connection string for the main database |
| `POSTGRES_DB` | Yes | `flowstead` | Database name |
| `POSTGRES_USER` | Yes | `flowstead` | Database user |
| `POSTGRES_PASSWORD` | Yes | `flowstead_local` | Database password |
| `POSTGRES_PORT` | Yes | `54329` | Local PostgreSQL port |

### NATS / JetStream

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NATS_URL` | Yes | `nats://127.0.0.1:42229` | NATS server URL |
| `NATS_PORT` | Yes | `42229` | NATS client port |
| `NATS_MONITOR_PORT` | Yes | `8229` | NATS monitor port |

## 2. Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLOWSTEAD_AUTH_MODE` | No | `supabase` | Auth mode (`supabase` or `legacy`) |
| `SUPABASE_AUTH_URL` | Yes (if `supabase`) | — | Supabase auth endpoint |
| `SUPABASE_JWT_ISSUER` | Yes (if `supabase`) | — | JWT issuer URL |
| `SUPABASE_JWT_AUDIENCE` | Yes (if `supabase`) | `authenticated` | JWT audience |
| `SUPABASE_JWT_ALGORITHMS` | Yes (if `supabase`) | `ES256,RS256` | Comma-separated JWT algorithms |
| `SUPABASE_AUTH_VERIFICATION_MODE` | Yes (if `supabase`) | `jwks` | JWKS or guarded legacy-auth-endpoint verification |
| `SUPABASE_PUBLISHABLE_KEY` | No | — | Browser-publishable key (identity only) |

**Note:** Server-only secrets must never appear in browser bundles. The frontend build takes only `VITE_*` values.

## 3. HTTP Policy

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLOWSTEAD_CORS_ORIGINS` | No | `http://127.0.0.1:5173,http://localhost:5173` | Allowed CORS origins |
| `FLOWSTEAD_TRUSTED_PROXIES` | No | — | Comma-separated trusted proxy IPs |
| `FLOWSTEAD_RATE_LIMIT_REQUESTS` | Yes | `600` | Global rate limit requests |
| `FLOWSTEAD_RATE_LIMIT_WINDOW_SECONDS` | Yes | `60` | Global rate limit window |
| `FLOWSTEAD_RATE_LIMIT_MAX_CLIENTS` | Yes | `4096` | Max rate-limited clients |
| `FLOWSTEAD_MAX_REQUEST_BODY_BYTES` | Yes | `16384` | Max request body size |
| `FLOWSTEAD_MAX_REQUEST_TARGET_BYTES` | Yes | `8192` | Max request target size |
| `FLOWSTEAD_FORECAST_RATE_LIMIT_REQUESTS` | Yes | `30` | Per-principal+Plant forecast limit |
| `FLOWSTEAD_FORECAST_RATE_LIMIT_WINDOW_SECONDS` | Yes | `60` | Forecast rate window |

## 4. Environment Files

| File | Scope | Versioned | Notes |
|------|-------|-----------|-------|
| `.env.example` | Repository | Yes | Template for local configuration |
| `.env` | Local | No | User-specific overrides (gitignored) |
| `compose.yml` | Local | Yes | Local development stack |
| `compose.hosted.yml` | Deployment | Yes | Hosted/staging stack |

## 5. Validation

The runtime validates required variables at startup. Missing required values fail fast with a clear error. Optional variables use documented defaults.

## 6. References

- `.env.example` — authoritative default values
- `compose.yml` — example local stack configuration
- `docs/setup/DEPLOYMENT_ARCHITECTURE.md` — deployment-specific configuration
