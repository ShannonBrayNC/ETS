"""Deterministic hash-chain blocks for ETS Sprint 1 compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ets.core.canonical_json import canonical_sha256
from ets.core.log import LogEntry

GENESIS_BLOCK_HASH = "0" * 64


@dataclass(frozen=True)
class HashChainBlock:
    """Immutable block containing ETS log entries and previous-block linkage."""

    block_number: int
    previous_block_hash: str
    block_hash: str
    events: tuple[LogEntry, ...]
    created_at_utc: datetime


@dataclass(frozen=True)
class ChainVerificationResult:
    valid: bool
    reason: str
    failed_block_number: int | None = None


def build_block(
    block_number: int,
    previous_block_hash: str,
    entries: list[LogEntry],
    created_at_utc: datetime,
) -> HashChainBlock:
    """Build an immutable hash-chain block from append-only log entries."""

    if block_number < 0:
        raise ValueError("block_number must be non-negative")
    _require_sha256_hex(previous_block_hash, "previous_block_hash")
    _require_utc(created_at_utc)
    events = tuple(entries)
    block_without_hash = {
        "block_number": block_number,
        "previous_block_hash": previous_block_hash,
        "events": [_entry_payload(entry) for entry in events],
        "created_at_utc": created_at_utc.astimezone(UTC).isoformat(),
    }
    return HashChainBlock(
        block_number=block_number,
        previous_block_hash=previous_block_hash,
        block_hash=canonical_sha256(block_without_hash),
        events=events,
        created_at_utc=created_at_utc.astimezone(UTC),
    )


def verify_chain(blocks: list[HashChainBlock]) -> ChainVerificationResult:
    """Verify block numbering, previous-hash continuity, and block hashes."""

    expected_previous_hash = GENESIS_BLOCK_HASH
    for expected_number, block in enumerate(blocks):
        if block.block_number != expected_number:
            return ChainVerificationResult(
                valid=False,
                reason="block number is not monotonic",
                failed_block_number=block.block_number,
            )
        if block.previous_block_hash != expected_previous_hash:
            return ChainVerificationResult(
                valid=False,
                reason="previous block hash does not match",
                failed_block_number=block.block_number,
            )
        recomputed = recompute_block_hash(block)
        if recomputed != block.block_hash:
            return ChainVerificationResult(
                valid=False,
                reason="block hash does not match block contents",
                failed_block_number=block.block_number,
            )
        expected_previous_hash = block.block_hash

    return ChainVerificationResult(valid=True, reason="ok")


def recompute_block_hash(block: HashChainBlock) -> str:
    """Recompute a block hash from its immutable contents."""

    _require_utc(block.created_at_utc)
    return canonical_sha256(
        {
            "block_number": block.block_number,
            "previous_block_hash": block.previous_block_hash,
            "events": [_entry_payload(entry) for entry in block.events],
            "created_at_utc": block.created_at_utc.astimezone(UTC).isoformat(),
        }
    )


def export_block(block: HashChainBlock) -> dict[str, Any]:
    """Export a hash-chain block as deterministic JSON-native data."""

    return {
        "block_number": block.block_number,
        "previous_block_hash": block.previous_block_hash,
        "block_hash": block.block_hash,
        "created_at_utc": block.created_at_utc.astimezone(UTC).isoformat(),
        "events": [_entry_payload(entry) for entry in block.events],
    }


def _entry_payload(entry: LogEntry) -> dict[str, Any]:
    return {
        "log_index": entry.log_index,
        "event_id": entry.event.event_id,
        "event_hash": entry.event_hash,
        "leaf_hash": entry.leaf_hash,
    }


def _require_sha256_hex(value: str, field_name: str) -> None:
    if len(value) != 64:
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    try:
        bytes.fromhex(value)
    except ValueError as ex:
        raise ValueError(f"{field_name} must be hex encoded") from ex


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("created_at_utc must be timezone-aware")
