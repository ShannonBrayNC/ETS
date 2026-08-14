from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ets.capture.otlp import OtlpObservationV1
from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayIngressConfig,
    GatewayIngressService,
)
from ets.gateway.otlp_capture import GatewayOtlpCaptureError, GatewayOtlpCaptureRequest
from ets.gateway.source_registry import (
    SourceAuthorizationError,
    SourceRegistration,
    StaticSourceRegistry,
)
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/otel-collector"


def _registration(*, enabled: bool = True) -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="otel-collector-a",
        source_system="opentelemetry",
        tenant_id="tenant_authoritative",
        workspace_id="workspace_authoritative",
        adapter_id="gateway-otlp",
        adapter_version="1.0",
        event_type="telemetry.observed",
        classification="internal",
        redaction_profile="otlp-redaction-v1",
        minimization_profile="otlp-metadata-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="synchronized",
        enabled=enabled,
    )


def _observation(**overrides: object) -> OtlpObservationV1:
    values: dict[str, object] = {
        "schema_version": "ets.otlp.observation.v1",
        "signal_class": "logs",
        "record_ordinal": 1,
        "source_timestamp_utc": datetime(2026, 8, 14, 0, 45, tzinfo=UTC),
        "decoder_profile": "otlp-semantic.v1",
        "transformation_profile": "otlp-metadata.v1",
        "resource_metadata": {"service.name": "orders"},
        "scope_metadata": {"name": "orders.instrumentation"},
        "record_metadata": {"severity": "INFO", "message": "accepted"},
    }
    values.update(overrides)
    return OtlpObservationV1.model_validate(values)


def _request(**overrides: object) -> GatewayOtlpCaptureRequest:
    values: dict[str, object] = {
        "observation": _observation(),
        "delivery_id": "delivery-42",
        "correlation_id": "corr-42",
    }
    values.update(overrides)
    return GatewayOtlpCaptureRequest(**values)  # type: ignore[arg-type]


def _service(
    tmp_path: Path,
    *,
    enabled: bool = True,
    queue: SyncQueue | None = None,
    now: datetime | None = None,
    max_otlp_committed_bytes: int = 12 * 1024,
) -> tuple[GatewayIngressService, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "otlp-sync.db")
    registry = StaticSourceRegistry([_registration(enabled=enabled)])
    clock = None if now is None else lambda: now
    service = GatewayIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=sync_queue,
        config=GatewayIngressConfig(max_otlp_committed_bytes=max_otlp_committed_bytes),
        now=clock,
    )
    return service, event_log, sync_queue


def test_otlp_ingest_uses_shared_commit_and_sync_path(tmp_path: Path) -> None:
    received = datetime(2026, 8, 14, 0, 46, tzinfo=UTC)
    service, event_log, sync_queue = _service(tmp_path, now=received)

    receipt = service.ingest_otlp(PRINCIPAL, _request())
    event = event_log.get_by_event_id(receipt.event_id).event

    assert receipt.committed_local is True
    assert receipt.sync_queued is True
    assert receipt.duplicate is False
    assert event.tenant_id == "tenant_authoritative"
    assert event.workspace_id == "workspace_authoritative"
    assert event.source_system == "opentelemetry"
    assert event.event_type == "telemetry.observed"
    assert event.created_at_utc == received
    assert event.metadata["observed_at_utc"] == "2026-08-14T00:45:00Z"
    assert event.metadata["capture_metadata"]["otlp_signal_class"] == "logs"
    assert event.metadata["capture_metadata"]["otlp_record_ordinal"] == 1
    assert event.metadata["source"]["transport_identity"] == PRINCIPAL

    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    assert queued[0].payload["raw_payload_included"] is False
    assert queued[0].payload["event_id"] == receipt.event_id


def test_otlp_identical_retry_reuses_event_and_sync_record(tmp_path: Path) -> None:
    service, event_log, sync_queue = _service(tmp_path)

    first = service.ingest_otlp(PRINCIPAL, _request())
    second = service.ingest_otlp(PRINCIPAL, _request())

    assert first.event_id == second.event_id
    assert first.log_index == second.log_index == 0
    assert first.duplicate is False
    assert second.duplicate is True
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_otlp_conflicting_retry_fails_without_second_append(tmp_path: Path) -> None:
    service, event_log, _ = _service(tmp_path)
    service.ingest_otlp(PRINCIPAL, _request())
    changed = _observation(record_metadata={"severity": "ERROR", "message": "changed"})

    with pytest.raises(GatewayConflictError):
        service.ingest_otlp(PRINCIPAL, _request(observation=changed))

    assert len(event_log.list_entries()) == 1


def test_otlp_privacy_minimization_precedes_commit_and_sync(tmp_path: Path) -> None:
    marker = "RAW-OTLP-SECRET"
    observation = _observation(
        resource_metadata={"service.name": "orders", "secret": marker},
        record_metadata={"message": "safe", "nested": {"secret": marker}},
    )
    service, event_log, sync_queue = _service(tmp_path)

    receipt = service.ingest_otlp(PRINCIPAL, _request(observation=observation))
    event = event_log.get_by_event_id(receipt.event_id).event
    serialized_event = json.dumps(event.model_dump(mode="json"), sort_keys=True)
    assert marker not in serialized_event
    assert event.metadata["capture_metadata"]["redacted_field_count"] == 2
    assert event.metadata["privacy"]["contains_raw_evidence"] is False

    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    assert marker not in json.dumps(queued[0].payload, sort_keys=True)


def test_otlp_precommit_queue_exhaustion_returns_backpressure(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "tiny-otlp.db", max_bytes=4095)
    service, event_log, _ = _service(tmp_path, queue=queue)

    with pytest.raises(GatewayBackpressureError):
        service.ingest_otlp(PRINCIPAL, _request())

    assert event_log.list_entries() == []


def test_otlp_disabled_source_fails_closed(tmp_path: Path) -> None:
    service, event_log, _ = _service(tmp_path, enabled=False)

    with pytest.raises(SourceAuthorizationError):
        service.ingest_otlp(PRINCIPAL, _request())

    assert event_log.list_entries() == []


def test_otlp_committed_representation_bound_fails_before_append(tmp_path: Path) -> None:
    service, event_log, _ = _service(tmp_path, max_otlp_committed_bytes=256)
    observation = _observation(record_metadata={"message": "x" * 2048})

    with pytest.raises(GatewayOtlpCaptureError, match="committed representation"):
        service.ingest_otlp(PRINCIPAL, _request(observation=observation))

    assert event_log.list_entries() == []


def test_otlp_delivery_identity_distinguishes_records_in_same_batch(tmp_path: Path) -> None:
    service, event_log, _ = _service(tmp_path)
    first = _observation(record_ordinal=1)
    second = _observation(record_ordinal=2)

    first_receipt = service.ingest_otlp(PRINCIPAL, _request(observation=first))
    second_receipt = service.ingest_otlp(PRINCIPAL, _request(observation=second))

    assert first_receipt.event_id != second_receipt.event_id
    assert len(event_log.list_entries()) == 2
