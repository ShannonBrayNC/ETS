import json
from pathlib import Path

import pytest

from ets.core.merkle import (
    EMPTY_TREE_ROOT,
    audit_path_for_leaf,
    compute_root_from_audit_path,
    leaf_hash_for_event_hash,
    merkle_root,
)

VECTOR_PATH = Path("ets/spec/test-vectors/merkle-vectors.json")


def test_empty_tree_root_is_explicit():
    assert merkle_root([]) == EMPTY_TREE_ROOT


def test_single_leaf_root_is_leaf_hash():
    leaf = "11" * 32

    assert merkle_root([leaf]) == leaf


def test_even_and_odd_tree_roots_match_vectors():
    vectors = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))

    assert merkle_root(vectors["leaves"][:2]) == vectors["roots"]["two_leaves"]
    assert merkle_root(vectors["leaves"][:3]) == vectors["roots"]["three_leaves"]
    assert merkle_root(vectors["leaves"]) == vectors["roots"]["four_leaves"]


def test_audit_path_reconstructs_root_for_odd_tree():
    leaves = ["00" * 32, "11" * 32, "22" * 32]
    path = audit_path_for_leaf(leaves, 2)

    assert compute_root_from_audit_path(leaves[2], path) == merkle_root(leaves)


def test_leaf_hash_for_event_hash_is_deterministic():
    event_hash = "ab" * 32

    assert leaf_hash_for_event_hash(event_hash) == leaf_hash_for_event_hash(event_hash)


@pytest.mark.parametrize("leaf_hashes", [["not-hex"], ["00"]])
def test_merkle_root_rejects_invalid_leaf_hashes(leaf_hashes):
    with pytest.raises(ValueError):
        merkle_root(leaf_hashes)
