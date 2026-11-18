"""Deterministic Docker ownership/readiness state-machine coverage, no daemon."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from backend.tests.db_lifecycle import (
    COMPOSE_FILE,
    PROJECT_ROOT,
    DatabaseLifecycleError,
    _check_url,
    ensure_database,
)


COMPOSE_UP = (
    "docker", "compose", "--project-directory", str(PROJECT_ROOT),
    "-f", str(COMPOSE_FILE), "-p",
    os.environ.get("COMPOSE_PROJECT_NAME") or PROJECT_ROOT.name,
    "up", "-d", "db",
)


class FakeDocker:
    def __init__(
        self, *, state: str = "healthy", foreign: bool = False,
        foreign_checkout: bool = False, foreign_workdir: bool = False,
        present: bool = True,
        host_ip: str = "127.0.0.1",
    ):
        self.present = present
        self.host_ip = host_ip
        self.foreign = foreign
        self.foreign_checkout = foreign_checkout
        self.foreign_workdir = foreign_workdir
        self.project = os.environ.get("COMPOSE_PROJECT_NAME") or PROJECT_ROOT.name
        self.state = state
        self.commands: list[tuple[str, ...]] = []

    def _container(self) -> dict:
        project = "unrelated" if self.foreign else self.project
        config = (
            PROJECT_ROOT.parent / "unrelated-checkout" / "compose.yml"
            if self.foreign_checkout else COMPOSE_FILE
        )
        workdir = (
            PROJECT_ROOT.parent / "unrelated-checkout"
            if self.foreign_workdir else PROJECT_ROOT
        )
        return {
            "Id": "abc123456789",
            "Config": {
                "Image": "postgres:16-alpine",
                "Env": ["POSTGRES_DB=flowstead", "POSTGRES_USER=flowstead"],
                "Labels": {
                    "com.docker.compose.project": project,
                    "com.docker.compose.project.config_files": str(config),
                    "com.docker.compose.project.working_dir": str(workdir),
                    "com.docker.compose.service": "db",
                },
            },
            "HostConfig": {
                "PortBindings": {
                    "5432/tcp": [{"HostIp": self.host_ip, "HostPort": "54329"}]
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
        if command == COMPOSE_UP:
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
    assert COMPOSE_UP not in fake.commands


def test_unhealthy_owned_postgres_is_restarted_once() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(state="unhealthy")
    assert ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None) == "restarted"
    assert fake.commands.count(("docker", "restart", "abc123456789")) == 1
    assert COMPOSE_UP not in fake.commands


def test_foreign_docker_port_owner_fails_without_mutation() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(foreign=True)
    with pytest.raises(DatabaseLifecycleError, match="foreign Docker container"):
        ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None)
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)


@pytest.mark.parametrize("lookalike", ("foreign_checkout", "foreign_workdir"))
def test_lookalike_compose_checkout_cannot_control_port(lookalike: str) -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(**{lookalike: True})
    with pytest.raises(DatabaseLifecycleError, match="foreign Docker container"):
        ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None)
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)


def test_only_configured_compose_project_is_owned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker()
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "different-configured-project")
    with pytest.raises(DatabaseLifecycleError, match="foreign Docker container"):
        ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None)
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)


def test_foreign_host_port_owner_fails_before_compose_start() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(present=False)
    with pytest.raises(DatabaseLifecycleError, match="foreign host process"):
        ensure_database(run=fake, port_open=lambda _: True, pause=lambda _: None)
    assert COMPOSE_UP not in fake.commands


def test_no_occupant_creates_controller_database_once() -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(present=False)
    assert ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None) == "created"
    assert fake.commands.count(COMPOSE_UP) == 1


@pytest.mark.parametrize("host_ip", ("0.0.0.0", "::", ""))
def test_wildcard_published_database_is_not_trusted_as_loopback(host_ip: str) -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    fake = FakeDocker(host_ip=host_ip)
    with pytest.raises(DatabaseLifecycleError, match="foreign Docker container"):
        ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None)
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)


@pytest.mark.parametrize(
    "option",
    (
        "hostaddr=203.0.113.10",
        "host=database.example",
        "dbname=protected_database",
        "port=5432",
        "service=other_cluster",
    ),
)
def test_preflight_rejects_libpq_target_overrides_before_docker(
    monkeypatch: pytest.MonkeyPatch, option: str
) -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://127.0.0.1:54329/flowstead?" + option
    )
    with pytest.raises(DatabaseLifecycleError, match="does not target"):
        _check_url(54329, "flowstead", required=True)


def test_preflight_allows_plain_configured_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://127.0.0.1:54329/flowstead"
    )
    _check_url(54329, "flowstead", required=True)


class PriorVerifyDocker(FakeDocker):
    """A real prior verify-N Compose provenance shape on the controller port."""

    def __init__(
        self, state_root: Path, *, project: str = "verify-33",
        working_dir: Path | None = None, config_file: Path | None = None,
        state: str = "healthy", host_ip: str = "127.0.0.1",
    ) -> None:
        super().__init__(state=state, host_ip=host_ip)
        self.verify_project = project
        self.verify_working_dir = (
            working_dir if working_dir is not None
            else state_root / "worktrees" / project
        )
        self.verify_config = (
            config_file if config_file is not None
            else self.verify_working_dir / "compose.yml"
        )

    def _container(self) -> dict:
        container = super()._container()
        labels = container["Config"]["Labels"]
        labels["com.docker.compose.project"] = self.verify_project
        labels["com.docker.compose.project.working_dir"] = str(self.verify_working_dir)
        labels["com.docker.compose.project.config_files"] = str(self.verify_config)
        container["Name"] = "/" + self.verify_project + "-db-1"
        return container


def test_healthy_prior_verify_database_is_reused_without_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    state_root = tmp_path / "omp-control-plane-e2e"
    monkeypatch.setenv("OMP_STATE_DIR", str(state_root))
    fake = PriorVerifyDocker(state_root)
    assert ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None) == "reused"
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)


@pytest.mark.parametrize(
    "lookalike",
    ("foreign_root", "wrong_workdir", "wrong_config", "wrong_project"),
)
def test_prior_verify_lookalikes_still_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lookalike: str,
) -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    state_root = tmp_path / "omp-control-plane-e2e"
    monkeypatch.setenv("OMP_STATE_DIR", str(state_root))
    options: dict = {}
    if lookalike == "foreign_root":
        options["working_dir"] = tmp_path / "unrelated" / "worktrees" / "verify-33"
        options["config_file"] = options["working_dir"] / "compose.yml"
    elif lookalike == "wrong_workdir":
        options["working_dir"] = state_root / "worktrees" / "verify-34"
    elif lookalike == "wrong_config":
        options["config_file"] = state_root / "worktrees" / "verify-33" / "other.yml"
    else:
        options["project"] = "verify-33-extra"
    fake = PriorVerifyDocker(state_root, **options)
    with pytest.raises(DatabaseLifecycleError, match="foreign Docker container"):
        ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None)
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)


@pytest.mark.parametrize("state", ("unhealthy", "starting"))
def test_prior_verify_database_is_never_restarted_by_another_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, state: str,
) -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    state_root = tmp_path / "omp-control-plane-e2e"
    monkeypatch.setenv("OMP_STATE_DIR", str(state_root))
    fake = PriorVerifyDocker(state_root, state=state)
    with pytest.raises(DatabaseLifecycleError, match="foreign Docker container"):
        ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None)
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)


@pytest.mark.parametrize("host_ip", ("0.0.0.0", "::", ""))
def test_prior_verify_wildcard_bindings_are_still_foreign(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, host_ip: str,
) -> None:
    """Case: UT-M4A-DB-LIFECYCLE"""
    state_root = tmp_path / "omp-control-plane-e2e"
    monkeypatch.setenv("OMP_STATE_DIR", str(state_root))
    fake = PriorVerifyDocker(state_root, host_ip=host_ip)
    with pytest.raises(DatabaseLifecycleError, match="foreign Docker container"):
        ensure_database(run=fake, port_open=fake.port_open, pause=lambda _: None)
    assert not any(cmd[1] in {"start", "restart", "compose"} for cmd in fake.commands)
