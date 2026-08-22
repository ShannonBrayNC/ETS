from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ets.fleet import (
    AttestationClass,
    AuthMethod,
    DeviceEnrollmentRecord,
    DeviceEnrollmentService,
    DeviceProfile,
    InMemoryEnrollmentStore,
    KeyCustody,
    ProductType,
    ProvisioningBackend,
    RegistrationState,
    ScopeBinding,
    derive_device_id,
)
from ets.fleet.portal import FleetPortalService, FleetPrincipal, FleetRole
from ets.fleet.portal_admin import (
    FleetAdminAction,
    FleetAdminConfirmationError,
    FleetAdminForbidden,
    FleetAdminIdempotencyConflict,
    FleetAdminNotFound,
    FleetAdminStepUpRequired,
    FleetPortalAdminService,
    FleetSecuritySession,
    InMemoryFleetAdministrativeEvidenceSink,
)
from ets.fleet.portal_api import build_fleet_portal_router

NOW = datetime(2026, 8, 22, 4, 50, tzinfo=UTC)
A = "a" * 64
B = "b" * 64
D = "d" * 64
E = "e" * 64
CSRF = "csrf-" + "x" * 40


class AcceptIdentity:
    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None:
        del record, now


class EmptyPresence:
    def snapshot(self, device_id: str, *, now: datetime) -> None:
        del device_id, now
        return None


def record(
    *,
    enrollment_id: str = "enr_001",
    fingerprint: str = A,
    thumbprint: str = D,
    device_id: str | None = None,
    scope: ScopeBinding | None = None,
    supersedes: str | None = None,
) -> DeviceEnrollmentRecord:
    binding = scope or ScopeBinding(tenant_id="tenant-a", workspace_id="workspace-a")
    return DeviceEnrollmentRecord(
        enrollment_id=enrollment_id,
        device_id=device_id or derive_device_id(ProductType.EDGE, fingerprint),
        product_type=ProductType.EDGE,
        profile=DeviceProfile.VIRTUAL_DEMO,
        auth_method=AuthMethod.X509,
        public_key_fingerprint_sha256=fingerprint,
        certificate_thumbprint_sha256=thumbprint,
        attestation_class=AttestationClass.SOFTWARE_DEMO,
        key_custody=KeyCustody.SOFTWARE_DEMO,
        hardware_attested=False,
        registration_state=RegistrationState.PENDING,
        scope_binding=binding,
        provisioning_backend=ProvisioningBackend.AZURE_IOT_DPS_V1,
        certificate_not_after_utc=NOW + timedelta(days=30),
        supersedes_enrollment_id=supersedes,
        created_at_utc=NOW,
    )


def principal(
    role: FleetRole,
    *,
    scope: ScopeBinding | None = None,
) -> FleetPrincipal:
    return FleetPrincipal(
        subject=f"subject-{role.value}",
        roles=(role,),
        scope_bindings=(scope or ScopeBinding(tenant_id="tenant-a", workspace_id="workspace-a"),),
    )


def session(*, step_up_age: timedelta | None = timedelta(minutes=1)) -> FleetSecuritySession:
    return FleetSecuritySession(
        session_id="session-1234567890abcdef",
        csrf_token=CSRF,
        authenticated_at_utc=NOW - timedelta(hours=1),
        step_up_at_utc=None if step_up_age is None else NOW - step_up_age,
    )


def runtime() -> tuple[
    InMemoryEnrollmentStore,
    DeviceEnrollmentService,
    InMemoryFleetAdministrativeEvidenceSink,
    FleetPortalAdminService,
]:
    store = InMemoryEnrollmentStore()
    enrollment = DeviceEnrollmentService(store, AcceptIdentity())
    evidence = InMemoryFleetAdministrativeEvidenceSink()
    admin = FleetPortalAdminService(
        enrollment_service=enrollment,
        enrollment_store=store,
        evidence_sink=evidence,
    )
    return store, enrollment, evidence, admin


def submit_pending(
    enrollment: DeviceEnrollmentService,
    item: DeviceEnrollmentRecord,
) -> DeviceEnrollmentRecord:
    return enrollment.submit(item, authoritative_scope=item.scope_binding, now=NOW)


def enroll(
    enrollment: DeviceEnrollmentService,
    item: DeviceEnrollmentRecord,
) -> DeviceEnrollmentRecord:
    submit_pending(enrollment, item)
    return enrollment.activate(item.enrollment_id, now=NOW)


