from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.fleet.models import (
    AttestationClass,
    AuthMethod,
    DeviceEnrollmentRecord,
    DeviceProfile,
    KeyCustody,
    ProductType,
    RegistrationState,
    ScopeBinding,
)
from ets.fleet.presence import (
    FleetPresenceService,
    HeartbeatEnvelope,
    HeartbeatPayload,
    HeartbeatPosture,
    InMemoryPresenceStore,
    PresenceReason,
    TransportPresence,
)
from ets.fleet.service import DeviceEnrollmentService
from ets.fleet.store import InMemoryEnrollmentStore

NOW = datetime(2026, 8, 22, 3, 0, tzinfo=UTC)
DEVICE_ID = "ets-edge:0123456789abcdef01234567"
FINGERPRINT = "a" * 64
CERT = "b" * 64
HUB_ID = (
    "/subscriptions/sub/resourceGroups/rg/providers/"
    "Microsoft.Devices/IotHubs/ets-fleet-hub"
)


class AcceptIdentity:
    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None:
        del record, now


class StaticHeartbeatVerifier:
    def verify(
        self,
        *,
        payload: bytes,
        signature: bytes,
        signer_fingerprint_sha256: str,
    ) -> bool:
        return (
            bool(payload)
            and signature == b"qualified-signature"
            and signer_fingerprint_sha256 == FINGERPRINT
        )


def _enrollment(*, state: RegistrationState = RegistrationState.PENDING) -> DeviceEnrollmentRecord:
    return DeviceEnrollmentRecord(
        enrollment_id="enr_presence_001",
        device_id=DEVICE_ID,
        product_type=ProductType.EDGE,
        profile=DeviceProfile.VIRTUAL_DEMO,
        auth_method=AuthMethod.X509,
        public_key_fingerprint_sha256=FINGERPRINT,
        certificate_thumbprint_sha256=CERT,
        attestation_class=AttestationClass.SOFTWARE_DEMO,
        key_custody=KeyCustody.SOFTWARE_DEMO,
        hardware_attested=False,
        registration_state=state,
        scope_binding=ScopeBinding(tenant_id="tenant-1", workspace_id="workspace-1"),
        certificate_not_after_utc=NOW + timedelta(days=1),
        created_at_utc=NOW,
    )


def _service() -> tuple[FleetPresenceService, DeviceEnrollmentService, InMemoryEnrollmentStore]:
    enrollment_store = InMemoryEnrollmentStore()
    enrollment_service = DeviceEnrollmentService(enrollment_store, AcceptIdentity())
    enrollment_service.submit(
        _enrollment(),
        authoritative_scope=ScopeBinding(tenant_id="tenant-1", workspace_id="workspace-1"),
        now=NOW,
    )
    enrollment_service.activate("enr_presence_001", now=NOW)
    service = FleetPresenceService(
        enrollment_store=enrollment_store,
        enrollment_authorizer=enrollment_service,
        presence_store=InMemoryPresenceStore(),
        heartbeat_verifier=StaticHeartbeatVerifier(),
        expected_iothub_resource_id=HUB_ID,
        heartbeat_stale_after=timedelta(minutes=5),
        max_clock_skew=timedelta(minutes=2),
    )
    return service, enrollment_service, enrollment_store


def _event(
    *,
    event_id: str = "event-1",
    event_type: str = "Microsoft.Devices.DeviceConnected",
    sequence: str = "0" * 63 + "1",
    source: str = HUB_ID,
    device_id: str = DEVICE_ID,
    subject: str | None = None,
) -> dict[str, object]:
    return {
        "id": event_id,
        "topic": source,
        "subject": subject or f"devices/{device_id}",
        "eventType": event_type,
        "eventTime": "2026-08-22T03:00:00Z",
        "data": {
            "deviceConnectionStateEventInfo": {"sequenceNumber": sequence},
            "hubName": "ets-fleet-hub",
            "deviceId": device_id,
        },
    }


