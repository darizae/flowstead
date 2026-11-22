"""Transaction boundary shared by application workflows."""

from __future__ import annotations

from typing import Any, Protocol, Self


class UnitOfWork(Protocol):
    connection: Any

    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None: ...
