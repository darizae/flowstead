"""Isolated JetStream NATS container lifecycle for live acceptance tests."""

from __future__ import annotations

import asyncio
import re
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from uuid import uuid4

from nats.aio.client import Client as NatsClient
from nats.errors import Error as NatsError

NATS_IMAGE = (
    "nats:2.12-alpine@sha256:b270f5e2428354c0335612694d7dd2fb588148e567a5757fdff325ef9c9332e6"
)


class LiveEnvironmentUnavailable(RuntimeError):
    """The local Docker service needed by the opt-in live suite is unavailable."""


def _port_is_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


@dataclass
class NatsContainer:
    name: str
    url: str

    @classmethod
    def start(cls) -> NatsContainer:
        if shutil.which("docker") is None:
            raise LiveEnvironmentUnavailable("Docker is required for the live NATS container")
        info = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, check=False, timeout=15
        )
        if info.returncode != 0:
            raise LiveEnvironmentUnavailable(
                f"Docker daemon is unavailable: {info.stderr.strip() or info.stdout.strip()}"
            )

        name = f"flowstead-live-nats-{uuid4().hex}"
        result = subprocess.run(
            [
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
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            raise LiveEnvironmentUnavailable(
                f"isolated NATS failed to start: {result.stderr.strip() or result.stdout.strip()}"
            )
        try:
            port_result = subprocess.run(
                ["docker", "port", name, "4222/tcp"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            match = re.search(r":(\d+)\s*$", port_result.stdout)
            if port_result.returncode != 0 or match is None:
                raise LiveEnvironmentUnavailable(
                    f"isolated NATS port lookup failed: {port_result.stderr.strip()}"
                )
            port = int(match.group(1))
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not _port_is_open(port):
                time.sleep(0.1)
            if not _port_is_open(port):
                raise LiveEnvironmentUnavailable("isolated NATS did not open its mapped port")
            url = f"nats://127.0.0.1:{port}"
            asyncio.run(_wait_for_jetstream(url))
            return cls(name=name, url=url)
        except BaseException:
            cls.stop(name)
            raise

    @staticmethod
    def stop(name: str | None) -> None:
        if name is None:
            return
        subprocess.run(
            ["docker", "rm", "--force", name],
            capture_output=True,
            check=False,
            timeout=15,
        )

    def close(self) -> None:
        self.stop(self.name)


async def _wait_for_jetstream(url: str) -> None:
    deadline = time.monotonic() + 30
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        client: NatsClient | None = None
        try:
            client = NatsClient()
            await client.connect(servers=[url], connect_timeout=2, max_reconnect_attempts=0)
            await client.flush(timeout=2)
            await client.jetstream().account_info()
            return
        except (NatsError, OSError, TimeoutError) as error:
            last_error = error
            await asyncio.sleep(0.15)
        finally:
            if client is not None:
                await client.close()
    raise LiveEnvironmentUnavailable(f"NATS JetStream was not ready: {last_error}")


__all__ = ["NATS_IMAGE", "LiveEnvironmentUnavailable", "NatsContainer"]
