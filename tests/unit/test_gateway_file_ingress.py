from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ets.capture.filesystem_object import FilesystemObjectDigest, FilesystemObjectMetadata
from ets.capture.object_digest import StreamDigestResult
from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.file_capture import GatewayFileCaptureRequest
from ets.gateway.file_ingress import GatewayFileIngressService
from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayPartialCommitError,
)
from ets.gateway.source_registry import (
    SourceAuthorizationError,
    SourceRegistration,
    StaticSourceRegistry,
)
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

PRINCIPAL = "spiffe://example.test/workload/file-drop"


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated queue race")
        return super().enqueue(payload)


def source_registration(*, enabled: bool = True) -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="file-drop-a",
        source_system="filesystem",
        tenant_id="tenant_authoritative",
        workspace_id="workspace_authoritative",
        adapter_id="gateway-file",
        adapter_version="1.0",
        event_type="file.observed",
        classification="internal",
        redaction_profile="file-metadata-v1",
        minimization_profile="file-digest-metadata-v1",
        clock_quality="synchronized",
        enabled=enabled,
    )


def observation(payload: bytes) -> FilesystemObjectDigest:
    digest = StreamDigestResult(
        algorithm="sha256",
        value=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        declared_length=len(payload),
    )
    metadata = FilesystemObjectMetadata(
        device=7,
        inode=11,
        size=len(payload),
        mtime_ns=123456789,
        ctime_ns=123456700,
    )
    return FilesystemObjectDigest(
        relative_path="drop/a.bin",
        digest=digest,
        observed_before=metadata,
        observed_after=metadata,
    )


def request(payload: bytes, delivery_id: str = "delivery-1") -> GatewayFileCaptureRequest:
    return GatewayFileCaptureRequest(
        observation=observation(payload),
        delivery_id=delivery_id,
        declared_filename="source-name.bin",
        declared_content_type="application/octet-stream",
    )


def make_service(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
    enabled: bool = True,
    now: datetime | None = None,
) -> tuple[GatewayFileIngressService, InMemoryAppendOnlyLog, SyncQueue]:
    log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "sync.db")
    registry = StaticSourceRegistry([source_registration(enabled=enabled)])
    clock = None if now is None else lambda: now
    service = GatewayFileIngressService(
        registry=registry,
        event_log=log,
        sync_queue=sync_queue,
        now=clock,
    )
    return service, log, sync_queue


def test_file_ingress_commits_authoritative_scope_and_queues_without_raw_payload(tmp_path: Path) -> None:
    marker = b"RAW-FILE-SECRET-MARKER"
    received = datetime(2026, 8, 14, 1, 30, tzinfo=UTC)
    service, event_log, sync_queue = make_service(tmp_path, now=received)

    receipt = service.ingest_file(PRINCIPAL, request(marker))
    event = event_log.get_by_event_id(receipt.event_id).event

    assert event.tenant_id == "tenant_authoritative"
    assert event.workspace_id == "workspace_authoritative"
    assert event.created_at_utc == received
    assert event.metadata["capture_metadata"]["object_digest"] == hashlib.sha256(marker).hexdigest()
    assert marker.decode() not in json.dumps(event.model_dump(mode="json"))
    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    assert queued[0].payload["raw_payload_included"] is False
    assert marker.decode() not in json.dumps(queued[0].payload)


def test_file_ingress_identical_retry_reuses_event_and_queue_record(tmp_path: Path) -> None:
    service, event_log, sync_queue = make_service(tmp_path)
    capture_request = request(b"same")

    first = service.ingest_file(PRINCIPAL, capture_request)
    second = service.ingest_file(PRINCIPAL, capture_request)

    assert first.event_id == second.event_id
    assert first.log_index == second.log_index == 0
    assert first.duplicate is False
    assert second.duplicate is True
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_file_ingress_conflicting_retry_fails_without_second_append(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path)
    service.ingest_file(PRINCIPAL, request(b"first"))

    with pytest.raises(GatewayConflictError):
        service.ingest_file(PRINCIPAL, request(b"different"))

    assert len(event_log.list_entries()) == 1


def test_file_ingress_precommit_queue_exhaustion_creates_no_event(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    service, event_log, _ = make_service(tmp_path, queue=queue)

    with pytest.raises(GatewayBackpressureError):
        service.ingest_file(PRINCIPAL, request(b"payload"))

    assert event_log.list_entries() == []


def test_file_ingress_partial_commit_recovers_idempotently(tmp_path: Path) -> None:
    queue = FailOnceQueue(tmp_path / "race.db")
    service, event_log, sync_queue = make_service(tmp_path, queue=queue)
    capture_request = request(b"payload")

    with pytest.raises(GatewayPartialCommitError) as caught:
        service.ingest_file(PRINCIPAL, capture_request)

    assert caught.value.receipt.committed_local is True
    assert caught.value.receipt.sync_queued is False
    assert len(event_log.list_entries()) == 1

    retry = service.ingest_file(PRINCIPAL, capture_request)
    assert retry.duplicate is True
    assert retry.sync_queued is True
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_file_ingress_disabled_source_fails_before_append(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path, enabled=False)

    with pytest.raises(SourceAuthorizationError):
        service.ingest_file(PRINCIPAL, request(b"payload"))

    assert event_log.list_entries() == []
