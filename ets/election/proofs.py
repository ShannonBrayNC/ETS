"""Election Merkle proof bundles and milestone root manifests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.merkle import leaf_hash_for_event_hash, merkle_root
from ets.core.proofs import (
    InclusionProof,
    VerificationResult,
    generate_inclusion_proof,
    verify_inclusion_proof,
)
from ets.election.ledger import ElectionLedgerEntry, PacketNotFoundError, export_election_audit_log


class ElectionRootManifest(BaseModel):
    """Published milestone root for an election evidence ledger checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: str = "ets.election.root_manifest.v1"
    election_id: str = Field(min_length=1, max_length=128)
    jurisdiction: str = Field(min_length=1, max_length=128)
    milestone: str = Field(min_length=1, max_length=128)
    tree_size: int = Field(ge=1)
    merkle_root: str = Field(min_length=64, max_length=64)
    event_ids: list[str]
    generated_at_utc: datetime
    hash_alg: str = "sha256"

    @field_validator("merkle_root")
    @classmethod
    def require_merkle_root_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value

    @field_validator("generated_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_event_ids_match_tree_size(self) -> ElectionRootManifest:
        if len(self.event_ids) != self.tree_size:
            raise ValueError("event_ids length must match tree_size")
        return self


class ElectionInclusionProofBundle(BaseModel):
    """Portable proof bundle for one election evidence packet."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: str = "ets.election.inclusion_bundle.v1"
    event_id: str = Field(min_length=1, max_length=128)
    election_id: str = Field(min_length=1, max_length=128)
    jurisdiction: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    privacy_class: str = Field(min_length=1, max_length=32)
    payload_hash: str = Field(min_length=64, max_length=64)
    event_hash: str = Field(min_length=64, max_length=64)
    leaf_hash: str = Field(min_length=64, max_length=64)
    root_manifest: ElectionRootManifest
    inclusion_proof: InclusionProof

    @field_validator("payload_hash", "event_hash", "leaf_hash")
    @classmethod
    def require_hash_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value


class ElectionBatchProofBundle(BaseModel):
    """Batch of portable proof bundles for a single milestone root."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: str = "ets.election.batch_inclusion_bundle.v1"
    root_manifest: ElectionRootManifest
    proofs: list[ElectionInclusionProofBundle]


def create_election_root_manifest(
    entries: list[ElectionLedgerEntry],
    *,
    milestone: str,
    generated_at_utc: datetime | None = None,
) -> ElectionRootManifest:
    """Create a milestone root manifest from ledger entries."""

    if not entries:
        raise ValueError("cannot publish an election root manifest for an empty ledger")

    first = entries[0].packet
    if any(entry.packet.election_id != first.election_id for entry in entries):
        raise ValueError("all entries must belong to the same election_id")
    if any(entry.packet.jurisdiction != first.jurisdiction for entry in entries):
        raise ValueError("all entries must belong to the same jurisdiction")

    leaf_hashes = _leaf_hashes(entries)
    return ElectionRootManifest(
        election_id=first.election_id,
        jurisdiction=first.jurisdiction,
        milestone=milestone,
        tree_size=len(entries),
        merkle_root=merkle_root(leaf_hashes),
        event_ids=[entry.packet.event_id for entry in entries],
        generated_at_utc=generated_at_utc or datetime.now(UTC),
    )


def create_election_inclusion_proof(
    entries: list[ElectionLedgerEntry],
    event_id: str,
    *,
    milestone: str,
    generated_at_utc: datetime | None = None,
) -> ElectionInclusionProofBundle:
    """Create a public-safe inclusion proof bundle for one election packet."""

    entry = _get_entry(entries, event_id)
    manifest = create_election_root_manifest(
        entries,
        milestone=milestone,
        generated_at_utc=generated_at_utc,
    )
    leaf_hashes = _leaf_hashes(entries)
    proof = generate_inclusion_proof(
        _proof_entries(entries),
        entry.sequence,
        generated_at_utc=generated_at_utc,
    )

    return ElectionInclusionProofBundle(
        event_id=entry.packet.event_id,
        election_id=entry.packet.election_id,
        jurisdiction=entry.packet.jurisdiction,
        event_type=entry.packet.event_type,
        privacy_class=entry.packet.privacy_class,
        payload_hash=entry.packet.payload_hash,
        event_hash=entry.event_hash,
        leaf_hash=leaf_hashes[entry.sequence],
        root_manifest=manifest,
        inclusion_proof=proof,
    )


def create_election_batch_proof(
    entries: list[ElectionLedgerEntry],
    event_ids: list[str],
    *,
    milestone: str,
    generated_at_utc: datetime | None = None,
) -> ElectionBatchProofBundle:
    """Create proof bundles for multiple event IDs at one milestone."""

    manifest = create_election_root_manifest(
        entries,
        milestone=milestone,
        generated_at_utc=generated_at_utc,
    )
    proofs = [
        create_election_inclusion_proof(
            entries,
            event_id,
            milestone=milestone,
            generated_at_utc=generated_at_utc,
        )
        for event_id in event_ids
    ]
    return ElectionBatchProofBundle(root_manifest=manifest, proofs=proofs)


def verify_election_inclusion_bundle(bundle: ElectionInclusionProofBundle) -> VerificationResult:
    """Verify an election proof bundle without sealed payload access."""

    verified_at = datetime.now(UTC)
    if bundle.root_manifest.hash_alg != "sha256":
        return _invalid(bundle, verified_at, "unsupported hash algorithm")
    if bundle.root_manifest.merkle_root != bundle.inclusion_proof.root_hash:
        return _invalid(bundle, verified_at, "manifest root does not match proof root")
    if bundle.root_manifest.tree_size != bundle.inclusion_proof.tree_size:
        return _invalid(bundle, verified_at, "manifest tree size does not match proof tree size")
    if bundle.event_id not in bundle.root_manifest.event_ids:
        return _invalid(bundle, verified_at, "event_id is absent from root manifest")
    if bundle.root_manifest.event_ids[bundle.inclusion_proof.leaf_index] != bundle.event_id:
        return _invalid(bundle, verified_at, "event_id does not match proof leaf index")
    if leaf_hash_for_event_hash(bundle.event_hash) != bundle.leaf_hash:
        return _invalid(bundle, verified_at, "leaf hash does not match event hash")
    if bundle.inclusion_proof.leaf_hash != bundle.leaf_hash:
        return _invalid(bundle, verified_at, "proof leaf hash does not match bundle leaf hash")

    result = verify_inclusion_proof(bundle.inclusion_proof)
    if not result.valid:
        return result
    return VerificationResult(
        valid=True,
        reason="ok",
        root_hash=bundle.root_manifest.merkle_root,
        leaf_hash=bundle.leaf_hash,
        tree_size=bundle.root_manifest.tree_size,
        verified_at_utc=verified_at,
    )


def verify_election_batch_bundle(bundle: ElectionBatchProofBundle) -> list[VerificationResult]:
    """Verify every proof in a batch bundle."""

    return [verify_election_inclusion_bundle(proof) for proof in bundle.proofs]


def export_election_proof_report(bundle: ElectionInclusionProofBundle) -> dict[str, Any]:
    """Return a human-readable and machine-readable proof summary."""

    result = verify_election_inclusion_bundle(bundle)
    return {
        "event_id": bundle.event_id,
        "election_id": bundle.election_id,
        "milestone": bundle.root_manifest.milestone,
        "privacy_class": bundle.privacy_class,
        "merkle_root": bundle.root_manifest.merkle_root,
        "leaf_hash": bundle.leaf_hash,
        "tree_size": bundle.root_manifest.tree_size,
        "valid": result.valid,
        "reason": result.reason,
    }


def export_root_manifest_audit_summary(
    entries: list[ElectionLedgerEntry],
    *,
    milestone: str,
    generated_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Export a manifest plus append-order audit summary."""

    manifest = create_election_root_manifest(
        entries,
        milestone=milestone,
        generated_at_utc=generated_at_utc,
    )
    return {
        "root_manifest": manifest.model_dump(mode="json"),
        "audit_log": export_election_audit_log(entries),
    }


def _leaf_hashes(entries: list[ElectionLedgerEntry]) -> list[str]:
    return [leaf_hash_for_event_hash(entry.event_hash) for entry in entries]


def _proof_entries(entries: list[ElectionLedgerEntry]) -> list[Any]:
    return [
        type(
            "ElectionProofEntry",
            (),
            {"leaf_hash": leaf_hash_for_event_hash(entry.event_hash)},
        )()
        for entry in entries
    ]


def _get_entry(entries: list[ElectionLedgerEntry], event_id: str) -> ElectionLedgerEntry:
    for entry in entries:
        if entry.packet.event_id == event_id:
            return entry
    raise PacketNotFoundError(f"election event_id not found: {event_id}")


def _invalid(
    bundle: ElectionInclusionProofBundle,
    verified_at_utc: datetime,
    reason: str,
) -> VerificationResult:
    return VerificationResult(
        valid=False,
        reason=reason,
        root_hash=bundle.root_manifest.merkle_root,
        leaf_hash=bundle.leaf_hash,
        tree_size=bundle.root_manifest.tree_size,
        verified_at_utc=verified_at_utc,
    )
