from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ets.capture.otlp import OtlpObservationV1
from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.ingress import GatewayIngressService, GatewayPartialCommitError
from ets.gateway.otlp_capture import GatewayOtlpCaptureRequest
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

PRINCIPAL = "spiffe://example.test/workload/otel-partial-commit"


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated OTLP sync enqueue race")
        return super().enqueue(payload)


def _request() -> GatewayOtlpCaptureRequest:
    observation = OtlpObservationV1(
        schema_version="ets.otlp.observation.v1",
        signal_class="logs",
        record_ordinal=0,
        source_timestamp_utc=datetime(2026, 8, 14, 1, 0, tzinfo=UTC),
        decoder_profile="otlp-semantic.v1",
        transformation_profile="otlp-metadata.v1",
        resource_metadata={"service.name": "orders"},
        scope_metadata={"name": "orders.instrumentation"},
        record_metadata={"message": "accepted"},
    )
    return GatewayOtlpCaptureRequest(
        observation=observation,
        delivery_id="delivery-partial-1",
    )


def test_otlp_retry_recovers_append_before_sync_enqueue_failure(tmp_path: Path) -> None:
    event_log = InMemoryAppendOnlyLog()
    queue = FailOnceQueue(tmp_path / "otlp-partial-sync.db")
    registry = StaticSourceRegistry(
        [
            SourceRegistration(
                principal=PRINCIPAL,
                source_id="otel-collector-a",
                source_system="opentelemetry",
                tenant_id="tenant_authoritative",
                workspace_id="workspace_authoritative",
                adapter_id="gateway-otlp",
                event_type="telemetry.observed",
            )
        ]
    )
    service = GatewayIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=queue,
        now=lambda: datetime(2026, 8, 14, 1, 1, tzinfo=UTC),
    )

    with pytest.raises(GatewayPartialCommitError) as caught:
        service.ingest_otlp(PRINCIPAL, _request())

    assert caught.value.receipt.committed_local is True
    assert caught.value.receipt.sync_queued is False
    assert len(event_log.list_entries()) == 1
    assert queue.status().queue_depth == 0

    retry = service.ingest_otlp(PRINCIPAL, _request())
    assert retry.duplicate is True
    assert retry.committed_local is True
    assert retry.sync_queued is True
    assert len(event_log.list_entries()) == 1
    assert queue.status().queue_depth == 1
