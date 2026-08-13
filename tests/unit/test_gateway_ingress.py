from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ets.core.api import (
    DuplicateEventError,
    EvidenceEvent,
    InMemoryAppendOnlyLog,
    LogEntry,
    canonicalize,
)
from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayIngressConfig,
    GatewayIngressError,
    GatewayIngressService,
    GatewayPartialCommitError,
    GatewayWebhookRequest,
)
from ets.gateway.source_registry import (
    SourceAuthorizationError,
    SourceRegistration,
    StaticSourceRegistry,
)
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

PRINCIPAL = "spiffe://example.test/workload/orders"


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated queue race")
        return super().enqueue(payload)


class DuplicateOnAppendLog(InMemoryAppendOnlyLog):
    """Simulate another writer winning between lookup and append."""

    def __init__(self, *, conflicting: bool = False) -> None:
        super().__init__()
        self._conflicting = conflicting
        self._raced = False

    def append(self, event: EvidenceEvent) -> LogEntry:
        if not self._raced:
            self._raced = True
            winner = event
            if self._conflicting:
                winner = event.model_copy(update={"content_hash": "0" * 64})
            super().append(winner)
            raise DuplicateEventError("simulated concurrent append winner")
        return super().append(event)


def source_registration(*, enabled: bool = True) -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="orders-service",
        source_system="orders",
        tenant_id="tenant_authoritative",
        workspace_id="workspace_authoritative",
        adapter_id="gateway-json",
        adapter_version="1.0",
        event_type="orders.received",
        classification="internal",
        redaction_profile="drop-secrets-v1",
        minimization_profile="gateway-json-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="synchronized",
        enabled=enabled,
    )


def make_service(
    tmp_path: Path,
    *,
    max_body_bytes: int = 1024 * 1024,
    queue: SyncQueue | None = None,
    event_log: InMemoryAppendOnlyLog | None = None,
    enabled: bool = True,
    now: datetime | None = None,
) -> tuple[GatewayIngressService, InMemoryAppendOnlyLog, SyncQueue]:
    log = event_log if event_log is not None else InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "sync.db")
    registry = StaticSourceRegistry([source_registration(enabled=enabled)])
    clock = None if now is None else lambda: now
    service = GatewayIngressService(
        registry=registry,
        event_log=log,
        sync_queue=sync_queue,
        config=GatewayIngressConfig(max_body_bytes=max_body_bytes),
        now=clock,
    )
    return service, log, sync_queue


def request(body: bytes, key: str = "request-1") -> GatewayWebhookRequest:
    return GatewayWebhookRequest(
        body=body,
        idempotency_key=key,
        declared_identity="orders-service-declared",
    )


def test_privacy_minimization_precedes_declared_representation_digest(tmp_path: Path) -> None:
    service, event_log, sync_queue = make_service(tmp_path)
    body = b'{"keep":"yes","secret":"secret-value","nested":{"secret":"nested-value"}}'

    receipt = service.ingest_json(PRINCIPAL, request(body))
    entry = event_log.get_by_event_id(receipt.event_id)
    expected = hashlib.sha256(canonicalize({"keep": "yes", "nested": {}})).hexdigest()

    assert entry.event.content_hash == expected
    assert entry.event.tenant_id == "tenant_authoritative"
    assert entry.event.workspace_id == "workspace_authoritative"
    assert entry.event.metadata["capture_metadata"]["redacted_field_count"] == 2
    assert entry.event.metadata["privacy"]["contains_raw_evidence"] is False
    assert entry.event.metadata["source"]["transport_identity"] == PRINCIPAL
    assert entry.event.metadata["source"]["declared_identity"] != PRINCIPAL
    assert "secret-value" not in json.dumps(entry.event.model_dump(mode="json"))

    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    assert queued[0].payload["raw_payload_included"] is False
    assert "secret-value" not in json.dumps(queued[0].payload)


def test_identical_retry_reuses_one_event_and_one_queue_record(tmp_path: Path) -> None:
    service, event_log, sync_queue = make_service(tmp_path)
    body = b'{"order_id":"42"}'

    first = service.ingest_json(PRINCIPAL, request(body))
    second = service.ingest_json(PRINCIPAL, request(body))

    assert first.event_id == second.event_id
    assert first.log_index == second.log_index == 0
    assert first.duplicate is False
    assert second.duplicate is True
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_conflicting_retry_fails_without_second_append(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path)
    service.ingest_json(PRINCIPAL, request(b'{"order_id":"42"}'))

    with pytest.raises(GatewayConflictError):
        service.ingest_json(PRINCIPAL, request(b'{"order_id":"43"}'))

    assert len(event_log.list_entries()) == 1


