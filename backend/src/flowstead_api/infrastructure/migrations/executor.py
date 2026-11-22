"""Run verified Alembic upgrade/rollback commands against guarded databases."""

from __future__ import annotations

import argparse
import os
import re
from urllib.parse import SplitResult, unquote, urlsplit

from alembic import command
from sqlalchemy import create_engine

from .safety import (
    MigrationStateError,
    _alembic_config,
    _inspect_state,
    _prepare_existing,
    _sqlalchemy_url,
)


def _run(database_url: str, operation: str, revision: str = "head") -> None:
    engine = create_engine(_sqlalchemy_url(database_url))
    try:
        with engine.begin() as connection:
            config = _alembic_config(connection)
            if operation == "upgrade":
                command.upgrade(config, revision)
            elif operation == "downgrade":
                command.downgrade(config, revision)
            elif operation == "current":
                command.current(config, verbose=True)
            else:
                raise ValueError(f"unsupported Alembic operation: {operation}")
    finally:
        engine.dispose()


def _require_local_database_url(database_url: str) -> SplitResult:
    """Fail before local DB administration if libpq URL options can redirect it.

    For disposable/local-only actions, reject *all* URI query parameters, not
    just known host/hostaddr/dbname overrides: libpq may add new options, and
    even seemingly harmless options are unnecessary for local acceptance.
    """
    try:
        parsed = urlsplit(database_url)
        _ = parsed.port  # also reject malformed port values before connecting
    except ValueError as exc:
        raise MigrationStateError("unsafe local PostgreSQL connection URL") from exc
    if (
        parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or not parsed.path.startswith("/")
        or parsed.path.count("/") != 1
        or not parsed.path[1:]
        or parsed.query
        or parsed.fragment
    ):
        raise MigrationStateError(
            "unsafe local PostgreSQL connection URL: require an explicit "
            "loopback database without libpq query options"
        )
    return parsed


def _require_disposable_database(database_url: str, *, disposable: bool) -> None:
    if not disposable:
        raise MigrationStateError(
            "destructive rollback refused: explicitly mark a loopback "
            "flowstead_test_<32 hex> database as disposable"
        )
    try:
        parsed = _require_local_database_url(database_url)
        database_name = unquote(parsed.path[1:])
        safe = re.fullmatch(r"flowstead_test_[0-9a-f]{32}", database_name)
    except MigrationStateError:
        safe = False
    if not safe:
        raise MigrationStateError(
            "destructive rollback refused: explicitly mark a loopback "
            "flowstead_test_<32 hex> database as disposable "
            "and exclude libpq query options"
        )


def migrate(database_url: str, rollback: bool = False, *, disposable: bool = False) -> None:
    """Upgrade safely; downgrade only an explicitly disposable, isolated local DB."""
    if rollback:
        _require_disposable_database(database_url, disposable=disposable)
    state = _inspect_state(database_url)
    if rollback:
        if state.clean:
            return
        _prepare_existing(database_url, state)
        _run(database_url, "downgrade", "base")
        return

    if state.clean:
        _run(database_url, "upgrade")
        return
    _prepare_existing(database_url, state)
    _run(database_url, "upgrade")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("upgrade", "current"), nargs="?", default="upgrade")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument(
        "--disposable",
        action="store_true",
        help="required for rollback on an isolated flowstead_test_<uuid> DB",
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")
    if args.operation == "current" and args.rollback:
        parser.error("--rollback cannot be combined with current")
    if args.operation == "current":
        _run(args.database_url, "current")
    else:
        migrate(args.database_url, rollback=args.rollback, disposable=args.disposable)
    return 0
