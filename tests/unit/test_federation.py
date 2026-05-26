from datetime import UTC, datetime

import pytest

from ets.core.federation import FederationObservation, assess_federation
from ets.core.tree_head import SignedTreeHead


def make_tree_head(
    root_hash: str = "a" * 64,
    tree_size: int = 3,
    log_id: str = "ets-log-a",
) -> SignedTreeHead:
    return SignedTreeHead(
        tree_size=tree_size,
        root_hash=root_hash,
        created_at_utc=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
        log_id=log_id,
    )


def make_observation(verifier_id: str, root_hash: str = "a" * 64) -> FederationObservation:
    return FederationObservation(verifier_id=verifier_id, tree_head=make_tree_head(root_hash))


def test_assess_federation_accepts_matching_quorum() -> None:
    assessment = assess_federation(
        [
            make_observation("verifier-a"),
            make_observation("verifier-b"),
            make_observation("verifier-c", "b" * 64),
        ],
        threshold=2,
    )

    assert assessment.accepted is False
    assert assessment.quorum_met is True
    assert assessment.quorum_root_hash == "a" * 64
    assert assessment.conflicts[0].root_hashes == ["a" * 64, "b" * 64]


def test_assess_federation_accepts_only_when_quorum_has_no_conflict() -> None:
    assessment = assess_federation(
        [make_observation("verifier-a"), make_observation("verifier-b")],
        threshold=2,
    )

    assert assessment.accepted is True
    assert assessment.reasons == ["ok"]


def test_assess_federation_rejects_missing_quorum() -> None:
    assessment = assess_federation([make_observation("verifier-a")], threshold=2)

    assert assessment.accepted is False
    assert assessment.quorum_met is False
    assert assessment.reasons == ["quorum threshold not met"]


def test_assess_federation_rejects_empty_observations() -> None:
    assessment = assess_federation([], threshold=1)

    assert assessment.accepted is False
    assert assessment.observation_count == 0
    assert assessment.reasons == ["no observations supplied", "quorum threshold not met"]


def test_assess_federation_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        assess_federation([], threshold=0)


def test_assess_federation_rejects_duplicate_verifier_ids() -> None:
    with pytest.raises(ValueError):
        assess_federation(
            [make_observation("verifier-a"), make_observation("verifier-a")],
            threshold=1,
        )
