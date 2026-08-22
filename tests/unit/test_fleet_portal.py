from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from ets.fleet.models import (
    AttestationClass,
    AuthMethod,
    DeviceEnrollmentRecord,
    DeviceProfile,
    KeyCustody,
    ProductType,
    ProvisioningBackend,
    RegistrationState,
    ScopeBinding,
)
from ets.fleet.portal import (
    FleetPortalNotFound,
    FleetPortalService,
    FleetPrincipal,
    FleetRole,
    principal_from_entra_claims,
)
from ets.fleet.portal_api import build_fleet_portal_router
from ets.fleet.presence import HeartbeatPosture, PresenceState, TransportPresence
from ets.fleet.store import InMemoryEnrollmentStore

NOW = datetime(2026, 8, 22, 4, 0, tzinfo=UTC)


class StaticPresenceReader:
    def __init__(self, states: dict[str, PresenceState]) -> None:
        self.states = states

    def snapshot(self, device_id: str, *, now: datetime) -> PresenceState | None:
        state = self.states.get(device_id)
        if state is None:
            return None
        if (
            state.heartbeat_received_at_utc is not None
            and now - state.heartbeat_received_at_utc > timedelta(minutes=5)
        ):
            return state.model_copy(update={"heartbeat_posture": HeartbeatPosture.STALE})
        return state


def _record(
    suffix: str,
    *,
    tenant: str = "tenant-a",
    workspace: str = "workspace-a",
    friendly_name: str | None = None,
    registration_state: RegistrationState = RegistrationState.ENROLLED,
    hardware_attested: bool = False,
    cert_days: int = 90,
) -> DeviceEnrollmentRecord:
    if hardware_attested:
        return DeviceEnrollmentRecord(
            enrollment_id=f"enr_{suffix}",
            device_id=f"ets-edge:{suffix}",
            product_type=ProductType.EDGE,
            profile=DeviceProfile.PHYSICAL_PILOT,
            auth_method=AuthMethod.TPM_ATTESTATION,
            public_key_fingerprint_sha256="a" * 64,
            attestation_class=AttestationClass.TPM2,
            key_custody=KeyCustody.TPM2,
            hardware_attested=True,
            registration_state=registration_state,
            scope_binding=ScopeBinding(tenant_id=tenant, workspace_id=workspace),
            provisioning_backend=ProvisioningBackend.AZURE_IOT_DPS_V1,
            created_at_utc=NOW - timedelta(days=1),
            metadata={} if friendly_name is None else {"friendly_name": friendly_name},
        )

    return DeviceEnrollmentRecord(
        enrollment_id=f"enr_{suffix}",
        device_id=f"ets-edge:{suffix}",
        product_type=ProductType.EDGE,
        profile=DeviceProfile.VIRTUAL_DEMO,
        auth_method=AuthMethod.X509,
        public_key_fingerprint_sha256="b" * 64,
        certificate_thumbprint_sha256="c" * 64,
        attestation_class=AttestationClass.SOFTWARE_DEMO,
        key_custody=KeyCustody.SOFTWARE_DEMO,
        hardware_attested=False,
        registration_state=registration_state,
        scope_binding=ScopeBinding(tenant_id=tenant, workspace_id=workspace),
        provisioning_backend=ProvisioningBackend.AZURE_IOT_DPS_V1,
        certificate_not_after_utc=NOW + timedelta(days=cert_days),
        created_at_utc=NOW - timedelta(days=1),
        metadata={} if friendly_name is None else {"friendly_name": friendly_name},
    )


def _store(*records: DeviceEnrollmentRecord) -> InMemoryEnrollmentStore:
    store = InMemoryEnrollmentStore()
    for record in records:
        store.put_enrollment(record)
        store.set_current_enrollment_id(record.device_id, record.enrollment_id)
    return store


def _principal(
    *,
    tenant: str = "tenant-a",
    workspace: str = "workspace-a",
    role: FleetRole = FleetRole.VIEWER,
) -> FleetPrincipal:
    return FleetPrincipal(
        subject="operator-1",
        roles=(role,),
        scope_bindings=(ScopeBinding(tenant_id=tenant, workspace_id=workspace),),
    )


def _service(
    store: InMemoryEnrollmentStore,
    states: dict[str, PresenceState] | None = None,
) -> FleetPortalService:
    return FleetPortalService(
        enrollment_reader=store,
        presence_reader=StaticPresenceReader(states or {}),
    )


def test_entra_claim_mapping_accepts_only_exact_fleet_app_roles() -> None:
    principal = principal_from_entra_claims(
        {"oid": "operator-1", "roles": ["Fleet.Viewer", "Fleet.Operator"]},
        scope_bindings=(ScopeBinding(tenant_id="tenant-a", workspace_id="workspace-a"),),
    )
    assert [item.value for item in principal.roles] == ["Fleet.Operator", "Fleet.Viewer"]
    assert [item.value for item in principal.capabilities] == ["fleet.operate", "fleet.read"]

    with pytest.raises(ValueError, match="unsupported Fleet app role"):
        principal_from_entra_claims(
            {"oid": "operator-1", "roles": ["Fleet.SuperAdminFromBrowser"]},
            scope_bindings=(ScopeBinding(tenant_id="tenant-a", workspace_id="workspace-a"),),
        )


