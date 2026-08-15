from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime

import pytest

from ets.core import DuplicateEventError, EventNotFoundError, EvidenceEvent
from ets.core.azure_table_store import (
    AZURE_TABLE_SCHEMA_VERSION,
    AzureTableConflictError,
    AzureTableEventStore,
    TableAction,
    VersionedTableEntity,
)
from ets.core.storage import StorageValidationError


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
        metadata={"case": "azure-table"},
        created_at_utc=datetime(2026, 8, 15, 3, 0, tzinfo=UTC),
    )


class FakeAzureTableBackend:
    def __init__(self) -> None:
        self._version = 0
        self.entities: dict[tuple[str, str], VersionedTableEntity] = {}
        self.before_transaction: Callable[[Sequence[TableAction]], None] | None = None

    def get(self, partition_key: str, row_key: str) -> VersionedTableEntity | None:
        return self.entities.get((partition_key, row_key))

    def create(self, values: Mapping[str, object]) -> None:
        key = self._key(values)
        if key in self.entities:
            raise AzureTableConflictError("exists")
        self.entities[key] = VersionedTableEntity(dict(values), self._etag())

    def transact(self, actions: Sequence[TableAction]) -> None:
        if self.before_transaction is not None:
            callback = self.before_transaction
            self.before_transaction = None
            callback(actions)

        staged = dict(self.entities)
        for action in actions:
            key = self._key(action.values)
            current = staged.get(key)
            if action.kind == "create":
                if current is not None:
                    raise AzureTableConflictError("create conflict")
                staged[key] = VersionedTableEntity(dict(action.values), self._etag())
                continue
            if current is None or current.etag != action.etag:
                raise AzureTableConflictError("etag conflict")
            staged[key] = VersionedTableEntity(dict(action.values), self._etag())
        self.entities = staged

    def list_entries(self, partition_key: str) -> list[Mapping[str, object]]:
        rows = [
            entity.values
            for (partition, row), entity in self.entities.items()
            if partition == partition_key and row.startswith("entry-")
        ]
        return sorted(rows, key=lambda row: str(row["RowKey"]))

    def force_replace(self, values: Mapping[str, object]) -> None:
        self.entities[self._key(values)] = VersionedTableEntity(dict(values), self._etag())

    def delete_row(self, partition_key: str, row_key: str) -> None:
        self.entities.pop((partition_key, row_key), None)

    def _key(self, values: Mapping[str, object]) -> tuple[str, str]:
        return str(values["PartitionKey"]), str(values["RowKey"])

    def _etag(self) -> str:
        self._version += 1
        return f'etag-{self._version}'


def test_event_store_contract_append_lookup_duplicate_and_order() -> None:
    backend = FakeAzureTableBackend()
    store = AzureTableEventStore(backend, log_id="hosted-pilot")

    first = store.append(make_event("evt_001"))
    second = store.append(make_event("evt_002"))

    assert first.log_index == 0
    assert second.log_index == 1
    assert store.get_by_index(0) == first
    assert store.get_by_event_id("evt_002") == second
    assert [entry.event.event_id for entry in store.list_entries()] == ["evt_001", "evt_002"]
    assert store.schema_version() == AZURE_TABLE_SCHEMA_VERSION

    with pytest.raises(DuplicateEventError):
        store.append(make_event("evt_001"))
    with pytest.raises(EventNotFoundError):
        store.get_by_index(99)
    with pytest.raises(EventNotFoundError):
        store.get_by_event_id("missing")


def test_reopening_store_reconstructs_existing_log_without_resetting_metadata() -> None:
    backend = FakeAzureTableBackend()
    first = AzureTableEventStore(backend, log_id="hosted-pilot")
    first.append(make_event("evt_001"))

    reopened = AzureTableEventStore(backend, log_id="hosted-pilot")
    second = reopened.append(make_event("evt_002"))

    assert second.log_index == 1
    assert [entry.event.event_id for entry in reopened.list_entries()] == ["evt_001", "evt_002"]


