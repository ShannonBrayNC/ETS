from __future__ import annotations

import ast
from pathlib import Path

GATEWAY_ROOT = Path("ets/gateway")


def test_gateway_does_not_import_edge_product_namespace() -> None:
    violations: list[str] = []
    for path in sorted(GATEWAY_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "ets.edge" or alias.name.startswith("ets.edge."):
                        violations.append(f"{path}:{node.lineno}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "ets.edge" or module.startswith("ets.edge."):
                    violations.append(f"{path}:{node.lineno}:{module}")

    assert violations == []
