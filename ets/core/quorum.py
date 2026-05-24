"""Verifier quorum decisions for federated ETS checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerifierVote:
    verifier_id: str
    valid: bool
    reason: str = "ok"


@dataclass(frozen=True)
class QuorumDecision:
    accepted: bool
    valid_votes: int
    total_votes: int
    threshold: int
    reasons: list[str]


def decide_quorum(votes: list[VerifierVote], threshold: int) -> QuorumDecision:
    if threshold < 1:
        raise ValueError("threshold must be at least 1")
    valid_votes = sum(1 for vote in votes if vote.valid)
    return QuorumDecision(
        accepted=valid_votes >= threshold,
        valid_votes=valid_votes,
        total_votes=len(votes),
        threshold=threshold,
        reasons=[vote.reason for vote in votes if not vote.valid],
    )
