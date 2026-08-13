from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _imports_under(relative_root: str) -> list[str]:
    imported: list[str] = []
    for path in (ROOT / relative_root).rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.append(node.module)
    return imported


def test_gateway_does_not_import_edge_product_namespace() -> None:
    imports = _imports_under("ets/gateway")
    assert not [name for name in imports if name == "ets.edge" or name.startswith("ets.edge.")]


def test_shared_runtime_does_not_import_product_namespaces() -> None:
    imports = _imports_under("ets/runtime")
    forbidden = [
        name
        for name in imports
        if name in {"ets.edge", "ets.gateway"}
        or name.startswith("ets.edge.")
        or name.startswith("ets.gateway.")
    ]
    assert not forbidden


def test_edge_sync_queue_is_a_compatibility_facade() -> None:
    source = (ROOT / "ets/edge/sync_queue.py").read_text(encoding="utf-8")
    assert "from ets.runtime.sync_queue import" in source
    assert "class SyncQueue:" not in source


def test_shared_queue_retains_required_durability_pragmas_and_schema() -> None:
    source = (ROOT / "ets/runtime/sync_queue.py").read_text(encoding="utf-8")
    assert 'PRAGMA journal_mode=WAL' in source
    assert 'PRAGMA synchronous=FULL' in source
    assert "CREATE TABLE IF NOT EXISTS sync_queue" in source
    assert "idempotency_key TEXT NOT NULL UNIQUE" in source
    assert "acknowledgement_hash TEXT" in source


def test_gateway_runtime_consumes_neutral_sync_queue() -> None:
    source = (ROOT / "ets/gateway/runtime.py").read_text(encoding="utf-8")
    assert "from ets.runtime.sync_queue import SyncQueue" in source
    assert "ets.edge" not in source