def _heartbeat(
    *,
    sequence: int = 0,
    boot_session_id: str = "boot-session-0001",
    observed_at: datetime = NOW,
    signer: str = FINGERPRINT,
    signature: bytes = b"qualified-signature",
) -> HeartbeatEnvelope:
    payload = HeartbeatPayload(
        device_id=DEVICE_ID,
        enrollment_id="enr_presence_001",
        boot_session_id=boot_session_id,
        sequence=sequence,
        observed_at_utc=observed_at,
        software_version="1.0.0",
        profile_version="edge-r1",
    )
    return HeartbeatEnvelope(
        payload=payload,
        signer_fingerprint_sha256=signer,
        signature_b64=base64.b64encode(signature).decode("ascii"),
    )


def test_transport_progresses_without_changing_heartbeat_posture() -> None:
    service, _, _ = _service()
    connected = service.ingest_transport(_event(), received_at_utc=NOW)
    assert connected.accepted is True
    assert connected.state is not None
    assert connected.state.transport_presence is TransportPresence.ONLINE
    assert connected.state.heartbeat_posture is HeartbeatPosture.MISSING

    disconnected = service.ingest_transport(
        _event(
            event_id="event-2",
            event_type="Microsoft.Devices.DeviceDisconnected",
            sequence="0" * 63 + "2",
        ),
        received_at_utc=NOW + timedelta(seconds=30),
    )
    assert disconnected.accepted is True
    assert disconnected.state is not None
    assert disconnected.state.transport_presence is TransportPresence.OFFLINE


def test_transport_deduplicates_and_rejects_reordered_sequence() -> None:
    service, _, _ = _service()
    assert service.ingest_transport(_event(), received_at_utc=NOW).accepted
    duplicate = service.ingest_transport(_event(), received_at_utc=NOW)
    assert duplicate.reason is PresenceReason.DUPLICATE_EVENT

    reordered = service.ingest_transport(
        _event(event_id="event-2", sequence="0" * 64),
        received_at_utc=NOW + timedelta(seconds=1),
    )
    assert reordered.reason is PresenceReason.REORDERED_EVENT
    assert reordered.state is not None
    assert reordered.state.transport_presence is TransportPresence.ONLINE


def test_transport_rejects_wrong_hub_and_subject_identity() -> None:
    service, _, _ = _service()
    wrong_hub = service.ingest_transport(
        _event(source=HUB_ID.replace("ets-fleet-hub", "other-hub")),
        received_at_utc=NOW,
    )
    assert wrong_hub.reason is PresenceReason.SOURCE_MISMATCH

    wrong_subject = service.ingest_transport(
        _event(event_id="event-2", subject="devices/not-the-device"),
        received_at_utc=NOW,
    )
    assert wrong_subject.reason is PresenceReason.DEVICE_MISMATCH


def test_unknown_device_transport_fails_closed() -> None:
    service, _, _ = _service()
    result = service.ingest_transport(
        _event(
            device_id="ets-edge:ffffffffffffffffffffffff",
            subject="devices/ets-edge:ffffffffffffffffffffffff",
        ),
        received_at_utc=NOW,
    )
    assert result.reason is PresenceReason.UNKNOWN_DEVICE


def test_valid_signed_heartbeat_is_independent_of_transport_presence() -> None:
    service, _, _ = _service()
    result = service.ingest_heartbeat(_heartbeat(), received_at_utc=NOW)
    assert result.accepted is True
    assert result.reason is PresenceReason.HEARTBEAT_ACCEPTED
    assert result.state is not None
    assert result.state.heartbeat_posture is HeartbeatPosture.CURRENT
    assert result.state.transport_presence is TransportPresence.UNKNOWN


