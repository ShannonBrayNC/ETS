from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from ets.fleet import (
    AttestationClass,
    AuthMethod,
    DeviceEnrollmentRecord,
    DeviceEnrollmentService,
    DeviceProfile,
    KeyCustody,
    ProductType,
    ProvisioningBackend,
    RegistrationState,
    ScopeBinding,
    derive_device_id,
)
from ets.fleet.entra_session import FleetSessionStanding
from ets.fleet.portal import FleetPrincipal, FleetRole
from ets.fleet.portal_admin import FleetAdminAction, FleetSecuritySession
from ets.fleet.portal_admin_durable import (
    DurableFleetPortalAdminService,
    FleetAdminMutationPending,
)
from ets.fleet.postgres import (
    PostgresConnection,
    PostgresEnrollmentStore,
    PostgresFleetAdminMutationJournal,
    apply_fleet_postgres_migrations,
)
from ets.fleet.postgres_auth import (
    PostgresFleetAuthorizationState,
    apply_fleet_postgres_authorization_migrations,
)

NOW = datetime(2026, 8, 22, 7, 0, tzinfo=UTC)
FINGERPRINT = "a" * 64
THUMBPRINT = "d" * 64
CSRF = "csrf-" + "x" * 40
RAW_IDEMPOTENCY_KEY = "c3b-restart-idempotency-secret"


class AcceptIdentity:
    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None:
        del record, now


