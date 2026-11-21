"""Security regression tests for the private interactive demo credential bootstrap."""
from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/provision_demo_runtime.py"


def _script():
    spec = importlib.util.spec_from_file_location("flowstead_demo_bootstrap", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bootstrap_verifier_matches_scram_sha256_without_plaintext() -> None:
    script = _script()
    password = "unrelated-local-test-secret-not-used-live"
    value = script.scram_verifier(password)
    assert password not in value
    match = re.fullmatch(r"SCRAM-SHA-256\$(\d+):([^$]+)\$([^:]+):(.+)", value)
    assert match
    iters, salt, stored, server = match.groups()
    assert int(iters) == 4096
    salted = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), base64.b64decode(salt), int(iters)
    )
    client = hmac.new(salted, b"Client Key", "sha256").digest()
    assert base64.b64decode(stored) == hashlib.sha256(client).digest()
    assert base64.b64decode(server) == hmac.new(salted, b"Server Key", "sha256").digest()


def test_bootstrap_envs_have_distinct_database_roles_and_no_admin_secret() -> None:
    script = _script()
    api = script.make_env("flowstead_api", "local-test-api-secret")
    worker = script.make_env("flowstead_worker", "local-test-worker-secret")
    assert "flowstead_api.hkyobferqdfiicnsaupl" in api
    assert "flowstead_worker.hkyobferqdfiicnsaupl" in worker
    assert "local-test-worker-secret" not in api
    assert "local-test-api-secret" not in worker
    assert "SUPABASE_AUTH_URL=https://" in api
    assert "SUPABASE_AUTH_URL" not in worker
    assert "NATS_URL" not in api + worker
    assert "sslmode=verify-full" in api and "sslmode=verify-full" in worker
    assert "sslrootcert=/etc/flowstead/supabase-root-2021.crt" in api + worker
    assert "FLOWSTEAD_CORS_ORIGINS=https://flowstead.darizae.dev" in api


def test_bootstrap_defaults_to_read_only_preflight_and_no_secret_output() -> None:
    text = SCRIPT.read_text()
    assert 'args.add_argument("--apply", action="store_true")' in text
    assert "getpass.getpass" in text
    assert "sys.stdin.isatty()" in text
    assert "sql.Literal(scram_verifier(role_passes[role]))" in text
    assert "input_text=stdin" not in text  # interactive password not sent to host
    assert 'Never log psycopg failure text' in text
