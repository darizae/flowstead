"""The acceptance entrypoint must never mistake skipped tests for coverage."""

from backend.tests.run_integration_gate import AcceptanceResults, _accepted, _preflight


def test_all_skipped_and_partial_runs_fail_closed() -> None:
    """Case: IT-TEST-GATE-01."""
    empty = AcceptanceResults(suite="all", collected=38, skipped=38, pytest_exit_code=0)
    assert not _accepted(empty)
    partial = AcceptanceResults(
        suite="all", collected=38, passed=25, skipped=13, pytest_exit_code=0
    )
    assert not _accepted(partial)
    valid = AcceptanceResults(suite="all", collected=38, passed=38, pytest_exit_code=0)
    assert _accepted(valid)
    assert not _accepted(AcceptanceResults(suite="all", collected=0, pytest_exit_code=0))


def test_missing_real_infrastructure_is_not_a_success(monkeypatch) -> None:
    """Case: IT-TEST-GATE-02."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FLOWSTEAD_M1_MANIFEST", raising=False)
    monkeypatch.delenv("FLOWSTEAD_M1_DATA", raising=False)
    problems = _preflight("db")
    assert "DATABASE_URL is required" in problems
    assert "FLOWSTEAD_M1_MANIFEST is required" in problems
    assert "FLOWSTEAD_M1_DATA is required" in problems


def test_live_gate_accepts_alternate_local_admin_url(monkeypatch) -> None:
    """Case: IT-TEST-GATE-02 — live-only suite accepts its documented admin URL."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("FLOWSTEAD_LIVE_DATABASE_URL", "postgresql://localhost/flowstead")
    assert not any("DATABASE_URL" in error for error in _preflight("live"))
