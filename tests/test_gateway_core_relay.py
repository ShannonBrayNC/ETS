from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from ets.core import EvidenceEvent, InMemoryAppendOnlyLog, LogEntry
from ets.gateway.core_relay import (
    CoreRelayRetryableError,
    CoreRelayTerminalError,
    GatewayCoreRelayWorker,
    ScopedBearerTokenProvider,
    core_event_json,
)
from ets.runtime.sync_queue import SyncQueue, SyncState


class FakeTokenProvider:
    def acquire(self, *, tenant_id: str, workspace_id: str) -> object:
        raise AssertionError("worker must delegate credential use to the relay client")


class FakeClient:
    def __init__(self, outcome: str = "success") -> None:
        self.outcome = outcome
        self.entries: list[LogEntry] = []
        self.records: list[object] = []

    def relay(
        self,
        entry: LogEntry,
        record: object,
        token_provider: ScopedBearerTokenProvider,
    ) -> dict[str, Any]:
        self.entries.append(entry)
        self.records.append(record)
        if self.outcome == "retryable":
            raise CoreRelayRetryableError("transient upstream failure")
        if self.outcome == "terminal":
            raise CoreRelayTerminalError("upstream rejected event")
        return {
            "status": "accepted",
            "event_id": entry.event.event_id,
            "event_hash": entry.event_hash,
        }


def event() -> EvidenceEvent:
    return EvidenceEvent(
        event_id="gateway:event-1",
        tenant_id="tenant-demo",
        workspace_id="workspace-demo",
        evidence_id="evidence-1",
        event_type="microsoft.sharepoint.document.changed",
        subject_ref="ets://m365/sharepoint/site/drive/item/version/1.0",
        content_hash=hashlib.sha256(b"document-version-1").hexdigest(),
        content_hash_alg="sha256",
        metadata={"source": "sharepoint"},
        created_at_utc=datetime(2026, 8, 16, 21, 30, tzinfo=UTC),
        source_system="microsoft-sharepoint",
        correlation_id="graph-correlation-1",
    )


def enqueue(queue: SyncQueue, entry: LogEntry, *, event_hash: str | None = None) -> None:
    queue.enqueue(
        {
            "sync_schema": "ets.gateway.sync.v1",
            "idempotency_key": "ets-gateway-sync-v1:test",
            "tenant_id": entry.event.tenant_id,
            "workspace_id": entry.event.workspace_id,
            "event_id": entry.event.event_id,
            "event_hash": event_hash or entry.event_hash,
            "log_index": entry.log_index,
            "capture": {
                "source_id": "sharepoint-demo",
                "content_hash": entry.event.content_hash,
                "content_hash_alg": entry.event.content_hash_alg,
            },
            "raw_payload_included": False,
        }
    )


def test_worker_relays_exact_local_event_and_marks_synchronized(tmp_path) -> None:
    log = InMemoryAppendOnlyLog()
    entry = log.append(event())
    queue = SyncQueue(tmp_path / "sync.db")
    enqueue(queue, entry)
    client = FakeClient()

    result = GatewayCoreRelayWorker(
        event_log=log,
        sync_queue=queue,
        client=client,
        token_provider=FakeTokenProvider(),
    ).run_once()

    assert result.claimed == 1
    assert result.synchronized == 1
    assert result.retryable_failure == 0
    assert result.terminal_failure == 0
    assert client.entries == [entry]
    record = queue.get("ets-gateway-sync-v1:test")
    assert record.state == SyncState.SYNCHRONIZED
    assert record.acknowledgement_hash is not None
    assert queue.get_upstream_status() == "healthy"


def test_retryable_failure_remains_durable_for_next_attempt(tmp_path) -> None:
    log = InMemoryAppendOnlyLog()
    entry = log.append(event())
    queue = SyncQueue(tmp_path / "sync.db")
    enqueue(queue, entry)

    result = GatewayCoreRelayWorker(
        event_log=log,
        sync_queue=queue,
        client=FakeClient("retryable"),
        token_provider=FakeTokenProvider(),
    ).run_once()

    assert result.retryable_failure == 1
    record = queue.get("ets-gateway-sync-v1:test")
    assert record.state == SyncState.RETRYABLE_FAILURE
    assert record.attempts == 1
    assert queue.get_upstream_status() == "degraded"


def test_terminal_failure_is_not_retried_automatically(tmp_path) -> None:
    log = InMemoryAppendOnlyLog()
    entry = log.append(event())
    queue = SyncQueue(tmp_path / "sync.db")
    enqueue(queue, entry)

    result = GatewayCoreRelayWorker(
        event_log=log,
        sync_queue=queue,
        client=FakeClient("terminal"),
        token_provider=FakeTokenProvider(),
    ).run_once()

    assert result.terminal_failure == 1
    record = queue.get("ets-gateway-sync-v1:test")
    assert record.state == SyncState.TERMINAL_FAILURE
    assert queue.get_upstream_status() == "integrity_failure"
    assert GatewayCoreRelayWorker(
        event_log=log,
        sync_queue=queue,
        client=FakeClient(),
        token_provider=FakeTokenProvider(),
    ).run_once().claimed == 0


def test_missing_local_event_fails_terminal_without_calling_upstream(tmp_path) -> None:
    log = InMemoryAppendOnlyLog()
    queue = SyncQueue(tmp_path / "sync.db")
    queue.enqueue(
        {
            "idempotency_key": "ets-gateway-sync-v1:test",
            "event_id": "missing-event",
            "event_hash": "a" * 64,
            "tenant_id": "tenant-demo",
            "workspace_id": "workspace-demo",
        }
    )
    client = FakeClient()

    result = GatewayCoreRelayWorker(
        event_log=log,
        sync_queue=queue,
        client=client,
        token_provider=FakeTokenProvider(),
    ).run_once()

    assert result.terminal_failure == 1
    assert client.entries == []
    assert queue.get("ets-gateway-sync-v1:test").state == SyncState.TERMINAL_FAILURE


def test_queue_event_hash_mismatch_fails_terminal_before_upstream(tmp_path) -> None:
    log = InMemoryAppendOnlyLog()
    entry = log.append(event())
    queue = SyncQueue(tmp_path / "sync.db")
    enqueue(queue, entry, event_hash="b" * 64)
    client = FakeClient()

    result = GatewayCoreRelayWorker(
        event_log=log,
        sync_queue=queue,
        client=client,
        token_provider=FakeTokenProvider(),
    ).run_once()

    assert result.terminal_failure == 1
    assert client.entries == []


def test_core_event_json_contains_the_exact_committed_event(tmp_path) -> None:
    del tmp_path
    log = InMemoryAppendOnlyLog()
    entry = log.append(event())

    decoded = json.loads(core_event_json(entry))

    assert decoded == entry.event.model_dump(mode="json")
    assert "idempotency_key" not in decoded
    assert "raw_payload_included" not in decoded
