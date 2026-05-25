from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel


class MemoryTrustReceipt(BaseModel):
    receipt_id: str
    entity_id: str
    provenance_hash: str
    verifier: str
    verified_utc: str


def issue_memory_receipt(entity_id: str, provenance_hash: str, verifier: str) -> MemoryTrustReceipt:
    return MemoryTrustReceipt(
        receipt_id=str(uuid4()),
        entity_id=entity_id,
        provenance_hash=provenance_hash,
        verifier=verifier,
        verified_utc=datetime.now(UTC).isoformat(),
    )
