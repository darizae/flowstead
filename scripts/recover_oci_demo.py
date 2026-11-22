#!/usr/bin/env python3
"""Inspect/recover the ONE existing Flowstead OCI micro. No credentials are printed.

Usage: python3 scripts/recover_oci_demo.py [--recover]
Default is read-only. --recover explicitly allows START of a stopped instance or
SOFTRESET of an unresponsive running instance; never force-stop or replace.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

NAME = "flowstead-demo-instance"
REGION = "eu-frankfurt-1"
HEALTH = "https://api.flowstead.darizae.dev/api/v1/health/ready"
KEY = pathlib.Path.home() / ".ssh/id_ed25519_flowstead_demo"


def command(*args: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          env={**os.environ, "SUPPRESS_LABEL_WARNING": "True"})


def oci(*args: str, timeout: int = 25) -> dict:
    result = command("oci", *args, "--region", REGION, "--output", "json", timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"OCI operation failed (exit {result.returncode}); check provider state independently")
    return json.loads(result.stdout)


def health() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=5) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def ssh(ip: str) -> bool:
    if not KEY.is_file():
        print("SSH identity missing; SSH check skipped.")
        return False
    result = command(
        "ssh", "-T", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=7",
        "-i", str(KEY), f"opc@{ip}",
        "sudo systemctl is-active flowstead-api flowstead-worker flowstead-nats flowstead-proxy",
        timeout=13,
    )
    if result.returncode == 0 and all(line == "active" for line in result.stdout.splitlines()):
        print("SSH and all four systemd services: healthy")
        return True
    print("SSH or systemd health: unavailable (check guest, firewall, service logs)")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recover", action="store_true", help="allow bounded OCI START/SOFTRESET")
    args = parser.parse_args()
    config = pathlib.Path.home() / ".oci/config"
    if not config.exists():
        print("OCI CLI profile absent", file=sys.stderr)
        return 2
    import configparser
    profile = configparser.ConfigParser()
    profile.read(config)
    tenancy = profile["DEFAULT"].get("tenancy", "").strip()
    if not tenancy:
        print("No tenancy in OCI profile", file=sys.stderr)
        return 2
    instances = oci("compute", "instance", "list", "--compartment-id", tenancy, "--all")["data"]
    matches = [item for item in instances if item.get("display-name") == NAME
               and item.get("lifecycle-state") != "TERMINATED"]
    if len(matches) != 1:
        print("Expected exactly one approved Flowstead instance; refusing action")
        return 2
    instance = matches[0]
    instance_id = instance["id"]
    state = instance["lifecycle-state"]
    print(f"{NAME}: {state}")
    if state in {"STARTING", "STOPPING", "PROVISIONING", "TERMINATING", "UPDATING"}:
        print("Instance in transition; do not issue a competing action. Re-run after transition.")
        return 1
    ip = None
    if state == "RUNNING":
        vnics = oci("compute", "instance", "list-vnics", "--instance-id", instance_id)["data"]
        ip = next((v.get("public-ip") for v in vnics if v.get("public-ip")), None)
    api_ok = health()
    print(f"Public API readiness: {'healthy' if api_ok else 'unavailable'}")
    guest_ok = ssh(ip) if ip else False
    if api_ok and guest_ok:
        print("No recovery needed.")
        return 0
    if not args.recover:
        print("Read-only diagnosis complete. Run with --recover to allow approved OCI recovery.")
        return 1
    if state not in {"STOPPED", "RUNNING"}:
        print("Unsafe lifecycle state for recovery; refusing action.")
        return 2
    action = "START" if state == "STOPPED" else "SOFTRESET"
    if state == "RUNNING" and (api_ok or guest_ok):
        print("Some guest checks are healthy: inspect service logs instead of resetting.")
        return 1
    print(f"Requesting {action} on approved existing instance only.")
    result = command("oci", "compute", "instance", "action", "--region", REGION,
                     "--instance-id", instance_id, "--action", action,
                     "--wait-for-state", "RUNNING", "--max-wait-seconds", "180", timeout=200)
    if result.returncode:
        print("OCI lifecycle action rejected or timed out; check the current lifecycle state. Never force-reset.")
        return 1
    print("OCI reports RUNNING; service/API readiness may lag boot. Re-run read-only checks.")
    return 0 if health() else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, subprocess.TimeoutExpired, KeyError, json.JSONDecodeError) as exc:
        print(f"Diagnostic unavailable: {type(exc).__name__}", file=sys.stderr)
        sys.exit(2)
