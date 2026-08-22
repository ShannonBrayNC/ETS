from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.fleet import (
    AttestationClass,
    AuthMethod,
    AuthorizationReason,
    DeviceEnrollmentRecord,
    DeviceEnrollmentService,
    DeviceProfile,
    EnrollmentErrorCode,
    EnrollmentValidationError,
    InMemoryEnrollmentStore,
    KeyCustody,
    ProductType,
    ProvisioningBackend,
    RegistrationState,
    ScopeBinding,
    derive_device_id,
)

NOW = datetime(2026, 8, 21, 16, 30, tzinfo=UTC)
A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64


class AcceptIdentity:
    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None:
        del record, now


class RejectIdentity:
    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None:
        del record, now
        raise ValueError("untrusted identity")


def service(*, reject: bool = False) -> DeviceEnrollmentService:
    validator = RejectIdentity() if reject else AcceptIdentity()
    return DeviceEnrollmentService(InMemoryEnrollmentStore(), validator)


def record(
    *,
    enrollment_id: str = "enr_virtual_001",
    fingerprint: str = A,
    thumbprint: str = D,
    device_id: str | None = None,
    scope: ScopeBinding | None = None,
    supersedes: str | None = None,
    expires_at: datetime | None = None,
) -> DeviceEnrollmentRecord:
    binding = scope or ScopeBinding(
        tenant_id="tenant-demo",
        workspace_id="workspace-demo",
    )
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
        certificate_not_after_utc=expires_at or NOW + timedelta(days=30),
        supersedes_enrollment_id=supersedes,
        created_at_utc=NOW,
    )


def enroll(
    runtime: DeviceEnrollmentService,
    item: DeviceEnrollmentRecord,
) -> DeviceEnrollmentRecord:
    runtime.submit(item, authoritative_scope=item.scope_binding, now=NOW)
    return runtime.activate(item.enrollment_id, now=NOW)


def authorize(
    runtime: DeviceEnrollmentService,
    item: DeviceEnrollmentRecord,
    *,
    fingerprint: str | None = None,
    tenant_id: str = "tenant-demo",
    now: datetime = NOW,
) -> AuthorizationReason:
    decision = runtime.authorize(
        device_id=item.device_id,
        public_key_fingerprint_sha256=fingerprint or item.public_key_fingerprint_sha256,
        tenant_id=tenant_id,
        workspace_id="workspace-demo",
        now=now,
    )
    return decision.reason


def test_authorization_is_scope_and_lifecycle_aware() -> None:
    runtime = service()
    item = enroll(runtime, record())
    assert authorize(runtime, item) is AuthorizationReason.AUTHORIZED
    assert authorize(runtime, item, tenant_id="attacker") is AuthorizationReason.SCOPE_MISMATCH
    runtime.transition(item.enrollment_id, RegistrationState.QUARANTINED, now=NOW)
    assert authorize(runtime, item) is AuthorizationReason.QUARANTINED


def test_unknown_device_and_wrong_credential_fail_closed() -> None:
    runtime = service()
    item = enroll(runtime, record())
    unknown = runtime.authorize(
        device_id="ets-edge:unknown-device",
        public_key_fingerprint_sha256=B,
        tenant_id="tenant-demo",
        workspace_id="workspace-demo",
        now=NOW,
    )
    assert unknown.reason is AuthorizationReason.UNKNOWN_DEVICE
    assert authorize(runtime, item, fingerprint=B) is AuthorizationReason.CREDENTIAL_MISMATCH


def test_duplicate_device_and_public_identity_conflicts_are_rejected() -> None:
    runtime = service()
    original = enroll(runtime, record())
    duplicate = record(
        enrollment_id="enr_virtual_002",
        fingerprint=B,
        thumbprint=E,
        device_id=original.device_id,
    )
    with pytest.raises(EnrollmentValidationError) as exc:
        runtime.submit(duplicate, authoritative_scope=duplicate.scope_binding, now=NOW)
    assert exc.value.code is EnrollmentErrorCode.DEVICE_IDENTITY_CONFLICT

    runtime2 = service()
    first = record()
    runtime2.submit(first, authoritative_scope=first.scope_binding, now=NOW)
    reused = record(
        enrollment_id="enr_virtual_003",
        device_id="ets-edge:different-device",
    )
    with pytest.raises(EnrollmentValidationError) as reused_exc:
        runtime2.submit(reused, authoritative_scope=reused.scope_binding, now=NOW)
    assert reused_exc.value.code is EnrollmentErrorCode.PUBLIC_IDENTITY_CONFLICT


def test_replay_and_scope_escalation_are_rejected_before_activation() -> None:
    runtime = service()
    item = record()
    runtime.submit(item, authoritative_scope=item.scope_binding, now=NOW)
    with pytest.raises(EnrollmentValidationError) as replay:
        runtime.submit(item, authoritative_scope=item.scope_binding, now=NOW)
    assert replay.value.code is EnrollmentErrorCode.REPLAYED_ENROLLMENT_ID

    runtime2 = service()
    with pytest.raises(EnrollmentValidationError) as scope:
        runtime2.submit(
            item,
            authoritative_scope=ScopeBinding(
                tenant_id="different-tenant",
                workspace_id="workspace-demo",
            ),
            now=NOW,
        )
    assert scope.value.code is EnrollmentErrorCode.SERVER_SCOPE_MISMATCH


