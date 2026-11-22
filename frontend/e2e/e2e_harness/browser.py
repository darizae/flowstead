"""Chromium executable resolution for the local Playwright gate."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _expected_chromium_revision() -> str | None:
    """Resolve the Chromium revision @playwright/test expects (browsers.json)."""
    browsers_json = (
        ROOT / "frontend" / "node_modules" / "playwright-core" / "browsers.json"
    )
    try:
        data = json.loads(browsers_json.read_text(encoding="utf-8"))
        for browser in data.get("browsers", []):
            if browser.get("name") == "chromium":
                return str(browser["revision"])
    except (OSError, KeyError, json.JSONDecodeError):
        return None
    return None


def _frame_complete(chromium_dir: Path) -> bool:
    """True when an installed Chromium.app has its Framework bundle extracted."""
    frameworks = (
        chromium_dir
        / "chrome-mac-arm64/Google Chrome for Testing.app/Contents/Frameworks"
    )
    return (
        any(frameworks.glob("*Framework.framework/Versions/*"))
        if frameworks.exists()
        else False
    )


def find_chromium_executable() -> str | None:
    """Return a usable Chromium executable for the browser gate.

    The installed @playwright/test expects a bundled revision that may be absent
    or incompletely extracted; fall back to the newest *complete* installed
    Chromium executable instead of requiring a repair download.
    """
    cache = Path.home() / "Library/Caches/ms-playwright"
    expected = _expected_chromium_revision()
    if expected:
        expected_dir = cache / f"chromium-{expected}"
        expected_exe = (
            expected_dir
            / "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        )
        if expected_exe.is_file() and _frame_complete(expected_dir):
            return None  # matching, complete bundled browser; use Playwright's default
    candidates = []
    for directory in sorted(cache.glob("chromium-*"), reverse=True):
        exe = (
            directory
            / "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        )
        if exe.is_file() and _frame_complete(directory):
            candidates.append(exe)
    return str(candidates[0]) if candidates else None
