"""Deterministic Docker ownership/readiness state-machine coverage, no daemon."""

from __future__ import annotations

import json

import pytest

from backend.tests.db_lifecycle import DatabaseLifecycleError, ensure_database


class FakeDocker:
    def __init__(self, *, state: str = "healthy", foreign: bool = False, present: bool = True):
        self.present = present
        self.foreign = foreign
        self.state = state
        self.commands: list[tuple[str, ...]] = []

    def _container(self) -> dict:
        project = "unrelated" if self.foreign else "verify-25"
        return {
            "Id": "abc123456789",
            "Config": {
                "Image": "postgres:16-alpine",
                "Env": ["POSTGRES_DB=flowstead", "POSTGRES_USER=flowstead"],
                "Labels": {
                    "com.docker.compose.project": project,
                    "com.docker.compose.project.config_files": "/tmp/flowstead/compose.yml",
                    "com.docker.compose.service": "db",
                },
            },
            "HostConfig": {
                "PortBindings": {
                    "5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "54329"}]
                }
            },
            "State": {
                "Running": self.state != "stopped",
                "Health": {"Status": self.state if self.state != "stopped" else "starting"},
            },
        }

    def __call__(self, argv: list[str]) -> str:
        command = tuple(argv)
        self.commands.append(command)
        if command == ("docker", "ps", "-aq"):
            return "abc123456789" if self.present else ""
        if command == ("docker", "inspect", "abc123456789"):
            return json.dumps([self._container()])
        if command == ("docker", "start", "abc123456789"):
            self.state = "healthy"
            return ""
        if command == ("docker", "restart", "abc123456789"):
            self.state = "healthy"
            return ""
        if command == ("docker", "compose", "up", "-d", "db"):
            self.present = True
            self.state = "healthy"
            return ""
        raise AssertionError(f"unexpected Docker operation: {command!r}")

    def port_open(self, _: int) -> bool:
        # A running container owns its bound port; a stopped container does not.
        return self.present and self.state != "stopped"


def test_already_running_owned_postgres_is_reused() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker()
    assert ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None) == "reused"
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)


def test_stopped_owned_postgres_is_started_not_recreated() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(state="stopped")
    assert ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None) == "started"
    assert ("docker", "start", "abc123456789") in fake.commands
    assert ("docker", "compose", "up", "-d", "db") not in fake.commands


def test_unhealthy_owned_postgres_is_restarted_once() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(state="unhealthy")
    assert ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None) == "restarted"
    assert fake.commands.count(("docker", "restart", "abc123456789")) == 1
    assert ("docker", "compose", "up", "-d", "db") not in fake.commands


def test_foreign_docker_port_owner_fails_without_mutation() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(foreign=True)
    with pytest.raises(DatabaseLifecycleError, match="foreign Docker container"):
        ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None)
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)


def test_foreign_host_port_owner_fails_before_compose_start() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(present=False)
    with pytest.raises(DatabaseLifecycleError, match="foreign host process"):
        ensure_database(run=fake, port_open=lambda _: True, pause=lambda _: None)
    assert ("docker", "compose", "up", "-d", "db") not in fake.commands


def test_no_occupant_creates_controller_database_once() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(present=False)
    assert ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None) == "created"
    assert fake.commands.count(("docker", "compose", "up", "-d", "db")) == 1
