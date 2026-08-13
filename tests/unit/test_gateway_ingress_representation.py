from __future__ import annotations

from pathlib import Path

import pytest

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.ingress import (
    GatewayIngressError,
    GatewayIngressService,
    GatewayWebhookRequest,
)
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/orders"


def make_service(tmp_path: Path) -> tuple[GatewayIngressService, InMemoryAppendOnlyLog]:
    event_log = InMemoryAppendOnlyLog()
    registration = SourceRegistration(
        principal=PRINCIPAL,
        source_id="orders-service",
        source_system="orders",
        tenant_id="tenant_authoritative",
        workspace_id="workspace_authoritative",
        adapter_id="gateway-json",
        event_type="orders.received",
        redacted_keys=frozenset({"secret"}),
    )
    service = GatewayIngressService(
        registry=StaticSourceRegistry([registration]),
        event_log=event_log,
        sync_queue=SyncQueue(tmp_path / "sync.db"),
    )
    return service, event_log


def test_canonical_json_is_not_claimed_source_byte_lossless(tmp_path: Path) -> None:
    service, event_log = make_service(tmp_path)
    body = b'{  "order_id" : "42" }'

    receipt = service.ingest_json(
        PRINCIPAL,
        GatewayWebhookRequest(body=body, idempotency_key="canonical"),
    )
    event = event_log.get_by_event_id(receipt.event_id).event
    capture_metadata = event.metadata["capture_metadata"]

    assert event.metadata["transformation"]["lossless"] is False
    assert event.metadata["content_digest"]["representation"] == "ets.gateway.canonical-json.v1"
    assert capture_metadata["input_content_length"] == len(body)
    assert capture_metadata["committed_representation_length"] < len(body)


def test_minimized_representation_lengths_are_explicit(tmp_path: Path) -> None:
    service, event_log = make_service(tmp_path)
    body = b'{"keep":"yes","secret":"remove-me"}'

    receipt = service.ingest_json(
        PRINCIPAL,
        GatewayWebhookRequest(body=body, idempotency_key="minimized"),
    )
    event = event_log.get_by_event_id(receipt.event_id).event
    capture_metadata = event.metadata["capture_metadata"]

    assert event.metadata["content_digest"]["representation"] == (
        "ets.gateway.minimized-canonical-json.v1"
    )
    assert capture_metadata["redacted_field_count"] == 1
    assert capture_metadata["input_content_length"] == len(body)
    assert capture_metadata["committed_representation_length"] < len(body)


def test_duplicate_json_member_names_are_rejected_before_append(tmp_path: Path) -> None:
    service, event_log = make_service(tmp_path)

    with pytest.raises(GatewayIngressError):
        service.ingest_json(
            PRINCIPAL,
            GatewayWebhookRequest(
                body=b'{"order_id":"42","order_id":"43"}',
                idempotency_key="duplicate-key",
            ),
        )

    assert event_log.list_entries() == []
