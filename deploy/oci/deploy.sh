#!/usr/bin/env bash
# Flowstead public-demo deployment driver (T-016) — run ON the OCI A1 ARM64 VM.
#
# Builds the ARM64 backend worker/API image from the committed uv.lock, then
# brings the hosted stack (nats, api, worker, proxy) up. No local PostgreSQL is
# started; the app uses the hosted Supabase DATABASE_URL from a host secret-file.
#
# Usage (from the repo root on the VM):
#   HOSTED_ENV_FILE=/etc/flowstead/hosted.env ./deploy/oci/deploy.sh
#
# The host secret-file must exist (chmod 600) and contain DATABASE_URL + auth
# settings (deploy/oci/env.hosted.example). This script never contacts OCI
# beyond Docker running locally; VM/network/NSG provisioning is a separate,
# manual, owner-approved OCI action.
set -euo pipefail
cd "$(dirname "$0")/../.."

: "${HOSTED_ENV_FILE:=/etc/flowstead/hosted.env}"
: "${HOSTED_IMAGE_TAG:=flowstead-backend:arm64-hosted}"
COMPOSE=(docker compose -f compose.hosted.yml -p flowstead-demo)

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found on $(uname -s)/$(uname -m)" >&2; exit 1
fi
if [[ ! -f "$HOSTED_ENV_FILE" ]]; then
  echo "ERROR: host secret-file '$HOSTED_ENV_FILE' missing (chmod 600). See deploy/oci/env.hosted.example." >&2; exit 1
fi

echo "== Building ARM64 backend image ($HOSTED_IMAGE_TAG) =="
docker build --platform linux/arm64 --load -f backend/Dockerfile -t "$HOSTED_IMAGE_TAG" backend

echo "== Verifying image architecture =="
docker image inspect --format 'os={{.Os}} arch={{.Architecture}}' "$HOSTED_IMAGE_TAG"

echo "== Validating hosted compose =="
HOSTED_ENV_FILE="$HOSTED_ENV_FILE" "${COMPOSE[@]}" config --quiet

echo "== Bringing up the hosted stack (nats, api, worker, proxy) =="
HOSTED_ENV_FILE="$HOSTED_ENV_FILE" "${COMPOSE[@]}" up -d --wait nats api worker

echo "== Public ports offered by the stack (only proxy expected) =="
for svc in nats api worker; do
  if "${COMPOSE[@]}" port "$svc" 2>/dev/null; then
    echo "UNEXPECTED public port on $svc" >&2
  fi
done

echo
echo "Hosted stack up. Proxy TLS is only active once the approved DNS hostname"
echo "is enabled in deploy/oci/Caddyfile (see that file's warning)."
echo "If a proxy is to run now, apply the approved Caddyfile first, then:"
echo "  ${COMPOSE[@]} up -d --wait proxy"