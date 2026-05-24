"""Canonical election evidence packet schema for the RC demo.

The packet model is intentionally domain-specific. It records election-adjacent
evidence metadata and hashes without storing ballots, voter data, or raw sealed
artifacts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.core.canonical_json import canonical_sha256, canonicalize

ElectionEventType = Literal[
    "election_config_registered",
    "logic_accuracy_test_registered",
    "ballot_batch_scanned",
    "custody_transfer",
    "observer_note_registered",
    "cvr_export_registered",
    "audit_started",
    "audit_completed",
    "certification_snapshot",
]

PrivacyClass = Literal["public", "restricted", "sealed"]

ELECTION_EVENT_TYPES: tuple[str, ...] = (
    "election_config_registered",
    "logic_accuracy_test_registered",
    "ballot_batch_scanned",
    "custody_transfer",
    "observer_note_registered",
    "cvr_export_registered",
    "audit_started",
    "audit_completed",
    "certification_snapshot",
)

PRIVACY_CLASSES: tuple[str, ...] = ("public", "restricted", "sealed")


class PacketSignature(BaseModel):
    """Signature envelope for election evidence packets.

    RC demo fixtures may use deterministic simulated signatures. Production
    signatures require the ETS signing policy and key-management review.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    algorithm: str = Field(min_length=1, max_length=64)
    key_id: str = Field(min_length=1, max_length=128)
    value: str = Field(min_length=1, max_length=512)


class ElectionEvidencePacket(BaseModel):
    """Canonical packet format for mock election evidence workflows."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.election.packet.v1"] = "ets.election.packet.v1"
    event_id: str = Field(min_length=1, max_length=128)
    election_id: str = Field(min_length=1, max_length=128)
    jurisdiction: str = Field(min_length=1, max_length=128)
    event_type: ElectionEventType
    actor_id: str = Field(min_length=1, max_length=128)
    device_id: str = Field(min_length=1, max_length=128)
    timestamp_utc: datetime
    payload_hash: str = Field(min_length=64, max_length=64)
    previous_event_hash: str | None = Field(min_length=64, max_length=64)
    signature: PacketSignature
    privacy_class: PrivacyClass
    artifact_ref: str | None = Field(default=None, max_length=256)
    metadata: dict[str, Any] = Field(default_factory=dict)

    HASHABLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "schema_version",
        "event_id",
        "election_id",
        "jurisdiction",
        "event_type",
        "actor_id",
        "device_id",
        "timestamp_utc",
        "payload_hash",
        "previous_event_hash",
        "privacy_class",
        "artifact_ref",
        "metadata",
    )

    @field_validator("timestamp_utc")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("payload_hash", "previous_event_hash")
    @classmethod
    def require_sha256_hex(cls, value: str | None) -> str | None:
        if value is not None:
            bytes.fromhex(value)
        return value

    @field_validator("metadata")
    @classmethod
    def require_json_native_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        encoded = canonicalize(value)
        if len(encoded) > 64 * 1024:
            raise ValueError("metadata must not exceed 64 KB")
        return value

    def hashable_payload(self) -> dict[str, Any]:
        """Return the deterministic payload used for packet hash generation."""

        payload = self.model_dump(mode="json")
        return {field: payload[field] for field in self.HASHABLE_FIELDS}


def hash_election_packet(packet: ElectionEvidencePacket) -> str:
    """Return the canonical SHA-256 hash for an election evidence packet."""

    return canonical_sha256(packet.hashable_payload())