def test_wrong_signer_and_bad_signature_fail_closed() -> None:
    service, _, _ = _service()
    wrong_signer = service.ingest_heartbeat(
        _heartbeat(signer="c" * 64),
        received_at_utc=NOW,
    )
    assert wrong_signer.reason is PresenceReason.SIGNER_MISMATCH

    bad_signature = service.ingest_heartbeat(
        _heartbeat(signature=b"not-qualified-signature"),
        received_at_utc=NOW,
    )
    assert bad_signature.reason is PresenceReason.SIGNATURE_INVALID


def test_heartbeat_sequence_replay_is_rejected() -> None:
    service, _, _ = _service()
    assert service.ingest_heartbeat(_heartbeat(), received_at_utc=NOW).accepted
    replay = service.ingest_heartbeat(
        _heartbeat(),
        received_at_utc=NOW + timedelta(seconds=1),
    )
    assert replay.reason is PresenceReason.HEARTBEAT_REPLAY

    next_heartbeat = service.ingest_heartbeat(
        _heartbeat(sequence=1),
        received_at_utc=NOW + timedelta(seconds=2),
    )
    assert next_heartbeat.accepted is True


def test_new_boot_session_must_start_at_zero_and_old_session_cannot_reappear() -> None:
    service, _, _ = _service()
    assert service.ingest_heartbeat(_heartbeat(), received_at_utc=NOW).accepted
    invalid_boot = service.ingest_heartbeat(
        _heartbeat(
            sequence=1,
            boot_session_id="boot-session-0002",
            observed_at=NOW + timedelta(seconds=5),
        ),
        received_at_utc=NOW + timedelta(seconds=5),
    )
    assert invalid_boot.reason is PresenceReason.BOOT_SEQUENCE_INVALID

    valid_boot = service.ingest_heartbeat(
        _heartbeat(
            sequence=0,
            boot_session_id="boot-session-0002",
            observed_at=NOW + timedelta(seconds=6),
        ),
        received_at_utc=NOW + timedelta(seconds=6),
    )
    assert valid_boot.accepted is True

    old_boot = service.ingest_heartbeat(
        _heartbeat(
            sequence=1,
            boot_session_id="boot-session-0001",
            observed_at=NOW + timedelta(seconds=7),
        ),
        received_at_utc=NOW + timedelta(seconds=7),
    )
    assert old_boot.reason is PresenceReason.BOOT_SESSION_REPLAY


def test_heartbeat_freshness_uses_service_receipt_time() -> None:
    service, _, _ = _service()
    assert service.ingest_heartbeat(_heartbeat(), received_at_utc=NOW).accepted
    stale = service.snapshot(DEVICE_ID, now=NOW + timedelta(minutes=6))
    assert stale is not None
    assert stale.heartbeat_posture is HeartbeatPosture.STALE


def test_revoked_device_heartbeat_is_rejected_by_authoritative_fleet_lifecycle() -> None:
    service, enrollment_service, _ = _service()
    enrollment_service.transition(
        "enr_presence_001",
        RegistrationState.REVOKED,
        now=NOW + timedelta(seconds=1),
    )
    result = service.ingest_heartbeat(
        _heartbeat(observed_at=NOW + timedelta(seconds=2)),
        received_at_utc=NOW + timedelta(seconds=2),
    )
    assert result.reason is PresenceReason.LIFECYCLE_DENIED
    assert result.authorization_reason is not None


def test_excessive_device_clock_skew_is_rejected() -> None:
    service, _, _ = _service()
    result = service.ingest_heartbeat(
        _heartbeat(observed_at=NOW - timedelta(minutes=3)),
        received_at_utc=NOW,
    )
    assert result.reason is PresenceReason.CLOCK_SKEW


def test_heartbeat_rejects_secret_shaped_metadata() -> None:
    with pytest.raises(ValidationError):
        HeartbeatPayload(
            device_id=DEVICE_ID,
            enrollment_id="enr_presence_001",
            boot_session_id="boot-session-0001",
            sequence=0,
            observed_at_utc=NOW,
            software_version="1.0.0",
            profile_version="edge-r1",
            metadata={"api_token": "should-not-be-retained"},
        )
