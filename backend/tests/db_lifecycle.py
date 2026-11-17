"""Safe, controller-owned local Docker PostgreSQL lifecycle for integration gates.

This CLI only manages the DB service defined by Flowstead's compose.yml.
It does not run migrations, truncate tables or stop a healthy owned database.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import time
from collections.abc import Callable
from urllib.parse import urlsplit

DEFAULT_PORT = 54329


class DatabaseLifecycleError(RuntimeError):
    """Docker endpoint ownership or readiness could not be established."""


def _docker(argv: list[str]) -> str:
    try:
        return subprocess.run(
            argv, check=True, text=True, capture_output=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        # Do not publish unfiltered stderr/paths/credentials in automated receipts.
        if isinstance(exc, subprocess.CalledProcessError):
            stderr = exc.stderr or ""
            if "port is already allocated" in stderr or "Bind for " in stderr:
                raise DatabaseLifecycleError(
                    "PostgreSQL port allocation raced with another owner; "
                    "inspect the host endpoint and Docker port bindings"
                ) from exc
            raise DatabaseLifecycleError(
                f"Docker command failed (exit {exc.returncode}); "
                "inspect the restricted local Docker log"
            ) from exc
        raise DatabaseLifecycleError("Docker CLI is not available") from exc


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def _containers(run: Callable[[list[str]], str]) -> list[dict]:
    ids = run(["docker", "ps", "-aq"]).split()
    containers: list[dict] = []
    for identifier in ids:
        payload = json.loads(run(["docker", "inspect", identifier]))
        if len(payload) != 1 or not isinstance(payload[0], dict):
            raise DatabaseLifecycleError("unexpected Docker inspect payload")
        containers.append(payload[0])
    return containers


def _bindings(container: dict) -> list[dict]:
    return (container.get("HostConfig", {}).get("PortBindings") or {}).get(
        "5432/tcp", []
    ) or []


def _published_on_loopback(container: dict, port: int) -> bool:
    return any(
        str(item.get("HostPort", "")) == str(port)
        and item.get("HostIp", "") in {"127.0.0.1", "0.0.0.0", "", "::"}
        for item in _bindings(container)
    )


def _owner(container: dict, port: int, db_name: str, db_user: str) -> bool:
    labels = container.get("Config", {}).get("Labels") or {}
    project = labels.get("com.docker.compose.project", "")
    config_files = labels.get("com.docker.compose.project.config_files", "")
    expected_project = os.environ.get("COMPOSE_PROJECT_NAME", "flowstead")
    controlled = (
        project == expected_project
        or project == "flowstead"
        or re.fullmatch(r"verify-[0-9]+", project) is not None
    )
    environment = set(container.get("Config", {}).get("Env") or [])
    return bool(
        controlled
        and labels.get("com.docker.compose.service") == "db"
        and any(value.strip().endswith("compose.yml") for value in config_files.split(","))
        and container.get("Config", {}).get("Image") == "postgres:16-alpine"
        and "POSTGRES_DB=" + db_name in environment
        and "POSTGRES_USER=" + db_user in environment
        and _published_on_loopback(container, port)
    )


def _running(container: dict) -> bool:
    return bool(container.get("State", {}).get("Running"))


def _health(container: dict) -> str:
    return (container.get("State", {}).get("Health") or {}).get("Status", "missing")


def _candidate(
    containers: list[dict], port: int, db_name: str, db_user: str
) -> dict | None:
    occupying = [
        item for item in containers
        if _running(item) and _published_on_loopback(item, port)
    ]
    for item in occupying:
        if not _owner(item, port, db_name, db_user):
            raise DatabaseLifecycleError(
                f"foreign Docker container {item.get('Id', '?')[:12]} owns "
                f"127.0.0.1:{port}; refusing to start/restart a database"
            )
    owned = [
        item for item in containers if _owner(item, port, db_name, db_user)
    ]
    running = [item for item in owned if _running(item)]
    if len(running) > 1:
        raise DatabaseLifecycleError(
            f"multiple controller-owned databases publish 127.0.0.1:{port}"
        )
    if running:
        return running[0]
    if len(owned) > 1:
        raise DatabaseLifecycleError(
            f"multiple stopped controller-owned databases claim 127.0.0.1:{port}; "
            "select a single Docker project manually"
        )
    return owned[0] if owned else None


def _check_url(port: int, db_name: str, *, required: bool) -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        if required:
            raise DatabaseLifecycleError(
                "DATABASE_URL is unset: integration gates require an explicit local DB URL"
            )
        return
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or (parsed.port or 5432) != port
        or parsed.path.lstrip("/") != db_name
    ):
        raise DatabaseLifecycleError(
            f"DATABASE_URL does not target the controller-owned "
            f"127.0.0.1:{port}/{db_name}; refusing integration against another DB"
        )


def ensure_database(
    *,
    run: Callable[[list[str]], str] = _docker,
    port_open: Callable[[int], bool] = _port_open,
    pause: Callable[[float], None] = time.sleep,
    port: int = DEFAULT_PORT,
    db_name: str = "flowstead",
    db_user: str = "flowstead",
    retries: int = 40,
) -> str:
    """Reuse healthy, start stopped, or restart unhealthy *owned* database only."""
    if not (1 <= port <= 65535):
        raise DatabaseLifecycleError("invalid PostgreSQL port")
    containers = _containers(run)
    selected = _candidate(containers, port, db_name, db_user)
    if selected is None:
        if port_open(port):
            raise DatabaseLifecycleError(
                f"foreign host process owns 127.0.0.1:{port} "
                "(no controller-owned Docker binding); no compose up attempted"
            )
        # It is safe to create only when no known controller DB and no port owner exist.
        run(["docker", "compose", "up", "-d", "db"])
        selected = _candidate(_containers(run), port, db_name, db_user)
        if selected is None:
            raise DatabaseLifecycleError(
                "docker compose up produced no recognizable controller-owned db"
            )
        action = "created"
    else:
        identifier = selected["Id"]
        if not _running(selected):
            if port_open(port):
                raise DatabaseLifecycleError(
                    f"foreign host process owns 127.0.0.1:{port}; "
                    "owned stopped DB cannot start"
                )
            run(["docker", "start", identifier])
            action = "started"
        elif _health(selected) == "unhealthy":
            run(["docker", "restart", identifier])
            action = "restarted"
        elif _health(selected) in {"healthy", "starting"}:
            action = "reused"
        else:
            raise DatabaseLifecycleError(
                "controller-owned database is running without a recognized Docker "
                "healthcheck; refusing blind restart"
            )

    identifier = selected["Id"]
    for attempt in range(retries):
        status = json.loads(run(["docker", "inspect", identifier]))[0]
        if not _owner(status, port, db_name, db_user):
            raise DatabaseLifecycleError("database ownership changed during readiness check")
        if _running(status) and _health(status) == "healthy" and port_open(port):
            return action
        if _health(status) == "unhealthy":
            raise DatabaseLifecycleError(
                f"controller-owned PostgreSQL on 127.0.0.1:{port} is unhealthy "
                "after the permitted lifecycle action"
            )
        if attempt + 1 < retries:
            pause(1)
    raise DatabaseLifecycleError(
        f"controller-owned PostgreSQL on 127.0.0.1:{port} failed readiness "
        f"after {retries} health probes"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-database-url", action="store_true")
    args = parser.parse_args()
    try:
        port = int(os.environ.get("POSTGRES_PORT", str(DEFAULT_PORT)))
        db_name = os.environ.get("POSTGRES_DB", "flowstead")
        db_user = os.environ.get("POSTGRES_USER", "flowstead")
        _check_url(port, db_name, required=args.require_database_url)
        result = ensure_database(port=port, db_name=db_name, db_user=db_user)
    except (DatabaseLifecycleError, ValueError) as exc:
        parser.exit(1, f"Flowstead PostgreSQL preflight: {exc}\n")
    print(f"Flowstead PostgreSQL 127.0.0.1:{port}: {result}, healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
