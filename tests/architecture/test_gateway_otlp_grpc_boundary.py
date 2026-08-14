from __future__ import annotations

import ast
from pathlib import Path

OTLP_GRPC_MODULE = Path("ets/gateway/otlp_grpc.py")


def test_otlp_grpc_transport_does_not_import_edge_or_core_internals() -> None:
    tree = ast.parse(OTLP_GRPC_MODULE.read_text(encoding="utf-8"))
    forbidden: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module.startswith(("ets.edge", "ets.core")):
                forbidden.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(("ets.edge", "ets.core")):
                    forbidden.append(alias.name)

    assert forbidden == []
