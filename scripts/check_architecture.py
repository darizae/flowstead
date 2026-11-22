#!/usr/bin/env python3
"""Enforce the import direction of the backend's pure domain package.

This deliberately uses only the standard library, so it is runnable before
installing dependencies and as part of the CI static gate.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "backend/src/flowstead_api/domain"
FORBIDDEN_ROOTS = frozenset(
    {"fastapi", "starlette", "psycopg", "sqlalchemy", "nats", "reportlab", "uvicorn"}
)
FORBIDDEN_INTERNAL = (
    "flowstead_api.application",
    "flowstead_api.infrastructure",
    "flowstead_api.interfaces",
    "flowstead_api.main",
    "flowstead_api.database",
    "flowstead_api.messaging",
    "flowstead_api.message_store",
    "backend.",
)


def invalid_import(name: str) -> bool:
    return name.split(".", maxsplit=1)[0] in FORBIDDEN_ROOTS or any(
        name == prefix.rstrip(".") or name.startswith(prefix)
        for prefix in FORBIDDEN_INTERNAL
    )


def main() -> int:
    if not DOMAIN.exists():
        print(
            "Domain package not found; architecture boundary check failed",
            file=sys.stderr,
        )
        return 1

    errors: list[str] = []
    for path in sorted(DOMAIN.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    modules.append(node.module or "")
                elif node.level >= 2:
                    # Relative imports escaping domain are forbidden.
                    modules.append("flowstead_api.infrastructure")
            if any(invalid_import(module) for module in modules):
                errors.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: forbidden domain dependency "
                    + ", ".join(modules)
                )
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(
        f"Domain import boundaries verified ({len(list(DOMAIN.rglob('*.py')))} modules)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
