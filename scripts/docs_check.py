#!/usr/bin/env python3
"""Validate tracked Markdown links, advertised recipes, and documentation sources."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
ACTIVE_COMMAND_DOCS = (
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "docs/planning/HANDOFF_SEQUENCE.md",
    ROOT / "docs/planning/IMPLEMENTATION_SPEC.md",
)
CASE_ID = re.compile(r"\b(?:CLOUD|DB|DOC|E2E|IDB|IT|MSG|OPS|SEC|UI|UT)-M\d+[A-Z]?-[A-Z0-9-]+\b")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
RECIPE = re.compile(r"(?m)^([A-Za-z0-9_-]+)(?:\s+[^:\n]*)?:")
JUST_CALL = re.compile(r"\bjust\s+([A-Za-z0-9_-]+|--list)\b")
TASK_HEADING = re.compile(r"^###\s+(T-\d+[a-z]?)\b", re.IGNORECASE)
INDEX_ROW = re.compile(r"^\|\s*`(" + CASE_ID.pattern + r")`\s*\|")
ALLOWED_CROSS_TASK_CASES = {
    "IT-M2-MIGRATE": frozenset({"t-002", "t-004a"}),
}
M1_VALUES = (
    "ad5c94d1f46e79312a99cb9721f38700f24fdf6b",
    "m1.v1",
    "20250101",
    "e670271d3d725051229adc844f4025033221a8599b49edb93ba08f3214814d3e",
)
M1_CONTRACT_DOCS = (
    ROOT / "AGENTS.md",
    ROOT / "docs/planning/HANDOFF_SEQUENCE.md",
    ROOT / "docs/planning/IMPLEMENTATION_SPEC.md",
    ROOT / "docs/testing/TEST_DATA_GUIDE.md",
)


def tracked_markdown() -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(ROOT / name for name in result.stdout.split("\0") if name)


def heading_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match is None:
            continue
        anchor = match.group(1).strip().lower()
        anchor = re.sub(r"[^\w\- ]", "", anchor, flags=re.UNICODE)
        anchor = re.sub(r"\s+", "-", anchor)
        count = counts.get(anchor, 0)
        counts[anchor] = count + 1
        anchors.add(anchor if count == 0 else f"{anchor}-{count}")
    return anchors


def check_links(paths: tuple[Path, ...], routes: set[str]) -> list[str]:
    errors: list[str] = []
    for source in paths:
        text = source.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            raw = match.group(1).strip()
            target = raw[1 : raw.index(">")] if raw.startswith("<") and ">" in raw else raw.split()[0]
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("//"):
                continue
            if parsed.path.startswith("/api/"):
                route = unquote(parsed.path)
                if route not in routes:
                    errors.append(f"{source.relative_to(ROOT)}:{line}: unknown API route link {route}")
                continue
            destination = source if not parsed.path else (source.parent / unquote(parsed.path)).resolve()
            if not destination.exists():
                errors.append(f"{source.relative_to(ROOT)}:{line}: missing link target {target}")
                continue
            if parsed.fragment and destination.is_file() and destination.suffix.lower() == ".md":
                fragment = unquote(parsed.fragment).lower()
                if fragment not in heading_anchors(destination):
                    errors.append(f"{source.relative_to(ROOT)}:{line}: missing heading #{fragment} in {destination.relative_to(ROOT)}")
    return errors


def api_routes() -> set[tuple[str, str]]:
    """Read FastAPI routes across the router modules without importing dependencies."""
    paths = [ROOT / "backend/src/flowstead_api/main.py"]
    paths.extend(sorted((ROOT / "backend/src/flowstead_api/interfaces/http/routers").glob("*.py")))
    routes: set[tuple[str, str]] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                if decorator.func.attr.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                    continue
                routes.add((decorator.func.attr.upper(), decorator.args[0].value))
    return routes


def check_backend_contract(routes: set[tuple[str, str]]) -> list[str]:
    errors: list[str] = []
    contract_path = ROOT / "docs/planning/IMPLEMENTATION_SPEC.md"
    contract = contract_path.read_text(encoding="utf-8")
    documented_routes = set(
        re.findall(r"`(GET|POST|PUT|PATCH|DELETE) (/api/v1/[^`]+)`", contract)
    )
    for method, route in sorted(routes - documented_routes):
        errors.append(
            f"{contract_path.relative_to(ROOT)}: missing current API route {method} {route}"
        )
    for method, route in sorted(documented_routes - routes):
        errors.append(f"{contract_path.relative_to(ROOT)}: stale API route {method} {route}")

    for path in M1_CONTRACT_DOCS:
        text = path.read_text(encoding="utf-8")
        for value in M1_VALUES:
            if value not in text:
                errors.append(f"{path.relative_to(ROOT)}: missing immutable M1 value {value}")

    importer = (ROOT / "backend/importer.py").read_text(encoding="utf-8")
    importer += (ROOT / "backend/src/flowstead_api/domain/m1.py").read_text(encoding="utf-8")
    for value in M1_VALUES[:3]:
        if value not in importer:
            errors.append(f"backend/importer.py: immutable M1 value differs from docs: {value}")
    return errors


def _module_exports(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in module.body:
        if isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def check_recipes(justfile: str) -> list[str]:
    errors: list[str] = []
    recipes = set(RECIPE.findall(justfile))
    for path in ACTIVE_COMMAND_DOCS:
        text = path.read_text(encoding="utf-8")
        for match in JUST_CALL.finditer(text):
            name = match.group(1)
            if name != "--list" and name not in recipes:
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{path.relative_to(ROOT)}:{line}: unknown just recipe {name}")

    references = set(
        re.findall(
            r"(?<![A-Za-z0-9_.-])((?:backend|scripts)(?:/[A-Za-z0-9_.-]+)*)",
            justfile,
        )
    )
    for reference in sorted(references):
        if not (ROOT / reference).exists():
            errors.append(f"justfile: missing referenced path {reference}")

    modules = set(
        re.findall(
            r"python\s+-m\s+((?:backend|flowstead_api)(?:\.[A-Za-z0-9_]+)+)",
            justfile,
        )
    )
    for module in sorted(modules):
        relative = Path(*module.split(".")).with_suffix(".py")
        if not (ROOT / relative).exists() and not (ROOT / "backend/src" / relative).exists():
            errors.append(f"justfile: missing referenced module {module}")

    for line_number, line in enumerate(justfile.splitlines(), start=1):
        target = re.search(
            r"\buvicorn\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*):([A-Za-z_]\w*)",
            line,
        )
        if target is None:
            continue
        app_dir = re.search(r"--app-dir\s+([A-Za-z0-9_./-]+)", line)
        module_root = ROOT / (app_dir.group(1) if app_dir else ".")
        module_path = module_root.joinpath(*target.group(1).split(".")).with_suffix(".py")
        if not module_path.is_file():
            errors.append(f"justfile:{line_number}: missing Uvicorn module {target.group(1)}")
            continue
        if target.group(2) not in _module_exports(module_path):
            errors.append(
                f"justfile:{line_number}: Uvicorn module {target.group(1)} "
                f"does not export {target.group(2)}"
            )
    return errors


def check_case_index() -> list[str]:
    index_path = ROOT / "docs/testing/INDEXED_TEST_PLAN.md"
    text = index_path.read_text(encoding="utf-8")
    errors: list[str] = []
    sections: dict[str, set[str]] = {}
    current_task: str | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        heading = TASK_HEADING.match(line)
        if heading:
            current_task = heading.group(1).casefold()
            if current_task in sections:
                errors.append(
                    f"{index_path.relative_to(ROOT)}:{line_number}: duplicate task section "
                    f"{heading.group(1)}"
                )
            else:
                sections[current_task] = set()
            continue
        row = INDEX_ROW.match(line)
        if row is None or current_task is None:
            continue
        case_id = row.group(1)
        if case_id in sections[current_task]:
            errors.append(
                f"{index_path.relative_to(ROOT)}:{line_number}: duplicate {case_id} "
                f"inside {current_task}"
            )
        sections[current_task].add(case_id)

    indexed = set().union(*sections.values())
    expected: set[str] = set()
    for path in (ROOT / "docs/planning/tasks").glob("*.md"):
        expected.update(CASE_ID.findall(path.read_text(encoding="utf-8")))
    for path in (ROOT / "backend/tests").rglob("test_*.py"):
        expected.update(CASE_ID.findall(path.read_text(encoding="utf-8")))
    for case_id in sorted(expected - indexed):
        errors.append(f"{index_path.relative_to(ROOT)}: missing case ID {case_id}")

    owners: dict[str, set[str]] = {}
    for task, case_ids in sections.items():
        for case_id in case_ids:
            owners.setdefault(case_id, set()).add(task)
    for case_id, tasks in sorted(owners.items()):
        if len(tasks) > 1 and frozenset(tasks) != ALLOWED_CROSS_TASK_CASES.get(case_id):
            errors.append(
                f"{index_path.relative_to(ROOT)}: {case_id} appears in conflicting task "
                f"sections {', '.join(sorted(tasks))}"
            )

    inventory = re.search(r"\*\*Inventory:\*\*\s*(\d+)\s+distinct indexed cases", text)
    if inventory is None:
        errors.append(f"{index_path.relative_to(ROOT)}: missing distinct-case inventory")
    elif int(inventory.group(1)) != len(indexed):
        errors.append(
            f"{index_path.relative_to(ROOT)}: inventory says {inventory.group(1)}, "
            f"but {len(indexed)} distinct cases are indexed"
        )
    return errors


def main() -> int:
    markdown = tracked_markdown()
    justfile = (ROOT / "justfile").read_text(encoding="utf-8")
    routes = api_routes()
    route_paths = {path for _, path in routes}
    errors = check_links(markdown, route_paths)
    errors.extend(check_recipes(justfile))
    errors.extend(check_case_index())
    errors.extend(check_backend_contract(routes))
    if errors:
        raise SystemExit("documentation check failed:\n" + "\n".join(f"- {error}" for error in errors))
    print(f"documentation check passed: {len(markdown)} Markdown files, links, recipes, sources, routes, M1 values, and case IDs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
