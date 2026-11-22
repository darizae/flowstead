"""Subprocess and process-group lifecycle helpers for the local E2E harness."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class RunnerError(RuntimeError):
    """Raised when the real local E2E environment cannot be established."""


def run(
    command: list[str], env: dict[str, str], *, timeout: float | None = None
) -> int:
    try:
        completed = subprocess.run(
            command, cwd=ROOT, env=env, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as error:
        raise RunnerError(f"command timed out: {' '.join(command)}") from error
    return completed.returncode


def terminate(process: subprocess.Popen[bytes] | None) -> None:
    """Terminate a process-group leader started with ``start_new_session=True``."""
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        if process.poll() is None:
            process.wait(timeout=10)
        return
    except (ProcessLookupError, subprocess.TimeoutExpired):
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
        if process.poll() is None:
            process.wait(timeout=5)
        return
    except (ProcessLookupError, subprocess.TimeoutExpired):
        pass


def add_repo_to_pythonpath(env: dict[str, str]) -> dict[str, str]:
    """Prepend the checkout root so backend.* modules resolve in child processes."""
    merged = env.copy()
    merged["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(ROOT), merged.get("PYTHONPATH")) if value
    )
    return merged


def port_occupied(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False
