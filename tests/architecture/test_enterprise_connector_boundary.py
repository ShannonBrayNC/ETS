from __future__ import annotations

import ast
from pathlib import Path

ENTERPRISE_PACKAGE = Path("ets/connectors/enterprise")


def test_enterprise_connector_package_does_not_import_gateway_core_or_edge() -> None:
    forbidden: list[str] = []

    for path in ENTERPRISE_PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                if node.module.startswith(("ets.gateway", "ets.core", "ets.edge")):
                    forbidden.append(f"{path}:{node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(("ets.gateway", "ets.core", "ets.edge")):
                        forbidden.append(f"{path}:{alias.name}")

    assert forbidden == []
