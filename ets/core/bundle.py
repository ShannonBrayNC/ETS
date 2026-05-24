"""Offline proof bundle contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ets.core.models import EvidenceEvent
from ets.core.proofs import InclusionProof, VerificationResult
from ets.core.tree_head import SignedTreeHead


class EvidenceProofBundle(BaseModel):
    """Downloadable proof package for offline evidence verification."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: str = "ets.proof_bundle.v1"
    event: EvidenceEvent
    event_hash: str = Field(min_length=64, max_length=64)
    leaf_hash: str = Field(min_length=64, max_length=64)
    tree_head: SignedTreeHead
    inclusion_proof: InclusionProof
    verification_result: VerificationResult
