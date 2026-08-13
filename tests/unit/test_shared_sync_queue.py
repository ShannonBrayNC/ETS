from __future__ import annotations

from pathlib import Path

import pytest

from ets.edge import sync_queue as edge_sync
from ets.gateway.runtime import GatewayRuntimeConfig, open_sync_queue
from ets.runtime import sync_queue as shared_sync


def _payload(key: str, *, event_hash: str = "a" * 64) -> dict[str, object]:
    return {
        "idempotency_key": key,
        "event_id": f"evt-{key}",
        "event_hash": event_hash,
        "tenant_id": "tenant-1",
        "workspace_id": "workspace-1",
        "checkpoint": {"tree_size": 1, "root_hash": "b" * 64},
    }


def test_edge_sync_queue_public_symbols_are_shared_runtime_symbols() -> None:
    assert edge_sync.SyncQueue is shared_sync.SyncQueue
    assert edge_sync.SyncState is shared_sync.SyncState
    assert edge_sync.SyncRecord is shared_sync.SyncRecord
    assert edge_sync.SyncQueueStatus is shared_sync.SyncQueueStatus
    assert edge_sync.QueueCapacityError is shared_sync.QueueCapacityError
    assert edge_sync.SyncConflictError is shared_sync.SyncConflictError


def test_gateway_opens_shared_queue(tmp_path: Path) -> None:
    config = GatewayRuntimeConfig(sync_db=tmp_path / "gateway-sync.db")
    queue = open_sync_queue(config)

    assert isinstance(queue, shared_sync.SyncQueue)
    assert queue.max_items == 10_000
    assert queue.max_bytes == 128 * 1024 * 1024


def test_duplicate_enqueue_is_idempotent_and_conflict_is_rejected(tmp_path: Path) -> None:
    queue = shared_sync.SyncQueue(tmp_path / "sync.db")
    payload = _payload("key-1")

    first = queue.enqueue(payload)
    second = queue.enqueue(payload)

    assert first == second
    assert queue.status().queue_depth == 1

    conflicting = dict(payload)
    conflicting["event_hash"] = "c" * 64
    with pytest.raises(shared_sync.SyncConflictError):
        queue.enqueue(conflicting)


def test_item_capacity_produces_explicit_backpressure(tmp_path: Path) -> None:
    queue = shared_sync.SyncQueue(tmp_path / "sync.db", max_items=1)
    queue.enqueue(_payload("key-1"))

    with pytest.raises(shared_sync.QueueCapacityError):
        queue.enqueue(_payload("key-2"))


def test_restart_recovers_in_flight_record_as_retryable(tmp_path: Path) -> None:
    db = tmp_path / "sync.db"
    queue = shared_sync.SyncQueue(db)
    queue.enqueue(_payload("key-1"))

    claimed = queue.claim_batch(1)
    assert len(claimed) == 1
    assert claimed[0].state is shared_sync.SyncState.IN_FLIGHT

    recovered = shared_sync.SyncQueue(db).get("key-1")
    assert recovered.state is shared_sync.SyncState.RETRYABLE_FAILURE
    assert recovered.last_error == "recovered in-flight record after process restart"


def test_conflicting_acknowledgement_is_rejected_after_sync(tmp_path: Path) -> None:
    queue = shared_sync.SyncQueue(tmp_path / "sync.db")
    queue.enqueue(_payload("key-1"))
    queue.claim_batch(1)
    queue.mark_synchronized("key-1", {"accepted": True, "receipt": "one"})

    with pytest.raises(shared_sync.SyncConflictError):
        queue.mark_synchronized("key-1", {"accepted": True, "receipt": "two"})
