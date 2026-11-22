"""Indexed browser coverage receipt generation from the Playwright JSON report."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .proc import RunnerError

T012_BROWSER_CASES = (
    "E2E-M12-PATH",
    "E2E-M12-MAP",
    "E2E-M12-FILES",
    "UI-M12-ALL",
    "E2E-M12-INDEX",
)


def write_coverage_report(report_path: Path, evidence_directory: Path) -> None:
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"Playwright JSON report is unavailable: {error}") from error
    coverage: dict[str, list[dict[str, object]]] = {}

    def visit(suite: dict[str, object]) -> None:
        for spec_value in suite.get("specs", []):
            if not isinstance(spec_value, dict):
                continue
            title = str(spec_value.get("title", ""))
            for case_id in sorted(
                set(
                    re.findall(
                        r"\b(?:E2E|IDB|SEC|UI|UT)-M\d+[A-Z]*(?:-[A-Z]+)+\b", title
                    )
                )
            ):
                for test_value in spec_value.get("tests", []):
                    if not isinstance(test_value, dict):
                        continue
                    results = test_value.get("results", [])
                    statuses = [
                        str(result.get("status", "unknown"))
                        for result in results
                        if isinstance(result, dict)
                    ]
                    coverage.setdefault(case_id, []).append(
                        {
                            "title": title,
                            "project": str(test_value.get("projectName", "")),
                            "statuses": statuses,
                        }
                    )
        for child in suite.get("suites", []):
            if isinstance(child, dict):
                visit(child)

    for suite in report.get("suites", []):
        if isinstance(suite, dict):
            visit(suite)
    for case_id in T012_BROWSER_CASES:
        entries = coverage.get(case_id, [])
        projects = {str(entry["project"]) for entry in entries}
        if projects != {"desktop", "mobile"} or any(
            status != "passed" for entry in entries for status in entry["statuses"]
        ):
            raise RunnerError(
                f"{case_id} lacks passing desktop and mobile Playwright coverage"
            )
    source_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    receipt = {
        "source_sha": source_sha,
        "command": "just test-e2e-local",
        "fixture": {
            "manifest": "m1.v1",
            "seed": 20250101,
            "source_sha": "ad5c94d1f46e79312a99cb9721f38700f24fdf6b",
            "telemetry_sha256": "e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e",
            "services": [
                "PostgreSQL 16",
                "NATS 2 JetStream",
                "FastAPI",
                "React/Vite",
                "Chromium",
            ],
        },
        "viewports": ["desktop 1330x900", "mobile 390x844", "Chromium page scale 200%"],
        "cases": dict(sorted(coverage.items())),
    }
    json_path = evidence_directory / "t012-index-coverage.json"
    markdown_path = evidence_directory / "t012-index-coverage.md"
    json_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rows = [
        "# T-012 browser indexed coverage",
        "",
        f"- Tested source SHA: `{source_sha}`",
        "- Command: `just test-e2e-local`",
        "- Fixture: pinned M1 + disposable PostgreSQL + isolated NATS/JetStream + real FastAPI/React/Chromium",
        "- Viewports: 1330x900, 390x844, and Chromium page scale 200%",
        "",
        "| Case | Projects | Runtime titles | Result |",
        "| --- | --- | --- | --- |",
    ]
    for case_id, entries in sorted(coverage.items()):
        projects = ", ".join(sorted({str(entry["project"]) for entry in entries}))
        titles = "<br>".join(sorted({str(entry["title"]) for entry in entries}))
        passed = all(
            status == "passed" for entry in entries for status in entry["statuses"]
        )
        rows.append(
            f"| `{case_id}` | {projects} | {titles} | {'PASS' if passed else 'FAIL'} |"
        )
    markdown_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
