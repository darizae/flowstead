"""Unit of Work: owns one PostgreSQL connection and transaction boundary."""

from __future__ import annotations

from typing import Any, Self

import psycopg


class UnitOfWork:
    """A single atomic PostgreSQL transaction shared by repository operations.

    Commits on a clean exit; rolls back when an exception propagates. Repositories
    receive ``self.connection`` and run inside this boundary so job, forecast,
    and outbox writes stay atomic.
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self.connection: psycopg.Connection[Any] | None = None
        self._transaction: Any = None

    def __enter__(self) -> Self:
        self.connection = psycopg.connect(self._database_url)
        self._transaction = self.connection.transaction()
        self._transaction.__enter__()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        try:
            self._transaction.__exit__(exc_type, exc_value, traceback)
        finally:
            self.connection.close()
            self.connection = None
            self._transaction = None
