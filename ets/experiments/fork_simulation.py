"""Fork simulation for detecting same-size divergent tree heads."""

from __future__ import annotations

from dataclasses import dataclass

from ets.core import InMemoryAppendOnlyLog, SignedTreeHead
from ets.core.merkle import merkle_root
from ets.experiments.dataset import generate_synthetic_events


@dataclass(frozen=True)
class ForkSimulationResult:
    fork_detected: bool
    left_root: str
    right_root: str
    tree_size: int


def run_fork_simulation(event_count: int = 3) -> ForkSimulationResult:
    left_log = InMemoryAppendOnlyLog()
    right_log = InMemoryAppendOnlyLog()
    for event in generate_synthetic_events(event_count):
        left_log.append(event)
    for event in reversed(generate_synthetic_events(event_count)):
        right_log.append(event)

    left_root = merkle_root([entry.leaf_hash for entry in left_log.list_entries()])
    right_root = merkle_root([entry.leaf_hash for entry in right_log.list_entries()])
    return ForkSimulationResult(
        fork_detected=left_root != right_root and event_count > 1,
        left_root=left_root,
        right_root=right_root,
        tree_size=event_count,
    )


def detect_fork(previous: SignedTreeHead, candidate: SignedTreeHead) -> bool:
    return previous.tree_size == candidate.tree_size and previous.root_hash != candidate.root_hash
