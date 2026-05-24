from __future__ import annotations

import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from ets.core import DuplicateEventError, EventNotFoundError, EvidenceEvent, InMemoryAppendOnlyLog
from ets.core.sqlite_store import SQLiteEventStore
from ets.core.storage import EventStore, StorageValidationError


def make_event(event_id: str = "evt_001") -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id=f"evidence_{event_id}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="e" * 64,
        content_hash_alg="sha256",
        metadata={"case": "alpha"},
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
    )


@pytest.fixture(params=["memory", "sqlite"])
def store_factory(
    request: pytest.FixtureRequest,
    tmp_path,
) -> Callable[[], EventStore]:
    if request.param == "memory":
        return InMemoryAppendOnlyLog
    return lambda: SQLiteEventStore(tmp_path / "ets.db")


def test_event_store_contract_append_lookup_duplicate_and_order(store_factory) -> None:
    store = store_factory()
    first = store.append(make_event("evt_001"))
    second = store.append(make_event("evt_002"))

    assert first.log_index == 0
    assert second.log_index == 1
    assert store.get_by_index(0) == first
    assert store.get_by_event_id("evt_002") == second
    assert [entry.event.event_id for entry in store.list_entries()] == ["evt_001", "evt_002"]

    with pytest.raises(DuplicateEventError):
        store.append(make_event("evt_001"))
    with pytest.raises(EventNotFoundError):
        store.get_by_index(99)
    with pytest.raises(EventNotFoundError):
        store.get_by_event_id("missing")


def test_sqlite_store_survives_restart_and_preserves_indexes(tmp_path) -> None:
    path = tmp_path / "ets.db"
    store = SQLiteEventStore(path)
    store.append(make_event("evt_001"))
    store.append(make_event("evt_002"))
    store.close()

    reopened = SQLiteEventStore(path)
    entries = reopened.list_entries()

    assert reopened.schema_version() == 1
    assert [entry.log_index for entry in entries] == [0, 1]
    assert [entry.event.event_id for entry in entries] == ["evt_001", "evt_002"]


def test_sqlite_initialization_is_idempotent(tmp_path) -> None:
    path = tmp_path / "ets.db"

    SQLiteEventStore(path).close()
    reopened = SQLiteEventStore(path)

    assert reopened.schema_version() == 1


def test_sqlite_detects_corrupted_stored_event_json(tmp_path) -> None:
    path = tmp_path / "ets.db"
    store = SQLiteEventStore(path)
    store.append(make_event("evt_001"))
    store.close()

    connection = sqlite3.connect(path)
    connection.execute("UPDATE events SET event_json = ?", ('{"bad": true}',))
    connection.commit()
    connection.close()

    reopened = SQLiteEventStore(path)
    with pytest.raises(StorageValidationError):
        reopened.get_by_event_id("evt_001")


def test_sqlite_duplicate_append_race_allows_one_success(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "ets.db")

    def append_duplicate() -> str:
        try:
            store.append(make_event("evt_001"))
        except DuplicateEventError:
            return "duplicate"
        return "success"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: append_duplicate(), range(2)))

    assert sorted(results) == ["duplicate", "success"]
    assert len(store.list_entries()) == 1
