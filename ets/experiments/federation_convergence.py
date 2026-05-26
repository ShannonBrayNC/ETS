"""Deterministic verifier-federation convergence experiments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ets.core.federation import FederationObservation, assess_federation
from ets.core.tree_head import SignedTreeHead


@dataclass(frozen=True)
class FederationConvergenceResult:
    verifier_count: int
    threshold: int
    conflicting_roots: int
    accepted: bool
    quorum_met: bool
    conflict_count: int


def run_federation_convergence(
    verifier_count: int = 3,
    threshold: int = 2,
    conflicting_roots: int = 0,
) -> FederationConvergenceResult:
    """Run a deterministic root-agreement experiment over synthetic verifiers."""

    if verifier_count < 1:
        raise ValueError("verifier_count must be at least 1")
    if conflicting_roots < 0 or conflicting_roots > verifier_count:
        raise ValueError("conflicting_roots must be between 0 and verifier_count")

    observations: list[FederationObservation] = []
    stable_root = "a" * 64
    conflict_root = "b" * 64
    for index in range(verifier_count):
        root_hash = conflict_root if index < conflicting_roots else stable_root
        observations.append(
            FederationObservation(
                verifier_id=f"verifier-{index:02d}",
                tree_head=SignedTreeHead(
                    tree_size=5,
                    root_hash=root_hash,
                    created_at_utc=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
                    log_id="ets-federation-lab",
                ),
            )
        )

    assessment = assess_federation(observations, threshold)
    return FederationConvergenceResult(
        verifier_count=verifier_count,
        threshold=threshold,
        conflicting_roots=conflicting_roots,
        accepted=assessment.accepted,
        quorum_met=assessment.quorum_met,
        conflict_count=len(assessment.conflicts),
    )
