"""Disposable runner-owned PostgreSQL database provisioning."""

from __future__ import annotations

import re
import uuid
from urllib.parse import SplitResult, quote, urlsplit, urlunsplit

import psycopg

from .m1 import DB_PREFIX
from .proc import RunnerError


def loopback_url(value: str) -> SplitResult:
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise RunnerError("DATABASE_URL must point to loopback PostgreSQL")
    if parsed.query or parsed.fragment:
        raise RunnerError(
            "DATABASE_URL must not include PostgreSQL query or fragment options"
        )
    try:
        _ = parsed.port
    except ValueError as error:
        raise RunnerError("DATABASE_URL has an invalid PostgreSQL port") from error
    return parsed


def _database_url(parsed: SplitResult, database: str) -> str:
    path = f"/{quote(database, safe='')}"
    return urlunsplit(
        (parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment)
    )


def _quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def create_database(base_url: str) -> tuple[str, str]:
    parsed = loopback_url(base_url)
    name = f"{DB_PREFIX}{uuid.uuid4().hex}"
    target_url = _database_url(parsed, name)
    with psycopg.connect(base_url, autocommit=True) as connection:
        connection.execute(f"CREATE DATABASE {_quoted_identifier(name)}")
    return name, target_url


def drop_database(name: str, base_url: str) -> None:
    if re.fullmatch(r"flowstead_test_[0-9a-f]{32}", name) is None:
        raise RunnerError(
            "refusing to drop a database outside the runner-owned name format"
        )
    with psycopg.connect(base_url, autocommit=True) as connection:
        connection.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s "
            "AND pid <> pg_backend_pid()",
            (name,),
        )
        connection.execute(f"DROP DATABASE IF EXISTS {_quoted_identifier(name)}")
