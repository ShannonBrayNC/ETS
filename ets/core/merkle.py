"""Deterministic Merkle tree construction for ETS.

This follows the RFC 6962 (Certificate Transparency) Merkle Tree Hash (MTH)
construction:

  * Leaf and internal-node hashes are domain-separated with a one-byte
    prefix (0x00 for leaves, 0x01 for internal nodes), so a node hash can
    never be replayed as a leaf hash or vice versa.
  * Trees with an odd number of nodes at a level are NOT balanced by
    duplicating the final node. Instead, the tree is split unevenly: the
    left subtree always has a power-of-two number of leaves. This avoids
    the classic "duplicate leaf" ambiguity (the same issue behind
    CVE-2012-2459 in early Bitcoin merkle trees), where two different
    leaf sequences could otherwise produce the same root.
"""

from __future__ import annotations

import hashlib

LEAF_HASH_PREFIX = b"\x00"
NODE_HASH_PREFIX = b"\x01"

EMPTY_TREE_ROOT = hashlib.sha256(b"").hexdigest()


def leaf_hash_for_event_hash(event_hash: str) -> str:
    """Hash a canonical event hash into the tree leaf namespace."""

    _require_sha256_hex(event_hash, "event_hash")
    return hashlib.sha256(LEAF_HASH_PREFIX + bytes.fromhex(event_hash)).hexdigest()


def merkle_root(leaf_hashes: list[str]) -> str:
    """Return the ETS Merkle tree hash (RFC 6962 MTH) for leaf hashes."""

    for leaf_hash in leaf_hashes:
        _require_sha256_hex(leaf_hash, "leaf_hash")

    if not leaf_hashes:
        return EMPTY_TREE_ROOT

    return _subtree_hash(leaf_hashes)


def audit_path_for_leaf(leaf_hashes: list[str], leaf_index: int) -> list[dict[str, str]]:
    """Return the Merkle audit path for a zero-based leaf index."""

    if leaf_index < 0 or leaf_index >= len(leaf_hashes):
        raise IndexError("leaf_index is outside the tree")

    for leaf_hash in leaf_hashes:
        _require_sha256_hex(leaf_hash, "leaf_hash")

    return _subtree_path(leaf_hashes, leaf_index)


def compute_root_from_audit_path(leaf_hash: str, audit_path: list[dict[str, str]]) -> str:
    """Reconstruct a Merkle root from a leaf hash and an ordered audit path."""

    _require_sha256_hex(leaf_hash, "leaf_hash")
    current = leaf_hash
    for step in audit_path:
        position = step.get("position")
        sibling_hash = step.get("hash")
        if sibling_hash is None:
            raise ValueError("audit path step is missing hash")
        _require_sha256_hex(sibling_hash, "audit_path.hash")

        if position == "left":
            current = _hash_pair(sibling_hash, current)
        elif position == "right":
            current = _hash_pair(current, sibling_hash)
        else:
            raise ValueError("audit path position must be left or right")

    return current


def split_point(tree_size: int) -> int:
    """Return the RFC 6962 split point: the largest power of two < tree_size."""

    if tree_size < 2:
        raise ValueError("split_point requires tree_size >= 2")
    k = 1
    while k * 2 < tree_size:
        k *= 2
    return k


def _subtree_hash(leaves: list[str]) -> str:
    if len(leaves) == 1:
        return leaves[0]
    k = split_point(len(leaves))
    left = _subtree_hash(leaves[:k])
    right = _subtree_hash(leaves[k:])
    return _hash_pair(left, right)


def _subtree_path(leaves: list[str], index: int) -> list[dict[str, str]]:
    if len(leaves) == 1:
        return []
    k = split_point(len(leaves))
    if index < k:
        path = _subtree_path(leaves[:k], index)
        path.append({"position": "right", "hash": _subtree_hash(leaves[k:])})
    else:
        path = _subtree_path(leaves[k:], index - k)
        path.append({"position": "left", "hash": _subtree_hash(leaves[:k])})
    return path


def _hash_pair(left_hex: str, right_hex: str) -> str:
    return hashlib.sha256(
        NODE_HASH_PREFIX + bytes.fromhex(left_hex) + bytes.fromhex(right_hex)
    ).hexdigest()


def _require_sha256_hex(value: str, field_name: str) -> None:
    if len(value) != 64:
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    try:
        bytes.fromhex(value)
    except ValueError as ex:
        raise ValueError(f"{field_name} must be hex encoded") from ex
