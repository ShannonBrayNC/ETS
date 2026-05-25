from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel


class LearningTrustReceipt(BaseModel):
    receipt_id: str
    outcome_id: str
    learning_hash: str
    verifier: str
    verified_utc: str


def issue_learning_receipt(
    outcome_id: str,
    learning_hash: str,
    verifier: str,
) -> LearningTrustReceipt:
    return LearningTrustReceipt(
        receipt_id=str(uuid4()),
        outcome_id=outcome_id,
        learning_hash=learning_hash,
        verifier=verifier,
        verified_utc=datetime.now(UTC).isoformat(),
    )
