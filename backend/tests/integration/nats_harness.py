"""Owned disposable NATS JetStream container lifecycle for integration tests."""

from __future__ import annotations

import asyncio
import atexit
import re
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass

from nats import connect as nats_connect
from nats.errors import Error as NatsError

NATS_IMAGE = (
    "nats:2.12-alpine@sha256:b270f5e2428354c0335612694d7dd2fb588148e567a5757fdff325ef9c9332e6"
)
NATS_PORT = 4222
START_TIMEOUT_SECONDS = 30.0
DOCKER_TIMEOUT_SECONDS = 15
PROBE_TIMEOUT_SECONDS = 3.0

_ACTIVE_CONTAINERS: set[str] = set()


class NatsHarnessError(RuntimeError):
    """Raised when an owned test broker cannot be started or made ready."""


def _available_loopback_port() -> int:
    """Reserve a stable published port at container creation, not at restart.

    Docker's anonymous host-port mappings can change when a stopped
    container restarts. A fixed test-owned mapping keeps the NATS_URL stable
    across the deliberate outage without changing shared Compose services.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


async def _probe_ready(url: str) -> None:
    """Confirm both the NATS protocol and JetStream are accepting requests."""
    client = await nats_connect(
        servers=[url],
        connect_timeout=1,
        max_reconnect_attempts=0,
    )
    try:
        await client.jetstream().account_info()
    finally:
        await client.close()


def _docker_output(command: list[str], *, timeout: int = DOCKER_TIMEOUT_SECONDS) -> str:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Docker error"
        raise NatsHarnessError(f"{' '.join(command)} failed: {detail}")
    return result.stdout.strip()


def _remove_container(name: str) -> None:
    try:
        subprocess.run(
            ["docker", "rm", "--force", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=DOCKER_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def _cleanup_active_containers() -> None:
    for name in tuple(_ACTIVE_CONTAINERS):
        _remove_container(name)
        _ACTIVE_CONTAINERS.discard(name)


atexit.register(_cleanup_active_containers)


@dataclass(slots=True)
class NatsHarness:
    """One disposable broker whose lifecycle is owned by the creating test."""

    name: str
    url: str

    @classmethod
    def create(cls) -> NatsHarness:
        name = f"flowstead-test-nats-{uuid.uuid4().hex}"
        host_port = _available_loopback_port()
        result = subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                name,
                "--label",
                "com.flowstead.test=integration-nats",
                "--publish",
                f"127.0.0.1:{host_port}:{NATS_PORT}",
                NATS_IMAGE,
                "-js",
                "-sd",
                "/data",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown Docker error"
            raise NatsHarnessError(f"isolated NATS failed to start: {detail}")

        _ACTIVE_CONTAINERS.add(name)
        try:
            mapped = _docker_output(["docker", "port", name, f"{NATS_PORT}/tcp"])
            match = re.search(r":(?P<port>[0-9]+)\s*$", mapped)
            if match is None or int(match.group("port")) != host_port:
                raise NatsHarnessError(f"isolated NATS port lookup returned {mapped!r}")
            harness = cls(name=name, url=f"nats://127.0.0.1:{host_port}")
            harness.wait_until_ready()
            return harness
        except BaseException:
            _remove_container(name)
            _ACTIVE_CONTAINERS.discard(name)
            raise

    def wait_until_ready(self) -> None:
        deadline = time.monotonic() + START_TIMEOUT_SECONDS
        last_error: BaseException | None = None
        while time.monotonic() < deadline:
            try:
                parsed_port = int(self.url.rsplit(":", 1)[1])
                with socket.create_connection(("127.0.0.1", parsed_port), timeout=0.5):
                    pass
                asyncio.run(
                    asyncio.wait_for(
                        _probe_ready(self.url),
                        timeout=PROBE_TIMEOUT_SECONDS,
                    )
                )
                return
            except (NatsError, OSError, TimeoutError) as error:
                last_error = error
                time.sleep(0.2)
        detail = self._diagnostics()
        raise NatsHarnessError(
            f"isolated NATS {self.name} was not JetStream-ready within "
            f"{START_TIMEOUT_SECONDS:.0f} seconds: {last_error!r}; {detail}"
        )

    def stop(self) -> None:
        """Stop the owned server while retaining its container for restart."""
        _docker_output(["docker", "stop", "--time", "5", self.name])

    def start(self) -> None:
        """Restart the owned server and wait for JetStream readiness."""
        _docker_output(["docker", "start", self.name])
        mapped = _docker_output(["docker", "port", self.name, f"{NATS_PORT}/tcp"])
        if mapped != f"127.0.0.1:{self.url.rsplit(':', 1)[1]}":
            raise NatsHarnessError(
                "owned NATS changed its published port after restart; "
                "cannot safely resume the original JetStream URL"
            )
        self.wait_until_ready()

    def close(self) -> None:
        """Remove only this harness's container, including after a failure."""
        _remove_container(self.name)
        _ACTIVE_CONTAINERS.discard(self.name)

    def _diagnostics(self) -> str:
        status = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", self.name],
            check=False,
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT_SECONDS,
        )
        logs = subprocess.run(
            ["docker", "logs", "--tail", "20", self.name],
            check=False,
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT_SECONDS,
        )
        state = status.stdout.strip() or status.stderr.strip() or "unknown state"
        output = logs.stdout.strip() or logs.stderr.strip() or "no container logs"
        return f"state={state}; logs={output}"


def start_nats() -> NatsHarness:
    """Start one owned broker; kept as a small fixture-friendly entry point."""
    return NatsHarness.create()


def stop_nats(harness: NatsHarness | None) -> None:
    """Best-effort teardown for callers that do not use the pytest fixture."""
    if harness is not None:
        harness.close()
