#!/usr/bin/env bash
# Install only local service definitions for the owner-selected x86_64 OCI VM.
# Does NOT download binaries, create credentials, start services or open ports.
set -euo pipefail
if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "ERROR: this is for the existing x86_64 Oracle Linux instance" >&2
  exit 1
fi
if [[ "$(id -u)" != "0" ]]; then
  echo "ERROR: run via sudo after reviewing files" >&2
  exit 1
fi
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! id flowstead >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/flowstead --shell /sbin/nologin flowstead
fi
install -d -o root -g flowstead -m 0750 /etc/flowstead
install -d -o flowstead -g flowstead -m 0700 /var/lib/flowstead/nats
install -d -o flowstead -g flowstead -m 0700 /var/lib/flowstead/caddy
install -d -o root -g root -m 0755 /opt/flowstead
install -m 0644 "$SELF/nats.conf" /etc/flowstead/nats.conf
install -m 0644 "$SELF/Caddyfile" /etc/flowstead/Caddyfile
for svc in flowstead-nats flowstead-api flowstead-worker flowstead-proxy; do
  install -m 0644 "$SELF/$svc.service" "/etc/systemd/system/$svc.service"
done
systemctl daemon-reload
echo "Unit files installed but NOT started. Provision restricted DB secret, runtime, and binaries first."
