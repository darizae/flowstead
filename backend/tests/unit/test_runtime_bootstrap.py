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
    assert 'args.add_argument("--resume", action="store_true"' in text
    assert 'if params.apply:\n' in text
    assert 'test_role_logins(role_passes)' in text
    assert 'install_runtime_secrets(ip, role_passes)' in text
    assert 'Resuming after the already-successful database role activation' in text
    assert "getpass.getpass" in text
    assert "sys.stdin.isatty()" in text
    assert "sql.Literal(scram_verifier(role_passes[role]))" in text
    assert "input_text=stdin" not in text  # interactive password not sent to host
    assert 'Never log psycopg failure text' in text

def test_bootstrap_installer_uses_linux_groups_and_stops_on_ownership_errors(monkeypatch) -> None:
    script = _script()
    calls: list[tuple[str, str | None]] = []

    def capture_ssh(_ip: str, shell: str, *, data: str | None = None) -> None:
        calls.append((shell, data))

    monkeypatch.setattr(script, "ssh", capture_ssh)
    script.install_runtime_secrets(
        "127.0.0.1",
        {"flowstead_api": "test-only-api", "flowstead_worker": "test-only-worker"},
    )
    api_install = [command for command, content in calls if content and "test-only-api" in content]
    worker_install = [command for command, content in calls if content and "test-only-worker" in content]
    assert len(api_install) == 1
    assert len(worker_install) == 1
    assert "set -eu;" in api_install[0] and "set -eu;" in worker_install[0]
    assert "chown root:flowstead-api /etc/flowstead/api.env" in api_install[0]
    assert "chown root:flowstead-worker /etc/flowstead/worker.env" in worker_install[0]
    assert "chown root:flowstead_api" not in api_install[0]
    assert "chown root:flowstead_worker" not in worker_install[0]
    assert all("test-only" not in command for command, _ in calls)


def test_https_readiness_retries_transient_502_without_logging_response(monkeypatch) -> None:
    from urllib.error import HTTPError

    script = _script()
    attempts: list[str] = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _max_bytes: int) -> bytes:
            return b'{"status":"ok"}'

    def open_url(url: str, *, timeout: int):
        attempts.append(url)
        if len(attempts) == 1:
            raise HTTPError(url, 502, "Bad Gateway", {}, None)
        return Response()

    monkeypatch.setattr(script, "urlopen", open_url)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)

    assert script.read_https_json_when_ready("/api/v1/health/live") == {"status": "ok"}
    assert len(attempts) == 2


def test_https_readiness_does_not_retry_authentication_errors(monkeypatch) -> None:
    from urllib.error import HTTPError
    import pytest

    script = _script()
    attempts = []

    def open_url(url: str, *, timeout: int):
        attempts.append(url)
        raise HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(script, "urlopen", open_url)
    with pytest.raises(RuntimeError, match="unexpected status 401"):
        script.read_https_json_when_ready("/api/v1/health/live")
    assert len(attempts) == 1
