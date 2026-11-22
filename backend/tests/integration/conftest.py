"""Isolated local PostgreSQL database for API and forecast integration tests.

The configured DATABASE_URL is the admin endpoint, never the data-reset target.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from urllib.parse import urlunsplit

import psycopg
import pytest
from backend.migrate import _require_local_database_url, migrate
from psycopg import sql


@pytest.fixture
def isolated_service_url() -> Iterator[str]:
    """Create and drop one unique loopback DB; preserve the configured base DB."""
    admin_url = os.environ.get("DATABASE_URL")
    if not admin_url:
        pytest.skip("DATABASE_URL is required for local PostgreSQL integration")
    parsed = _require_local_database_url(admin_url)
    name = "flowstead_test_" + uuid.uuid4().hex
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))

    target = urlunsplit(parsed._replace(path="/" + name, query="", fragment=""))
    try:
        migrate(target)
        yield target
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
