from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DistributedNodeHealth:
    node_id: str
    status: str
    trust_domain: str
    heartbeat_utc: str


class DistributedTrustVerifier:
    def validate_node(self, node: DistributedNodeHealth) -> bool:
        return node.status in {'healthy', 'degraded'}
