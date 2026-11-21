"""Hosted-config local acceptance for T-016 (OPS-M16-ARM/QUEUE, SEC-M16-NET).

Boots compose.hosted.yml — the OCI-hosted stack with NO local PostgreSQL service
— against an EXTERNAL disposable PostgreSQL (a temporary `docker run` database,
standing in for the hosted Supabase), then proves the durable queue survives a
worker restart and that only the proxy publishes host ports.

Requires flowstead-backend:amd64-hosted already built (`just build-backend-image-host`).
Run via:  just test-deploy-hosted
or:       uv run --project backend python scripts/test_deploy_hosted.py
"""

from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
# backend.importer / flowstead_api / the shared test helpers are imported at
# module load, so the repo root and backend src must be importable first.
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_SRC))

import psycopg

from backend.importer import APPROVED_PLANT_IDS, SOURCE_SHA, import_m1
from flowstead_api.message_store import enqueue_forecast
from test_deploy_local import (
    _job_status,
    _seed_readings,
    _write_import,
    assert_eq,
    assert_true,
    sh,
)

PROJECT = "flowstead-demo"

# External disposable PostgreSQL (NOT part of compose.hosted.yml).
TEST_PG_CONTAINER = "flowstead-hosted-test-db"
PORT_PG = 54439
DB = "flowstead"
DB_USER = "flowstead"
DB_PASSWORD = "flowstead_local"
HOST_DB_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{PORT_PG}/{DB}?sslmode=disable"
)
# Containers reach the host-mapped DB through Docker Desktop's host gateway.
CONTAINER_DB_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@host.docker.internal:{PORT_PG}/{DB}?sslmode=disable"
)

IMAGE = "flowstead-backend:amd64-hosted"
NATS_IMAGE = "nats:2.12-alpine@sha256:b270f5e2428354c0335612694d7dd2fb588148e567a5757fdff325ef9c9332e6"
CADDY_IMAGE = "caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d"

# Proxy host ports for the local smoke (loopback only).
PORT_PROXY_HTTP = 18081
PORT_PROXY_HTTPS = 18443
PROXY_API = f"http://127.0.0.1:{PORT_PROXY_HTTP}"
TEST_DIR = REPO_ROOT / ".deploy_test" / "hosted"
OVERRIDE = TEST_DIR / "override.yml"
SECRET_ENV = TEST_DIR / "hosted.env"


