from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

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
from ets.fleet.portal import FleetPrincipal, FleetRole
from ets.fleet.portal_admin import (
    FleetAdminAction,
    FleetAdminIdempotencyConflict,
    FleetSecuritySession,
    _request_fingerprint,
)
from ets.fleet.portal_admin_durable import (
    DurableFleetPortalAdminService,
    FleetAdminDurabilityError,
    FleetAdminMutationPending,
    SQLiteFleetAdminMutationJournal,
)

NOW = datetime(2026, 8, 22, 5, 15, tzinfo=UTC)
A = "a" * 64
D = "d" * 64
CSRF = "csrf-" + "x" * 40


class AcceptIdentity:
    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None:
        del record, now


def record() -> DeviceEnrollmentRecord:
    fingerprint = A
    return DeviceEnrollmentRecord(
        enrollment_id="enr_0001",
        device_id=derive_device_id(ProductType.EDGE, fingerprint),
        product_type=ProductType.EDGE,
        profile=DeviceProfile.VIRTUAL_DEMO,
        auth_method=AuthMethod.X509,
        public_key_fingerprint_sha256=fingerprint,
        certificate_thumbprint_sha256=D,
        attestation_class=AttestationClass.SOFTWARE_DEMO,
        key_custody=KeyCustody.SOFTWARE_DEMO,
        hardware_attested=False,
        registration_state=RegistrationState.PENDING,
        scope_binding=ScopeBinding(tenant_id="tenant-a", workspace_id="workspace-a"),
        provisioning_backend=ProvisioningBackend.AZURE_IOT_DPS_V1,
        certificate_not_after_utc=NOW + timedelta(days=30),
        created_at_utc=NOW,
    )


def principal(
    role: FleetRole = FleetRole.OPERATOR,
    *,
    scope: ScopeBinding | None = None,
) -> FleetPrincipal:
    return FleetPrincipal(
        subject=f"subject-{role.value}",
        roles=(role,),
        scope_bindings=(scope or ScopeBinding(tenant_id="tenant-a", workspace_id="workspace-a"),),
    )


def session() -> FleetSecuritySession:
    return FleetSecuritySession(
        session_id="session-1234567890abcdef",
        csrf_token=CSRF,
        authenticated_at_utc=NOW - timedelta(hours=1),
        step_up_at_utc=NOW - timedelta(minutes=1),
    )


def runtime(
    db_path: object,
    *,
    store: InMemoryEnrollmentStore | None = None,
) -> tuple[
    InMemoryEnrollmentStore,
    DeviceEnrollmentService,
    SQLiteFleetAdminMutationJournal,
    DurableFleetPortalAdminService,
]:
    enrollment_store = store or InMemoryEnrollmentStore()
    enrollment = DeviceEnrollmentService(enrollment_store, AcceptIdentity())
    journal = SQLiteFleetAdminMutationJournal(db_path)  # type: ignore[arg-type]
    admin = DurableFleetPortalAdminService(
        enrollment_service=enrollment,
        enrollment_store=enrollment_store,
        journal=journal,
    )
    return enrollment_store, enrollment, journal, admin


def submit_pending(
    enrollment: DeviceEnrollmentService,
    item: DeviceEnrollmentRecord,
) -> DeviceEnrollmentRecord:
    return enrollment.submit(item, authoritative_scope=item.scope_binding, now=NOW)


def test_committed_replay_survives_service_and_journal_restart(tmp_path: object) -> None:
    db_path = tmp_path / "fleet-admin.db"  # type: ignore[operator]
    store, enrollment, journal, admin = runtime(db_path)
    item = submit_pending(enrollment, record())
    actor = principal()

    first = admin.mutate(
        principal=actor,
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key="restart-safe-key",
        csrf_token=CSRF,
        now=NOW,
    )
    assert first.resulting_state is RegistrationState.ENROLLED
    assert journal.count_pending() == 0
    journal.close()

    _store2, _enrollment2, journal2, admin2 = runtime(db_path, store=store)
    replay = admin2.mutate(
        principal=actor,
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key="restart-safe-key",
        csrf_token=CSRF,
        now=NOW + timedelta(minutes=1),
    )
    assert replay.idempotent_replay is True
    assert replay.administrative_evidence_id == first.administrative_evidence_id
    assert len(journal2.list_records()) == 1
    journal2.close()


def test_conflicting_reuse_survives_restart_and_fails_closed(tmp_path: object) -> None:
    db_path = tmp_path / "fleet-admin.db"  # type: ignore[operator]
    store, enrollment, journal, admin = runtime(db_path)
    item = submit_pending(enrollment, record())
    actor = principal()
    admin.mutate(
        principal=actor,
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key="same-key",
        csrf_token=CSRF,
        now=NOW,
    )
    journal.close()

    _store2, _enrollment2, journal2, admin2 = runtime(db_path, store=store)
    with pytest.raises(FleetAdminIdempotencyConflict):
        admin2.mutate(
            principal=actor,
            security_session=session(),
            action=FleetAdminAction.RESTORE,
            device_id=item.device_id,
            idempotency_key="same-key",
            csrf_token=CSRF,
            now=NOW + timedelta(minutes=1),
        )
    journal2.close()


