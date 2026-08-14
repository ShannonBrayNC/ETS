from __future__ import annotations

import ast
from pathlib import Path

OTLP_TRANSPORT_FILES = (
    Path("ets/gateway/otlp_http.py"),
    Path("ets/gateway/otlp_protobuf.py"),
)


def test_otlp_transport_does_not_import_edge_or_core_internals() -> None:
    forbidden: list[str] = []

    for path in OTLP_TRANSPORT_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                if node.module.startswith(("ets.edge", "ets.core")):
                    forbidden.append(f"{path}:{node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(("ets.edge", "ets.core")):
                        forbidden.append(f"{path}:{alias.name}")

    assert forbidden == []
