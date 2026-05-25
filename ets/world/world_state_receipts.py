from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel


class WorldStateReceipt(BaseModel):
    receipt_id: str
    snapshot_id: str
    state_hash: str
    verifier: str
    verified_utc: str


def issue_world_state_receipt(
    snapshot_id: str,
    state_hash: str,
    verifier: str,
) -> WorldStateReceipt:
    return WorldStateReceipt(
        receipt_id=str(uuid4()),
        snapshot_id=snapshot_id,
        state_hash=state_hash,
        verifier=verifier,
        verified_utc=datetime.now(UTC).isoformat(),
    )