def test_overview_preserves_lifecycle_transport_and_heartbeat_dimensions() -> None:
    one = _record("device-one", cert_days=10)
    two = _record("device-two", hardware_attested=True)
    store = _store(one, two)
    states = {
        one.device_id: PresenceState(
            device_id=one.device_id,
            transport_presence=TransportPresence.ONLINE,
            heartbeat_posture=HeartbeatPosture.CURRENT,
            heartbeat_received_at_utc=NOW - timedelta(minutes=1),
            software_version="1.2.3",
            profile_version="fleet-v1",
        ),
        two.device_id: PresenceState(
            device_id=two.device_id,
            transport_presence=TransportPresence.OFFLINE,
            heartbeat_posture=HeartbeatPosture.MISSING,
        ),
    }
    overview = _service(store, states).overview(_principal(), now=NOW)
    assert overview.total == 2
    assert overview.online == 1
    assert overview.offline == 1
    assert overview.heartbeat_current == 1
    assert overview.heartbeat_missing == 1
    assert overview.expiring_certificates == 1
    assert overview.hardware_attested == 1
    assert overview.evidence_verified is False
    assert overview.health_asserted is False


def test_stale_heartbeat_is_computed_at_read_time() -> None:
    record = _record("stale-device")
    store = _store(record)
    state = PresenceState(
        device_id=record.device_id,
        transport_presence=TransportPresence.ONLINE,
        heartbeat_posture=HeartbeatPosture.CURRENT,
        heartbeat_received_at_utc=NOW - timedelta(minutes=10),
    )
    page = _service(store, {record.device_id: state}).list_devices(
        _principal(),
        now=NOW,
    )
    assert page.items[0].transport_presence is TransportPresence.ONLINE
    assert page.items[0].heartbeat_posture is HeartbeatPosture.STALE


def test_cross_scope_device_is_filtered_and_detail_returns_same_not_found() -> None:
    own = _record("own-device")
    foreign = _record("foreign-device", tenant="tenant-b", workspace="workspace-b")
    service = _service(_store(own, foreign))
    page = service.list_devices(_principal(), now=NOW)
    assert [item.device_id for item in page.items] == [own.device_id]

    with pytest.raises(FleetPortalNotFound):
        service.get_device(_principal(), foreign.device_id, now=NOW)
    with pytest.raises(FleetPortalNotFound):
        service.get_device(_principal(), "ets-edge:not-present", now=NOW)


def test_friendly_name_is_bounded_and_control_characters_are_removed() -> None:
    record = _record(
        "named-device",
        friendly_name="\x00\x1f<script>alert(1)</script>" + ("x" * 200),
    )
    page = _service(_store(record)).list_devices(_principal(), now=NOW)
    assert "\x00" not in page.items[0].friendly_name
    assert len(page.items[0].friendly_name) <= 128
    assert "<script>" in page.items[0].friendly_name


def test_list_devices_enforces_server_side_pagination_bounds() -> None:
    service = _service(_store(_record("device-one")))
    with pytest.raises(ValueError, match="limit"):
        service.list_devices(_principal(), limit=101, now=NOW)
    with pytest.raises(ValueError, match="offset"):
        service.list_devices(_principal(), offset=100_001, now=NOW)


def _client(
    principal: FleetPrincipal | None,
    *,
    store: InMemoryEnrollmentStore | None = None,
) -> TestClient:
    app = FastAPI()
    fleet_store = store or _store(_record("device-one", friendly_name="<img src=x onerror=1>"))
    service = _service(fleet_store)

    def resolver(_request: Request) -> FleetPrincipal | None:
        return principal

    app.include_router(
        build_fleet_portal_router(
            service=service,
            principal_resolver=resolver,
        )
    )
    return TestClient(app)


def test_all_portal_routes_require_authenticated_principal() -> None:
    client = _client(None)
    for path in (
        "/fleet",
        "/fleet/assets/app.css",
        "/fleet/assets/app.js",
        "/fleet/bff/v1/session",
        "/fleet/bff/v1/overview",
        "/fleet/bff/v1/devices",
    ):
        response = client.get(path)
        assert response.status_code == 401
        assert response.headers["cache-control"].startswith("no-store")


def test_bff_returns_scope_filtered_json_with_security_headers() -> None:
    client = _client(_principal())
    response = client.get("/fleet/bff/v1/devices")
    assert response.status_code == 200
    payload = response.json()
    assert payload["returned"] == 1
    assert payload["items"][0]["friendly_name"] == "<img src=x onerror=1>"
    assert "private_key" not in response.text.lower()
    assert "connectionstring" not in response.text.lower()
    assert "bearer " not in response.text.lower()
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "no-referrer"


def test_dark_pro_shell_uses_external_assets_and_no_inline_script() -> None:
    client = _client(_principal())
    response = client.get("/fleet")
    assert response.status_code == 200
    assert '<script src="/fleet/assets/app.js" defer></script>' in response.text
    assert "<script>" not in response.text
    assert "<style>" not in response.text
    assert "localStorage" not in response.text
    assert "sessionStorage" not in response.text


def test_dark_pro_javascript_uses_text_content_not_inner_html() -> None:
    client = _client(_principal())
    response = client.get("/fleet/assets/app.js")
    assert response.status_code == 200
    assert "textContent" in response.text
    assert "innerHTML" not in response.text
    assert "localStorage" not in response.text
    assert "sessionStorage" not in response.text


def test_device_detail_does_not_reveal_cross_scope_existence() -> None:
    own = _record("own-device")
    foreign = _record("foreign-device", tenant="tenant-b", workspace="workspace-b")
    client = _client(_principal(), store=_store(own, foreign))

    foreign_response = client.get(f"/fleet/bff/v1/devices/{foreign.device_id}")
    missing_response = client.get("/fleet/bff/v1/devices/ets-edge:not-present")
    assert foreign_response.status_code == 404
    assert missing_response.status_code == 404
    assert foreign_response.json() == missing_response.json()


def test_query_limit_is_bounded_by_http_contract() -> None:
    client = _client(_principal())
    response = client.get("/fleet/bff/v1/devices?limit=101")
    assert response.status_code == 422
