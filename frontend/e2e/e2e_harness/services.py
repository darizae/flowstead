"""Durable worker and FastAPI startup against the disposable E2E environment."""

from __future__ import annotations

import subprocess
import time
from urllib.request import urlopen

from .proc import RunnerError, add_repo_to_pythonpath, port_occupied, terminate

API_PORT = 8000


def start_worker(env: dict[str, str]) -> subprocess.Popen[bytes]:
    process_env = add_repo_to_pythonpath(env)
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "--project",
            "backend",
            "python",
            "-m",
            "flowstead_api.messaging",
            "run",
        ],
        cwd=None,
        env=process_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    time.sleep(1)
    if process.poll() is not None:
        output = (
            process.stdout.read().decode(errors="replace") if process.stdout else ""
        )
        raise RunnerError(f"forecast worker exited before browser startup:\n{output}")
    return process


def start_api(env: dict[str, str]) -> subprocess.Popen[bytes]:
    if port_occupied(API_PORT):
        raise RunnerError(
            f"refusing to start FastAPI: 127.0.0.1:{API_PORT} is already occupied"
        )
    process: subprocess.Popen[bytes] | None = None
    process_env = add_repo_to_pythonpath(env)
    try:
        process = subprocess.Popen(
            [
                "uv",
                "run",
                "--project",
                "backend",
                "uvicorn",
                "flowstead_api.main:app",
                "--app-dir",
                "backend/src",
                "--host",
                "127.0.0.1",
                "--port",
                str(API_PORT),
            ],
            cwd=None,
            env=process_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = (
                    process.stdout.read().decode(errors="replace")
                    if process.stdout
                    else ""
                )
                raise RunnerError(f"FastAPI exited before startup:\n{output}")
            try:
                with urlopen(
                    f"http://127.0.0.1:{API_PORT}/api/v1/health", timeout=1
                ) as response:
                    if response.status == 200:
                        if process.poll() is not None:
                            raise RunnerError(
                                "FastAPI exited immediately after health readiness"
                            )
                        return process
            except OSError:
                time.sleep(0.25)
        raise RunnerError("FastAPI did not become healthy within 30 seconds")
    except BaseException:
        terminate(process)
        raise
