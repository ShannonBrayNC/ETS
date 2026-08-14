from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_PREFIXES = (
    "ets.core",
    "ets.edge",
    "ets.core.signing",
)
TARGETS = (
    ROOT / "ets" / "connectors" / "runtime.py",
    ROOT / "ets" / "connectors" / "runtime_store.py",
    ROOT / "ets" / "gateway" / "connector_management.py",
    ROOT / "ets" / "gateway" / "connector_management_api.py",
)


def test_connector_runtime_and_management_do_not_import_forbidden_boundaries() -> None:
    violations: list[str] = []
    for path in TARGETS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names.append(node.module)
            for name in names:
                forbidden = any(
                    name == prefix or name.startswith(f"{prefix}.")
                    for prefix in FORBIDDEN_PREFIXES
                )
                if forbidden:
                    violations.append(f"{path.relative_to(ROOT)} imports {name}")
    assert violations == []
