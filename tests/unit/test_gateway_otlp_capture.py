from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

from ets.capture.otlp import OtlpObservationV1
from ets.core.api import canonicalize
from ets.gateway.otlp_capture import (
    GatewayOtlpCaptureError,
    GatewayOtlpCaptureRequest,
    build_otlp_capture,
)
from ets.gateway.source_registry import SourceRegistration

PRINCIPAL = "spiffe://example.test/workload/otlp-sender"


def _registration(*, redacted_keys: frozenset[str] = frozenset()) -> SourceRegistration:
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
        redacted_keys=redacted_keys,
        clock_quality="synchronized",
    )


def _observation(**overrides: object) -> OtlpObservationV1:
    values: dict[str, object] = {
        "schema_version": "ets.otlp.observation.v1",
        "signal_class": "logs",
        "record_ordinal": 3,
        "source_timestamp_utc": datetime(2026, 8, 14, 0, 30, tzinfo=UTC),
        "decoder_profile": "otlp-semantic.v1",
        "transformation_profile": "otlp-metadata.v1",
        "resource_metadata": {"service.name": "orders", "host.name": "node-7"},
        "scope_metadata": {"name": "orders.instrumentation", "version": "2.0"},
        "record_metadata": {"severity": "INFO", "message": "order accepted"},
    }
    values.update(overrides)
    return OtlpObservationV1.model_validate(values)


def _request(**overrides: object) -> GatewayOtlpCaptureRequest:
    values: dict[str, object] = {
        "observation": _observation(),
        "delivery_id": "batch-42",
        "received_at_utc": datetime(2026, 8, 14, 0, 31, tzinfo=UTC),
        "correlation_id": "corr-42",
    }
    values.update(overrides)
    return GatewayOtlpCaptureRequest(**values)  # type: ignore[arg-type]


def test_otlp_capture_uses_server_authorized_scope_and_separates_source_time() -> None:
    mapped = build_otlp_capture(_registration(), _request())
    envelope = mapped.envelope

    assert envelope.source.tenant_id == "tenant_authoritative"
    assert envelope.source.workspace_id == "workspace_authoritative"
    assert envelope.source.identifier == "otel-collector-a"
    assert envelope.source.transport_identity == PRINCIPAL
    assert envelope.source.sequence == 3
    assert envelope.source.idempotency_key == "otlp:batch-42:3"
    assert envelope.observed_at_utc == datetime(2026, 8, 14, 0, 30, tzinfo=UTC)
    assert envelope.received_at_utc == datetime(2026, 8, 14, 0, 31, tzinfo=UTC)
    assert envelope.metadata["otlp_signal_class"] == "logs"
    assert envelope.metadata["raw_transport_payload_retained"] is False
    assert envelope.privacy.contains_raw_evidence is False


def test_otlp_capture_commits_bounded_metadata_representation() -> None:
    observation = _observation()
    mapped = build_otlp_capture(_registration(), _request(observation=observation))
    expected = canonicalize(
        {
            "schema": "ets.gateway.otlp-metadata.v1",
            "signal_class": "logs",
            "record_ordinal": 3,
            "source_timestamp_utc": "2026-08-14T00:30:00Z",
            "decoder_profile": "otlp-semantic.v1",
            "transformation_profile": "otlp-metadata.v1",
            "resource_metadata": {"host.name": "node-7", "service.name": "orders"},
            "scope_metadata": {"name": "orders.instrumentation", "version": "2.0"},
            "record_metadata": {"message": "order accepted", "severity": "INFO"},
        }
    )

    assert mapped.committed_representation == expected
    assert mapped.envelope.content_digest.value == hashlib.sha256(expected).hexdigest()
    assert mapped.envelope.content_digest.representation == "ets.gateway.otlp-metadata.v1"


def test_otlp_capture_redacts_configured_keys_before_commitment() -> None:
    marker = "RAW-OTLP-SECRET"
    observation = _observation(
        resource_metadata={"service.name": "orders", "secret": marker},
        record_metadata={"nested": {"secret": marker}, "message": "safe"},
    )
    mapped = build_otlp_capture(
        _registration(redacted_keys=frozenset({"secret"})),
        _request(observation=observation),
    )

    event_visible = json.dumps(mapped.envelope.model_dump(mode="json"), sort_keys=True)
    assert marker not in mapped.committed_representation.decode("utf-8")
    assert marker not in event_visible
    assert mapped.envelope.metadata["redacted_field_count"] == 2
    assert mapped.envelope.metadata["committed_resource_metadata"] == {
        "service.name": "orders"
    }
    assert mapped.envelope.metadata["committed_record_metadata"] == {
        "nested": {},
        "message": "safe",
    }


def test_otlp_capture_is_deterministic_for_same_scope_delivery_and_observation() -> None:
    first = build_otlp_capture(_registration(), _request())
    second = build_otlp_capture(_registration(), _request())

    assert first.envelope.capture_id == second.envelope.capture_id
    assert first.envelope.content_digest.value == second.envelope.content_digest.value
    assert first.committed_representation == second.committed_representation


def test_otlp_capture_rejects_invalid_delivery_and_time() -> None:
    with pytest.raises(GatewayOtlpCaptureError, match="delivery_id"):
        build_otlp_capture(_registration(), _request(delivery_id=""))

    with pytest.raises(GatewayOtlpCaptureError, match="timezone-aware"):
        build_otlp_capture(
            _registration(),
            _request(received_at_utc=datetime(2026, 8, 14, 0, 31)),
        )


def test_otlp_capture_rejects_committed_representation_over_bound() -> None:
    observation = _observation(record_metadata={"message": "x" * 2048})

    with pytest.raises(GatewayOtlpCaptureError, match="committed representation"):
        build_otlp_capture(
            _registration(),
            _request(observation=observation),
            maximum_committed_bytes=256,
        )
