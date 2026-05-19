"""Deterministic Merkle tree construction for ETS."""

from __future__ import annotations

import hashlib

EMPTY_TREE_ROOT = hashlib.sha256(b"").hexdigest()


def leaf_hash_for_event_hash(event_hash: str) -> str:
    """Hash a canonical event hash into the tree leaf namespace."""

    _require_sha256_hex(event_hash, "event_hash")
    return hashlib.sha256(bytes.fromhex(event_hash)).hexdigest()


def merkle_root(leaf_hashes: list[str]) -> str:
    """Return the ETS Merkle root for leaf hashes.

    Parent hash is SHA-256(left || right). When a level has an odd number of
    nodes, the final node is duplicated before hashing.
    """

    for leaf_hash in leaf_hashes:
        _require_sha256_hex(leaf_hash, "leaf_hash")

    if not leaf_hashes:
        return EMPTY_TREE_ROOT

    level = list(leaf_hashes)
    while len(level) > 1:
        level = _next_level(level)
    return level[0]


def audit_path_for_leaf(leaf_hashes: list[str], leaf_index: int) -> list[dict[str, str]]:
    """Return the Merkle audit path for a zero-based leaf index."""

    if leaf_index < 0 or leaf_index >= len(leaf_hashes):
        raise IndexError("leaf_index is outside the tree")

    for leaf_hash in leaf_hashes:
        _require_sha256_hex(leaf_hash, "leaf_hash")

    path: list[dict[str, str]] = []
    index = leaf_index
    level = list(leaf_hashes)

    while len(level) > 1:
        if index % 2 == 0:
            sibling_index = index + 1 if index + 1 < len(level) else index
            position = "right"
        else:
            sibling_index = index - 1
            position = "left"

        path.append({"position": position, "hash": level[sibling_index]})
        level = _next_level(level)
        index //= 2

    return path


def compute_root_from_audit_path(leaf_hash: str, audit_path: list[dict[str, str]]) -> str:
    """Reconstruct a Merkle root from a leaf hash and audit path."""

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


def _next_level(level: list[str]) -> list[str]:
    next_level: list[str] = []
    for index in range(0, len(level), 2):
        left = level[index]
        right = level[index + 1] if index + 1 < len(level) else left
        next_level.append(_hash_pair(left, right))
    return next_level


def _hash_pair(left_hex: str, right_hex: str) -> str:
    return hashlib.sha256(bytes.fromhex(left_hex) + bytes.fromhex(right_hex)).hexdigest()


def _require_sha256_hex(value: str, field_name: str) -> None:
    if len(value) != 64:
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    try:
        bytes.fromhex(value)
    except ValueError as ex:
        raise ValueError(f"{field_name} must be hex encoded") from ex
