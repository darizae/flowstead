#!/usr/bin/env python3
"""Privately bootstrap Flowstead's existing demo DB roles and OCI API/worker.

Run in an interactive Mac terminal. The Supabase Postgres owner password is
entered via hidden getpass() and is NEVER stored, logged, or sent to ChatGPT.
The application receives two separate randomly generated least-privilege
credentials. This script never creates infrastructure or invites real users.
"""
from __future__ import annotations

import argparse
import base64
import configparser
import getpass
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

import psycopg
from psycopg import sql

REF = "hkyobferqdfiicnsaupl"
DB_HOST = "aws-1-eu-west-1.pooler.supabase.com"
VM_NAME = "flowstead-demo-instance"
REGION = "eu-frankfurt-1"
API_HOST = "api.flowstead.darizae.dev"
ROLES = ("flowstead_api", "flowstead_worker")
HOME = Path.home()
SECRET_DIR = HOME / "Library/Application Support/Flowstead/secrets"
CA_FILE = SECRET_DIR / "supabase-root-2021.crt"
CA_FINGERPRINT = (
    "80:70:25:AD:50:D4:ED:21:9D:2C:9C:7D:29:9C:00:4F:"
    "82:4E:B0:0C:F7:F6:5A:FE:F6:07:D0:7B:72:E6:CA:FA"
)
LOCAL_ROLE_FILE = SECRET_DIR / "runtime-roles.json"
REMOTE_CA = "/etc/flowstead/supabase-root-2021.crt"
SSH_KEY = HOME / ".ssh/id_ed25519_flowstead_demo"


def checked(args: list[str], *, stdin: str | None = None, seconds: int = 45) -> str:
    proc = subprocess.run(
        args, text=True, input=stdin, capture_output=True, timeout=seconds
    )
    if proc.returncode:
        # Deliberately never expose stderr or command arguments: either may
        # contain connection details or a credential-bearing diagnostic.
        raise RuntimeError("An external command failed; inspect locally without logging secrets")
    return proc.stdout


def verify_ca() -> None:
    if not CA_FILE.is_file():
        raise RuntimeError("Supabase CA file missing; obtain it from Database Settings")
    out = checked([
        "openssl", "x509", "-in", str(CA_FILE),
        "-noout", "-fingerprint", "-sha256"
    ])
    if CA_FINGERPRINT not in out:
        raise RuntimeError("Supabase CA fingerprint mismatch")


def vm_ip() -> str:
    cfg = configparser.ConfigParser()
    if not cfg.read(HOME / ".oci/config"):
        raise RuntimeError("OCI CLI profile missing")
    env = dict(os.environ, SUPPRESS_LABEL_WARNING="True")
    def oci(*args: str):
        proc = subprocess.run(
            ["oci", *args, "--region", REGION, "--output", "json"],
            capture_output=True, text=True, timeout=45, env=env
        )
        if proc.returncode:
            raise RuntimeError("OCI read failed")
        return json.loads(proc.stdout)["data"]
    tenancy = cfg.get("DEFAULT", "tenancy")
    vm = next(
        (item for item in oci("compute", "instance", "list",
                             "--compartment-id", tenancy, "--all")
         if item.get("display-name") == VM_NAME), None
    )
    if (vm is None or vm["lifecycle-state"] != "RUNNING" or
            vm["shape"] != "VM.Standard.E2.1.Micro"):
        raise RuntimeError("Existing Oracle VM is not RUNNING in the approved shape")
    vnics = oci("compute", "instance", "list-vnics", "--instance-id", vm["id"])
    if len(vnics) != 1 or not vnics[0].get("public-ip"):
        raise RuntimeError("Unexpected OCI VNIC state")
    return vnics[0]["public-ip"]


def db_params(role: str, password: str) -> dict[str, object]:
    return {
        "host": DB_HOST, "port": 5432, "dbname": "postgres",
        "user": role + "." + REF, "password": password,
        "sslmode": "verify-full", "sslrootcert": str(CA_FILE),
        "connect_timeout": 12,
    }


def scram_verifier(password: str) -> str:
    salt = secrets.token_bytes(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 4096)
    client = hmac.new(salted, b"Client Key", "sha256").digest()
    stored = hashlib.sha256(client).digest()
    server = hmac.new(salted, b"Server Key", "sha256").digest()
    b64 = lambda value: base64.b64encode(value).decode("ascii")
    # PostgreSQL's SCRAM verifier is not the plaintext password.
    return "SCRAM-SHA-256$4096:" + b64(salt) + "$" + b64(stored) + ":" + b64(server)


