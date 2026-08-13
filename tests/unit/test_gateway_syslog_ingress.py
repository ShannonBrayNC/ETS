from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ets.core.api import InMemoryAppendOnlyLog, canonicalize
from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayIngressConfig,
    GatewayIngressService,
    GatewayPartialCommitError,
)
from ets.gateway.source_registry import (
    SourceAuthorizationError,
    SourceRegistration,
    StaticSourceRegistry,
)
from ets.gateway.syslog_capture import (
    SYSLOG_COMMITTED_REPRESENTATION,
    GatewaySyslogCaptureError,
    GatewaySyslogCaptureRequest,
)
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

PRINCIPAL = "spiffe://example.test/workload/syslog-sender"


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
        source_id="syslog-source-1",
        source_system="enterprise-syslog",
        tenant_id="tenant_authoritative",
        workspace_id="workspace_authoritative",
        adapter_id="gateway-syslog",
        adapter_version="1.0",
        event_type="evidence.captured.syslog",
        classification="internal",
        redaction_profile="syslog-header-only-v1",
        minimization_profile="syslog-header-only-v1",
        clock_quality="synchronized",
        enabled=enabled,
    )


def make_service(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
    enabled: bool = True,
    now: datetime | None = None,
    max_syslog_message_bytes: int = 8192,
) -> tuple[GatewayIngressService, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "syslog-sync.db")
    registry = StaticSourceRegistry([source_registration(enabled=enabled)])
    clock = None if now is None else lambda: now
    service = GatewayIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=sync_queue,
        config=GatewayIngressConfig(max_syslog_message_bytes=max_syslog_message_bytes),
        now=clock,
    )
    return service, event_log, sync_queue


def request(
    message: bytes,
    delivery_id: str = "delivery-1",
    *,
    received_at_utc: datetime | None = None,
) -> GatewaySyslogCaptureRequest:
    return GatewaySyslogCaptureRequest(
        message=message,
        delivery_id=delivery_id,
        received_at_utc=received_at_utc,
    )


def test_syslog_scope_and_transport_identity_are_server_authorized(tmp_path: Path) -> None:
    service, event_log, sync_queue = make_service(tmp_path)
    message = (
        b"<34>1 2026-08-13T21:00:00Z attacker-host app 123 ID47 - "
        b"super-secret-body"
    )

    receipt = service.ingest_syslog(PRINCIPAL, request(message))
    event = event_log.get_by_event_id(receipt.event_id).event

    assert event.tenant_id == "tenant_authoritative"
    assert event.workspace_id == "workspace_authoritative"
    assert event.source_system == "enterprise-syslog"
    assert event.metadata["source"]["transport_identity"] == PRINCIPAL
    assert event.metadata["source"]["declared_identity"] == "attacker-host"
    assert event.metadata["privacy"]["contains_raw_evidence"] is False
    assert event.metadata["capture_metadata"]["raw_payload_retained"] is False
    assert "super-secret-body" not in json.dumps(event.model_dump(mode="json"))

    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    assert queued[0].payload["raw_payload_included"] is False
    assert "super-secret-body" not in json.dumps(queued[0].payload)


def test_syslog_digest_is_over_declared_header_only_representation(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path)
    message = b"<34>1 2026-08-13T21:00:00Z host app 123 ID47 - payload"

    receipt = service.ingest_syslog(PRINCIPAL, request(message))
    event = event_log.get_by_event_id(receipt.event_id).event
    expected = canonicalize(
        {
            "schema": SYSLOG_COMMITTED_REPRESENTATION,
            "priority": 34,
            "facility": 4,
            "severity": 2,
            "version": 1,
            "timestamp": "2026-08-13T21:00:00Z",
            "hostname": "host",
            "app_name": "app",
            "procid": "123",
            "msgid": "ID47",
        }
    )

    assert event.content_hash == hashlib.sha256(expected).hexdigest()
    assert event.content_hash != hashlib.sha256(message).hexdigest()
    assert event.metadata["content_digest"]["representation"] == SYSLOG_COMMITTED_REPRESENTATION
    assert event.metadata["transformation"]["lossless"] is False


