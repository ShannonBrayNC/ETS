from __future__ import annotations

import ast
from pathlib import Path

CREDENTIAL_ROOT = Path(__file__).parents[2] / "ets" / "connectors" / "credentials"
FORBIDDEN_PREFIXES = (
    "ets.api.azure_signing",
    "ets.core",
    "ets.edge",
    "ets.gateway",
)


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def test_credential_package_does_not_cross_product_or_signing_boundaries() -> None:
    for path in CREDENTIAL_ROOT.rglob("*.py"):
        for module in imported_modules(path):
            assert not module.startswith(FORBIDDEN_PREFIXES), f"{path}: forbidden import {module}"
