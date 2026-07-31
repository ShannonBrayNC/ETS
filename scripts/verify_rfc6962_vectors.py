"""Independently verify ETS RFC 6962 vectors without importing ETS runtime code."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

PROFILE = "ets.merkle.rfc6962_sha256.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
VECTOR_ROOT = REPO_ROOT / "ets" / "spec" / "test-vectors" / "v0.1"


def reference_leaf_hash(event_hash_hex: str) -> str:
    """Return SHA-256(0x00 || raw event digest)."""

    event_hash = bytes.fromhex(event_hash_hex)
    if len(event_hash) != 32:
        raise ValueError("event hash must decode to 32 bytes")
    return sha256(b"\x00" + event_hash).hexdigest()


def reference_node_hash(left_hex: str, right_hex: str) -> str:
    """Return SHA-256(0x01 || raw left digest || raw right digest)."""

    left = bytes.fromhex(left_hex)
    right = bytes.fromhex(right_hex)
    if len(left) != 32 or len(right) != 32:
        raise ValueError("child hashes must decode to 32 bytes")
    return sha256(b"\x01" + left + right).hexdigest()


def reference_merkle_root(leaf_hashes: list[str]) -> str:
    """Return the RFC 6962 root for already domain-separated leaf hashes."""

    if not leaf_hashes:
        return sha256(b"").hexdigest()
    if len(leaf_hashes) == 1:
        leaf = bytes.fromhex(leaf_hashes[0])
        if len(leaf) != 32:
            raise ValueError("leaf hash must decode to 32 bytes")
        return leaf.hex()
    split = 1 << ((len(leaf_hashes) - 1).bit_length() - 1)
    left = reference_merkle_root(leaf_hashes[:split])
    right = reference_merkle_root(leaf_hashes[split:])
    return reference_node_hash(left, right)


def verify_checked_in_vectors() -> list[str]:
    """Return descriptions of all mismatches in the checked-in vector set."""

    merkle = json.loads((VECTOR_ROOT / "merkle-vectors.json").read_text(encoding="utf-8"))
    event = json.loads((VECTOR_ROOT / "event-vectors.json").read_text(encoding="utf-8"))
    errors: list[str] = []

    if merkle.get("merkle_profile") != PROFILE:
        errors.append("merkle vector profile does not match reference profile")
    if event.get("merkle_profile") != PROFILE:
        errors.append("event vector profile does not match reference profile")

    leaves = merkle["leaf_hashes"]
    expected_roots = merkle["roots"]
    root_cases = {
        "empty": reference_merkle_root([]),
        "single_leaf": reference_merkle_root(leaves[:1]),
        "two_leaves": reference_merkle_root(leaves[:2]),
        "three_leaves": reference_merkle_root(leaves[:3]),
        "four_leaves": reference_merkle_root(leaves[:4]),
    }
    for name, actual in root_cases.items():
        if actual != expected_roots[name]:
            errors.append(f"{name} root mismatch: {actual} != {expected_roots[name]}")

    event_leaf = reference_leaf_hash(event["expected"]["event_hash"])
    if event_leaf != event["expected"]["leaf_hash"]:
        errors.append(f"event leaf mismatch: {event_leaf} != {event['expected']['leaf_hash']}")
    return errors


def main() -> int:
    errors = verify_checked_in_vectors()
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {PROFILE} vectors verified independently")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
