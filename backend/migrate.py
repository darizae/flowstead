"""Stable backend.migrate CLI and compatibility API for validated Alembic migrations.

Source implementation is kept in the installed Flowstead infrastructure package.
"""

from __future__ import annotations

import psycopg

from flowstead_api.infrastructure.migrations import executor as _executor
from flowstead_api.infrastructure.migrations import safety as _safety
from flowstead_api.infrastructure.migrations.executor import (
    _require_disposable_database,
    _require_local_database_url,
)
from flowstead_api.infrastructure.migrations.safety import (
    ALEMBIC_INI,
    BACKEND_ROOT,
    EXPECTED_COLUMNS,
    REQUIRED_CONSTRAINTS,
    REQUIRED_INDEXES,
    DatabaseState,
    MigrationStateError,
    _alembic_config,
    _alembic_revision,
    _inspect_state,
    _is_descendant,
    _prepare_existing,
    _reference_catalog,
    _schema_catalog,
    _script_directory,
    _sqlalchemy_url,
    _table_columns,
    _validate_schema,
    _validate_schema_migrations,
)

__all__ = [
    "ALEMBIC_INI",
    "BACKEND_ROOT",
    "EXPECTED_COLUMNS",
    "REQUIRED_CONSTRAINTS",
    "REQUIRED_INDEXES",
    "DatabaseState",
    "MigrationStateError",
    "_alembic_config",
    "_alembic_revision",
    "_inspect_state",
    "_is_descendant",
    "_prepare_existing",
    "_reference_catalog",
    "_require_disposable_database",
    "_require_local_database_url",
    "_run",
    "_schema_catalog",
    "_script_directory",
    "_sqlalchemy_url",
    "_table_columns",
    "_validate_schema",
    "_validate_schema_migrations",
    "main",
    "migrate",
    "psycopg",
]


def _run(database_url: str, operation: str, revision: str = "head") -> None:
    """Compatibility entry point honoring the selectable Alembic config."""
    original_ini = _safety.ALEMBIC_INI
    try:
        _safety.ALEMBIC_INI = ALEMBIC_INI
        _executor._run(database_url, operation, revision)
    finally:
        _safety.ALEMBIC_INI = original_ini


def migrate(database_url: str, rollback: bool = False, *, disposable: bool = False) -> None:
    """Run the canonical executor with optional test-local Alembic revisions."""
    original_ini = _safety.ALEMBIC_INI
    try:
        _safety.ALEMBIC_INI = ALEMBIC_INI
        _executor.migrate(database_url, rollback=rollback, disposable=disposable)
    finally:
        _safety.ALEMBIC_INI = original_ini


def main() -> int:
    """Retain the historical CLI while using the standalone executor."""
    return _executor.main()


if __name__ == "__main__":
    raise SystemExit(main())
