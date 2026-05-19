from ets.crypto.hash import hash_evidence
from ets.merkle.tree import MerkleTree


class TransparencyNode:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.events = []
        self.hashes = []

    def append(self, evidence: dict):
        evidence_hash = hash_evidence(evidence)

        evidence["hash"] = evidence_hash

        self.events.append(evidence)
        self.hashes.append(evidence_hash)

        return evidence_hash

    def merkle_root(self):
        if not self.hashes:
            return None

        return MerkleTree(self.hashes).root
