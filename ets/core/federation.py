"""Deterministic verifier-federation assessment primitives."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ets.core.tree_head import SignedTreeHead


class FederationObservation(BaseModel):
    """A verifier's observed tree head for a log node."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    verifier_id: str = Field(min_length=1, max_length=128)
    tree_head: SignedTreeHead


class FederationConflict(BaseModel):
    """A same-log, same-size root disagreement observed by the federation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    log_id: str
    tree_size: int
    root_hashes: list[str]
    verifier_ids_by_root: dict[str, list[str]]


class FederationAssessment(BaseModel):
    """Quorum and fork-suspicion result for a set of verifier observations."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    accepted: bool
    threshold: int
    observation_count: int
    quorum_met: bool
    quorum_log_id: str | None
    quorum_tree_size: int | None
    quorum_root_hash: str | None
    conflicts: list[FederationConflict]
    reasons: list[str]


def assess_federation(
    observations: list[FederationObservation],
    threshold: int,
) -> FederationAssessment:
    """Assess root agreement and quorum over verifier observations.

    Patent-awareness note: this function intentionally models ETS federation
    semantics as protocol integration logic. It does not claim novelty in
    generic threshold voting, hashing, signatures, or Merkle trees.
    """

    if threshold < 1:
        raise ValueError("threshold must be at least 1")

    verifier_ids = [observation.verifier_id for observation in observations]
    if len(verifier_ids) != len(set(verifier_ids)):
        raise ValueError("verifier_id values must be unique per assessment")

    root_groups: dict[tuple[str, int, str], list[str]] = {}
    view_groups: dict[tuple[str, int], dict[str, list[str]]] = {}
    for observation in observations:
        tree_head = observation.tree_head
        root_key = (tree_head.log_id, tree_head.tree_size, tree_head.root_hash)
        view_key = (tree_head.log_id, tree_head.tree_size)
        root_groups.setdefault(root_key, []).append(observation.verifier_id)
        view_groups.setdefault(view_key, {}).setdefault(tree_head.root_hash, []).append(
            observation.verifier_id
        )

    conflicts = [
        FederationConflict(
            log_id=log_id,
            tree_size=tree_size,
            root_hashes=sorted(roots),
            verifier_ids_by_root={root: sorted(ids) for root, ids in sorted(roots.items())},
        )
        for (log_id, tree_size), roots in sorted(view_groups.items())
        if len(roots) > 1
    ]

    quorum_candidates = [
        (log_id, tree_size, root_hash, sorted(ids))
        for (log_id, tree_size, root_hash), ids in root_groups.items()
        if len(ids) >= threshold
    ]
    quorum_candidates.sort(key=lambda item: (-len(item[3]), item[0], item[1], item[2]))
    quorum = quorum_candidates[0] if quorum_candidates else None

    reasons: list[str] = []
    if not observations:
        reasons.append("no observations supplied")
    if quorum is None:
        reasons.append("quorum threshold not met")
    for conflict in conflicts:
        reasons.append(
            f"conflicting roots for log_id={conflict.log_id} tree_size={conflict.tree_size}"
        )

    quorum_met = quorum is not None
    return FederationAssessment(
        accepted=quorum_met and not conflicts,
        threshold=threshold,
        observation_count=len(observations),
        quorum_met=quorum_met,
        quorum_log_id=quorum[0] if quorum else None,
        quorum_tree_size=quorum[1] if quorum else None,
        quorum_root_hash=quorum[2] if quorum else None,
        conflicts=conflicts,
        reasons=reasons or ["ok"],
    )
