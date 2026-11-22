"""Pytest fixtures for the opt-in real-process backend live suite."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

from .harness.auth import LocalJwksAuthority
from .harness.db import admin_url_from_environment, disposable_database
from .harness.nats import LiveEnvironmentUnavailable, NatsContainer
from .harness.stack import LiveStack


def _strict_live_environment() -> bool:
    return os.environ.get("FLOWSTEAD_LIVE_STRICT") == "1"


@pytest.fixture(scope="session")
def live_stack() -> Iterator[LiveStack]:
    """One isolated migrated stack, with API real-process startup but no worker yet."""
    if os.environ.get("FLOWSTEAD_RUN_LIVE") != "1":
        pytest.skip("set FLOWSTEAD_RUN_LIVE=1 to run the disposable live backend suite")
    admin_url = admin_url_from_environment(dict(os.environ))
    if not admin_url:
        pytest.skip("set DATABASE_URL or FLOWSTEAD_LIVE_DATABASE_URL for live PostgreSQL")

    try:
        with disposable_database(admin_url) as database_url:
            nats: NatsContainer | None = None
            authority: LocalJwksAuthority | None = None
            stack: LiveStack | None = None
            try:
                nats = NatsContainer.start()
                authority = LocalJwksAuthority.start()
                temporary_directory = tempfile.TemporaryDirectory(prefix="flowstead-live-stack-")
                stack = LiveStack(database_url, nats.url, authority, temporary_directory)
                stack.start_api()
                yield stack
            finally:
                if stack is not None:
                    stack.close()
                elif authority is not None:
                    authority.close()
                if nats is not None:
                    nats.close()
    except LiveEnvironmentUnavailable as error:
        if _strict_live_environment():
            pytest.fail(str(error))
        pytest.skip(str(error))


@pytest.fixture
def running_worker(live_stack: LiveStack) -> Iterator[LiveStack]:
    """Start the real worker only for tests that need terminal processing."""
    live_stack.start_worker()
    try:
        yield live_stack
    finally:
        live_stack.stop_worker()


__all__ = ["live_stack", "running_worker"]
