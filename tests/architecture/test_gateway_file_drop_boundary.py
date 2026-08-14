from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "ets" / "gateway" / "file_drop_host.py"
FORBIDDEN_PREFIXES = (
    "ets.edge",
    "ets.core",
    "ets.core.signing",
)


def test_file_drop_host_does_not_import_edge_or_core_internals() -> None:
    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))
    violations: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
        for name in names:
            if any(
                name == prefix or name.startswith(f"{prefix}.")
                for prefix in FORBIDDEN_PREFIXES
            ):
                violations.append(name)
    assert violations == []
