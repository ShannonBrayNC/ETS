from __future__ import annotations

import ast
import hashlib
from pathlib import Path

CAPTURE_ROOT = Path(__file__).parents[2] / "ets" / "capture"
EDGE_SCHEMA = Path(__file__).parents[2] / "schemas" / "edge" / "v1" / "capture-envelope.schema.json"
EXPECTED_EDGE_SCHEMA_GIT_BLOB = "d92cc0ce063b48502a0c6030353a6e7f282f6c12"


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def git_blob_sha1(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def test_capture_package_has_no_product_to_product_dependency() -> None:
    for path in CAPTURE_ROOT.rglob("*.py"):
        for module in imported_modules(path):
            assert not module.startswith("ets.edge"), f"{path}: forbidden import {module}"
            assert not module.startswith("ets.gateway"), f"{path}: forbidden import {module}"


def test_capture_uses_only_public_core_boundary() -> None:
    for path in CAPTURE_ROOT.rglob("*.py"):
        for module in imported_modules(path):
            if module.startswith("ets.core."):
                assert module == "ets.core.api", f"{path}: Core internal import {module}"


def test_historical_edge_capture_schema_is_unchanged() -> None:
    assert git_blob_sha1(EDGE_SCHEMA) == EXPECTED_EDGE_SCHEMA_GIT_BLOB
