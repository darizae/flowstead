"""Isolated pinned NATS 2 JetStream container lifecycle."""

from __future__ import annotations

import re
import subprocess
import time
import uuid

from .proc import RunnerError, port_occupied

NATS_IMAGE = "nats:2.12-alpine@sha256:b270f5e2428354c0335612694d7dd2fb588148e567a5757fdff325ef9c9332e6"
ROOT_TIMEOUT = 30


def start_nats() -> tuple[str, str]:
    name = f"flowstead-e2e-nats-{uuid.uuid4().hex}"
    command = [
        "docker",
        "run",
        "--detach",
        "--rm",
        "--name",
        name,
        "--publish",
        "127.0.0.1::4222",
        NATS_IMAGE,
        "-js",
        "-sd",
        "/data",
    ]
    result = subprocess.run(
        command, cwd=None, check=False, capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RunnerError(f"isolated NATS failed to start: {result.stderr.strip()}")
    try:
        port_result = subprocess.run(
            ["docker", "port", name, "4222/tcp"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        match = re.search(r":(\d+)\s*$", port_result.stdout)
        if port_result.returncode != 0 or match is None:
            raise RunnerError(
                f"isolated NATS port lookup failed: {port_result.stderr.strip()}"
            )
        port = int(match.group(1))
        deadline = time.monotonic() + ROOT_TIMEOUT
        while time.monotonic() < deadline:
            if port_occupied(port):
                return name, f"nats://127.0.0.1:{port}"
            time.sleep(0.2)
        raise RunnerError("isolated NATS did not accept connections within 30 seconds")
    except BaseException:
        stop_nats(name)
        raise


def stop_nats(name: str | None) -> None:
    if name is None:
        return
    subprocess.run(
        ["docker", "rm", "--force", name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=15,
    )
