from datetime import UTC, datetime

import pytest

from ets.core import (
    GENESIS_BLOCK_HASH,
    InMemoryAppendOnlyLog,
    build_block,
    export_block,
    recompute_block_hash,
    verify_chain,
)
from ets.core.models import EvidenceEvent


def make_event(event_id: str = "evt_001", content_hash: str = "a" * 64) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id=f"evidence_{event_id}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash=content_hash,
        content_hash_alg="sha256",
        metadata={"case": "hash-chain"},
        created_at_utc=datetime(2026, 5, 26, 12, 0, tzinfo=UTC),
    )


def make_entries() -> list:
    log = InMemoryAppendOnlyLog()
    return [log.append(make_event("evt_001")), log.append(make_event("evt_002", "b" * 64))]


def test_build_block_hash_is_reproducible() -> None:
    entries = make_entries()
    created_at = datetime(2026, 5, 26, 12, 30, tzinfo=UTC)

    first = build_block(0, GENESIS_BLOCK_HASH, entries, created_at)
    second = build_block(0, GENESIS_BLOCK_HASH, entries, created_at)

    assert first == second
    assert len(first.block_hash) == 64
    assert recompute_block_hash(first) == first.block_hash


def test_build_block_rejects_invalid_inputs() -> None:
    entries = make_entries()

    with pytest.raises(ValueError):
        build_block(-1, GENESIS_BLOCK_HASH, entries, datetime(2026, 5, 26, tzinfo=UTC))
    with pytest.raises(ValueError):
        build_block(0, "bad", entries, datetime(2026, 5, 26, tzinfo=UTC))
    with pytest.raises(ValueError):
        build_block(0, GENESIS_BLOCK_HASH, entries, datetime(2026, 5, 26))


def test_verify_chain_accepts_continuous_blocks() -> None:
    entries = make_entries()
    created_at = datetime(2026, 5, 26, 12, 30, tzinfo=UTC)
    first = build_block(0, GENESIS_BLOCK_HASH, [entries[0]], created_at)
    second = build_block(1, first.block_hash, [entries[1]], created_at)

    result = verify_chain([first, second])

    assert result.valid is True
    assert result.reason == "ok"
    assert result.failed_block_number is None


def test_verify_chain_detects_broken_previous_hash() -> None:
    entries = make_entries()
    created_at = datetime(2026, 5, 26, 12, 30, tzinfo=UTC)
    first = build_block(0, GENESIS_BLOCK_HASH, [entries[0]], created_at)
    second = build_block(1, "1" * 64, [entries[1]], created_at)

    result = verify_chain([first, second])

    assert result.valid is False
    assert result.reason == "previous block hash does not match"
    assert result.failed_block_number == 1


def test_verify_chain_detects_block_hash_tampering() -> None:
    entries = make_entries()
    created_at = datetime(2026, 5, 26, 12, 30, tzinfo=UTC)
    block = build_block(0, GENESIS_BLOCK_HASH, [entries[0]], created_at)
    tampered = build_block(0, GENESIS_BLOCK_HASH, [entries[1]], created_at)
    tampered_with_old_hash = tampered.__class__(
        block_number=tampered.block_number,
        previous_block_hash=tampered.previous_block_hash,
        block_hash=block.block_hash,
        events=tampered.events,
        created_at_utc=tampered.created_at_utc,
    )

    result = verify_chain([tampered_with_old_hash])

    assert result.valid is False
    assert result.reason == "block hash does not match block contents"
    assert result.failed_block_number == 0


def test_verify_chain_detects_non_monotonic_block_numbers() -> None:
    entries = make_entries()
    created_at = datetime(2026, 5, 26, 12, 30, tzinfo=UTC)
    block = build_block(1, GENESIS_BLOCK_HASH, [entries[0]], created_at)

    result = verify_chain([block])

    assert result.valid is False
    assert result.reason == "block number is not monotonic"
    assert result.failed_block_number == 1


def test_export_block_returns_json_native_data() -> None:
    entries = make_entries()
    created_at = datetime(2026, 5, 26, 12, 30, tzinfo=UTC)
    block = build_block(0, GENESIS_BLOCK_HASH, entries, created_at)

    exported = export_block(block)

    assert exported["block_number"] == 0
    assert exported["previous_block_hash"] == GENESIS_BLOCK_HASH
    assert exported["block_hash"] == block.block_hash
    assert exported["events"][0]["event_id"] == "evt_001"
