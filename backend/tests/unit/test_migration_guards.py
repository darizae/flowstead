"""Guard destructive migration operations before opening a database."""

import pytest
from backend.migrate import MigrationStateError, _require_local_database_url, migrate


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


@pytest.mark.parametrize(
    "option",
    [
        "hostaddr=203.0.113.10",
        "host=database.example",
        "dbname=important_database",
        "port=5432",
        "service=external_cluster",
        "options=-c%20search_path%3Dpublic",
    ],
)
def test_disposable_rollback_rejects_libpq_overrides_before_connection(
    monkeypatch: pytest.MonkeyPatch, option: str
) -> None:
    """Case: IT-M2-MIGRATE"""
    import backend.migrate as migrations

    def forbid_connection(*args: object, **kwargs: object) -> None:
        raise AssertionError("invalid URL must fail before opening PostgreSQL")

    monkeypatch.setattr(migrations.psycopg, "connect", forbid_connection)
    target = "postgresql://127.0.0.1:54329/flowstead_test_" + "a" * 32
    with pytest.raises(MigrationStateError, match="destructive rollback refused"):
        migrate(target + "?" + option, rollback=True, disposable=True)


@pytest.mark.parametrize(
    "option",
    (
        "hostaddr=203.0.113.10",
        "host=database.example",
        "dbname=protected_db",
        "port=5432",
        "service=foreign",
    ),
)
def test_disposable_fixture_base_rejects_libpq_target_overrides(option: str) -> None:
    """Case: DB-M4A-MISMATCH"""
    with pytest.raises(MigrationStateError, match="unsafe local PostgreSQL"):
        _require_local_database_url("postgresql://127.0.0.1:54329/flowstead?" + option)


def test_plain_loopback_fixture_url_keeps_existing_behavior() -> None:
    """Case: DB-M4A-FRESH"""
    parsed = _require_local_database_url("postgresql://127.0.0.1:54329/flowstead")
    assert parsed.hostname == "127.0.0.1" and parsed.path == "/flowstead"
