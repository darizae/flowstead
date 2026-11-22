"""Guardrail tests for production operator smoke with owner-protected secret files."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/hosted_operator_smoke.py"


def load_smoke():
    spec = importlib.util.spec_from_file_location("hosted_operator_smoke", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_password_loading_requires_owner_private_regular_file(tmp_path: Path) -> None:
    smoke = load_smoke()
    path = tmp_path / "test-account.txt"
    path.write_text("fake-test-password\n", encoding="utf-8")
    path.chmod(0o600)
    assert smoke.read_owner_only_password(path) == "fake-test-password"
    path.chmod(0o644)
    with pytest.raises(smoke.SmokeFailure, match="not private"):
        smoke.read_owner_only_password(path)


def test_password_loading_rejects_symlink_multiline_and_short_values(tmp_path: Path) -> None:
    smoke = load_smoke()
    original = tmp_path / "source.txt"
    original.write_text("fake-private-password", encoding="utf-8")
    original.chmod(0o600)
    symlink = tmp_path / "linked.txt"
    symlink.symlink_to(original)
    with pytest.raises(OSError):
        smoke.read_owner_only_password(symlink)
    original.write_text("first-line\nsecond-line\n", encoding="utf-8")
    with pytest.raises(smoke.SmokeFailure, match="exactly one"):
        smoke.read_owner_only_password(original)
    original.write_text("too", encoding="utf-8")
    with pytest.raises(smoke.SmokeFailure, match="invalid size"):
        smoke.read_owner_only_password(original)


def test_smoke_defaults_do_not_enqueue_forecasts() -> None:
    text = SCRIPT.read_text()
    assert 'parser.add_argument("--enqueue-one", action="store_true"' in text
    assert 'parser.add_argument("--auth-only", action="store_true"' in text
    assert "FLOWSTEAD_SUPABASE_PUBLISHABLE_KEY" in text
    assert '"Authorization"] = "Bearer " + token' in text
    assert "access_token" in text
    assert "passwords.clear()" in text
    assert "print(token)" not in text
    assert "print(password)" not in text
