from __future__ import annotations

import json
from pathlib import Path

from ets.core.merkle import EMPTY_TREE_ROOT, merkle_root

REPO_ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = REPO_ROOT / "ets" / "spec" / "test-vectors"


def test_merkle_vectors_match_implementation() -> None:
    vector = json.loads((VECTOR_ROOT / "merkle-vectors.json").read_text(encoding="utf-8"))
    leaves = vector["leaves"]
    roots = vector["roots"]

    assert roots["empty"] == EMPTY_TREE_ROOT
    assert merkle_root([]) == roots["empty"]
    assert merkle_root(leaves[:1]) == roots["single_leaf"]
    assert merkle_root(leaves[:2]) == roots["two_leaves"]
    assert merkle_root(leaves[:3]) == roots["three_leaves"]
    assert merkle_root(leaves[:4]) == roots["four_leaves"]
