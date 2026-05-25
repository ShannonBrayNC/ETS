from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class TrustRole(str, Enum):
    SYSTEM = 'system'
    GOVERNANCE = 'governance'
    EXECUTION = 'execution'
    VERIFIER = 'verifier'


class FederatedIdentity(BaseModel):
    identity_id: str
    display_name: str
    role: TrustRole
    public_key_fingerprint: str
    workspace_id: str
    trust_score: float


class SignedExecutionRequest(BaseModel):
    execution_id: str
    actor_identity_id: str
    payload_hash: str
    signature: str
    delegated_by: str | None = None
