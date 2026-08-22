from __future__ import annotations

from pathlib import Path

SOURCE = Path("ets/fleet/presence.py")
DOC = Path("docs/fleet/ETS_FLEET_PRESENCE_RUNTIME_V1.md")


def test_presence_runtime_is_provider_neutral_and_does_not_import_product_planes() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    forbidden_imports = (
        "azure.",
        "azure_",
        "ets.core",
        "ets.edge",
        "ets.gateway",
        "requests",
        "httpx",
    )
    for forbidden in forbidden_imports:
        assert forbidden not in source.lower()


def test_presence_runtime_does_not_use_iot_hub_twin_connection_state_as_truth() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert '.get("connectionState")' not in source
    assert '["connectionState"]' not in source
    assert "connectionStateUpdatedTime" not in source


def test_transport_and_heartbeat_are_separate_state_dimensions() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "transport_presence: TransportPresence" in source
    assert "heartbeat_posture: HeartbeatPosture" in source
    assert "last_transport_received_at_utc" in source
    assert "heartbeat_received_at_utc" in source


def test_event_grid_source_identity_and_sequence_are_validated() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "deviceConnectionStateEventInfo" in source
    assert "sequenceNumber" in source
    assert "expected_iothub_resource_id" in source
    assert "event.sequence_number <= current.last_transport_sequence" in source


def test_heartbeat_is_bound_to_authoritative_enrollment_and_signature_verifier() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "EnrollmentAuthorizer" in source
    assert "HeartbeatSignatureVerifier" in source
    assert "decision.enrollment_id != payload.enrollment_id" in source
    assert "signer_fingerprint_sha256" in source


def test_presence_docs_preserve_truth_and_freshness_boundaries() -> None:
    text = DOC.read_text(encoding="utf-8").lower()
    assert "presence is not health" in text
    assert "heartbeat is not evidence verification" in text
    assert "service receipt time" in text
    assert "connectionstate" in text
    assert "not" in text