def test_syslog_identical_retry_reuses_event_and_sync_record(tmp_path: Path) -> None:
    service, event_log, sync_queue = make_service(tmp_path)
    message = b"<13>1 - host app p m - payload"

    first = service.ingest_syslog(PRINCIPAL, request(message))
    second = service.ingest_syslog(PRINCIPAL, request(message))

    assert first.event_id == second.event_id
    assert first.log_index == second.log_index == 0
    assert first.duplicate is False
    assert second.duplicate is True
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_syslog_conflicting_retry_fails_without_second_append(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path)
    first = b"<13>1 - host-a app p m - payload"
    conflicting = b"<13>1 - host-b app p m - payload"

    service.ingest_syslog(PRINCIPAL, request(first))
    with pytest.raises(GatewayConflictError):
        service.ingest_syslog(PRINCIPAL, request(conflicting))

    assert len(event_log.list_entries()) == 1


def test_syslog_precommit_queue_exhaustion_creates_no_event(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    service, event_log, _ = make_service(tmp_path, queue=queue)

    with pytest.raises(GatewayBackpressureError):
        service.ingest_syslog(PRINCIPAL, request(b"<13>1 - host app p m - payload"))

    assert event_log.list_entries() == []


def test_syslog_retry_recovers_partial_commit(tmp_path: Path) -> None:
    queue = FailOnceQueue(tmp_path / "race.db")
    service, event_log, sync_queue = make_service(tmp_path, queue=queue)
    message = b"<13>1 - host app p m - payload"

    with pytest.raises(GatewayPartialCommitError) as caught:
        service.ingest_syslog(PRINCIPAL, request(message))

    assert caught.value.receipt.committed_local is True
    assert caught.value.receipt.sync_queued is False
    assert len(event_log.list_entries()) == 1

    retry = service.ingest_syslog(PRINCIPAL, request(message))
    assert retry.duplicate is True
    assert retry.sync_queued is True
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_syslog_disabled_source_fails_closed(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path, enabled=False)

    with pytest.raises(SourceAuthorizationError):
        service.ingest_syslog(PRINCIPAL, request(b"<13>1 - host app p m - payload"))

    assert event_log.list_entries() == []


def test_syslog_source_and_receipt_time_remain_distinct(tmp_path: Path) -> None:
    received = datetime(2026, 8, 13, 21, 0, 30, tzinfo=UTC)
    service, event_log, _ = make_service(tmp_path, now=received)
    message = b"<13>1 2026-08-13T21:00:00Z host app p m - payload"

    receipt = service.ingest_syslog(PRINCIPAL, request(message))
    event = event_log.get_by_event_id(receipt.event_id).event

    assert event.created_at_utc == received
    assert event.metadata["observed_at_utc"] == "2026-08-13T21:00:00Z"
    assert event.metadata["capture_metadata"]["source_timestamp_status"] == "parsed"


def test_invalid_source_timestamp_is_preserved_as_claim_not_observation(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path)
    message = b"<13>1 2026-08-13t21:00:00Z host app p m - payload"

    receipt = service.ingest_syslog(PRINCIPAL, request(message))
    event = event_log.get_by_event_id(receipt.event_id).event

    assert event.metadata["observed_at_utc"] is None
    assert event.metadata["capture_metadata"]["source_timestamp_claim"] == "2026-08-13t21:00:00Z"
    assert event.metadata["capture_metadata"]["source_timestamp_status"] == "invalid"


def test_syslog_message_limit_exact_and_plus_one(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path, max_syslog_message_bytes=8192)
    prefix = b"<13>1 - host app p m - "
    exact = prefix + (b"x" * (8192 - len(prefix)))
    plus_one = exact + b"x"

    service.ingest_syslog(PRINCIPAL, request(exact, "exact"))
    with pytest.raises(GatewaySyslogCaptureError, match="configured limit"):
        service.ingest_syslog(PRINCIPAL, request(plus_one, "plus"))

    assert len(event_log.list_entries()) == 1


def test_syslog_invalid_delivery_id_fails_before_append(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path)

    with pytest.raises(GatewaySyslogCaptureError, match="delivery_id"):
        service.ingest_syslog(
            PRINCIPAL,
            GatewaySyslogCaptureRequest(
                message=b"<13>1 - host app p m - payload",
                delivery_id="",
            ),
        )

    assert event_log.list_entries() == []
