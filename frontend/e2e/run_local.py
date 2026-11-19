"""Run the public Flowstead browser gate against an owned disposable database."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import http.server
import ipaddress
import json
import os
import re
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import SplitResult, quote, urlsplit, urlunsplit
from urllib.request import urlopen

import certifi
import jwt
import psycopg
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = "ad5c94d1f46e79312a99cb9721f38700f24fdf6b"
TELEMETRY_SHA256 = "e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e"
DB_PREFIX = "flowstead_test_"


def _expected_chromium_revision() -> str | None:
    """Resolve the Chromium revision @playwright/test expects (browsers.json)."""
    browsers_json = ROOT / "frontend" / "node_modules" / "playwright-core" / "browsers.json"
    try:
        data = json.loads(browsers_json.read_text(encoding="utf-8"))
        for browser in data.get("browsers", []):
            if browser.get("name") == "chromium":
                return str(browser["revision"])
    except (OSError, KeyError, json.JSONDecodeError):
        return None
    return None


def _frame_complete(chromium_dir: Path) -> bool:
    """True when an installed Chromium.app has its Framework bundle extracted."""
    frameworks = chromium_dir / "chrome-mac-arm64/Google Chrome for Testing.app/Contents/Frameworks"
    return any(frameworks.glob("*Framework.framework/Versions/*")) if frameworks.exists() else False


def _find_chromium_executable() -> str | None:
    """Return a usable Chromium executable for the browser gate.

    The installed @playwright/test expects a bundled revision that may be absent
    or incompletely extracted; fall back to the newest *complete* installed
    Chromium executable instead of requiring a repair download.
    """
    cache = Path.home() / "Library/Caches/ms-playwright"
    expected = _expected_chromium_revision()
    if expected:
        expected_dir = cache / f"chromium-{expected}"
        expected_exe = expected_dir / "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        if expected_exe.is_file() and _frame_complete(expected_dir):
            return None  # matching, complete bundled browser; use Playwright's default
    candidates = []
    for directory in sorted(cache.glob("chromium-*"), reverse=True):
        exe = directory / "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        if exe.is_file() and _frame_complete(directory):
            candidates.append(exe)
    return str(candidates[0]) if candidates else None

class RunnerError(RuntimeError):
    """Raised when the real local E2E environment cannot be established."""


def _loopback_url(value: str) -> SplitResult:
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RunnerError("DATABASE_URL must point to loopback PostgreSQL")
    if parsed.query or parsed.fragment:
        raise RunnerError("DATABASE_URL must not include PostgreSQL query or fragment options")
    try:
        parsed.port
    except ValueError as error:
        raise RunnerError("DATABASE_URL has an invalid PostgreSQL port") from error
    return parsed


def _database_url(parsed: SplitResult, database: str) -> str:
    path = f"/{quote(database, safe='')}"
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))

def _quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _verify_m1(manifest_path: Path, data_path: Path) -> None:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"cannot read M1 manifest: {error}") from error
    schema_version = manifest.get("schema_version")
    if schema_version is None and isinstance(manifest.get("schema"), dict):
        schema_version = manifest["schema"].get("version")
    if schema_version != "m1.v1" or manifest.get("seed") != 20250101:
        raise RunnerError("M1 manifest must declare schema m1.v1 and seed 20250101")
    provenance = manifest.get("provenance")
    if provenance != "synthetic" and not (isinstance(provenance, dict) and provenance.get("kind", provenance.get("type")) == "synthetic"):
        raise RunnerError("M1 manifest must declare synthetic provenance")
    # The generator may or may not embed a source SHA; when one is declared it
    # must match the pinned source. The authoritative source is passed to the
    # importer via --source-sha (importer.py does not require a manifest field).
    declared_sources = [
        manifest.get(name)
        for name in ("source_sha", "source_commit")
        if name in manifest
    ]
    if any(source != SOURCE_SHA for source in declared_sources):
        raise RunnerError("M1 manifest must not declare a source SHA/commit other than the pinned source")
    files = manifest.get("files")
    entry = files.get("telemetry.csv") if isinstance(files, dict) else None
    expected = entry.get("sha256", entry.get("sha")) if isinstance(entry, dict) else None
    if expected != TELEMETRY_SHA256:
        raise RunnerError("M1 manifest telemetry SHA does not match the canonical digest")
    if data_path.name != "telemetry.csv" or data_path.parent.resolve() != manifest_path.parent.resolve():
        raise RunnerError("M1 telemetry.csv must be next to the manifest")
    digest = hashlib.sha256()
    try:
        with data_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise RunnerError(f"cannot read M1 telemetry: {error}") from error
    if digest.hexdigest() != TELEMETRY_SHA256:
        raise RunnerError("M1 telemetry SHA does not match the canonical digest")


def _create_database(base_url: str) -> tuple[str, str]:
    parsed = _loopback_url(base_url)
    name = f"{DB_PREFIX}{uuid.uuid4().hex}"
    target_url = _database_url(parsed, name)
    with psycopg.connect(base_url, autocommit=True) as connection:
        connection.execute(f"CREATE DATABASE {_quoted_identifier(name)}")
    return name, target_url


def _drop_database(name: str, base_url: str) -> None:
    if re.fullmatch(r"flowstead_test_[0-9a-f]{32}", name) is None:
        raise RunnerError("refusing to drop a database outside the runner-owned name format")
    with psycopg.connect(base_url, autocommit=True) as connection:
        connection.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (name,))
        connection.execute(f"DROP DATABASE IF EXISTS {_quoted_identifier(name)}")


def _run(command: list[str], env: dict[str, str], *, timeout: float | None = None) -> int:
    try:
        completed = subprocess.run(command, cwd=ROOT, env=env, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise RunnerError(f"command timed out: {' '.join(command)}") from error
    return completed.returncode


def _terminate(process: subprocess.Popen[bytes] | None) -> None:
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        if process.poll() is None:
            process.wait(timeout=10)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _port_occupied(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def _start_api(env: dict[str, str]) -> subprocess.Popen[bytes]:
    if _port_occupied(8000):
        raise RunnerError("refusing to start FastAPI: 127.0.0.1:8000 is already occupied")
    process: subprocess.Popen[bytes] | None = None
    process_env = env.copy()
    process_env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(ROOT), process_env.get("PYTHONPATH")) if value
    )
    try:
        process = subprocess.Popen(
            ["uv", "run", "--project", "backend", "uvicorn", "flowstead_api.main:app", "--app-dir", "backend/src", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT,
            env=process_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read().decode(errors="replace") if process.stdout else ""
                raise RunnerError(f"FastAPI exited before startup:\n{output}")
            try:
                with urlopen("http://127.0.0.1:8000/api/v1/health", timeout=1) as response:
                    if response.status == 200:
                        if process.poll() is not None:
                            raise RunnerError("FastAPI exited immediately after health readiness")
                        return process
            except OSError:
                time.sleep(0.25)
        raise RunnerError("FastAPI did not become healthy within 30 seconds")
    except BaseException:
        _terminate(process)
        raise


TEST_AUTH_PORT = 8443
TEST_AUTH_BASE = f"https://127.0.0.1:{TEST_AUTH_PORT}/auth/v1"
TEST_AUTH_ISSUER = TEST_AUTH_BASE
TEST_AUTH_AUDIENCE = "authenticated"
TEST_AUTH_KEY_ID = "e2e-test-key"


def _seed_principal_access(database_url: str, assignments: dict[str, list[str]]) -> None:
    """Grant the deterministic test principals access to M1 Plants in the DB."""
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        for subject, plant_ids in assignments.items():
            for plant_id in plant_ids:
                cursor.execute(
                    "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (subject, plant_id),
                )


def _generate_ca() -> tuple[rsa.RSAPrivateKey, x509.Certificate, rsa.RSAPrivateKey, x509.Certificate, str]:
    """Return (ca_key, ca_cert, server_key, server_cert, server_cert_pem_and_key)."""
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Flowstead E2E Test CA")])
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_name).issuer_name(ca_cert.subject)
        .public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=2))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    server_pem = server_cert.public_bytes(serialization.Encoding.PEM) + server_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    return ca_key, ca_cert, server_key, server_cert, server_pem.decode()


class _JWKSHandler(http.server.BaseHTTPRequestHandler):
    """Serve the test authority JWKS document over HTTPS for FastAPI verification."""

    jwks_document = b""

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.jwks_document)

    def log_message(self, _format: str, *args: object) -> None:
        return


def _start_jwks_server(ca_cert: x509.Certificate, server_key: rsa.RSAPrivateKey, server_cert: x509.Certificate) -> http.server.HTTPServer:
    """Start an HTTPS mock Auth authority resolving /.well-known/jwks.json."""
    public_numbers = server_key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": TEST_AUTH_KEY_ID,
                "alg": "RS256",
                "use": "sig",
                "n": _b64(public_numbers.n),
                "e": _b64(public_numbers.e),
            }
        ]
    }
    _JWKSHandler.jwks_document = json.dumps(jwks).encode()
    server = http.server.HTTPServer(("127.0.0.1", TEST_AUTH_PORT), _JWKSHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(
        keyfile=_PEM(server_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())),
        certfile=_PEM(server_cert.public_bytes(serialization.Encoding.PEM)),
    )
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _PEM(data: bytes) -> str:
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    path.write(data)
    path.close()
    return path.name


def _b64(value: int) -> str:
    from base64 import urlsafe_b64encode
    length = (value.bit_length() + 7) // 8
    return urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode()


def _mint_token(private_key: rsa.RSAPrivateKey, subject: str, *, minutes: int = 30) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    claims = {
        "sub": subject,
        "iss": TEST_AUTH_ISSUER,
        "aud": TEST_AUTH_AUDIENCE,
        "iat": int((now - datetime.timedelta(seconds=1)).timestamp()),
        "nbf": int((now - datetime.timedelta(seconds=1)).timestamp()),
        "exp": int((now + datetime.timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": TEST_AUTH_KEY_ID, "typ": "JWT"})


def _setup_test_auth(env: dict[str, str], database_url: str) -> dict[str, object]:
    """Configure FastAPI to verify deterministic RS256 JWTs against a local mock authority."""
    ca_key, ca_cert, server_key, server_cert, _ = _generate_ca()
    # Seed two disjoint test principals against the approved M1 Plants.
    assignments = {"test-principal-a": ["plant-01", "plant-02"], "test-principal-b": ["plant-03"]}
    _seed_principal_access(database_url, assignments)
    server = _start_jwks_server(ca_cert, server_key, server_cert)
    # Trust our CA alongside the system bundle so httpx (FastAPI verifier) accepts the mock.
    combined = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    combined.write(open(certifi.where(), "rb").read())
    combined.write(b"\n")
    combined.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    combined.close()
    env["SUPABASE_AUTH_URL"] = TEST_AUTH_BASE
    env["SUPABASE_JWT_ISSUER"] = TEST_AUTH_ISSUER
    env["SUPABASE_JWT_AUDIENCE"] = TEST_AUTH_AUDIENCE
    env["SUPABASE_JWT_ALGORITHMS"] = "RS256"
    env["SUPABASE_AUTH_VERIFICATION_MODE"] = "jwks"
    env["SSL_CERT_FILE"] = combined.name
    env["REQUESTS_CA_BUNDLE"] = combined.name
    return {
        "server": server,
        "private_key": server_key,
        "assignments": assignments,
    }


def _terminate_server(server: http.server.HTTPServer | None) -> None:
    if server is None:
        return
    try:
        server.shutdown()
        server.server_close()
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=os.environ.get("FLOWSTEAD_M1_MANIFEST") or os.environ.get("M1_MANIFEST"))
    parser.add_argument("--data", type=Path, default=os.environ.get("FLOWSTEAD_M1_DATA") or os.environ.get("M1_DATA"))
    args = parser.parse_args()
    base_url = os.environ.get("DATABASE_URL")
    if not base_url:
        raise RunnerError("DATABASE_URL is required")
    if args.manifest is None or args.data is None:
        raise RunnerError("FLOWSTEAD_M1_MANIFEST and FLOWSTEAD_M1_DATA are required")
    manifest_path = Path(args.manifest).resolve()
    data_path = Path(args.data).resolve()
    _verify_m1(manifest_path, data_path)

    database_name: str | None = None
    api_process: subprocess.Popen[bytes] | None = None
    auth_server: http.server.HTTPServer | None = None
    previous_handlers: dict[int, object] = {}
    cleanup_started = False

    def request_shutdown(signum: int, _frame: object) -> None:
        if cleanup_started:
            return
        raise RunnerError(f"received signal {signum}; cleaning up owned E2E resources")

    try:
        if _port_occupied(8000):
            raise RunnerError("refusing to start E2E: 127.0.0.1:8000 is already occupied")
        database_name, disposable_url = _create_database(base_url)
        previous_handlers = {signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)}
        for signum in previous_handlers:
            signal.signal(signum, request_shutdown)
        env = os.environ.copy()
        env["DATABASE_URL"] = disposable_url
        if _run(["uv", "run", "--project", "backend", "python", "-m", "backend.migrate", "upgrade"], env) != 0:
            raise RunnerError("Alembic migration failed")
        if _run(["uv", "run", "--project", "backend", "python", "-m", "backend.importer", "--manifest", str(manifest_path), "--data", str(data_path), "--source-sha", SOURCE_SHA], env) != 0:
            raise RunnerError("M1 import failed")
        # Build the deterministic 12-hour forecast so the forecast API returns
        # "available" 12-target points (otherwise it reports unavailable).
        if _run(["uv", "run", "--project", "backend", "python", "-m", "flowstead_api.forecast"], env) != 0:
            raise RunnerError("forecast build failed")
        # Configure a deterministic local Supabase-compatible Auth authority and
        # seed the two disjoint test principals so the real FastAPI authorizes
        # test-principal RS256 JWTs during the browser gate.
        auth_setup = _setup_test_auth(env, disposable_url)
        auth_server = auth_setup["server"]
        private_key = auth_setup["private_key"]
        env["FLOWSTEAD_TEST_PRINCIPAL_A_TOKEN"] = _mint_token(private_key, "test-principal-a")
        env["FLOWSTEAD_TEST_PRINCIPAL_B_TOKEN"] = _mint_token(private_key, "test-principal-b")
        env["FLOWSTEAD_TEST_PRINCIPAL_C_TOKEN"] = _mint_token(private_key, "test-principal-c")
        env["FLOWSTEAD_TEST_EXPIRED_TOKEN"] = _mint_token(private_key, "test-principal-a", minutes=-30)
        env["FLOWSTEAD_TEST_ASSIGNMENTS"] = json.dumps(auth_setup["assignments"])
        api_process = _start_api(env)
        evidence_directory = ROOT / "docs/design/evidence"
        evidence_directory.mkdir(parents=True, exist_ok=True)
        e2e_env = env | {"PLAYWRIGHT_BASE_URL": "http://127.0.0.1:5173", "FLOWSTEAD_EVIDENCE_DIR": str(evidence_directory)}
        if "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH" not in e2e_env or not e2e_env["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]:
            chromium_executable = _find_chromium_executable()
            if chromium_executable:
                e2e_env["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = chromium_executable
        if _run(["npm", "--prefix", "frontend", "run", "e2e"], e2e_env, timeout=300) != 0:
            raise RunnerError("Playwright E2E failed")
        return 0
    finally:
        cleanup_started = True
        try:
            _terminate_server(auth_server)
        finally:
            try:
                _terminate(api_process)
            finally:
                try:
                    _drop_database(database_name, base_url) if database_name is not None else None
                finally:
                    for signum, previous in previous_handlers.items():
                        signal.signal(signum, previous)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as error:
        print(f"E2E runner failed: {error}", file=sys.stderr)
        raise SystemExit(1)
