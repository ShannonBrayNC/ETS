from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ets.runtime.sync_queue import SyncQueue
from ets.runtime.sync_queue_scope import (
    GATEWAY_SYNC_SCHEMA,
    ScopedSyncQueueStatusError,
    source_scoped_sync_queue_status,
)

TENANT = "tenant-authoritative"
WORKSPACE = "workspace-authoritative"
SOURCE_A = "microsoft-sharepoint-a"
SOURCE_B = "microsoft-sharepoint-b"


def _gateway_payload(
    key: str,
    *,
    tenant_id: str = TENANT,
    workspace_id: str = WORKSPACE,
    source_id: str = SOURCE_A,
) -> dict[str, object]:
    return {
        "sync_schema": GATEWAY_SYNC_SCHEMA,
        "idempotency_key": key,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "event_id": f"event-{key}",
        "event_hash": f"hash-{key}",
        "log_index": 1,
        "capture": {
            "source_id": source_id,
            "content_hash": f"content-{key}",
            "content_hash_alg": "sha256",
        },
        "raw_payload_included": False,
    }


def test_scoped_status_excludes_other_sources_and_tenants(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync.db")
    queue.enqueue(_gateway_payload("a-pending"))
    source_b = queue.enqueue(_gateway_payload("b-terminal", source_id=SOURCE_B))
    other_tenant = queue.enqueue(
        _gateway_payload("other-terminal", tenant_id="tenant-other")
    )
    queue.mark_terminal(source_b.idempotency_key, "source B failed")
    queue.mark_terminal(other_tenant.idempotency_key, "other tenant failed")

    status = source_scoped_sync_queue_status(
        queue,
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        source_id=SOURCE_A,
        now=datetime.now(UTC) + timedelta(seconds=1),
    )

    assert status.tenant_id == TENANT
    assert status.workspace_id == WORKSPACE
    assert status.source_id == SOURCE_A
    assert status.queue_depth == 1
    assert status.pending == 1
    assert status.terminal_failure == 0
    assert status.retryable_failure == 0
    assert status.latest_active_failure is None
    assert status.oldest_unsynchronized_age_seconds is not None
    assert status.oldest_unsynchronized_age_seconds >= 0


def test_scoped_status_reports_own_active_failure_and_last_success(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync.db")
    retryable = queue.enqueue(_gateway_payload("a-retry"))
    synchronized = queue.enqueue(_gateway_payload("a-synced"))
    queue.mark_retryable(retryable.idempotency_key, "temporary upstream failure")
    queue.mark_synchronized(synchronized.idempotency_key, {"status": "accepted"})

    status = source_scoped_sync_queue_status(
        queue,
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        source_id=SOURCE_A,
        upstream_status="reachable",
        now=datetime.now(UTC) + timedelta(seconds=1),
    )

    assert status.queue_depth == 1
    assert status.retryable_failure == 1
    assert status.synchronized == 1
    assert status.last_successful_sync is not None
    assert status.latest_active_failure is not None
    assert "temporary upstream failure" in status.latest_active_failure
    assert status.upstream_status == "reachable"


def test_resolved_failure_is_not_misrepresented_as_scoped_historical_failure(
    tmp_path: Path,
) -> None:
    queue = SyncQueue(tmp_path / "sync.db")
    record = queue.enqueue(_gateway_payload("a-recovered"))
    queue.mark_retryable(record.idempotency_key, "temporary failure")
    queue.mark_synchronized(record.idempotency_key, {"status": "accepted-after-retry"})

    status = source_scoped_sync_queue_status(
        queue,
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        source_id=SOURCE_A,
    )

    assert status.queue_depth == 0
    assert status.synchronized == 1
    assert status.last_successful_sync is not None
    assert status.latest_active_failure is None


def test_non_gateway_payload_in_same_scope_is_not_misattributed(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync.db")
    queue.enqueue(
        {
            "sync_schema": "another.product.sync.v1",
            "idempotency_key": "other-product",
            "tenant_id": TENANT,
            "workspace_id": WORKSPACE,
            "event_id": "other-event",
            "event_hash": "other-hash",
        }
    )

    status = source_scoped_sync_queue_status(
        queue,
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        source_id=SOURCE_A,
    )

    assert status.queue_depth == 0
    assert status.synchronized == 0
    assert status.latest_active_failure is None


def test_malformed_gateway_source_identity_fails_closed(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync.db")
    queue.enqueue(
        {
            "sync_schema": GATEWAY_SYNC_SCHEMA,
            "idempotency_key": "malformed",
            "tenant_id": TENANT,
            "workspace_id": WORKSPACE,
            "event_id": "event-malformed",
            "event_hash": "hash-malformed",
        }
    )

    with pytest.raises(ScopedSyncQueueStatusError, match="capture object"):
        source_scoped_sync_queue_status(
            queue,
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            source_id=SOURCE_A,
        )


def test_scoped_status_validates_scope_and_clock_inputs(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync.db")

    with pytest.raises(ValueError, match="source_id"):
        source_scoped_sync_queue_status(
            queue,
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            source_id="",
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        source_scoped_sync_queue_status(
            queue,
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            source_id=SOURCE_A,
            now=datetime(2026, 8, 18, 3, 0),
        )
