from __future__ import annotations

from pathlib import Path

import pytest

from ets.edge.sync_queue import QueueCapacityError, SyncConflictError, SyncQueue, SyncState


def _payload(event_id: str = "evt-1", event_hash: str = "a" * 64) -> dict[str, object]:
    return {
        "sync_schema": "ets.edge.sync.v1",
        "idempotency_key": f"tenant:workspace:{event_id}:{event_hash}",
        "tenant_id": "tenant",
        "workspace_id": "workspace",
        "event_id": event_id,
        "event_hash": event_hash,
        "raw_payload_included": False,
        "tree_head": {"root_hash": "b" * 64, "tree_size": 1, "signature": "sig"},
    }


def test_queue_persists_pending_state_across_restart(tmp_path: Path) -> None:
    path = tmp_path / "sync.db"
    queue = SyncQueue(path)
    record = queue.enqueue(_payload())
    assert record.state is SyncState.PENDING

    restarted = SyncQueue(path)
    loaded = restarted.get(record.idempotency_key)
    assert loaded.state is SyncState.PENDING
    assert restarted.status().queue_depth == 1


def test_in_flight_record_becomes_retryable_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "sync.db"
    queue = SyncQueue(path)
    queue.enqueue(_payload())
    [claimed] = queue.claim_batch()
    assert claimed.state is SyncState.IN_FLIGHT

    restarted = SyncQueue(path)
    recovered = restarted.get(claimed.idempotency_key)
    assert recovered.state is SyncState.RETRYABLE_FAILURE
    assert recovered.last_error is not None


def test_replay_is_logically_idempotent(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync.db")
    first = queue.enqueue(_payload())
    second = queue.enqueue(_payload())
    assert first.idempotency_key == second.idempotency_key
    assert queue.status().queue_depth == 1

    [claimed] = queue.claim_batch()
    ack = {
        "idempotency_key": claimed.idempotency_key,
        "event_id": claimed.event_id,
        "event_hash": claimed.event_hash,
        "status": "accepted",
    }
    queue.mark_synchronized(claimed.idempotency_key, ack)
    queue.mark_synchronized(claimed.idempotency_key, ack)
    assert queue.status().queue_depth == 0
    assert queue.status().synchronized == 1


def test_conflicting_idempotency_content_fails_closed(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync.db")
    original = _payload()
    queue.enqueue(original)
    changed = dict(original)
    changed["event_hash"] = "c" * 64

    with pytest.raises(SyncConflictError):
        queue.enqueue(changed)


def test_queue_capacity_applies_backpressure(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync.db", max_items=1, max_bytes=1024 * 1024)
    queue.enqueue(_payload())
    with pytest.raises(QueueCapacityError):
        queue.ensure_capacity()


def test_terminal_failure_remains_operator_visible(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync.db")
    record = queue.enqueue(_payload())
    queue.mark_terminal(record.idempotency_key, "conflicting upstream acknowledgement")
    status = queue.status(upstream_status="conflict")
    assert status.queue_depth == 1
    assert status.terminal_failure == 1
    assert status.last_failure is not None
