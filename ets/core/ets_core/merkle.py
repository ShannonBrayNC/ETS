import hashlib


def _hash_pair(left_hex: str, right_hex: str) -> str:
    data = bytes.fromhex(left_hex) + bytes.fromhex(right_hex)
    return hashlib.sha256(data).hexdigest()


def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return hashlib.sha256(b"").hexdigest()

    level = leaves[:]
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            next_level.append(_hash_pair(left, right))
        level = next_level
    return level[0]


def inclusion_proof(leaves: list[str], index: int) -> list[dict[str, str]]:
    if index < 0 or index >= len(leaves):
        raise IndexError("Leaf index out of range")

    proof: list[dict[str, str]] = []
    level = leaves[:]
    idx = index

    while len(level) > 1:
        next_level: list[str] = []

        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left

            if i == idx or i + 1 == idx:
                if idx == i:
                    sibling = right
                    position = "right"
                else:
                    sibling = left
                    position = "left"
                proof.append(
                    {
                        "position": position,
                        "hash": sibling,
                    }
                )

            next_level.append(_hash_pair(left, right))

        idx = idx // 2
        level = next_level

    return proof


def verify_inclusion(leaf_hash: str, proof: list[dict[str, str]], expected_root: str) -> bool:
    current = leaf_hash
    for step in proof:
        sibling = step["hash"]
        position = step["position"]

        if position == "left":
            current = _hash_pair(sibling, current)
        elif position == "right":
            current = _hash_pair(current, sibling)
        else:
            raise ValueError(f"Invalid proof position: {position}")

    return current == expected_root
