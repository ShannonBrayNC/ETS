import hashlib


class MerkleTree:
    def __init__(self, leaves: list[str]):
        self.leaves = leaves or []
        self.levels = []

        if self.leaves:
            self._build()

    @staticmethod
    def _hash_pair(left: str, right: str) -> str:
        return hashlib.sha256(
            f"{left}{right}".encode("utf-8")
        ).hexdigest()

    def _build(self):
        level = self.leaves[:]
        self.levels.append(level)

        while len(level) > 1:
            next_level = []

            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left

                next_level.append(self._hash_pair(left, right))

            level = next_level
            self.levels.append(level)

    @property
    def root(self):
        if not self.levels:
            return None

        return self.levels[-1][0]
