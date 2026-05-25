from __future__ import annotations

from pydantic import BaseModel, Field


class LanternGovernanceEvent(BaseModel):
    event_id: str
    source_system: str
    workspace: str
    recommendation_id: str
    event_type: str
    actor: str
    timestamp_utc: str
    payload_hash: str


class LanternTrustReceipt(BaseModel):
    receipt_id: str
    governance_event: LanternGovernanceEvent
    canonical_hash: str
    previous_hash: str = Field(default="genesis")
    receipt_hash: str
    verifier: str
    verified_utc: str