def _factory() -> PostgresConnection:
    dsn = os.getenv("ETS_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("ETS_TEST_POSTGRES_DSN is not configured")
    import psycopg
    from psycopg.rows import dict_row

    return cast(PostgresConnection, psycopg.connect(dsn, row_factory=dict_row))


def _reset_database() -> None:
    connection = _factory()
    try:
        connection.execute(
            """
            DROP TABLE IF EXISTS fleet_session_standing,
                                 fleet_principal_scopes,
                                 fleet_admin_evidence,
                                 fleet_admin_mutations,
                                 fleet_rotations,
                                 fleet_public_identity_owners,
                                 fleet_current_enrollments,
                                 fleet_enrollments,
                                 ets_fleet_schema
            CASCADE
            """
        )
        connection.commit()
    finally:
        connection.close()


def _record() -> DeviceEnrollmentRecord:
    return DeviceEnrollmentRecord(
        enrollment_id="enr_c3b_0001",
        device_id=derive_device_id(ProductType.EDGE, FINGERPRINT),
        product_type=ProductType.EDGE,
        profile=DeviceProfile.VIRTUAL_DEMO,
        auth_method=AuthMethod.X509,
        public_key_fingerprint_sha256=FINGERPRINT,
        certificate_thumbprint_sha256=THUMBPRINT,
        attestation_class=AttestationClass.SOFTWARE_DEMO,
        key_custody=KeyCustody.SOFTWARE_DEMO,
        hardware_attested=False,
        registration_state=RegistrationState.PENDING,
        scope_binding=ScopeBinding(
            tenant_id="ets-tenant",
            workspace_id="workspace-a",
        ),
        provisioning_backend=ProvisioningBackend.AZURE_IOT_DPS_V1,
        certificate_not_after_utc=NOW + timedelta(days=30),
        created_at_utc=NOW,
    )


def _principal() -> FleetPrincipal:
    return FleetPrincipal(
        subject="operator-object-id",
        roles=(FleetRole.OPERATOR,),
        scope_bindings=(
            ScopeBinding(tenant_id="ets-tenant", workspace_id="workspace-a"),
        ),
    )


def _session() -> FleetSecuritySession:
    return FleetSecuritySession(
        session_id="session-1234567890abcdef",
        csrf_token=CSRF,
        authenticated_at_utc=NOW - timedelta(minutes=30),
    )


def test_shared_postgres_state_and_durable_replay_survive_service_recreation() -> None:
    _reset_database()
    apply_fleet_postgres_migrations(_factory)
    apply_fleet_postgres_migrations(_factory)
    apply_fleet_postgres_authorization_migrations(_factory)

    store_a = PostgresEnrollmentStore(_factory)
    service_a = DeviceEnrollmentService(store_a, AcceptIdentity())
    item = _record()
    service_a.submit(item, authoritative_scope=item.scope_binding, now=NOW)

    store_b = PostgresEnrollmentStore(_factory)
    assert store_b.get_enrollment(item.enrollment_id) == item
    assert store_b.get_current_enrollment_id(item.device_id) == item.enrollment_id

    journal_a = PostgresFleetAdminMutationJournal(_factory)
    admin_a = DurableFleetPortalAdminService(
        enrollment_service=service_a,
        enrollment_store=store_a,
        journal=journal_a,
    )
    first = admin_a.mutate(
        principal=_principal(),
        security_session=_session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key=RAW_IDEMPOTENCY_KEY,
        csrf_token=CSRF,
        now=NOW,
    )
    assert first.resulting_state is RegistrationState.ENROLLED
    assert first.idempotent_replay is False

    service_b = DeviceEnrollmentService(store_b, AcceptIdentity())
    journal_b = PostgresFleetAdminMutationJournal(_factory)
    admin_b = DurableFleetPortalAdminService(
        enrollment_service=service_b,
        enrollment_store=store_b,
        journal=journal_b,
    )
    replay = admin_b.mutate(
        principal=_principal(),
        security_session=_session(),
        action=FleetAdminAction.APPROVE,
        device_id=item.device_id,
        idempotency_key=RAW_IDEMPOTENCY_KEY,
        csrf_token=CSRF,
        now=NOW + timedelta(seconds=2),
    )
    assert replay.idempotent_replay is True
    assert replay.administrative_evidence_id == first.administrative_evidence_id

    connection = _factory()
    try:
        row = connection.execute(
            """
            SELECT idempotency_key_sha256
            FROM fleet_admin_mutations
            WHERE actor_subject = %s
            """,
            (_principal().subject,),
        ).fetchone()
        assert row is not None
        assert row["idempotency_key_sha256"] != RAW_IDEMPOTENCY_KEY
        serialized = str(
            connection.execute(
                "SELECT row_to_json(m)::text AS value FROM fleet_admin_mutations m LIMIT 1"
            ).fetchone()
        )
        assert RAW_IDEMPOTENCY_KEY not in serialized
    finally:
        connection.close()


def test_pending_reservation_is_shared_and_requires_reconciliation() -> None:
    _reset_database()
    apply_fleet_postgres_migrations(_factory)
    journal_a = PostgresFleetAdminMutationJournal(_factory)
    journal_b = PostgresFleetAdminMutationJournal(_factory)
    key_hash = "1" * 64
    request_hash = "2" * 64

    assert (
        journal_a.reserve(
            actor_subject="actor",
            idempotency_key_sha256=key_hash,
            request_fingerprint_sha256=request_hash,
            now=NOW,
        )
        is None
    )
    with pytest.raises(FleetAdminMutationPending):
        journal_b.reserve(
            actor_subject="actor",
            idempotency_key_sha256=key_hash,
            request_fingerprint_sha256=request_hash,
            now=NOW + timedelta(seconds=1),
        )


def test_server_owned_scope_and_session_standing_are_shared_and_hash_session_id() -> None:
    _reset_database()
    apply_fleet_postgres_migrations(_factory)
    apply_fleet_postgres_authorization_migrations(_factory)
    state_a = PostgresFleetAuthorizationState(_factory)
    state_b = PostgresFleetAuthorizationState(_factory)
    scope = ScopeBinding(tenant_id="ets-tenant", workspace_id="workspace-a")
    standing = FleetSessionStanding(
        active=True,
        generation=3,
        roles=(FleetRole.SECURITY_ADMIN,),
        not_before_utc=NOW - timedelta(minutes=5),
        step_up_not_before_utc=NOW - timedelta(minutes=2),
    )
    raw_session_id = "browser-session-1234567890abcdef"

    state_a.grant_scope(
        subject="object-123",
        entra_tenant_id="entra-tenant",
        scope=scope,
        now=NOW,
    )
    state_a.upsert_session_standing(
        subject="object-123",
        entra_tenant_id="entra-tenant",
        session_id=raw_session_id,
        standing=standing,
        now=NOW,
    )

    assert state_b.resolve_scopes(
        subject="object-123",
        entra_tenant_id="entra-tenant",
    ) == (scope,)
    assert state_b.resolve_standing(
        subject="object-123",
        entra_tenant_id="entra-tenant",
        session_id=raw_session_id,
    ) == standing

    connection = _factory()
    try:
        row = connection.execute(
            "SELECT session_id_sha256 FROM fleet_session_standing LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row["session_id_sha256"] != raw_session_id
        assert raw_session_id not in str(row)
    finally:
        connection.close()