def test_operator_can_approve_and_restore_but_viewer_cannot_mutate() -> None:
    _store, enrollment, evidence, admin = runtime()
    item = submit_pending(enrollment, record())

    with pytest.raises(FleetAdminForbidden):
        admin.mutate(
            principal=principal(FleetRole.VIEWER),
            security_session=session(),
            action=FleetAdminAction.APPROVE,
            device_id=item.device_id,
            idempotency_key="viewer-denied",
            csrf_token=CSRF,
            now=NOW,
        )

    approved = admin.mutate(
        principal=principal(FleetRole.OPERATOR),
        security_session=session(step_up_age=None),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key="approve-001",
        csrf_token=CSRF,
        now=NOW,
    )
    assert approved.resulting_state is RegistrationState.ENROLLED
    assert evidence.list_records()[0].action is FleetAdminAction.APPROVE


def test_security_admin_action_requires_fresh_step_up_and_confirmation() -> None:
    _store, enrollment, _evidence, admin = runtime()
    item = enroll(enrollment, record())
    actor = principal(FleetRole.SECURITY_ADMIN)

    with pytest.raises(FleetAdminStepUpRequired):
        admin.mutate(
            principal=actor,
            security_session=session(step_up_age=timedelta(minutes=11)),
            action=FleetAdminAction.QUARANTINE,
            device_id=item.device_id,
            idempotency_key="quarantine-001",
            csrf_token=CSRF,
            confirmation=f"QUARANTINE:{item.device_id}",
            now=NOW,
        )

    with pytest.raises(FleetAdminConfirmationError):
        admin.mutate(
            principal=actor,
            security_session=session(),
            action=FleetAdminAction.QUARANTINE,
            device_id=item.device_id,
            idempotency_key="quarantine-002",
            csrf_token=CSRF,
            confirmation="wrong",
            now=NOW,
        )


def test_csrf_scope_and_idempotency_fail_closed() -> None:
    _store, enrollment, evidence, admin = runtime()
    item = submit_pending(enrollment, record())
    actor = principal(FleetRole.OPERATOR)

    with pytest.raises(FleetAdminForbidden):
        admin.mutate(
            principal=actor,
            security_session=session(),
            action=FleetAdminAction.APPROVE,
            device_id=item.device_id,
            idempotency_key="approve-csrf",
            csrf_token="attacker",
            now=NOW,
        )

    with pytest.raises(FleetAdminNotFound):
        admin.mutate(
            principal=principal(
                FleetRole.OPERATOR,
                scope=ScopeBinding(tenant_id="tenant-b", workspace_id="workspace-b"),
            ),
            security_session=session(),
            action=FleetAdminAction.APPROVE,
            device_id=item.device_id,
            idempotency_key="cross-scope",
            csrf_token=CSRF,
            now=NOW,
        )

    first = admin.mutate(
        principal=actor,
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key="same-key",
        csrf_token=CSRF,
        now=NOW,
    )
    replay = admin.mutate(
        principal=actor,
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key="same-key",
        csrf_token=CSRF,
        now=NOW + timedelta(seconds=1),
    )
    assert replay.idempotent_replay is True
    assert replay.administrative_evidence_id == first.administrative_evidence_id
    assert len(evidence.list_records()) == 1

    with pytest.raises(FleetAdminIdempotencyConflict):
        admin.mutate(
            principal=actor,
            security_session=session(),
            action=FleetAdminAction.RESTORE,
            device_id=item.device_id,
            idempotency_key="same-key",
            csrf_token=CSRF,
            now=NOW + timedelta(seconds=2),
        )


def test_rotation_replay_is_idempotent_after_current_enrollment_changes() -> None:
    store, enrollment, evidence, admin = runtime()
    current = enroll(enrollment, record())
    replacement = record(
        enrollment_id="enr_002",
        fingerprint=B,
        thumbprint=E,
        device_id=current.device_id,
        supersedes=current.enrollment_id,
    )
    submit_pending(enrollment, replacement)
    actor = principal(FleetRole.SECURITY_ADMIN)
    confirmation = f"BEGIN_ROTATION:{current.device_id}"

    first = admin.mutate(
        principal=actor,
        security_session=session(),
        action=FleetAdminAction.BEGIN_ROTATION,
        device_id=current.device_id,
        idempotency_key="rotate-001",
        csrf_token=CSRF,
        confirmation=confirmation,
        replacement_enrollment_id=replacement.enrollment_id,
        overlap_expires_at_utc=NOW + timedelta(minutes=5),
        now=NOW,
    )
    assert store.get_current_enrollment_id(current.device_id) == replacement.enrollment_id

    replay = admin.mutate(
        principal=actor,
        security_session=session(),
        action=FleetAdminAction.BEGIN_ROTATION,
        device_id=current.device_id,
        idempotency_key="rotate-001",
        csrf_token=CSRF,
        confirmation=confirmation,
        replacement_enrollment_id=replacement.enrollment_id,
        overlap_expires_at_utc=NOW + timedelta(minutes=5),
        now=NOW + timedelta(seconds=1),
    )
    assert replay.idempotent_replay is True
    assert replay.administrative_evidence_id == first.administrative_evidence_id
    assert len(evidence.list_records()) == 1


