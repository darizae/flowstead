"""Local staging-like container acceptance for T-015.

Exercises OPS-M15-BUILD, IT-M15-START, SEC-M15-CONFIG and OPS-M15-RECOVER
against an isolated disposable Compose project (fresh PostgreSQL + NATS volumes,
api and worker built from flowstead-backend:local). Requires the staging image
and frontend bundle already built (just build-backend-image / just build).

Run via:  just test-deploy-local
or:       uv run --project backend python scripts/test_deploy_local.py
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

PROJECT = "flowstead-deploy"
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_SRC))

# Isolated loopback ports so the dev stack (54329/42229/8229/8000) can coexist.
PORT_DB = 54339
PORT_NATS = 42239
PORT_NATS_MONITOR = 8239
# Higher port to avoid common dev tools (e.g. tunnels) grabbing 8090.
PORT_API = 18080
DB = "flowstead"
DB_USER = "flowstead"
DB_PASSWORD = "flowstead_local"
DB_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{PORT_DB}/{DB}"
    f"?sslmode=disable"
)
API = f"http://127.0.0.1:{PORT_API}"

import psycopg
from flowstead_api.message_store import enqueue_forecast

from backend.importer import (
    APPROVED_PLANT_IDS,
    SOURCE_SHA,
    import_m1,
)


def compose(
    args: list[str], *, check: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged = {
        **os.environ,
        "COMPOSE_PROJECT_NAME": PROJECT,
        "POSTGRES_PORT": str(PORT_DB),
        "NATS_PORT": str(PORT_NATS),
        "NATS_MONITOR_PORT": str(PORT_NATS_MONITOR),
        "API_PORT": str(PORT_API),
        **(env or {}),
    }
    return subprocess.run(
        ["docker", "compose", *args], cwd=REPO_ROOT, env=merged, text=True, check=check
    )


def sh(*args: list[str], env: dict[str, str] | None = None, check: bool = True) -> str:
    merged = {**os.environ, **(env or {})}
    result = subprocess.run(args, capture_output=True, text=True, check=check, env=merged)
    return result.stdout


def assert_eq(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
    print(f"  ok {label}: {expected!r}")


def assert_true(value: bool, label: str) -> None:
    if not value:
        raise AssertionError(label)
    print(f"  ok {label}")


def wait_ready(path: str, timeout: float = 120.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        code = _http_get(path)
        if code == 200:
            return
        time.sleep(1.0)
    raise AssertionError(f"timed out waiting for {path}")


def _http(method: str, path: str, *, headers: dict[str, str] | None = None) -> tuple[int, str, dict[str, str]]:
    conn = http.client.HTTPConnection("127.0.0.1", PORT_API, timeout=20)
    conn.request(method, path, body=None, headers=headers or {})
    response = conn.getresponse()
    body = response.read().decode("utf-8", "replace")
    resp_headers = {k.lower(): v for k, v in response.getheaders()}
    conn.close()
    return response.status, body, resp_headers


def _http_get(path: str, headers: dict[str, str] | None = None) -> int:
    return _http("GET", path, headers=headers)[0]


def _plant_ids(url: str) -> list[str]:
    conn = http.client.HTTPConnection("127.0.0.1", PORT_API, timeout=20)
    conn.request("GET", "/api/v1/public/plants")
    response = conn.getresponse()
    body = json.loads(response.read().decode())
    conn.close()
    return [p["plant_id"] for p in body["plants"]]


def _fingerprint(cur) -> str:
    """Checksum of deterministic M1 seed content (runtime pipeline state
    excluded, so restore and re-import must reproduce the identical seed)."""
    counts: dict[str, int] = {}
    for table in ("plants", "hourly_readings", "ingest_batches"):
        (counts[table],) = cur.execute(
            f"SELECT count(*) FROM app.{table}"
        ).fetchone()
    digests = cur.execute(
        "SELECT content_sha256 FROM app.ingest_batches ORDER BY id"
    ).fetchall()
    payload = json.dumps(
        {"counts": counts, "ingest_digests": [d[0] for d in digests]}, sort_keys=True
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _job_status(cur, correlation_id: str) -> str:
    (status,) = cur.execute(
        "SELECT status FROM app.forecast_jobs WHERE correlation_id = %s",
        (correlation_id,),
    ).fetchone()
    return status


def main() -> int:
    print(f"== {PROJECT}: local staging-like container acceptance ==")

    # --- OPS-M15-BUILD --------------------------------------------
    print("OPS-M15-BUILD: production image + frontend bundle, no secrets")
    image = sh("docker", "image", "inspect", "flowstead-backend:local", check=False).strip()
    assert_true(bool(image), "flowstead-backend:local image exists")
    image_env = sh("docker", "run", "--rm", "--entrypoint", "printenv", "flowstead-backend:local")
    for secret in ("SUPABASE", "DATABASE_URL", "service-role", "flowstead_local"):
        assert_true(secret not in image_env, f"image env does not leak {secret!r}")
    # Non-root runtime identity.
    who = sh("docker", "run", "--rm", "--entrypoint", "id", "flowstead-backend:local", "-u").strip()
    assert_eq(who, "10001", "image runs as non-root uid 10001")
    dist = REPO_ROOT / "frontend" / "dist"
    assert_true(dist.exists(), "frontend/dist exists after just build")
    bundle = "".join(p.read_text(errors="ignore") for p in dist.rglob("*.js"))
    assert_true(
        "https://api.flowstead.darizae.dev/api/v1" in bundle,
        "bundle contains the explicit HTTPS API URL",
    )
    for secret in ("flowstead_local", "service-role", "SUPABASE_PASSWORD"):
        assert_true(secret not in bundle, f"bundle does not leak {secret!r}")

    # --- IT-M15-START / SEC-M15-CONFIG : boot the isolated stack ----
    print("IT-M15-START: boot isolated PostgreSQL + NATS + API + worker")
    for port in (PORT_DB, PORT_NATS, PORT_API):
        used = sh("lsof", "-nP", "-iTCP", f":{port}", "-sTCP:LISTEN", check=False)
        assert_true(not used.strip(), f"loopback port {port} is free")
    # Boot order mirrors a real deploy: infrastructure first, then Alembic
    # upgrade-to-head, then the API and worker (so they never race the schema).
    compose(["up", "-d", "--wait", "db", "nats"])

    # Real Alembic upgrade-to-head on the fresh disposable database.
    sh(
        "uv", "run", "--project", str(REPO_ROOT / "backend"),
        "python", "-m", "backend.migrate", "upgrade",
        env={"DATABASE_URL": DB_URL},
    )
    with psycopg.connect(DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        (version,) = cur.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        assert_eq(version, "003_jetstream_messages", "Alembic reaches head 003_jetstream_messages")

    # Real M1 import (canonical source) into the fresh database.
    manifest, data = _write_import(REPO_ROOT / ".deploy_test")
    assert_true(import_m1(DB_URL, manifest, data, SOURCE_SHA), "M1 import succeeds")
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        import_fp = _fingerprint(cur)
    # Supplement with a bounded history window and explicit operator access so
    # the real worker can compute a forecast for the private pipeline path.
    _seed_readings(DB_URL)
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        seed_before = _fingerprint(cur)
    # Boot the API and forecast worker against the migrated, seeded database.
    compose(["up", "-d", "--wait", "api", "worker"])
    wait_ready("/api/v1/health/ready")
    wait_ready("/api/v1/health")

    # --- SEC-M15-CONFIG -------------------------------------------
    print("SEC-M15-CONFIG: fail-closed auth, CORS, no open signup/SQL")
    status, _, headers = _http("GET", "/api/v1/plants")
    assert_eq(status, 401, "private route fails closed without auth config")
    status, _, headers = _http(
        "GET", "/api/v1/public/plants", headers={"Origin": "http://127.0.0.1:5173"}
    )
    assert_eq(status, 200, "allowed loopback origin is served")
    assert_eq(
        headers.get("access-control-allow-origin"), "http://127.0.0.1:5173",
        "CORS echoes the reviewed allowed origin",
    )
    status, _, headers = _http(
        "GET", "/api/v1/public/plants", headers={"Origin": "https://evil.example"}
    )
    assert_true(
        "access-control-allow-origin" not in headers,
        "CORS does not echo an unreviewed origin",
    )
    for path in ("/api/v1/auth/signup", "/api/v1/signup", "/api/v1/sql", "/api/v1/query"):
        status, _, _ = _http("GET", path)
        assert_eq(status, 404, f"no open endpoint at {path}")
    # Bounded request: oversized body is rejected with 413 before any route.
    conn = http.client.HTTPConnection("127.0.0.1", PORT_API, timeout=20)
    conn.putrequest("POST", "/api/v1/health")
    conn.putheader("Content-Length", "99999")
    conn.endheaders()
    response = conn.getresponse()
    status = response.status
    response.read()
    conn.close()
    assert_eq(status, 413, "oversized body is bounded (413)")
    # Bounded read: public plants list is bounded to the approved five.
    plants = _plant_ids(API)
    assert_eq(sorted(plants), sorted(APPROVED_PLANT_IDS), "public plants bounded to approved set")

    # --- IT-M15-START : outbox -> JetStream -> worker -> restart ----
    print("IT-M15-START: message pipeline (outbox replay through worker restart)")
    # Enqueue through the shared message_store path (the HTTP route is private
    # and fails closed under no-auth staging, which is the SEC-M15-CONFIG proof).
    job = enqueue_forecast(DB_URL, plant_id="plant-01", subject_id="operator-a")
    assert_true(job is not None, "forecast command enqueued to outbox + job")
    correlation_id = str(job.correlation_id)

    def wait_job(target: str, timeout: float = 90.0) -> str:
        deadline = time.monotonic() + timeout
        status = None
        while time.monotonic() < deadline:
            with psycopg.connect(DB_URL) as c, c.cursor() as cur:
                status = _job_status(cur, target)
            if status in {"completed", "failed", "dead_lettered"}:
                return status
            time.sleep(1.0)
        raise AssertionError(f"job {target} reached {status!r} within timeout")

    assert_eq(wait_job(correlation_id), "completed", "worker processed one message to completion")

    # Restart recovery: stop worker, enqueue a second command, restart, verify
    # it completes (durable consumer + outbox replay survive the restart).
    compose(["stop", "worker"])
    job2 = enqueue_forecast(DB_URL, plant_id="plant-02", subject_id="operator-a")
    assert_true(job2 is not None, "second forecast command enqueued while worker stopped")
    with psycopg.connect(DB_URL) as c, c.cursor() as cur:
        (outbox_status,) = cur.execute(
            "SELECT status FROM app.message_outbox WHERE event_id = %s",
            (job2.request_event_id,),
        ).fetchone()
        assert_eq(outbox_status, "pending", "pending outbox row survives worker stop (uncatchable)")
    compose(["start", "worker"])
    assert_eq(
        wait_job(str(job2.correlation_id)),
        "completed",
        "restarted worker replays pending outbox to completion",
    )

    # --- Graceful shutdown -----------------------------------------
    print("IT-M15-START: graceful shutdown")
    compose(["stop", "api", "worker"])
    for service in ("api", "worker"):
        cid = f"{PROJECT}-{service}-1"
        exit_code = sh("docker", "inspect", "-f", "{{.State.ExitCode}}", cid).strip()
        assert_eq(exit_code, "0", f"{service} exited 0 on SIGTERM (graceful)")

    # --- OPS-M15-RECOVER ------------------------------------------
    print("OPS-M15-RECOVER: backup / restore / reseed / rollback on a disposable copy")
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        (n,) = cur.execute("SELECT count(*) FROM app.plants").fetchone()
    assert_true(n == 5, "seeded plants present before backup")

    dump = REPO_ROOT / ".deploy_test" / "flowstead.sql"
    dump.parent.mkdir(parents=True, exist_ok=True)
    with dump.open("w", encoding="utf-8") as out:
        subprocess.run(
            ["docker", "compose", "-p", PROJECT, "exec", "-T", "db", "pg_dump", "-U", DB_USER, "-d", DB],
            cwd=REPO_ROOT, env=os.environ, stdout=out, text=True, check=True,
        )

    recover = "flowstead_recover"
    with psycopg.connect(DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{recover}"')
    restore_url = DB_URL.replace("/flowstead?", f"/{recover}?")
    with dump.open("rb") as src:
        subprocess.run(
            ["docker", "compose", "-p", PROJECT, "exec", "-T", "db", "psql", "-U", DB_USER, "-d", recover],
            cwd=REPO_ROOT, env=os.environ, stdin=src, text=False, check=True,
        )
    with psycopg.connect(restore_url) as conn, conn.cursor() as cur:
        restored = _fingerprint(cur)
        assert_eq(restored, seed_before, "restored copy fingerprint equals seed (restore)")
    # Reseed: build a fresh disposable database, migrate to head and re-import
    # M1, then confirm the seed fingerprint reproduces (deterministic synthetic
    # reseed restores known data checksums).
    reseed_db = "flowstead_reseed"
    with psycopg.connect(DB_URL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{reseed_db}"')
    reseed_url = DB_URL.replace("/flowstead?", f"/{reseed_db}?")
    sh(
        "uv", "run", "--project", str(REPO_ROOT / "backend"),
        "python", "-m", "backend.migrate", "upgrade",
        env={"DATABASE_URL": reseed_url},
    )
    manifest, data = _write_import(REPO_ROOT / ".deploy_test")
    import_m1(reseed_url, manifest, data, SOURCE_SHA)
    with psycopg.connect(reseed_url) as conn, conn.cursor() as cur:
        reseed = _fingerprint(cur)
        assert_eq(reseed, import_fp, "reseeded disposable DB reproduces the import fingerprint")

    # Rollback: record the running image digest as the rollback target and
    # confirm the tagged image still resolves (documented revert command).
    digest = sh(
        "docker", "image", "inspect", "--format",
        "{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}",
        "flowstead-backend:local",
    ).strip()
    assert_true(bool(digest), f"image digest recorded for rollback ({digest})")

    # --- teardown ---------------------------------------------------
    print("teardown: removing disposable stack")
    compose(["down", "-v"])

    print("RESULT: OPS-M15-BUILD, IT-M15-START, SEC-M15-CONFIG, OPS-M15-RECOVER passed")
    return 0


def _seed_readings(database_url: str) -> None:
    """Insert a bounded hourly history + operator access on a seeded database."""
    with psycopg.connect(database_url) as conn, conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM app.ingest_batches ORDER BY id LIMIT 1"
        )
        (batch_id,) = cur.fetchone()
        start = datetime(2026, 11, 16, tzinfo=UTC)
        for plant_id in ("plant-01", "plant-02"):
            for hour in range(25):
                cur.execute(
                    """
                    INSERT INTO app.hourly_readings
                        (plant_id, timestamp_utc, influent_flow,
                         influent_flow_quality, rainfall, rainfall_quality,
                         dissolved_oxygen, dissolved_oxygen_quality,
                         effluent_ph, effluent_ph_quality, source_batch_id)
                    VALUES (%s, %s, %s, 'valid', 0, 'valid', 2, 'valid',
                            7, 'valid', %s)
                    """,
                    (plant_id, start + timedelta(hours=hour), Decimal(100) + hour, batch_id),
                )
        cur.executemany(
            "INSERT INTO app.operator_plant_access (subject_id, plant_id) VALUES (%s, %s)",
            [("operator-a", "plant-01"), ("operator-a", "plant-02")],
        )


def _write_import(tmp: Path) -> tuple[Path, Path]:
    tmp.mkdir(parents=True, exist_ok=True)
    data = tmp / "telemetry.csv"
    # All five approved plants so the public list is fully populated.
    header = (
        "plant_id,timestamp_utc,influent_flow,influent_flow_quality,rainfall,"
        "rainfall_quality,dissolved_oxygen,dissolved_oxygen_quality,"
        "effluent_ph,effluent_ph_quality"
    )
    csv_rows = []
    for pid in sorted(APPROVED_PLANT_IDS):
        csv_rows.append(
            f"{pid},2026-11-18T00:00:00Z,100,valid,0,valid,2,valid,7,valid"
        )
    data.write_text(header + "\n" + "\n".join(csv_rows) + "\n", encoding="utf-8")
    manifest = tmp / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "m1.v1",
                "generator_version": "deploy-smoke",
                "seed": 20250101,
                "provenance": "synthetic",
                "source_sha": SOURCE_SHA,
                "units": {
                    "influent_flow": "gal/h",
                    "rainfall": "in/h",
                    "dissolved_oxygen": "mg/L",
                    "effluent_ph": "unitless",
                },
                "plants": sorted(APPROVED_PLANT_IDS),
                "files": {
                    "telemetry.csv": {
                        "sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
                        "bytes": data.stat().st_size,
                        "rows": 5,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return manifest, data


if __name__ == "__main__":
    raise SystemExit(main())