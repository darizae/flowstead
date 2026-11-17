"""Check that local command documentation names the implemented task gates."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_RECIPES = (
    "db-up",
    "db-down",
    "migrate-local",
    "import-m1-local",
    "check-backend",
    "test-backend-unit",
    "test-db-integration",
    "audit-backend",
    "docs-check",
)


def main() -> int:
    justfile = (ROOT / "justfile").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = [
        name
        for name in REQUIRED_RECIPES
        if re.search(rf"(?m)^{re.escape(name)}(?:\s+[^:\n]*)?:", justfile) is None
    ]
    if missing:
        raise SystemExit(f"missing just recipes: {', '.join(missing)}")
    if "just test-backend-unit" not in readme or "just test-db-integration" not in readme:
        raise SystemExit("README does not document the backend test gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
