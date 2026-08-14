from __future__ import annotations

import ast
from pathlib import Path

CONNECTOR_ROOT = Path(__file__).parents[2] / "ets" / "connectors"
FORBIDDEN_PREFIXES = ("ets.edge", "ets.gateway", "ets.core")


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def test_connector_sdk_has_no_product_or_core_dependency() -> None:
    for path in CONNECTOR_ROOT.rglob("*.py"):
        for module in imported_modules(path):
            assert not module.startswith(FORBIDDEN_PREFIXES), f"{path}: forbidden import {module}"
