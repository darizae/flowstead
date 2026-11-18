"""Run the public Flowstead browser gate against an owned disposable database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import SplitResult, quote, urlsplit, urlunsplit
from urllib.request import urlopen

import psycopg

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = "ad5c94d1f46e79312a99cb9721f38700f24fdf6b"
TELEMETRY_SHA256 = "e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e"
DB_PREFIX = "flowstead_test_"

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
    declared_sources = [
        manifest.get(name)
        for name in ("source_sha", "source_commit")
        if name in manifest
    ]
    if not declared_sources or any(source != SOURCE_SHA for source in declared_sources):
        raise RunnerError("M1 manifest must declare source_sha/source_commit exactly matching the pinned source")
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
    try:
        process = subprocess.Popen(
            ["uv", "run", "--project", "backend", "uvicorn", "flowstead_api.main:app", "--app-dir", "backend/src", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT,
            env=env,
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
        api_process = _start_api(env)
        evidence_directory = ROOT / "docs/design/evidence"
        evidence_directory.mkdir(parents=True, exist_ok=True)
        e2e_env = env | {"PLAYWRIGHT_BASE_URL": "http://127.0.0.1:5173", "FLOWSTEAD_EVIDENCE_DIR": str(evidence_directory)}
        if _run(["npm", "--prefix", "frontend", "run", "e2e"], e2e_env, timeout=300) != 0:
            raise RunnerError("Playwright E2E failed")
        return 0
    finally:
        cleanup_started = True
        try:
            _terminate(api_process)
        finally:
            try:
                if database_name is not None:
                    _drop_database(database_name, base_url)
            finally:
                for signum, previous in previous_handlers.items():
                    signal.signal(signum, previous)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as error:
        print(f"E2E runner failed: {error}", file=sys.stderr)
        raise SystemExit(1)
