# Flowstead — boot, SSH and host diagnostics for the existing OCI VM

**Target:** `flowstead-demo-instance` in `eu-frankfurt-1`, **`VM.Standard.E2.1.Micro`**, Oracle Linux 9.8 on x86_64. This is the owner's chosen and only approved host. Do not create or recommend another machine.

**Recorded 2026-11-21:** OCI `STOPPED` → `RUNNING` via CLI was **EXECUTED** successfully. Before START, the existing VCN default security list was updated so SSH port 22 is accessible only from the owner's then-current public IPv4 `/32`; existing ICMP rules were retained. SSH `opc` authenticated with the private key and noninteractive sudo succeeded. A later prolonged package probe was followed by SSH timeouts, so re-check liveness before installing anything else.

## Inspect or start the existing instance

Never paste Oracle OCIDs, SSH keys or current public IP into Git or chat. Use the configured `oci` profile and look up `INSTANCE_ID` privately from the root-compartment instance list.

```sh
oci compute instance get --region eu-frankfurt-1 --instance-id "$INSTANCE_ID" --query 'data."lifecycle-state"'
# Only if STOPPED, and only on the already-provisioned demo instance:
oci compute instance action --region eu-frankfurt-1 --instance-id "$INSTANCE_ID" --action START --wait-for-state RUNNING
```

Get its live public IPv4 from its attached VNIC; it may change when stopped/started. Confirm the SSH security list admits only the owner's **current** IPv4 /32, not a wildcard. From the Mac:

```sh
chmod 600 ~/.ssh/id_ed25519_flowstead_demo
ssh -i ~/.ssh/id_ed25519_flowstead_demo -o IdentitiesOnly=yes opc@"$INSTANCE_IP"
```

## Non-destructive host checks

```sh
uname -m
cat /etc/os-release
free -m
df -h /
systemctl is-active sshd
sudo ss -lnt
```

The guest has limited RAM/swap; check `journalctl -b --no-pager -n 100`, `systemctl --failed` and `dmesg` for memory pressure if remote commands hang. Do not blindly restart a running task. The reported 47 GB boot volume and current ~30 GB root filesystem are distinct measurements; check partition/filesystem expansion separately if needed, without destructive reformatting.

Keep only planned HTTPS/proxy ports public when fully configured; API 8000, NATS 4222/8222, Postgres 5432/6543 and Docker socket must remain private. Restrict SSH to the owner CIDR, protect all host secrets and avoid running the service as root.

## Shutdown, only when specifically intended

```sh
oci compute instance action --region eu-frankfurt-1 --instance-id "$INSTANCE_ID" --action SOFTSTOP --wait-for-state STOPPED
```

Stopping is not deletion. Do not terminate, resize, replace, reset, or add paid resources as a diagnostic shortcut. Cloud Free Tier eligibility and budget alerts are not a hard spending cap. Refer to [HOSTED_DEPLOYMENT.md](HOSTED_DEPLOYMENT.md) for actual running-service verification.
