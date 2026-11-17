"""Guard destructive migration operations before opening a database."""

import pytest

from backend.migrate import MigrationStateError, migrate


@pytest.mark.parametrize(
    "url,disposable",
    [
        ("postgresql://localhost:54329/flowstead", False),
        ("postgresql://localhost:54329/flowstead", True),
        ("postgresql://database.example:5432/flowstead_test_" + "a" * 32, True),
        ("postgresql://127.0.0.1:54329/flowstead_test_" + "a" * 32, False),
    ],
)
def test_rollback_rejects_non_disposable_target_without_connecting(
    url: str, disposable: bool
) -> None:
    """Case: IT-M2-MIGRATE"""
    with pytest.raises(MigrationStateError, match="destructive rollback refused"):
        migrate(url, rollback=True, disposable=disposable)