def get_role_secrets() -> dict[str, str]:
    SECRET_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(SECRET_DIR, 0o700)
    if LOCAL_ROLE_FILE.exists():
        if LOCAL_ROLE_FILE.is_symlink():
            raise RuntimeError("Refusing symlinked runtime secret file")
        os.chmod(LOCAL_ROLE_FILE, 0o600)
        data = json.loads(LOCAL_ROLE_FILE.read_text())
        if set(data) != set(ROLES) or any(len(data[r]) < 55 for r in ROLES):
            raise RuntimeError("Existing runtime credential file did not pass validation")
        return data
    data = {role: secrets.token_urlsafe(48) for role in ROLES}
    fd = os.open(LOCAL_ROLE_FILE, os.O_WRONLY | os.O_EXCL | os.O_CREAT, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(data, output)
    return data


def activate_roles(owner_pass: str, role_passes: dict[str, str]) -> None:
    with psycopg.connect(**db_params("postgres", owner_pass)) as db:
        counts = db.execute(
            "SELECT (SELECT count(*) FROM app.plants),"
            " (SELECT count(*) FROM app.hourly_readings)"
        ).fetchone()
        if tuple(counts) != (5, 43800):
            raise RuntimeError("Unexpected DB dataset, refusing to activate roles")
        rows = db.execute(
            "SELECT rolname FROM pg_roles WHERE rolname IN"
            " ('flowstead_api', 'flowstead_worker')"
        ).fetchall()
        if {r[0] for r in rows} != set(ROLES):
            raise RuntimeError("Expected least-privilege DB roles are missing")
        for role in ROLES:
            # No plaintext password or admin key appears inside SQL.
            statement = sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(role), sql.Literal(scram_verifier(role_passes[role]))
            )
            db.execute(statement)
    print("Database roles enabled using separate, pre-hashed SCRAM verifiers.")


def test_role_logins(role_passes: dict[str, str]) -> None:
    for role in ROLES:
        with psycopg.connect(**db_params(role, role_passes[role])) as db:
            who = db.execute("SELECT current_user").fetchone()[0]
            if who != role:
                raise RuntimeError("Runtime connected as an unexpected DB role")
            grants = db.execute(
                "SELECT has_schema_privilege(current_user, 'app', 'USAGE'),"
                " has_table_privilege(current_user,'app.plants','UPDATE'),"
                " has_table_privilege(current_user,'app.operator_plant_access','UPDATE'),"
                " has_table_privilege(current_user,'public.alembic_version','SELECT')"
            ).fetchone()
            if tuple(grants) != (True, False, False, False):
                raise RuntimeError("Runtime DB privilege regression")
            if db.execute("SELECT count(*) FROM app.plants").fetchone()[0] != 5:
                raise RuntimeError("Runtime DB cannot read synthetic Plants")
            if role == "flowstead_worker":
                can_read_grants = db.execute(
                    "SELECT has_table_privilege(current_user,"
                    "'app.operator_plant_access','SELECT')"
                ).fetchone()[0]
                if can_read_grants:
                    raise RuntimeError("Worker must not inspect operator grants")
        print("Verified restricted database login for " + role + " with valid TLS.")


def make_env(role: str, password: str) -> str:
    url = (
        "postgresql://" + role + "." + REF + ":" +
        quote(password, safe="") + "@" + DB_HOST + ":5432/postgres"
        "?sslmode=verify-full&sslrootcert=" + REMOTE_CA + "&connect_timeout=5"
    )
    lines = ["DATABASE_URL=" + url]
    if role == "flowstead_api":
        lines.extend([
            "FLOWSTEAD_AUTH_MODE=supabase",
            "SUPABASE_AUTH_URL=https://" + REF + ".supabase.co/auth/v1",
            "SUPABASE_JWT_ISSUER=https://" + REF + ".supabase.co/auth/v1",
            "SUPABASE_JWT_AUDIENCE=authenticated",
            "SUPABASE_JWT_ALGORITHMS=ES256",
            "SUPABASE_AUTH_VERIFICATION_MODE=jwks",
            "FLOWSTEAD_CORS_ORIGINS=https://flowstead.darizae.dev",
            "FLOWSTEAD_TRUSTED_PROXIES=127.0.0.1/32",
            "FLOWSTEAD_RATE_LIMIT_REQUESTS=180",
            "FLOWSTEAD_FORECAST_RATE_LIMIT_REQUESTS=10",
            "FLOWSTEAD_FORECAST_RATE_LIMIT_WINDOW_SECONDS=60",
        ])
    return "\n".join(lines) + "\n"


