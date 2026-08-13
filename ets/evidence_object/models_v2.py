"""Canonical Evidence Object v2 contract.

Version 2 is additive to both ``ets.event.v1`` and Evidence Object v1.  It
defines an explicit canonical identity boundary while allowing proof material
to evolve independently.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DigestRef(StrictV2Model):
    algorithm: Literal["sha256"] = "sha256"
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvidenceIdentityV2(StrictV2Model):
    object_id: str = Field(min_length=1, max_length=256)
    namespace: str = Field(min_length=1, max_length=256)
    object_type: str = Field(min_length=1, max_length=128)
    version: int = Field(ge=1)


class ContractBinding(StrictV2Model):
    """A typed reference to a separately versioned evidence contract."""

    binding_type: Literal[
        "event",
        "claim",
        "provenance",
        "context",
        "relationship",
        "policy",
        "privacy",
        "verification",
    ]
    contract_id: str = Field(min_length=1, max_length=256)
    subject_ref: str = Field(min_length=1, max_length=2048)
    commitment: DigestRef | None = None


class PolicyDescriptorV2(StrictV2Model):
    policy_ref: str = Field(min_length=1, max_length=2048)
    purpose: str | None = Field(default=None, max_length=256)
    audience: tuple[str, ...] = ()


class PrivacyDescriptorV2(StrictV2Model):
    classification: str = Field(min_length=1, max_length=128)
    contains_pii: bool = False
    minimization_profile: str | None = Field(default=None, max_length=256)
    disclosure_policy_ref: str | None = Field(default=None, max_length=2048)


class ProofMaterialV2(StrictV2Model):
    """Non-identity proof attachment.

    ``proof_type`` and ``material`` deliberately permit future proof profiles.
    The entire collection is excluded from the canonical identity preimage.
    """

    proof_type: str = Field(min_length=1, max_length=256)
    profile: str = Field(min_length=1, max_length=256)
    material: dict[str, Any]


class EvidenceObjectV2(StrictV2Model):
    """Normative Evidence Object v2 envelope and identity boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/evidence-object/v2"
        },
    )

    schema_id: Literal[
        "https://lanternprotocol.org/schemas/ets/evidence-object/v2"
    ] = "https://lanternprotocol.org/schemas/ets/evidence-object/v2"
    identity: EvidenceIdentityV2
    created_at: datetime
    bindings: tuple[ContractBinding, ...] = Field(min_length=1)
    policies: tuple[PolicyDescriptorV2, ...] = ()
    privacy: PrivacyDescriptorV2 | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)
    proof_material: tuple[ProofMaterialV2, ...] = ()

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_unique_bindings(self) -> EvidenceObjectV2:
        keys = {
            (item.binding_type, item.contract_id, item.subject_ref)
            for item in self.bindings
        }
        if len(keys) != len(self.bindings):
            raise ValueError("bindings must be unique")
        return self
