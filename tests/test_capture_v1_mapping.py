from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ets.capture import CaptureEnvelopeV1, to_evidence_event

EXAMPLE_PATH = (
    Path(__file__).parents[1]
    / "schemas"
    / "capture"
    / "v1"
    / "examples"
    / "minimal.json"
)


def capture() -> CaptureEnvelopeV1:
    return CaptureEnvelopeV1.model_validate_json(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_mapping_uses_receipt_time_and_declared_representation_digest() -> None:
    parsed = capture()
    event = to_evidence_event(
        parsed,
        event_id="evt_capture_1",
        evidence_id="capture:1",
        subject_ref="order:42",
    )
    assert event.created_at_utc == datetime(2026, 8, 13, 14, 30, 1, tzinfo=UTC)
    assert event.created_at_utc == parsed.received_at_utc
    assert event.created_at_utc != parsed.observed_at_utc
    assert event.content_hash == parsed.content_digest.value
    assert event.tenant_id == parsed.source.tenant_id
    assert event.workspace_id == parsed.source.workspace_id
    assert event.metadata["observed_at_utc"] == "2026-08-13T14:30:00Z"
    assert event.metadata["content_digest"]["representation"] == "minimized-json-v1"


def test_transport_and_declared_identity_remain_distinct_in_metadata() -> None:
    event = to_evidence_event(
        capture(),
        event_id="evt_capture_1",
        evidence_id="capture:1",
    )
    source = event.metadata["source"]
    assert source["transport_identity"] == "spiffe://example.test/workload/orders"
    assert source["declared_identity"] == "orders-service"


def test_mapping_is_deterministic_for_fixed_inputs() -> None:
    parsed = capture()
    kwargs = {
        "event_id": "evt_capture_1",
        "evidence_id": "capture:1",
        "subject_ref": "order:42",
        "actor_id": "actor:test",
    }
    first = to_evidence_event(parsed, **kwargs).model_dump(mode="json")
    second = to_evidence_event(parsed, **kwargs).model_dump(mode="json")
    assert first == second