def test_administrative_evidence_is_hashed_bounded_and_scope_filtered() -> None:
    _store, enrollment, evidence, admin = runtime()
    item = submit_pending(enrollment, record())
    raw_key = "super-secret-looking-idempotency-value"
    admin.mutate(
        principal=principal(FleetRole.OPERATOR),
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key=raw_key,
        csrf_token=CSRF,
        now=NOW,
    )

    exported = admin.audit_export(principal(FleetRole.VIEWER))
    assert len(exported) == 1
    serialized = exported[0].model_dump_json()
    assert raw_key not in serialized
    assert CSRF not in serialized
    assert "bearer" not in serialized.lower()
    assert len(exported[0].idempotency_key_sha256) == 64

    other = principal(
        FleetRole.VIEWER,
        scope=ScopeBinding(tenant_id="tenant-b", workspace_id="workspace-b"),
    )
    assert admin.audit_export(other) == ()
    assert evidence.list_records() == list(exported)


def _client(
    *,
    role: FleetRole,
    step_up_age: timedelta | None = timedelta(minutes=1),
) -> tuple[TestClient, DeviceEnrollmentService, DeviceEnrollmentRecord]:
    store, enrollment, _evidence, admin = runtime()
    item = submit_pending(enrollment, record())
    portal = FleetPortalService(enrollment_reader=store, presence_reader=EmptyPresence())
    actor = principal(role)
    security = session(step_up_age=step_up_age)
    app = FastAPI()
    app.include_router(
        build_fleet_portal_router(
            service=portal,
            principal_resolver=lambda request: actor,
            admin_service=admin,
            security_session_resolver=lambda request: security,
        )
    )
    return TestClient(app), enrollment, item


def test_bff_rejects_mass_assignment_and_requires_csrf_idempotency() -> None:
    client, _enrollment, item = _client(role=FleetRole.OPERATOR)
    path = f"/fleet/bff/v1/devices/{item.device_id}/actions/{FleetAdminAction.APPROVE.value}"

    mass_assignment = client.post(
        path,
        headers={"X-CSRF-Token": CSRF, "Idempotency-Key": "api-001"},
        json={"tenant_id": "attacker", "roles": ["Fleet.SecurityAdmin"]},
    )
    assert mass_assignment.status_code == 422
    assert mass_assignment.json()["detail"]["code"] == "ETS_FLEET_MUTATION_INVALID"

    missing_csrf = client.post(
        path,
        headers={"Idempotency-Key": "api-002"},
        json={},
    )
    assert missing_csrf.status_code == 403

    missing_key = client.post(
        path,
        headers={"X-CSRF-Token": CSRF},
        json={},
    )
    assert missing_key.status_code == 422


def test_bff_security_admin_step_up_and_sanitized_errors() -> None:
    client, enrollment, item = _client(
        role=FleetRole.SECURITY_ADMIN,
        step_up_age=timedelta(minutes=20),
    )
    enrollment.activate(item.enrollment_id, now=NOW)
    action = FleetAdminAction.REVOKE
    path = f"/fleet/bff/v1/devices/{item.device_id}/actions/{action.value}"
    response = client.post(
        path,
        headers={"X-CSRF-Token": CSRF, "Idempotency-Key": "api-revoke"},
        json={"confirmation": f"REVOKE:{item.device_id}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ETS_FLEET_STEP_UP_REQUIRED"
    assert response.headers["cache-control"].startswith("no-store")


def test_bff_rate_limit_hook_runs_server_side() -> None:
    store, enrollment, _evidence, admin = runtime()
    item = submit_pending(enrollment, record())
    actor = principal(FleetRole.OPERATOR)
    security = session()
    portal = FleetPortalService(enrollment_reader=store, presence_reader=EmptyPresence())
    app = FastAPI()
    app.include_router(
        build_fleet_portal_router(
            service=portal,
            principal_resolver=lambda request: actor,
            admin_service=admin,
            security_session_resolver=lambda request: security,
            mutation_rate_limiter=lambda resolved, action: False,
        )
    )
    response = TestClient(app).post(
        f"/fleet/bff/v1/devices/{item.device_id}/actions/{FleetAdminAction.APPROVE.value}",
        headers={"X-CSRF-Token": CSRF, "Idempotency-Key": "rate-limit"},
        json={},
    )
    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "ETS_FLEET_MUTATION_RATE_LIMITED"
