import pytest

from ets.core.quorum import VerifierVote, decide_quorum


def test_decide_quorum_accepts_threshold() -> None:
    decision = decide_quorum(
        [
            VerifierVote("v1", True),
            VerifierVote("v2", True),
            VerifierVote("v3", False, "bad proof"),
        ],
        threshold=2,
    )

    assert decision.accepted is True
    assert decision.valid_votes == 2
    assert decision.reasons == ["bad proof"]


def test_decide_quorum_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        decide_quorum([], threshold=0)
