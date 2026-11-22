"""Fail-closed pytest acceptance gate for real backend integration tests.

Unlike bare pytest, a run with every test skipped must never be reported green.
Pass --receipt to persist a machine-readable result outside the source tree.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_PATHS = {
    "api": ("backend/tests/integration/test_api.py",),
    "auth": ("backend/tests/integration/test_auth.py",),
    "db": ("backend/tests/integration",),
    "forecast": ("backend/tests/integration/test_forecast.py",),
    "messaging": ("backend/tests/integration/test_messaging.py",),
    "live": ("backend/tests/live",),
    "all": ("backend/tests/integration", "backend/tests/live"),
}


@dataclass
class AcceptanceResults:
    suite: str
    source_sha: str = ""
    collected: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    skip_reasons: list[str] = field(default_factory=list)
    pytest_exit_code: int = -1
    accepted: bool = False


class AcceptancePlugin:
    def __init__(self, results: AcceptanceResults) -> None:
        self.results = results

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.results.collected = len(session.items)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when == "call":
            if report.passed:
                self.results.passed += 1
            elif report.failed:
                self.results.failed += 1
        if report.skipped:
            self.results.skipped += 1
            reason = str(report.longrepr)
            self.results.skip_reasons.append(f"{report.nodeid}: {reason[-250:]}")
        if report.when in ("setup", "teardown") and report.failed:
            self.results.errors += 1


def _preflight(suite: str) -> list[str]:
    problems: list[str] = []
    if suite == "live":
        if not (os.environ.get("DATABASE_URL") or os.environ.get("FLOWSTEAD_LIVE_DATABASE_URL")):
            problems.append("DATABASE_URL or FLOWSTEAD_LIVE_DATABASE_URL is required")
    elif not os.environ.get("DATABASE_URL"):
        problems.append("DATABASE_URL is required")
    if suite in ("api", "db", "forecast", "all"):
        for name in ("FLOWSTEAD_M1_MANIFEST", "FLOWSTEAD_M1_DATA"):
            value = os.environ.get(name)
            if not value:
                problems.append(f"{name} is required")
            elif not Path(value).is_file():
                problems.append(f"{name} does not name an existing file")
    # The database suite includes the real JetStream tests. A green run must
    # never depend on an absent Docker daemon being misreported as a skip.
    if suite in ("db", "live", "all", "messaging"):
        try:
            process = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                check=False,
                capture_output=True,
                timeout=10,
            )
            if process.returncode:
                problems.append("Docker daemon is not available")
        except (OSError, subprocess.TimeoutExpired):
            problems.append("Docker daemon is not available")
    return problems


def _accepted(results: AcceptanceResults) -> bool:
    return (
        results.pytest_exit_code == int(pytest.ExitCode.OK)
        and results.collected > 0
        and results.passed == results.collected
        and results.skipped == 0
        and results.failed == 0
        and results.errors == 0
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=sorted(TEST_PATHS), default="all")
    parser.add_argument("--receipt", type=Path, help="Write execution result as JSON")
    parser.add_argument("pytest_args", nargs="*", help="Additional pytest flags after --")
    args = parser.parse_args(argv)
    results = AcceptanceResults(suite=args.suite)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    results.source_sha = commit.stdout.strip() if commit.returncode == 0 else "unknown"
    problems = _preflight(args.suite)
    if problems:
        for problem in problems:
            print(f"Integration preflight failed: {problem}", file=sys.stderr)
    else:
        # This command is an acceptance run, never an opt-in exploratory pytest
        # invocation. The live fixtures must not silently report SKIP.
        if args.suite in ("live", "all"):
            os.environ["FLOWSTEAD_RUN_LIVE"] = "1"
            os.environ["FLOWSTEAD_LIVE_STRICT"] = "1"
        extra = list(args.pytest_args)
        if extra and extra[0] == "--":
            extra.pop(0)
        plugin = AcceptancePlugin(results)
        results.pytest_exit_code = int(
            pytest.main(["-q", "-ra", *TEST_PATHS[args.suite], *extra], plugins=[plugin])
        )
        results.accepted = _accepted(results)

    print(
        f"Integration gate: {results.passed} passed, {results.skipped} skipped, "
        f"{results.failed} failed, {results.errors} errors, "
        f"{results.collected} collected — "
        f"{'PASS' if results.accepted else 'FAIL'}"
    )
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(results)
        payload["timestamp_utc"] = datetime.now(UTC).isoformat()
        payload["preflight_errors"] = problems
        payload["command"] = f"python -m backend.tests.run_integration_gate --suite {args.suite}"
        args.receipt.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0 if results.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