def compose(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    merged = {
        **os.environ,
        "COMPOSE_PROJECT_NAME": PROJECT,
        "HOSTED_ENV_FILE": str(SECRET_ENV),
        "PROXY_HTTP_PORT": str(PORT_PROXY_HTTP),
        "PROXY_HTTPS_PORT": str(PORT_PROXY_HTTPS),
    }
    return subprocess.run(
        ["docker", "compose", "-f", "compose.hosted.yml", "-f", str(OVERRIDE), *args],
        cwd=REPO_ROOT, env=merged, text=True, check=check, capture_output=True,
    )


def wait_ready(path: str, timeout: float = 150.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", PORT_PROXY_HTTP, timeout=10)
            conn.request("GET", path)
            code = conn.getresponse().status
            conn.close()
            if code == 200:
                return
        except OSError:
            pass
        time.sleep(1.0)
    raise AssertionError(f"timed out waiting for {PROXY_API}{path}")


def http_get(path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str]]:
    conn = http.client.HTTPConnection("127.0.0.1", PORT_PROXY_HTTP, timeout=20)
    conn.request("GET", path, headers=headers or {})
    response = conn.getresponse()
    body = response.read().decode("utf-8", "replace")
    resp_headers = {k.lower(): v for k, v in response.getheaders()}
    conn.close()
    return response.status, resp_headers, body


def main() -> int:
    print(f"== {PROJECT}: hosted-config (no local PostgreSQL) acceptance ==")

    # ---- OPS-M16-ARM ------------------------------------------------
    print("OPS-M16-ARM: linux/amd64 images and manifests")
    arch = sh("docker", "image", "inspect", "--format", "{{.Os}}/{{.Architecture}}", IMAGE).strip()
    assert_eq(arch, "linux/amd64", f"{IMAGE} is a linux/amd64 image")
    for ref in (NATS_IMAGE, CADDY_IMAGE):
        avail = sh("docker", "manifest", "inspect", ref, check=False)
        manifest = json.loads(avail)
        has_amd64 = any(
            m.get("platform", {}).get("os") == "linux"
            and m.get("platform", {}).get("architecture") == "amd64"
            for m in manifest.get("manifests", [])
        )
        assert_true(has_amd64, f"{ref} publishes a linux/amd64 manifest")
    image_env = sh("docker", "run", "--rm", "--entrypoint", "printenv", IMAGE)
    for secret in ("SUPABASE", "DATABASE_URL", "service-role", "flowstead_local"):
        assert_true(secret not in image_env, f"{IMAGE} does not bake {secret!r}")
    who = sh("docker", "run", "--rm", "--entrypoint", "id", IMAGE, "-u").strip()
    assert_eq(who, "10001", "hosted image runs as non-root uid 10001")

    # ---- SEC-M16-NET (config level) --------------------------------
    print("SEC-M16-NET: only the proxy publishes host ports (8000/4222/8222 non-public)")
    # The compose contract: only `proxy` declares host ports. Verified again on
    # live containers after boot via `docker port` (loopback/local only here).
    cfg = sh("docker", "compose", "-f", "compose.hosted.yml", "config", check=False)
    for stale in ("5432:", ":4222:", ":8222:", ":8000:"):
        assert_true(stale not in cfg, f"hosted compose never publishes {stale.strip(':')!r}")

    # ---- infrastructure: external disposable PostgreSQL -------------
    print("IT: disposable EXTERNAL PostgreSQL (hosted compose has no db service)")
    sh(
        "docker", "rm", "-f", TEST_PG_CONTAINER, check=False,
    )
    sh(
        "docker", "run", "-d", "--name", TEST_PG_CONTAINER,
        "-e", f"POSTGRES_DB={DB}", "-e", f"POSTGRES_USER={DB_USER}",
        "-e", f"POSTGRES_PASSWORD={DB_PASSWORD}",
        "-p", f"127.0.0.1:{PORT_PG}:5432", "postgres:16-alpine",
    )
    try:
        deadline = time.monotonic() + 90
        while True:
            try:
                with psycopg.connect(HOST_DB_URL, connect_timeout=3) as c:
                    c.execute("SELECT 1")
                break
            except (psycopg.Error, OSError):
                if time.monotonic() > deadline:
                    raise AssertionError("external test PostgreSQL did not become ready")
                time.sleep(1.0)

        # ---- real Alembic + M1 import against the external DB ----------
        sh(
            "uv", "run", "--project", str(REPO_ROOT / "backend"),
            "python", "-m", "backend.migrate", "upgrade",
            env={"DATABASE_URL": HOST_DB_URL},
        )
        with psycopg.connect(HOST_DB_URL, autocommit=True) as conn, conn.cursor() as cur:
            (version,) = cur.execute("SELECT version_num FROM alembic_version").fetchone()
            assert_eq(version, "003_jetstream_messages", "Alembic reaches head 003_jetstream_messages")
        manifest, data = _write_import(TEST_DIR)
        assert_true(import_m1(HOST_DB_URL, manifest, data, SOURCE_SHA), "M1 import succeeds")
        _seed_readings(HOST_DB_URL)
        with psycopg.connect(HOST_DB_URL) as conn, conn.cursor() as cur:
            (n,) = cur.execute("SELECT count(*) FROM app.plants").fetchone()
            assert_eq(n, 5, "exactly five synthetic Plants imported")

        # ---- secret env file (simulating the host secret-store) -------
        TEST_DIR.mkdir(parents=True, exist_ok=True)
        SECRET_ENV.write_text(
            "\n".join(
                [
                    f"DATABASE_URL={CONTAINER_DB_URL}",
                    "FLOWSTEAD_AUTH_MODE=supabase",
                    "FLOWSTEAD_CORS_ORIGINS=http://127.0.0.1:5173",
                    "FLOWSTEAD_TRUSTED_PROXIES=",
                    "FLOWSTEAD_RATE_LIMIT_REQUESTS=600",
                    "FLOWSTEAD_RATE_LIMIT_WINDOW_SECONDS=60",
                    "FLOWSTEAD_RATE_LIMIT_MAX_CLIENTS=4096",
                    "FLOWSTEAD_MAX_REQUEST_BODY_BYTES=16384",
                    "FLOWSTEAD_MAX_REQUEST_TARGET_BYTES=8192",
                    "FLOWSTEAD_FORECAST_RATE_LIMIT_REQUESTS=30",
                    "FLOWSTEAD_FORECAST_RATE_LIMIT_WINDOW_SECONDS=60",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        OVERRIDE.write_text(
            "services:\n"
            "  proxy:\n"
            "    volumes:\n"
            "      - ./deploy/oci/Caddyfile.test:/etc/caddy/Caddyfile:ro\n",
            encoding="utf-8",
        )

        # ---- boot hosted stack (nats, api, worker, proxy) ------------
        print("IT: boot compose.hosted.yml (nats + api + worker + proxy)")
        for port in (PORT_PG, PORT_PROXY_HTTP, PORT_PROXY_HTTPS):
            used = sh("lsof", "-nP", "-iTCP", f":{port}", "-sTCP:LISTEN", check=False)
            assert_true(not used.strip(), f"loopback port {port} is free")
        compose(["up", "-d", "--wait", "nats", "api", "worker", "proxy"])
        wait_ready("/api/v1/health/ready")
        wait_ready("/api/v1/health")

        # ---- SEC-M16-NET: live containers expose no API/NATS ports ----
        # `docker port <cid>` lists real host-published bindings; EXPOSE alone
        # prints nothing (the app ports are reachable only inside the network).
        for svc in ("api", "nats", "worker"):
            cid = compose(["ps", "-q", svc]).stdout.strip()
            published = sh("docker", "port", cid).strip()
            assert_true(not published, f"{svc} publishes no host ports ({published!r})")

        # ---- public reads via the proxy (bounded synthetic) ----------
        status, headers, body = http_get("/api/v1/public/plants")
        assert_eq(status, 200, "public plants reachable through the proxy")
        ids = sorted(p["plant_id"] for p in json.loads(body)["plants"])
        assert_eq(ids, sorted(APPROVED_PLANT_IDS), "public plants bounded to the approved five")
        status, _, _ = http_get(
            "/api/v1/public/plants", headers={"Origin": "http://127.0.0.1:5173"}
        )
        assert_eq(status, 200, "allowed loopback origin served through proxy")
        status, headers, _ = http_get(
            "/api/v1/public/plants", headers={"Origin": "https://evil.example"}
        )
        assert_true("access-control-allow-origin" not in headers,
                    "CORS does not echo an unreviewed origin")
        # Fail-closed private route (no Supabase auth config in this test env).
        status, _, _ = http_get("/api/v1/plants")
        assert_eq(status, 401, "private route fails closed through the proxy")

        # ---- OPS-M16-QUEUE: durable worker + restart recovery ---------
        print("OPS-M16-QUEUE: outbox → JetStream → worker → restart recovery")
        job = enqueue_forecast(HOST_DB_URL, plant_id="plant-01", subject_id="operator-a")
        assert_true(job is not None, "forecast command enqueued to outbox + job")

        def wait_job(target: str, timeout: float = 120.0) -> str:
            deadline = time.monotonic() + timeout
            status = None
            while time.monotonic() < deadline:
                with psycopg.connect(HOST_DB_URL) as c, c.cursor() as cur:
                    status = _job_status(cur, target)
                if status in {"completed", "failed", "dead_lettered"}:
                    return status
                time.sleep(1.0)
            raise AssertionError(f"job {target} reached {status!r} within timeout")

        assert_eq(wait_job(str(job.correlation_id)), "completed",
                  "worker processed a message to completion")
        compose(["stop", "worker"])
        job2 = enqueue_forecast(HOST_DB_URL, plant_id="plant-02", subject_id="operator-a")
        assert_true(job2 is not None, "second command enqueued while worker stopped")
        with psycopg.connect(HOST_DB_URL) as c, c.cursor() as cur:
            (outbox_status,) = cur.execute(
                "SELECT status FROM app.message_outbox WHERE event_id = %s",
                (job2.request_event_id,),
            ).fetchone()
            assert_eq(outbox_status, "pending", "pending outbox survives worker stop")
        compose(["start", "worker"])
        assert_eq(wait_job(str(job2.correlation_id)), "completed",
                  "restarted worker replays pending outbox to completion (durable queue)")

        # ---- graceful shutdown ---------------------------------------
        # Capture container ids while running; `ps -q` returns nothing for a
        # stopped service, so do not re-resolve after `stop`.
        api_cid = compose(["ps", "-q", "api"]).stdout.strip()
        worker_cid = compose(["ps", "-q", "worker"]).stdout.strip()
        assert_true(bool(api_cid and worker_cid), "api/worker container ids captured")
        compose(["stop", "api", "worker", "proxy"])
        for label, cid in (("api", api_cid), ("worker", worker_cid)):
            exit_code = sh("docker", "inspect", "-f", "{{.State.ExitCode}}", cid).strip()
            assert_eq(exit_code, "0", f"{label} exited 0 on SIGTERM (graceful)")

        digest = sh("docker", "image", "inspect", "--format",
                    "{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}", IMAGE).strip()
        assert_true(bool(digest), f"image digest recorded for rollback ({digest})")

        print(f"RESULT: pass. host DB {n} plants; hosted image digest {digest}")
        print("Live OCI VM/billing/TLS/DNS checks are UNVERIFIED in this local run.")
        return 0
    finally:
        print("teardown: removing hosted stack + external test PostgreSQL")
        compose(["down", "-v"], check=False)
        sh("docker", "rm", "-f", TEST_PG_CONTAINER, check=False)


if __name__ == "__main__":
    raise SystemExit(main())