def test_pending_reservation_survives_restart_and_blocks_automatic_replay(
    tmp_path: object,
) -> None:
    db_path = tmp_path / "fleet-admin.db"  # type: ignore[operator]
    _store, _enrollment, journal, _admin = runtime(db_path)
    actor = principal()
    item = record()
    key_hash = hashlib.sha256(b"interrupted-key").hexdigest()
    fingerprint = _request_fingerprint(
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        confirmation=None,
        replacement_enrollment_id=None,
        overlap_expires_at_utc=None,
    )
    assert (
        journal.reserve(
            actor_subject=actor.subject,
            idempotency_key_sha256=key_hash,
            request_fingerprint_sha256=fingerprint,
            now=NOW,
        )
        is None
    )
    assert journal.count_pending() == 1
    journal.close()

    journal2 = SQLiteFleetAdminMutationJournal(db_path)
    with pytest.raises(FleetAdminMutationPending):
        journal2.reserve(
            actor_subject=actor.subject,
            idempotency_key_sha256=key_hash,
            request_fingerprint_sha256=fingerprint,
            now=NOW + timedelta(minutes=1),
        )
    assert journal2.count_pending() == 1
    journal2.close()


def test_evidence_survives_restart_and_remains_scope_filtered(tmp_path: object) -> None:
    db_path = tmp_path / "fleet-admin.db"  # type: ignore[operator]
    store, enrollment, journal, admin = runtime(db_path)
    item = submit_pending(enrollment, record())
    admin.mutate(
        principal=principal(),
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key="audit-key",
        csrf_token=CSRF,
        now=NOW,
    )
    journal.close()

    _store2, _enrollment2, journal2, admin2 = runtime(db_path, store=store)
    exported = admin2.audit_export(principal(FleetRole.VIEWER))
    assert len(exported) == 1
    other_scope = ScopeBinding(tenant_id="tenant-b", workspace_id="workspace-b")
    assert admin2.audit_export(principal(FleetRole.VIEWER, scope=other_scope)) == ()
    journal2.close()


def test_raw_idempotency_key_is_never_persisted(tmp_path: object) -> None:
    db_path = tmp_path / "fleet-admin.db"  # type: ignore[operator]
    _store, enrollment, journal, admin = runtime(db_path)
    item = submit_pending(enrollment, record())
    raw_key = "this-raw-idempotency-value-must-never-be-retained"
    admin.mutate(
        principal=principal(),
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key=raw_key,
        csrf_token=CSRF,
        now=NOW,
    )
    journal.close()

    assert raw_key.encode("utf-8") not in db_path.read_bytes()
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT idempotency_key_sha256 FROM fleet_admin_mutations"
        ).fetchone()
    assert row is not None
    assert row[0] == hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def test_corrupt_retained_result_fails_validation_instead_of_replaying(tmp_path: object) -> None:
    db_path = tmp_path / "fleet-admin.db"  # type: ignore[operator]
    store, enrollment, journal, admin = runtime(db_path)
    item = submit_pending(enrollment, record())
    actor = principal()
    admin.mutate(
        principal=actor,
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key="corrupt-result",
        csrf_token=CSRF,
        now=NOW,
    )
    journal.close()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE fleet_admin_mutations SET result_json = '{}' WHERE status = 'committed'"
        )
        connection.commit()

    _store2, _enrollment2, journal2, admin2 = runtime(db_path, store=store)
    with pytest.raises(FleetAdminDurabilityError):
        admin2.mutate(
            principal=actor,
            security_session=session(),
            action=FleetAdminAction.APPROVE,
            device_id=item.device_id,
            idempotency_key="corrupt-result",
            csrf_token=CSRF,
            now=NOW + timedelta(minutes=1),
        )
    journal2.close()


def test_corrupt_retained_evidence_fails_audit_validation(tmp_path: object) -> None:
    db_path = tmp_path / "fleet-admin.db"  # type: ignore[operator]
    store, enrollment, journal, admin = runtime(db_path)
    item = submit_pending(enrollment, record())
    admin.mutate(
        principal=principal(),
        security_session=session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key="corrupt-evidence",
        csrf_token=CSRF,
        now=NOW,
    )
    journal.close()
    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE fleet_admin_evidence SET evidence_json = '{}'")
        connection.commit()

    _store2, _enrollment2, journal2, admin2 = runtime(db_path, store=store)
    with pytest.raises(FleetAdminDurabilityError):
        admin2.audit_export(principal(FleetRole.VIEWER))
    journal2.close()
