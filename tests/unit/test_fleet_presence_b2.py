from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
    PresenceReason,
)
from ets.fleet.presence_api import build_fleet_presence_router
from ets.fleet.presence_ops import (
    FleetPresenceCoordinator,
    MaterialTransitionType,
    OperatorNotification,
)
from ets.fleet.presence_sqlite import SQLitePresenceStore
from ets.fleet.service import DeviceEnrollmentService
from ets.fleet.store import InMemoryEnrollmentStore

NOW = datetime(2026, 8, 22, 3, 30, tzinfo=UTC)
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


class CaptureNotifier:
    def __init__(self) -> None:
        self.items: list[OperatorNotification] = []

    def send(self, notification: OperatorNotification) -> None:
        self.items.append(notification)


def _enrollment(*, state: RegistrationState = RegistrationState.PENDING) -> DeviceEnrollmentRecord:
    return DeviceEnrollmentRecord(
        enrollment_id="enr_presence_b2_001",
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


def _runtime(path: Path) -> tuple[
    FleetPresenceCoordinator,
    DeviceEnrollmentService,
    SQLitePresenceStore,
]:
    enrollment_store = InMemoryEnrollmentStore()
    enrollment_service = DeviceEnrollmentService(enrollment_store, AcceptIdentity())
    enrollment_service.submit(
        _enrollment(),
        authoritative_scope=ScopeBinding(tenant_id="tenant-1", workspace_id="workspace-1"),
        now=NOW,
    )
    enrollment_service.activate("enr_presence_b2_001", now=NOW)
    presence_store = SQLitePresenceStore(path)
    presence = FleetPresenceService(
        enrollment_store=enrollment_store,
        enrollment_authorizer=enrollment_service,
        presence_store=presence_store,
        heartbeat_verifier=StaticHeartbeatVerifier(),
        expected_iothub_resource_id=HUB_ID,
        heartbeat_stale_after=timedelta(minutes=5),
        max_clock_skew=timedelta(minutes=2),
    )
    coordinator = FleetPresenceCoordinator(
        presence_service=presence,
        operations_store=presence_store,
        reconnect_after=timedelta(minutes=5),
        disconnect_after=timedelta(minutes=5),
    )
    return coordinator, enrollment_service, presence_store


def _event(
    *,
    event_id: str = "event-1",
    event_type: str = "Microsoft.Devices.DeviceConnected",
    sequence: str = "0" * 63 + "1",
    source: str = HUB_ID,
) -> dict[str, object]:
    return {
        "id": event_id,
        "topic": source,
        "subject": f"devices/{DEVICE_ID}",
        "eventType": event_type,
        "eventTime": "2026-08-22T03:30:00Z",
        "data": {
            "deviceConnectionStateEventInfo": {"sequenceNumber": sequence},
            "hubName": "ets-fleet-hub",
            "deviceId": DEVICE_ID,
        },
    }


def _heartbeat(
    *,
    sequence: int = 0,
    observed_at: datetime = NOW,
    signer: str = FINGERPRINT,
    signature: bytes = b"qualified-signature",
) -> HeartbeatEnvelope:
    return HeartbeatEnvelope(
        payload=HeartbeatPayload(
            device_id=DEVICE_ID,
            enrollment_id="enr_presence_b2_001",
            boot_session_id="boot-session-b2-0001",
            sequence=sequence,
            observed_at_utc=observed_at,
            software_version="1.0.0",
            profile_version="edge-r1",
        ),
        signer_fingerprint_sha256=signer,
        signature_b64=base64.b64encode(signature).decode("ascii"),
    )


def test_sqlite_presence_survives_restart_and_deduplicates_transport(tmp_path: Path) -> None:
    db = tmp_path / "fleet-presence.db"
    coordinator, _, store = _runtime(db)
    first = coordinator.ingest_transport(_event(), received_at_utc=NOW)
    assert first.accepted is True
    store.close()

    coordinator2, _, store2 = _runtime(db)
    duplicate = coordinator2.ingest_transport(_event(), received_at_utc=NOW + timedelta(seconds=1))
    assert duplicate.reason is PresenceReason.DUPLICATE_EVENT
    assert duplicate.state is not None
    assert duplicate.state.transport_presence.value == "online"
    assert len(store2.list_pending_notifications()) == 1
    store2.close()


def test_first_online_and_reconnect_are_deduplicated_material_transitions(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    assert coordinator.ingest_transport(_event(), received_at_utc=NOW).accepted
    assert not coordinator.ingest_transport(_event(), received_at_utc=NOW).accepted

    disconnect = _event(
        event_id="event-2",
        event_type="Microsoft.Devices.DeviceDisconnected",
        sequence="0" * 63 + "2",
    )
    assert coordinator.ingest_transport(
        disconnect,
        received_at_utc=NOW + timedelta(minutes=1),
    ).accepted
    reconnect = _event(event_id="event-3", sequence="0" * 63 + "3")
    assert coordinator.ingest_transport(
        reconnect,
        received_at_utc=NOW + timedelta(minutes=7),
    ).accepted

    pending = store.list_pending_notifications()
    assert [item.transition_type for item in pending] == [
        MaterialTransitionType.FIRST_ONLINE,
        MaterialTransitionType.RECONNECT,
    ]
    store.close()


def test_persistent_disconnect_and_stale_heartbeat_are_policy_evaluated(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    assert coordinator.ingest_transport(_event(), received_at_utc=NOW).accepted
    assert coordinator.ingest_heartbeat(_heartbeat(), received_at_utc=NOW).accepted

    disconnect = _event(
        event_id="event-2",
        event_type="Microsoft.Devices.DeviceDisconnected",
        sequence="0" * 63 + "2",
    )
    assert coordinator.ingest_transport(
        disconnect,
        received_at_utc=NOW + timedelta(minutes=1),
    ).accepted
    coordinator.evaluate(DEVICE_ID, now=NOW + timedelta(minutes=7))
    types = {item.transition_type for item in store.list_pending_notifications()}
    assert MaterialTransitionType.PERSISTENT_DISCONNECT in types
    store.close()


def test_stale_heartbeat_while_transport_online_is_material(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    assert coordinator.ingest_transport(_event(), received_at_utc=NOW).accepted
    assert coordinator.ingest_heartbeat(_heartbeat(), received_at_utc=NOW).accepted
    coordinator.evaluate(DEVICE_ID, now=NOW + timedelta(minutes=6))
    types = {item.transition_type for item in store.list_pending_notifications()}
    assert MaterialTransitionType.HEARTBEAT_STALE in types
    store.close()


def test_revoked_heartbeat_emits_one_critical_notification(tmp_path: Path) -> None:
    coordinator, enrollment_service, store = _runtime(tmp_path / "presence.db")
    assert coordinator.ingest_transport(_event(), received_at_utc=NOW).accepted
    enrollment_service.transition(
        "enr_presence_b2_001",
        RegistrationState.REVOKED,
        now=NOW + timedelta(seconds=1),
    )
    result = coordinator.ingest_heartbeat(
        _heartbeat(observed_at=NOW + timedelta(seconds=2)),
        received_at_utc=NOW + timedelta(seconds=2),
    )
    assert result.reason is PresenceReason.LIFECYCLE_DENIED
    revoked = [
        item
        for item in store.list_pending_notifications()
        if item.transition_type is MaterialTransitionType.REVOKED
    ]
    assert len(revoked) == 1
    assert revoked[0].severity == "critical"
    store.close()


def test_notification_outbox_retries_until_marked_delivered(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    assert coordinator.ingest_transport(_event(), received_at_utc=NOW).accepted
    notifier = CaptureNotifier()
    assert coordinator.dispatch_pending(notifier, now=NOW + timedelta(seconds=1)) == 1
    assert len(notifier.items) == 1
    assert store.list_pending_notifications() == []
    assert "evidence-verification" in notifier.items[0].body
    assert "<" not in notifier.items[0].body and ">" not in notifier.items[0].body
    store.close()


def test_notification_rate_limit_records_transition_without_flooding(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    limited = FleetPresenceCoordinator(
        presence_service=coordinator._presence,  # noqa: SLF001 - deliberate policy test seam
        operations_store=store,
        disconnect_after=timedelta(minutes=1),
        max_notifications_per_window=1,
    )
    assert limited.ingest_transport(_event(), received_at_utc=NOW).accepted
    disconnect = _event(
        event_id="event-2",
        event_type="Microsoft.Devices.DeviceDisconnected",
        sequence="0" * 63 + "2",
    )
    assert limited.ingest_transport(
        disconnect,
        received_at_utc=NOW + timedelta(seconds=10),
    ).accepted
    limited.evaluate(DEVICE_ID, now=NOW + timedelta(minutes=2))
    assert len(store.list_pending_notifications()) == 1
    assert store.has_transition(f"persistent-disconnect:{DEVICE_ID}:event-2")
    store.close()


def test_production_event_grid_router_requires_authenticator(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    with pytest.raises(ValueError, match="Microsoft Entra"):
        build_fleet_presence_router(
            coordinator=coordinator,
            expected_iothub_resource_id=HUB_ID,
            production=True,
        )
    store.close()


def test_event_grid_ingress_requires_auth_and_supports_validation(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    app = FastAPI()
    app.include_router(
        build_fleet_presence_router(
            coordinator=coordinator,
            expected_iothub_resource_id=HUB_ID,
            production=True,
            event_grid_authenticator=lambda request: (
                request.headers.get("authorization") == "Bearer ok"
            ),
        )
    )
    client = TestClient(app)
    validation = [
        {
            "id": "validation-1",
            "topic": HUB_ID,
            "subject": "",
            "eventType": "Microsoft.EventGrid.SubscriptionValidationEvent",
            "eventTime": "2026-08-22T03:30:00Z",
            "data": {"validationCode": "validation-code-123"},
        }
    ]
    assert client.post("/fleet/v1/azure/event-grid", json=validation).status_code == 401
    response = client.post(
        "/fleet/v1/azure/event-grid",
        json=validation,
        headers={"Authorization": "Bearer ok"},
    )
    assert response.status_code == 200
    assert response.json() == {"validationResponse": "validation-code-123"}
    store.close()


def test_event_grid_ingress_passes_runtime_source_checks(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    app = FastAPI()
    app.include_router(
        build_fleet_presence_router(
            coordinator=coordinator,
            expected_iothub_resource_id=HUB_ID,
            production=True,
            event_grid_authenticator=lambda request: True,
        )
    )
    client = TestClient(app)
    wrong_source = _event(source=HUB_ID.replace("ets-fleet-hub", "wrong-hub"))
    response = client.post("/fleet/v1/azure/event-grid", json=[wrong_source])
    assert response.status_code == 200
    assert response.json()["results"][0]["reason"] == "source_mismatch"
    store.close()


def test_unenrolled_html_shaped_device_cannot_generate_notification(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    event = _event(event_id="event-injection")
    event["subject"] = "devices/<script>alert(1)</script>"
    data = event["data"]
    assert isinstance(data, dict)
    data["deviceId"] = "<script>alert(1)</script>"
    decision = coordinator.ingest_transport(event, received_at_utc=NOW)
    assert decision.accepted is False
    assert decision.reason is PresenceReason.UNKNOWN_DEVICE
    assert store.list_pending_notifications() == []
    store.close()


def test_heartbeat_ingress_is_bounded_and_returns_no_truth_claim(tmp_path: Path) -> None:
    coordinator, _, store = _runtime(tmp_path / "presence.db")
    app = FastAPI()
    app.include_router(
        build_fleet_presence_router(
            coordinator=coordinator,
            expected_iothub_resource_id=HUB_ID,
            production=False,
        )
    )
    client = TestClient(app)
    response = client.post(
        "/fleet/v1/heartbeat",
        json=_heartbeat(observed_at=datetime.now(UTC)).model_dump(mode="json"),
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["evidence_verified"] is False
    assert response.json()["health_asserted"] is False

    oversized = client.post(
        "/fleet/v1/heartbeat",
        content=b"{" + b"x" * (16 * 1024) + b"}",
        headers={"content-type": "application/json"},
    )
    assert oversized.status_code == 413
    store.close()
