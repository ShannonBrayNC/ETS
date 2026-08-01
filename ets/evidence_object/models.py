"""Canonical Evidence Object Model v1.

The model is additive to the v0.1 EvidenceEvent protocol. It defines the
semantic object that future graph, policy, edge, and federation capabilities
will exchange without rewriting historical transparency-log entries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Base configuration for normative Evidence Object structures."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class HashAlgorithm(StrEnum):
    SHA256 = "sha256"


class RelationshipType(StrEnum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    CORROBORATES = "corroborates"
    GENERATED = "generated"
    OBSERVED = "observed"
    DERIVED = "derived"
    SUPERSEDES = "supersedes"
    REFERENCES = "references"
    DUPLICATES = "duplicates"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"


class LifecycleState(StrEnum):
    CREATED = "created"
    OBSERVED = "observed"
    COLLECTED = "collected"
    REGISTERED = "registered"
    VERIFIED = "verified"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"
    DESTROYED = "destroyed"


class VerificationResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INDETERMINATE = "indeterminate"


class EvidenceIdentity(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=256)
    version: int = Field(ge=1)
    namespace: str = Field(min_length=1, max_length=256)
    evidence_type: str = Field(min_length=1, max_length=128)
    schema_version: Literal["ets.evidence-object.v1"] = "ets.evidence-object.v1"


class Claim(StrictModel):
    claim_id: str = Field(min_length=1, max_length=256)
    subject: str = Field(min_length=1, max_length=2048)
    predicate: str = Field(min_length=1, max_length=256)
    object: str | None = Field(default=None, max_length=2048)
    value: Any | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_ref: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def require_object_or_value(self) -> Claim:
        if self.object is None and self.value is None:
            raise ValueError("claim requires object or value")
        return self


class Assertion(StrictModel):
    assertion_id: str = Field(min_length=1, max_length=256)
    claim_id: str = Field(min_length=1, max_length=256)
    actor_ref: str = Field(min_length=1, max_length=2048)
    asserted_at: datetime
    signature_ref: str | None = Field(default=None, max_length=2048)
    policy_ref: str | None = Field(default=None, max_length=2048)

    @field_validator("asserted_at")
    @classmethod
    def normalize_asserted_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("asserted_at must be timezone-aware")
        return value.astimezone(UTC)


class Provenance(StrictModel):
    collected_by: str | None = Field(default=None, max_length=2048)
    source_system: str | None = Field(default=None, max_length=256)
    device_ref: str | None = Field(default=None, max_length=2048)
    workflow_ref: str | None = Field(default=None, max_length=2048)
    repository_ref: str | None = Field(default=None, max_length=2048)
    commit_ref: str | None = Field(default=None, max_length=256)
    branch_ref: str | None = Field(default=None, max_length=256)
    operator_ref: str | None = Field(default=None, max_length=2048)


class EvidenceContext(StrictModel):
    context_type: str = Field(min_length=1, max_length=128)
    context_ref: str = Field(min_length=1, max_length=2048)
    attributes: dict[str, Any] = Field(default_factory=dict)


class Relationship(StrictModel):
    relationship_id: str = Field(min_length=1, max_length=256)
    relationship_type: RelationshipType
    target_evidence_ref: str = Field(min_length=1, max_length=2048)
    observed: bool = True
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class IntegrityBinding(StrictModel):
    algorithm: HashAlgorithm = HashAlgorithm.SHA256
    digest: str = Field(min_length=64, max_length=64)
    scope: str = Field(min_length=1, max_length=256)
    profile: str = Field(min_length=1, max_length=256)

    @field_validator("digest")
    @classmethod
    def require_hex_digest(cls, value: str) -> str:
        bytes.fromhex(value)
        return value.lower()


class VerificationRecord(StrictModel):
    verification_id: str = Field(min_length=1, max_length=256)
    method: str = Field(min_length=1, max_length=256)
    verified_at: datetime
    result: VerificationResult
    policy_ref: str | None = Field(default=None, max_length=2048)
    details: dict[str, Any] = Field(default_factory=dict)
    certificate_ref: str | None = Field(default=None, max_length=2048)

    @field_validator("verified_at")
    @classmethod
    def normalize_verified_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("verified_at must be timezone-aware")
        return value.astimezone(UTC)


class PrivacyPolicy(StrictModel):
    classification: str = Field(min_length=1, max_length=128)
    owner_ref: str | None = Field(default=None, max_length=2048)
    contains_pii: bool = False
    encryption_required: bool = False
    retention_policy_ref: str | None = Field(default=None, max_length=2048)
    legal_hold: bool = False
    redaction_profile: str | None = Field(default=None, max_length=256)


class LifecycleRecord(StrictModel):
    state: LifecycleState
    occurred_at: datetime
    actor_ref: str | None = Field(default=None, max_length=2048)
    reason: str | None = Field(default=None, max_length=2048)

    @field_validator("occurred_at")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value.astimezone(UTC)


class EvidenceObject(StrictModel):
    """Normative Evidence Object v1 contract."""

    schema_id: Literal[
        "https://lanternprotocol.org/schemas/ets/evidence-object/v1"
    ] = "https://lanternprotocol.org/schemas/ets/evidence-object/v1"
    identity: EvidenceIdentity
    created_at: datetime
    claims: tuple[Claim, ...] = ()
    assertions: tuple[Assertion, ...] = ()
    provenance: Provenance | None = None
    contexts: tuple[EvidenceContext, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    integrity: tuple[IntegrityBinding, ...] = ()
    verifications: tuple[VerificationRecord, ...] = ()
    policy_refs: tuple[str, ...] = ()
    privacy: PrivacyPolicy | None = None
    lifecycle: tuple[LifecycleRecord, ...] = ()
    corrects_ref: str | None = Field(default=None, max_length=2048)
    supersedes_ref: str | None = Field(default=None, max_length=2048)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_internal_references(self) -> EvidenceObject:
        claim_ids = {claim.claim_id for claim in self.claims}
        if len(claim_ids) != len(self.claims):
            raise ValueError("claim_id values must be unique")
        for assertion in self.assertions:
            if assertion.claim_id not in claim_ids:
                raise ValueError(
                    f"assertion references unknown claim_id: {assertion.claim_id}"
                )
        relationship_ids = {item.relationship_id for item in self.relationships}
        if len(relationship_ids) != len(self.relationships):
            raise ValueError("relationship_id values must be unique")
        return self
