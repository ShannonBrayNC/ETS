from __future__ import annotations

import ast
from pathlib import Path

NATIVE_CONNECTOR_MODULE = Path("ets/connectors/native.py")


def test_native_connector_packaging_does_not_import_gateway_or_core_runtime() -> None:
    tree = ast.parse(NATIVE_CONNECTOR_MODULE.read_text(encoding="utf-8"))
    forbidden: list[str] = []

    for node in ast.walk(tree):
        module: str | None = None
        if isinstance(node, ast.ImportFrom):
            module = node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(("ets.gateway", "ets.core", "ets.edge")):
                    forbidden.append(alias.name)
        if module is not None and module.startswith(("ets.gateway", "ets.core", "ets.edge")):
            forbidden.append(module)

    assert forbidden == []
