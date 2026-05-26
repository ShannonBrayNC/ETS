"""Phase 3 distributed trust validation demo payload."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DemoNode:
    node_id: str
    ledger_root: str
    signed_root: str
    blocks: tuple[str, ...]


def run_demo() -> dict[str, Any]:
    blocks = ("block-a", "block-b", "block-c")
    shared_root = root_for(blocks)
    nodes = [
        build_node("node-a", blocks),
        build_node("node-b", blocks),
        build_node("node-c", blocks),
    ]
    divergent = build_node("node-c", ("block-a", "block-b", "tampered-block-c"))
    synchronized = validate_synchronized_roots(nodes)
    divergence_report = detect_divergence([nodes[0], nodes[1], divergent])

    return {
        "demo": "phase3-distributed-trust",
        "steps": [
            "start multiple ETS nodes",
            "synchronize ledger roots",
            "verify shared evidence",
            "introduce divergence",
            "detect and report inconsistency",
        ],
        "nodes": [node.__dict__ for node in nodes],
        "synchronization": {
            "valid": synchronized,
            "sharedRoot": shared_root,
            "signedRootExchange": [node.signed_root for node in nodes],
        },
        "sharedEvidenceVerification": {
            "block": "block-b",
            "presentOnAllNodes": all("block-b" in node.blocks for node in nodes),
        },
        "divergenceReport": divergence_report,
        "compatibility": ["SignalForge routing", "OpsHelm analytics", "ETS proof replay"],
        "note": (
            "Local deterministic verifier federation demo; "
            "not a distributed consensus implementation."
        ),
    }


def build_node(node_id: str, blocks: tuple[str, ...]) -> DemoNode:
    ledger_root = root_for(blocks)
    return DemoNode(
        node_id=node_id,
        ledger_root=ledger_root,
        signed_root=sign_root(node_id, ledger_root),
        blocks=blocks,
    )


def validate_synchronized_roots(nodes: list[DemoNode]) -> bool:
    roots = {node.ledger_root for node in nodes}
    signatures = {node.signed_root for node in nodes}
    return len(roots) == 1 and len(signatures) == len(nodes)


def detect_divergence(nodes: list[DemoNode]) -> dict[str, Any]:
    expected_root = nodes[0].ledger_root
    divergent_nodes = [
        {
            "nodeId": node.node_id,
            "ledgerRoot": node.ledger_root,
            "reason": "mismatched block root",
        }
        for node in nodes
        if node.ledger_root != expected_root
    ]
    return {
        "valid": not divergent_nodes,
        "expectedRoot": expected_root,
        "divergentNodes": divergent_nodes,
    }


def root_for(blocks: tuple[str, ...]) -> str:
    return hashlib.sha256("|".join(blocks).encode("utf-8")).hexdigest()


def sign_root(node_id: str, ledger_root: str) -> str:
    return hashlib.sha256(f"{node_id}:{ledger_root}".encode()).hexdigest()


def main() -> None:
    print(json.dumps(run_demo(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
