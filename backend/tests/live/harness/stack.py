"""Real Uvicorn and Flowstead worker subprocesses for the live suite."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from .auth import LocalJwksAuthority

ROOT = Path(__file__).resolve().parents[4]
TERMINATE_TIMEOUT = 10


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@dataclass
class ProcessHandle:
    name: str
    process: subprocess.Popen[bytes]
    log_file: object
    log_path: Path

    @classmethod
    def start(
        cls, name: str, command: list[str], environment: dict[str, str], log_path: Path
    ) -> ProcessHandle:
        log_file = log_path.open("wb")
        try:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=environment,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except BaseException:
            log_file.close()
            raise
        return cls(name, process, log_file, log_path)

    @property
    def exit_code(self) -> int | None:
        return self.process.poll()

    def report(self) -> str:
        output = self.log_path.read_text(errors="replace")[-4000:]
        status = "running" if self.exit_code is None else f"exited {self.exit_code}"
        return f"{self.name} ({status})\n{output}"

    def stop(self) -> None:
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=TERMINATE_TIMEOUT)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                if self.process.poll() is None:
                    try:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    self.process.wait(timeout=TERMINATE_TIMEOUT)
        self.log_file.close()


@dataclass
class LiveStack:
    database_url: str
    nats_url: str
    authority: LocalJwksAuthority
    _temporary_directory: tempfile.TemporaryDirectory[str]
    api: ProcessHandle | None = None
    worker: ProcessHandle | None = None
    api_url: str | None = None

    def environment(self) -> dict[str, str]:
        source_path = os.pathsep.join(
            value
            for value in (str(ROOT), str(ROOT / "backend" / "src"), os.environ.get("PYTHONPATH"))
            if value
        )
        environment = os.environ.copy()
        environment.update(
            {
                "DATABASE_URL": self.database_url,
                "NATS_URL": self.nats_url,
                "PYTHONPATH": source_path,
            }
        )
        environment.update(self.authority.environment())
        return environment

    def start_api(self) -> None:
        if self.api is not None:
            return
        port = _free_port()
        self.api_url = f"http://127.0.0.1:{port}"
        log_path = Path(self._temporary_directory.name) / "uvicorn.log"
        self.api = ProcessHandle.start(
            "uvicorn",
            [
                sys.executable,
                "-m",
                "uvicorn",
                "flowstead_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            self.environment(),
            log_path,
        )
        self._wait_for_http("/api/v1/health/live", expected_status=200)
        self._wait_for_http("/api/v1/health/ready", expected_status=200)

    def start_worker(self) -> None:
        if self.worker is not None:
            return
        log_path = Path(self._temporary_directory.name) / "worker.log"
        self.worker = ProcessHandle.start(
            "flowstead-worker",
            [sys.executable, "-m", "flowstead_api.messaging", "run"],
            self.environment(),
            log_path,
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.worker.exit_code is not None:
                raise AssertionError(self.worker.report())
            time.sleep(0.1)
        if self.worker.exit_code is not None:
            raise AssertionError(self.worker.report())

    def stop_worker(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.worker = None

    def client(self, subject: str) -> httpx.Client:
        if self.api_url is None:
            raise RuntimeError("API process is not running")
        return httpx.Client(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {self.authority.token(subject)}"},
            timeout=5,
        )

    def anonymous_client(self) -> httpx.Client:
        if self.api_url is None:
            raise RuntimeError("API process is not running")
        return httpx.Client(base_url=self.api_url, timeout=5)

    def close(self) -> None:
        self.stop_worker()
        if self.api is not None:
            self.api.stop()
            self.api = None
        self.authority.close()
        self._temporary_directory.cleanup()

    def _wait_for_http(self, path: str, *, expected_status: int) -> None:
        assert self.api_url is not None
        deadline = time.monotonic() + 30
        last_error = "no response"
        while time.monotonic() < deadline:
            if self.api is not None and self.api.exit_code is not None:
                raise AssertionError(self.api.report())
            try:
                response = httpx.get(f"{self.api_url}{path}", timeout=1)
                if response.status_code == expected_status:
                    return
                last_error = f"{response.status_code}: {response.text[:200]}"
            except httpx.HTTPError as error:
                last_error = f"{type(error).__name__}: {error}"
            time.sleep(0.15)
        report = self.api.report() if self.api is not None else "API was not started"
        raise AssertionError(f"{path} did not become ready: {last_error}\n{report}")


__all__ = ["ROOT", "LiveStack", "ProcessHandle"]