def test_expired_x509_cannot_activate_or_remain_authorized() -> None:
    runtime = service()
    expired = record(expires_at=NOW - timedelta(seconds=1))
    runtime.submit(expired, authoritative_scope=expired.scope_binding, now=NOW)
    with pytest.raises(EnrollmentValidationError) as exc:
        runtime.activate(expired.enrollment_id, now=NOW)
    assert exc.value.code is EnrollmentErrorCode.CERTIFICATE_EXPIRED

    runtime2 = service()
    active = enroll(runtime2, record(expires_at=NOW + timedelta(seconds=1)))
    reason = authorize(runtime2, active, now=NOW + timedelta(seconds=2))
    assert reason is AuthorizationReason.CREDENTIAL_EXPIRED


def test_rotation_has_bounded_overlap_and_superseded_key_fails_closed() -> None:
    runtime = service()
    original = enroll(runtime, record())
    replacement = record(
        enrollment_id="enr_virtual_002",
        fingerprint=B,
        thumbprint=E,
        device_id=original.device_id,
        supersedes=original.enrollment_id,
    )
    runtime.submit(replacement, authoritative_scope=replacement.scope_binding, now=NOW)
    runtime.begin_rotation(
        replacement.enrollment_id,
        overlap_expires_at_utc=NOW + timedelta(minutes=10),
        now=NOW,
    )
    assert authorize(
        runtime,
        original,
        fingerprint=A,
        now=NOW + timedelta(minutes=5),
    ) is AuthorizationReason.AUTHORIZED
    assert authorize(
        runtime,
        original,
        fingerprint=A,
        now=NOW + timedelta(minutes=11),
    ) is AuthorizationReason.SUPERSEDED_CREDENTIAL
    assert authorize(
        runtime,
        original,
        fingerprint=B,
        now=NOW + timedelta(minutes=11),
    ) is AuthorizationReason.AUTHORIZED


def test_rotation_race_and_scope_drift_fail_closed() -> None:
    runtime = service()
    original = enroll(runtime, record())
    replacement = record(
        enrollment_id="enr_virtual_002",
        fingerprint=B,
        thumbprint=E,
        device_id=original.device_id,
        supersedes=original.enrollment_id,
    )
    runtime.submit(replacement, authoritative_scope=replacement.scope_binding, now=NOW)
    runtime.begin_rotation(
        replacement.enrollment_id,
        overlap_expires_at_utc=NOW + timedelta(minutes=10),
        now=NOW,
    )
    third = record(
        enrollment_id="enr_virtual_003",
        fingerprint=C,
        thumbprint="f" * 64,
        device_id=original.device_id,
        supersedes=replacement.enrollment_id,
    )
    with pytest.raises(EnrollmentValidationError) as race:
        runtime.submit(third, authoritative_scope=third.scope_binding, now=NOW)
    assert race.value.code is EnrollmentErrorCode.ROTATION_IN_PROGRESS

    runtime2 = service()
    original2 = enroll(runtime2, record())
    drifted = record(
        enrollment_id="enr_virtual_002",
        fingerprint=B,
        thumbprint=E,
        device_id=original2.device_id,
        supersedes=original2.enrollment_id,
        scope=ScopeBinding(tenant_id="other", workspace_id="workspace-demo"),
    )
    with pytest.raises(EnrollmentValidationError) as drift:
        runtime2.submit(drifted, authoritative_scope=drifted.scope_binding, now=NOW)
    assert drift.value.code is EnrollmentErrorCode.ROTATION_REPLACEMENT_INVALID


def test_rotation_completion_revokes_old_credential() -> None:
    runtime = service()
    original = enroll(runtime, record())
    replacement = record(
        enrollment_id="enr_virtual_002",
        fingerprint=B,
        thumbprint=E,
        device_id=original.device_id,
        supersedes=original.enrollment_id,
    )
    runtime.submit(replacement, authoritative_scope=replacement.scope_binding, now=NOW)
    runtime.begin_rotation(
        replacement.enrollment_id,
        overlap_expires_at_utc=NOW + timedelta(minutes=10),
        now=NOW,
    )
    revoked = runtime.complete_rotation(original.device_id, now=NOW + timedelta(minutes=1))
    assert revoked.registration_state is RegistrationState.REVOKED
    assert authorize(runtime, original, fingerprint=A) is AuthorizationReason.CREDENTIAL_MISMATCH


def test_invalid_lifecycle_and_revoked_device_fail_closed() -> None:
    runtime = service()
    item = enroll(runtime, record())
    with pytest.raises(EnrollmentValidationError) as invalid:
        runtime.transition(item.enrollment_id, RegistrationState.DECOMMISSIONED, now=NOW)
    assert invalid.value.code is EnrollmentErrorCode.INVALID_LIFECYCLE_TRANSITION
    runtime.transition(item.enrollment_id, RegistrationState.REVOKED, now=NOW)
    assert authorize(runtime, item) is AuthorizationReason.REVOKED


def test_external_identity_validation_failure_is_fail_closed() -> None:
    runtime = service(reject=True)
    item = record()
    with pytest.raises(EnrollmentValidationError) as exc:
        runtime.submit(item, authoritative_scope=item.scope_binding, now=NOW)
    assert exc.value.code is EnrollmentErrorCode.IDENTITY_VALIDATION_FAILED