def ssh(ip: str, shell: str, *, data: str | None = None) -> None:
    if not SSH_KEY.is_file():
        raise RuntimeError("Owner SSH private key missing")
    checked([
        "ssh", "-T", "-i", str(SSH_KEY), "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes", "-o", "ConnectTimeout=12",
        "-o", "StrictHostKeyChecking=yes", "opc@" + ip, shell
    ], stdin=data, seconds=50)


def install_runtime_secrets(ip: str, role_passes: dict[str, str]) -> None:
    ssh(ip,
        "test -f /etc/flowstead/supabase-root-2021.crt &&"
        " systemctl is-active --quiet flowstead-nats &&"
        " systemctl is-active --quiet flowstead-proxy &&"
        " id -u flowstead-api >/dev/null &&"
        " id -u flowstead-worker >/dev/null"
    )
    for role in ROLES:
        filename = "api.env" if role == "flowstead_api" else "worker.env"
        # Password contents are sent via encrypted stdin, never argv or chat.
        # Root:role 0640; cross-role reads blocked by Linux permissions.
        shell = (
            "sudo -n sh -c 'umask 077; "
            "cat > /etc/flowstead/" + filename + "; "
            "chown root:" + role + " /etc/flowstead/" + filename + "; "
            "chmod 0640 /etc/flowstead/" + filename + "'"
        )
        ssh(ip, shell, data=make_env(role, role_passes[role]))
    ssh(ip,
        "sudo -n -u flowstead-api test -r /etc/flowstead/api.env &&"
        " sudo -n -u flowstead-worker test -r /etc/flowstead/worker.env &&"
        " ! sudo -n -u flowstead-api test -r /etc/flowstead/worker.env &&"
        " ! sudo -n -u flowstead-worker test -r /etc/flowstead/api.env &&"
        " sudo -n -u flowstead-worker test -r /etc/flowstead/nats-worker.env"
    )
    print("Installed independent protected API and worker secrets on existing OCI VM.")


def launch_and_check(ip: str, worker_password: str) -> None:
    ssh(ip, "sudo -n systemctl start flowstead-worker")
    time.sleep(3)
    ssh(ip, "systemctl is-active --quiet flowstead-worker")
    ssh(ip, "sudo -n systemctl start flowstead-api")
    time.sleep(3)
    ssh(ip, "systemctl is-active --quiet flowstead-api")
    with urlopen("https://" + API_HOST + "/api/v1/health/live", timeout=15) as r:
        if r.status != 200:
            raise RuntimeError("HTTPS API health did not return HTTP 200")
    with urlopen("https://" + API_HOST + "/api/v1/public/plants", timeout=15) as r:
        if r.status != 200:
            raise RuntimeError("Public Plants API did not return HTTP 200")
        payload = json.loads(r.read(65536))
    plants = payload.get("plants") if isinstance(payload, dict) else payload
    if not isinstance(plants, list) or len(plants) != 5:
        raise RuntimeError("Public API response must return exactly five Plants")
    print("Verified HTTPS API health and five synthetic public Plants.")
    with psycopg.connect(**db_params("flowstead_worker", worker_password)) as db:
        n = db.execute(
            "SELECT count(*) FROM app.message_outbox WHERE status='pending'"
        ).fetchone()[0]
        print("Remaining pending ingestion events:", n)


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--apply", action="store_true")
    params = args.parse_args()
    verify_ca()
    ip = vm_ip()
    print("Preflight passed: CA and existing Oracle VM verified.")
    if not params.apply:
        print("Run with --apply in a private interactive Mac Terminal.")
        return
    if not sys.stdin.isatty():
        raise RuntimeError("A private interactive Mac Terminal is required")
    owner_pass = getpass.getpass(
        "Enter the flowstead-demo Postgres DB password (hidden; never stored): "
    )
    if not owner_pass:
        raise RuntimeError("No password supplied; reset it in Supabase DB Settings")
    role_passes = get_role_secrets()
    try:
        activate_roles(owner_pass, role_passes)
        test_role_logins(role_passes)
    finally:
        owner_pass = ""
    install_runtime_secrets(ip, role_passes)
    launch_and_check(ip, role_passes["flowstead_worker"])
    print("Complete: runtime services configured and checked.")


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as e:
        # Never log psycopg failure text or credentials. The failure *class*
        # lets the user report the stage without exposing sensitive context.
        print("Stopped safely (" + type(e).__name__ + ").", file=sys.stderr)
        sys.exit(1)
