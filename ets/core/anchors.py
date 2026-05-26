"""Deterministic external anchor exports for ETS ledger checkpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.core.canonical_json import canonical_sha256
from ets.core.tree_head import SignedTreeHead

AnchorTarget = Literal["github_release", "azure_immutable_storage", "local_file"]


class AnchorExport(BaseModel):
    """Portable checkpoint intended for publication to an external trust anchor."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: str = "ets.anchor_export.v1"
    anchor_id: str = Field(min_length=1)
    anchor_hash: str = Field(min_length=64, max_length=64)
    target: AnchorTarget
    source_log_id: str = Field(min_length=1)
    tree_size: int = Field(ge=0)
    merkle_root: str = Field(min_length=64, max_length=64)
    latest_block_hash: str = Field(min_length=64, max_length=64)
    signed_tree_head: SignedTreeHead
    exported_at_utc: datetime
    notes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("anchor_hash", "merkle_root", "latest_block_hash")
    @classmethod
    def require_hash_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value

    @field_validator("exported_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("exported_at_utc must be timezone-aware")
        return value.astimezone(UTC)


class AnchorVerificationResult(BaseModel):
    """Deterministic result for offline anchor continuity checks."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    valid: bool
    reason: str
    anchor_id: str
    anchor_hash: str
    source_log_id: str
    tree_size: int
    merkle_root: str


def anchor_export_payload(anchor: AnchorExport) -> dict[str, object]:
    """Return the canonical hash payload for an anchor export."""

    return {
        "schema_version": anchor.schema_version,
        "target": anchor.target,
        "source_log_id": anchor.source_log_id,
        "tree_size": anchor.tree_size,
        "merkle_root": anchor.merkle_root,
        "latest_block_hash": anchor.latest_block_hash,
        "signed_tree_head": anchor.signed_tree_head.model_dump(mode="json"),
        "exported_at_utc": anchor.exported_at_utc.astimezone(UTC).isoformat(),
        "notes": list(anchor.notes),
    }


def build_anchor_export(
    *,
    target: AnchorTarget,
    tree_head: SignedTreeHead,
    latest_block_hash: str,
    exported_at_utc: datetime,
    notes: tuple[str, ...] = (),
) -> AnchorExport:
    """Build an exportable ledger-root anchor from a signed tree head."""

    exported_at = _require_utc(exported_at_utc, "exported_at_utc")
    _require_sha256_hex(latest_block_hash, "latest_block_hash")
    partial = AnchorExport(
        anchor_id="pending",
        anchor_hash="0" * 64,
        target=target,
        source_log_id=tree_head.log_id,
        tree_size=tree_head.tree_size,
        merkle_root=tree_head.root_hash,
        latest_block_hash=latest_block_hash,
        signed_tree_head=tree_head,
        exported_at_utc=exported_at,
        notes=notes,
    )
    anchor_hash = canonical_sha256(anchor_export_payload(partial))
    anchor_id = _anchor_id(target, tree_head.log_id, tree_head.tree_size, anchor_hash)
    return partial.model_copy(update={"anchor_id": anchor_id, "anchor_hash": anchor_hash})


def verify_anchor_export(anchor: AnchorExport) -> AnchorVerificationResult:
    """Verify that an anchor export is internally consistent and untampered."""

    if anchor.source_log_id != anchor.signed_tree_head.log_id:
        return _verification_result(anchor, False, "source log id does not match tree head")
    if anchor.tree_size != anchor.signed_tree_head.tree_size:
        return _verification_result(anchor, False, "tree size does not match tree head")
    if anchor.merkle_root != anchor.signed_tree_head.root_hash:
        return _verification_result(anchor, False, "merkle root does not match tree head")

    expected_hash = canonical_sha256(anchor_export_payload(anchor))
    if anchor.anchor_hash != expected_hash:
        return _verification_result(anchor, False, "anchor hash does not match contents")

    expected_id = _anchor_id(
        anchor.target,
        anchor.source_log_id,
        anchor.tree_size,
        expected_hash,
    )
    if anchor.anchor_id != expected_id:
        return _verification_result(anchor, False, "anchor id does not match contents")

    return _verification_result(anchor, True, "ok")


def _verification_result(
    anchor: AnchorExport,
    valid: bool,
    reason: str,
) -> AnchorVerificationResult:
    return AnchorVerificationResult(
        valid=valid,
        reason=reason,
        anchor_id=anchor.anchor_id,
        anchor_hash=anchor.anchor_hash,
        source_log_id=anchor.source_log_id,
        tree_size=anchor.tree_size,
        merkle_root=anchor.merkle_root,
    )


def _anchor_id(
    target: AnchorTarget,
    source_log_id: str,
    tree_size: int,
    anchor_hash: str,
) -> str:
    return f"ets-anchor:{target}:{source_log_id}:{tree_size}:{anchor_hash[:16]}"


def _require_sha256_hex(value: str, field_name: str) -> None:
    if len(value) != 64:
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be hex encoded") from exc


def _require_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)
