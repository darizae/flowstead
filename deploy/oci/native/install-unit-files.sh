#!/usr/bin/env bash
# Install unit definitions on the existing Oracle Linux x86_64 micro.
# Does not install binaries or credentials or enable any API/worker service.
set -euo pipefail
if [[ "$(uname -m)" != "x86_64" || "$(id -u)" != "0" ]]; then
  echo "ERROR: execute only as root on the existing x86_64 VM" >&2
  exit 1
fi
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for svc in flowstead flowstead-api flowstead-worker flowstead-proxy; do
  if ! id "$svc" >/dev/null 2>&1; then
    useradd --system --user-group --home-dir "/var/lib/$svc" --shell /sbin/nologin "$svc"
  fi
done
# Protected files in this directory have role-specific group permissions.
# The traversable directory deliberately does NOT grant a common group access
# to both API and worker secrets.
install -d -o root -g root -m 0711 /etc/flowstead
install -d -o flowstead -g flowstead -m 0700 /var/lib/flowstead/nats
install -d -o flowstead-proxy -g flowstead-proxy -m 0700 /var/lib/flowstead/caddy
install -d -o root -g root -m 0755 /opt/flowstead

# Fail CLOSED if NATS token auth is absent. Auth is provisioned separately,
# not compiled into the repo or included in user-visible diagnostics.
if [[ ! -f /etc/flowstead/nats-auth.conf ]]; then
  echo "ERROR: protected NATS auth file not provisioned; refusing broker config install" >&2
  exit 1
fi

install -o root -g flowstead -m 0640 "$SELF/nats.conf" /etc/flowstead/nats.conf
install -o root -g root -m 0644 "$SELF/Caddyfile" /etc/flowstead/Caddyfile
for svc in flowstead-nats flowstead-api flowstead-worker flowstead-proxy; do
  install -o root -g root -m 0644 "$SELF/$svc.service" "/etc/systemd/system/$svc.service"
done
systemctl daemon-reload
echo "Service definitions installed but not enabled or started."
echo "API/worker require separate restricted database logins, secrets and verified TLS."