def test_competing_append_conflict_reloads_metadata_and_allocates_next_index() -> None:
    backend = FakeAzureTableBackend()
    store = AzureTableEventStore(backend, log_id="hosted-pilot")

    def insert_competing_event(actions: Sequence[TableAction]) -> None:
        metadata_action = actions[0]
        partition = str(metadata_action.values["PartitionKey"])
        metadata = backend.get(partition, "meta")
        assert metadata is not None
        competitor = make_event("evt_competing")
        from ets.core.canonical_json import canonical_sha256
        from ets.core.merkle import leaf_hash_for_event_hash

        event_hash = canonical_sha256(competitor.hashable_payload())
        backend.transact(
            (
                TableAction(
                    "replace",
                    {**metadata.values, "next_index": 1},
                    metadata.etag,
                ),
                TableAction(
                    "create",
                    {
                        "PartitionKey": partition,
                        "RowKey": "entry-00000000000000000000",
                        "kind": "entry",
                        "log_index": 0,
                        "event_json": competitor.model_dump_json(),
                        "event_hash": event_hash,
                        "leaf_hash": leaf_hash_for_event_hash(event_hash),
                    },
                ),
                TableAction(
                    "create",
                    {
                        "PartitionKey": partition,
                        "RowKey": (
                            "event-"
                            "07a8b10c03f7f38b91416de7af426fb3db75c26009dde216de171545b64fbb5e"
                        ),
                        "kind": "event_index",
                        "event_id": "evt_competing",
                        "log_index": 0,
                    },
                ),
            )
        )
        raise AzureTableConflictError("simulated stale metadata")

    backend.before_transaction = insert_competing_event
    appended = store.append(make_event("evt_ours"))

    assert appended.log_index == 1
    assert [entry.log_index for entry in store.list_entries()] == [0, 1]
    assert [entry.event.event_id for entry in store.list_entries()] == [
        "evt_competing",
        "evt_ours",
    ]


def test_duplicate_race_detects_event_index_after_transaction_conflict() -> None:
    backend = FakeAzureTableBackend()
    store = AzureTableEventStore(backend, log_id="hosted-pilot")
    target = make_event("evt_race")

    def win_duplicate_race(actions: Sequence[TableAction]) -> None:
        backend.before_transaction = None
        backend.transact(actions)
        raise AzureTableConflictError("simulated duplicate race")

    backend.before_transaction = win_duplicate_race
    with pytest.raises(DuplicateEventError):
        store.append(target)
    assert store.get_by_event_id("evt_race").log_index == 0


def test_corrupted_event_json_fails_closed() -> None:
    backend = FakeAzureTableBackend()
    store = AzureTableEventStore(backend, log_id="hosted-pilot")
    store.append(make_event("evt_001"))
    partition = next(key[0] for key in backend.entities if key[1] == "meta")
    entity = backend.get(partition, "entry-00000000000000000000")
    assert entity is not None
    backend.force_replace({**entity.values, "event_json": '{"bad":true}'})

    with pytest.raises(StorageValidationError):
        store.get_by_index(0)


def test_entry_gap_or_metadata_count_mismatch_fails_closed() -> None:
    backend = FakeAzureTableBackend()
    store = AzureTableEventStore(backend, log_id="hosted-pilot")
    store.append(make_event("evt_001"))
    store.append(make_event("evt_002"))
    partition = next(key[0] for key in backend.entities if key[1] == "meta")
    backend.delete_row(partition, "entry-00000000000000000000")

    with pytest.raises(StorageValidationError, match="entry count"):
        store.list_entries()


def test_event_index_hash_collision_is_detected_before_wrong_event_is_returned() -> None:
    backend = FakeAzureTableBackend()
    store = AzureTableEventStore(backend, log_id="hosted-pilot")
    store.append(make_event("evt_001"))
    partition = next(key[0] for key in backend.entities if key[1] == "meta")
    event_index_key = next(
        key for key in backend.entities if key[0] == partition and key[1].startswith("event-")
    )
    index = backend.entities[event_index_key]
    backend.force_replace({**index.values, "event_id": "evt_collision"})

    with pytest.raises(StorageValidationError, match="hash collision"):
        store.get_by_event_id("evt_001")