def test_concurrent_identical_append_reconciles_existing_event(tmp_path: Path) -> None:
    race_log = DuplicateOnAppendLog()
    service, event_log, sync_queue = make_service(tmp_path, event_log=race_log)

    receipt = service.ingest_json(PRINCIPAL, request(b'{"order_id":"42"}'))

    assert receipt.duplicate is True
    assert receipt.log_index == 0
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_concurrent_conflicting_append_returns_conflict(tmp_path: Path) -> None:
    race_log = DuplicateOnAppendLog(conflicting=True)
    service, event_log, sync_queue = make_service(tmp_path, event_log=race_log)

    with pytest.raises(GatewayConflictError):
        service.ingest_json(PRINCIPAL, request(b'{"order_id":"42"}'))

    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 0


def test_body_limit_minus_one_exact_and_plus_one(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path, max_body_bytes=12)
    minus_one = b'    {"a":1}'
    exact = b'     {"a":1}'
    plus_one = b'      {"a":1}'

    service.ingest_json(PRINCIPAL, request(minus_one, "minus"))
    service.ingest_json(PRINCIPAL, request(exact, "exact"))
    with pytest.raises(GatewayIngressError):
        service.ingest_json(PRINCIPAL, request(plus_one, "plus"))

    assert len(event_log.list_entries()) == 2


def test_precommit_queue_exhaustion_returns_backpressure(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    service, event_log, _ = make_service(tmp_path, queue=queue)

    with pytest.raises(GatewayBackpressureError):
        service.ingest_json(PRINCIPAL, request(b'{"order_id":"42"}'))

    assert event_log.list_entries() == []


def test_retry_recovers_append_before_queue_enqueue_failure(tmp_path: Path) -> None:
    queue = FailOnceQueue(tmp_path / "race.db")
    service, event_log, sync_queue = make_service(tmp_path, queue=queue)
    body = b'{"order_id":"42"}'

    with pytest.raises(GatewayPartialCommitError) as caught:
        service.ingest_json(PRINCIPAL, request(body))

    assert caught.value.receipt.committed_local is True
    assert caught.value.receipt.sync_queued is False
    assert len(event_log.list_entries()) == 1

    retry = service.ingest_json(PRINCIPAL, request(body))
    assert retry.duplicate is True
    assert retry.sync_queued is True
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_disabled_source_fails_closed(tmp_path: Path) -> None:
    service, event_log, _ = make_service(tmp_path, enabled=False)

    with pytest.raises(SourceAuthorizationError):
        service.ingest_json(PRINCIPAL, request(b'{"order_id":"42"}'))

    assert event_log.list_entries() == []


def test_source_and_receipt_time_remain_distinct(tmp_path: Path) -> None:
    received = datetime(2026, 8, 13, 17, 0, 0, tzinfo=UTC)
    observed = datetime(2026, 8, 13, 16, 59, 30, tzinfo=UTC)
    service, event_log, _ = make_service(tmp_path, now=received)
    capture_request = GatewayWebhookRequest(
        body=b'{"order_id":"42"}',
        idempotency_key="timed",
        observed_at_utc=observed,
    )

    receipt = service.ingest_json(PRINCIPAL, capture_request)
    event = event_log.get_by_event_id(receipt.event_id).event

    assert event.created_at_utc == received
    assert event.metadata["observed_at_utc"] == "2026-08-13T16:59:30Z"


@pytest.mark.parametrize(
    "capture_request",
    [
        GatewayWebhookRequest(body=b"[]", idempotency_key="root"),
        GatewayWebhookRequest(body=b"{bad", idempotency_key="json"),
        GatewayWebhookRequest(
            body=b"{}",
            idempotency_key="type",
            media_type="application/octet-stream",
        ),
        GatewayWebhookRequest(body=b"{}", idempotency_key=""),
    ],
)
def test_invalid_requests_fail_before_append(
    tmp_path: Path,
    capture_request: GatewayWebhookRequest,
) -> None:
    service, event_log, _ = make_service(tmp_path)

    with pytest.raises(GatewayIngressError):
        service.ingest_json(PRINCIPAL, capture_request)

    assert event_log.list_entries() == []
