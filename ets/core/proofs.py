"""Inclusion proof generation and verification."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.core.log import LogEntry
from ets.core.merkle import audit_path_for_leaf, compute_root_from_audit_path, merkle_root


class AuditPathStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    position: Literal["left", "right"]
    hash: str = Field(min_length=64, max_length=64)

    @field_validator("hash")
    @classmethod
    def require_hash_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value


class InclusionProof(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: str = "ets.inclusion_proof.v1"
    tree_size: int = Field(ge=1)
    leaf_index: int = Field(ge=0)
    leaf_hash: str = Field(min_length=64, max_length=64)
    root_hash: str = Field(min_length=64, max_length=64)
    audit_path: list[AuditPathStep]
    hash_alg: str = "sha256"
    generated_at_utc: datetime

    @field_validator("leaf_hash", "root_hash")
    @classmethod
    def require_hash_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value

    @field_validator("generated_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at_utc must be timezone-aware")
        return value.astimezone(UTC)


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    valid: bool
    reason: str
    root_hash: str | None = None
    leaf_hash: str | None = None
    tree_size: int | None = None
    verified_at_utc: datetime


def generate_inclusion_proof(
    entries: list[LogEntry],
    leaf_index: int,
    generated_at_utc: datetime | None = None,
) -> InclusionProof:
    """Generate an inclusion proof from append-only log entries."""

    if leaf_index < 0 or leaf_index >= len(entries):
        raise IndexError("leaf_index is outside the tree")

    leaf_hashes = [entry.leaf_hash for entry in entries]
    generated_at = generated_at_utc or datetime.now(UTC)

    return InclusionProof(
        tree_size=len(leaf_hashes),
        leaf_index=leaf_index,
        leaf_hash=leaf_hashes[leaf_index],
        root_hash=merkle_root(leaf_hashes),
        audit_path=[
            AuditPathStep.model_validate(step)
            for step in audit_path_for_leaf(leaf_hashes, leaf_index)
        ],
        generated_at_utc=generated_at,
    )


def verify_inclusion_proof(proof: InclusionProof) -> VerificationResult:
    """Verify a self-contained ETS inclusion proof."""

    verified_at = datetime.now(UTC)

    if proof.hash_alg != "sha256":
        return _invalid(proof, verified_at, "unsupported hash algorithm")

    if proof.leaf_index >= proof.tree_size:
        return _invalid(proof, verified_at, "leaf index is outside tree size")

    if proof.tree_size == 1 and proof.audit_path:
        return _invalid(proof, verified_at, "single-leaf tree must not have an audit path")

    expected_positions = _expected_audit_path_positions(proof.tree_size, proof.leaf_index)
    actual_positions = [step.position for step in proof.audit_path]
    if actual_positions != expected_positions:
        return _invalid(proof, verified_at, "audit path does not match leaf index")

    try:
        path = [step.model_dump() for step in proof.audit_path]
        computed_root = compute_root_from_audit_path(proof.leaf_hash, path)
    except ValueError as ex:
        return _invalid(proof, verified_at, str(ex))

    if computed_root != proof.root_hash:
        return _invalid(proof, verified_at, "computed root does not match proof root")

    return VerificationResult(
        valid=True,
        reason="ok",
        root_hash=proof.root_hash,
        leaf_hash=proof.leaf_hash,
        tree_size=proof.tree_size,
        verified_at_utc=verified_at,
    )


def _expected_audit_path_positions(tree_size: int, leaf_index: int) -> list[str]:
    positions: list[str] = []
    level_size = tree_size
    index = leaf_index

    while level_size > 1:
        positions.append("right" if index % 2 == 0 else "left")
        index //= 2
        level_size = (level_size + 1) // 2

    return positions


def _invalid(
    proof: InclusionProof,
    verified_at_utc: datetime,
    reason: str,
) -> VerificationResult:
    return VerificationResult(
        valid=False,
        reason=reason,
        root_hash=proof.root_hash,
        leaf_hash=proof.leaf_hash,
        tree_size=proof.tree_size,
        verified_at_utc=verified_at_utc,
    )
