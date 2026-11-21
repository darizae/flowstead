#!/usr/bin/env bash
# Flowstead optional Docker deployment on the existing OCI E2 micro (x86_64).
# NATS, worker and API only; proxy requires independent verified TLS/DNS.
# API and worker use different restricted database credentials (SEC19-04).
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."

: "${HOSTED_API_ENV_FILE:=/etc/flowstead/api.env}"
: "${HOSTED_WORKER_ENV_FILE:=/etc/flowstead/worker.env}"
: "${HOSTED_CA_FILE:=/etc/flowstead/supabase-root-2021.crt}"
: "${HOSTED_NATS_AUTH_FILE:=/etc/flowstead/nats-auth.conf}"
: "${HOSTED_IMAGE_TAG:=flowstead-backend:amd64-hosted}"
COMPOSE=(docker compose -f compose.hosted.yml -p flowstead-demo)

if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "ERROR: this release targets the existing x86_64 host" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker unavailable; use the native systemd deployment on the E2 micro" >&2
  exit 1
fi
if [[ "$(realpath "$HOSTED_API_ENV_FILE")" == "$(realpath "$HOSTED_WORKER_ENV_FILE")" ]]; then
  echo "ERROR: API and worker must use distinct secret files" >&2
  exit 1
fi

check_secret_file() {
  local path="$1"
  local role="$2"
  if [[ ! -f "$path" || -L "$path" ]]; then
    echo "ERROR: missing or symlinked runtime secret file for $role" >&2
    exit 1
  fi
  local mode owner
  mode="$(stat -c %a "$path")"
  owner="$(stat -c %U "$path")"
  if [[ "$owner" != root || ( "$mode" != 600 && "$mode" != 640 ) ]]; then
    echo "ERROR: runtime secret file for $role must be root-owned and mode 0600/0640" >&2
    exit 1
  fi
  if grep -Eq '^[[:space:]]*(export[[:space:]]+)?(MIGRATION_DATABASE_URL|SUPABASE_SERVICE_ROLE_KEY|SUPABASE_SECRET_KEY)[[:space:]]*=' "$path"; then
    echo "ERROR: privileged credential appears in the $role environment file" >&2
    exit 1
  fi
  if ! grep -Eq "^DATABASE_URL=postgresql://$role[.]" "$path"; then
    echo "ERROR: wrong database role for $role" >&2
    exit 1
  fi
  if ! grep -E '^DATABASE_URL=' "$path" | grep -Eq 'sslmode=verify-full.*sslrootcert=|sslrootcert=.*sslmode=verify-full'; then
    echo "ERROR: verified TLS with explicit CA is required for $role" >&2
    exit 1
  fi
}

if [[ ! -f "$HOSTED_CA_FILE" || -L "$HOSTED_CA_FILE" ]] || ! openssl x509 -in "$HOSTED_CA_FILE" -noout >/dev/null 2>&1; then
  echo "ERROR: verified Supabase CA certificate missing or invalid" >&2
  exit 1
fi

check_secret_file "$HOSTED_API_ENV_FILE" flowstead_api
check_secret_file "$HOSTED_WORKER_ENV_FILE" flowstead_worker
if [[ ! -f "$HOSTED_NATS_AUTH_FILE" || -L "$HOSTED_NATS_AUTH_FILE" || "$(stat -c %U "$HOSTED_NATS_AUTH_FILE")" != root || "$(stat -c %a "$HOSTED_NATS_AUTH_FILE")" != 600 ]]; then
  echo "ERROR: missing or insecure root-owned 0600 NATS auth file" >&2
  exit 1
fi
# Compare the worker credential against the broker token without echoing it.
python3 - "$HOSTED_NATS_AUTH_FILE" "$HOSTED_WORKER_ENV_FILE" <<'PY'
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
conf = Path(sys.argv[1]).read_text()
worker = Path(sys.argv[2]).read_text()
auth = re.search(r'token\\s*:\\s*"([^"]+)"', conf)
url_line = re.search(r'^NATS_URL=(.+)
echo "Building x86_64 backend image"
docker build --platform linux/amd64 --load -f backend/Dockerfile -t "$HOSTED_IMAGE_TAG" backend
docker image inspect --format 'os={{.Os}} arch={{.Architecture}}' "$HOSTED_IMAGE_TAG"

echo "Validating Compose without printing runtime secrets"
HOSTED_API_ENV_FILE="$HOSTED_API_ENV_FILE" HOSTED_WORKER_ENV_FILE="$HOSTED_WORKER_ENV_FILE" HOSTED_CA_FILE="$HOSTED_CA_FILE" HOSTED_NATS_AUTH_FILE="$HOSTED_NATS_AUTH_FILE" "${COMPOSE[@]}" config --quiet

echo "Starting internal broker, API and worker only"
HOSTED_API_ENV_FILE="$HOSTED_API_ENV_FILE" HOSTED_WORKER_ENV_FILE="$HOSTED_WORKER_ENV_FILE" HOSTED_CA_FILE="$HOSTED_CA_FILE" HOSTED_NATS_AUTH_FILE="$HOSTED_NATS_AUTH_FILE" "${COMPOSE[@]}" up -d --wait nats api worker

for svc in api nats worker; do
  if "${COMPOSE[@]}" port "$svc" 2>/dev/null; then
    echo "ERROR: internal service $svc unexpectedly publishes a host port" >&2
    exit 1
  fi
done

echo "Internal stack started; public proxy remains disabled until verified TLS and DNS"
, worker, re.MULTILINE)
if not auth or not url_line:
    raise SystemExit("ERROR: NATS auth token and worker connection must be configured")
url = urlsplit(url_line.group(1).strip())
if url.scheme != "nats" or url.hostname != "nats" or url.port != 4222 or url.username != auth.group(1) or url.password is not None:
    raise SystemExit("ERROR: NATS worker token mismatch or wrong private broker")
PY

echo "Building x86_64 backend image"
docker build --platform linux/amd64 --load -f backend/Dockerfile -t "$HOSTED_IMAGE_TAG" backend
docker image inspect --format 'os={{.Os}} arch={{.Architecture}}' "$HOSTED_IMAGE_TAG"

echo "Validating Compose without printing runtime secrets"
HOSTED_API_ENV_FILE="$HOSTED_API_ENV_FILE" HOSTED_WORKER_ENV_FILE="$HOSTED_WORKER_ENV_FILE" HOSTED_CA_FILE="$HOSTED_CA_FILE" HOSTED_NATS_AUTH_FILE="$HOSTED_NATS_AUTH_FILE" "${COMPOSE[@]}" config --quiet

echo "Starting internal broker, API and worker only"
HOSTED_API_ENV_FILE="$HOSTED_API_ENV_FILE" HOSTED_WORKER_ENV_FILE="$HOSTED_WORKER_ENV_FILE" HOSTED_CA_FILE="$HOSTED_CA_FILE" HOSTED_NATS_AUTH_FILE="$HOSTED_NATS_AUTH_FILE" "${COMPOSE[@]}" up -d --wait nats api worker

for svc in api nats worker; do
  if "${COMPOSE[@]}" port "$svc" 2>/dev/null; then
    echo "ERROR: internal service $svc unexpectedly publishes a host port" >&2
    exit 1
  fi
done

echo "Internal stack started; public proxy remains disabled until verified TLS and DNS"
