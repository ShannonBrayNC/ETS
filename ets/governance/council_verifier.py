from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CouncilDecisionRecord:
    proposal_id: str
    approved: bool
    verifier_separated: bool
    quorum_reached: bool


class CouncilVerifier:
    def validate(self, decision: CouncilDecisionRecord) -> bool:
        return (
            decision.approved
            and decision.verifier_separated
            and decision.quorum_reached
        )
