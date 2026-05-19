from datetime import UTC, datetime

import pytest

from ets.core import DuplicateEventError, EventNotFoundError, EvidenceEvent, InMemoryAppendOnlyLog
from ets.core.canonical_json import canonical_sha256
from ets.core.merkle import leaf_hash_for_event_hash


def make_event(event_id: str = "evt_001") -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id=f"evidence_{event_id}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="a" * 64,
        content_hash_alg="sha256",
        metadata={"case": "alpha"},
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
    )


def test_append_assigns_monotonic_indexes_and_hashes_events():
    log = InMemoryAppendOnlyLog()

    first = log.append(make_event("evt_001"))
    second = log.append(make_event("evt_002"))

    assert first.log_index == 0
    assert second.log_index == 1
    assert first.event_hash == canonical_sha256(first.event.hashable_payload())
    assert first.leaf_hash == leaf_hash_for_event_hash(first.event_hash)


def test_duplicate_event_ids_are_rejected():
    log = InMemoryAppendOnlyLog()
    log.append(make_event("evt_001"))

    with pytest.raises(DuplicateEventError):
        log.append(make_event("evt_001"))


def test_entries_can_be_retrieved_by_index_and_event_id():
    log = InMemoryAppendOnlyLog()
    entry = log.append(make_event("evt_001"))

    assert log.get_by_index(0) == entry
    assert log.get_by_event_id("evt_001") == entry


def test_missing_entries_raise_clear_errors():
    log = InMemoryAppendOnlyLog()

    with pytest.raises(EventNotFoundError):
        log.get_by_index(0)

    with pytest.raises(EventNotFoundError):
        log.get_by_event_id("missing")


def test_list_entries_returns_index_order_without_mutating_log():
    log = InMemoryAppendOnlyLog()
    log.append(make_event("evt_001"))
    listed = log.list_entries()

    listed.clear()

    assert len(log.list_entries()) == 1
