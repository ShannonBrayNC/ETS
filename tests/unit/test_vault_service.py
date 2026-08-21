from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.vault import (
    InMemoryVaultBackend,
    InMemoryVaultCatalog,
    VaultAuthorization,
    VaultJournalEntry,
    VaultPolicy,
    VaultPolicyError,
    VaultProductionReadinessError,
    VaultService,
)

FIXED_NOW = datetime(2026, 8, 21, 6, 30, tzinfo=UTC)


def _service(
    *,
    now: datetime = FIXED_NOW,
    policy: VaultPolicy | None = None,
) -> tuple[VaultService, InMemoryVaultBackend, InMemoryVaultCatalog]:
    backend = InMemoryVaultBackend()
    catalog = InMemoryVaultCatalog()
    service = VaultService(
        backend,
        catalog,
        policy=policy,
        clock=lambda: now,
        nonce_factory=lambda: "test-nonce",
    )
    return service, backend, catalog


def _preserve(service: VaultService, *, hold: bool = False) -> str:
    receipt = service.preserve(
        b"vault evidence payload",
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        media_type="application/octet-stream",
        retain_until_utc=FIXED_NOW + timedelta(days=30),
        actor_id="custodian-a",
        source_event_id="event-123",
        legal_holds=("case-42",) if hold else (),
    )
    return receipt.record.object_id


def _authorization() -> VaultAuthorization:
    return VaultAuthorization(
        primary_actor_id="records-admin-a",
        secondary_actor_id="records-admin-b",
        reason="approved records disposition",
    )


def test_preserve_and_verify_integrity() -> None:
    service, backend, _ = _service()
    object_id = _preserve(service)

    result = service.verify_integrity(object_id)

    assert result.valid is True
    assert result.actual_hash == result.expected_hash
    assert result.actual_byte_size == result.expected_byte_size
    assert backend.exists(object_id) is True


def test_preserve_rejects_expected_hash_mismatch() -> None:
    service, backend, _ = _service()

    with pytest.raises(VaultPolicyError, match="does not match"):
        service.preserve(
            b"payload",
            tenant_id="tenant-a",
            workspace_id="workspace-a",
            media_type="application/octet-stream",
            retain_until_utc=FIXED_NOW + timedelta(days=1),
            actor_id="custodian-a",
            expected_sha256="0" * 64,
        )

    assert backend.exists("vault:" + "0" * 64) is False


def test_preserve_rejects_expired_retention() -> None:
    service, _, _ = _service()

    with pytest.raises(VaultPolicyError, match="must be in the future"):
        service.preserve(
            b"payload",
            tenant_id="tenant-a",
            workspace_id="workspace-a",
            media_type="application/octet-stream",
            retain_until_utc=FIXED_NOW,
            actor_id="custodian-a",
        )


def test_retention_can_extend_but_not_shorten() -> None:
    service, _, _ = _service()
    object_id = _preserve(service)

    receipt = service.extend_retention(
        object_id,
        retain_until_utc=FIXED_NOW + timedelta(days=60),
        actor_id="records-admin-a",
    )

    assert receipt.record.retention.retain_until_utc == FIXED_NOW + timedelta(days=60)
    assert receipt.record.generation == 2

    with pytest.raises(VaultPolicyError, match="may never be shortened"):
        service.extend_retention(
            object_id,
            retain_until_utc=FIXED_NOW + timedelta(days=45),
            actor_id="records-admin-a",
        )


def test_compliance_mode_cannot_downgrade() -> None:
    service, _, _ = _service()
    object_id = _preserve(service)

    with pytest.raises(VaultPolicyError, match="may never be downgraded"):
        service.extend_retention(
            object_id,
            retain_until_utc=FIXED_NOW + timedelta(days=60),
            retention_mode="governance",
            actor_id="records-admin-a",
        )


def test_governance_mode_can_upgrade_to_compliance() -> None:
    service, _, _ = _service()
    receipt = service.preserve(
        b"payload",
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        media_type="application/octet-stream",
        retain_until_utc=FIXED_NOW + timedelta(days=30),
        retention_mode="governance",
        actor_id="custodian-a",
    )

    upgraded = service.extend_retention(
        receipt.record.object_id,
        retain_until_utc=receipt.record.retention.retain_until_utc,
        retention_mode="compliance",
        actor_id="records-admin-a",
    )

    assert upgraded.record.retention.mode == "compliance"


def test_legal_hold_blocks_purge_after_retention_expiry() -> None:
    initial, backend, catalog = _service(now=FIXED_NOW)
    object_id = _preserve(initial, hold=True)
    later = VaultService(
        backend,
        catalog,
        clock=lambda: FIXED_NOW + timedelta(days=31),
        nonce_factory=lambda: "later",
    )

    with pytest.raises(VaultPolicyError, match="legal hold"):
        later.purge(object_id, authorization=_authorization())


def test_legal_hold_release_requires_two_distinct_actors() -> None:
    service, _, _ = _service()
    object_id = _preserve(service, hold=True)

    with pytest.raises(ValidationError, match="two distinct actors"):
        VaultAuthorization(
            primary_actor_id="same-admin",
            secondary_actor_id="same-admin",
            reason="invalid",
        )

    released = service.release_legal_hold(
        object_id,
        hold_id="case-42",
        authorization=_authorization(),
    )
    assert released.record.retention.legal_holds == ()


def test_purge_requires_expired_retention_and_dual_control() -> None:
    initial, backend, catalog = _service(now=FIXED_NOW)
    object_id = _preserve(initial)

    with pytest.raises(VaultPolicyError, match="still inside"):
        initial.purge(object_id, authorization=_authorization())

    later = VaultService(
        backend,
        catalog,
        clock=lambda: FIXED_NOW + timedelta(days=31),
        nonce_factory=lambda: "later",
    )
    receipt = later.purge(object_id, authorization=_authorization())

    assert receipt.record.purged_at_utc == FIXED_NOW + timedelta(days=31)
    assert backend.exists(object_id) is False
    assert later.verify_integrity(object_id).valid is False


def test_journal_chain_verifies_and_detects_tampering() -> None:
    service, _, catalog = _service()
    object_id = _preserve(service)
    service.apply_legal_hold(
        object_id,
        hold_id="audit-1",
        actor_id="records-admin-a",
        reason="audit preservation",
    )

    verified = service.verify_journal()
    assert verified.valid is True
    assert verified.entry_count == 2

    original = catalog._journal[0]  # noqa: SLF001 - intentional corruption test
    catalog._journal[0] = VaultJournalEntry(  # noqa: SLF001 - intentional corruption test
        sequence=original.sequence,
        operation=original.operation,
        object_id=original.object_id,
        record_generation=original.record_generation,
        actor_id=original.actor_id,
        secondary_actor_id=original.secondary_actor_id,
        reason="tampered reason",
        occurred_at_utc=original.occurred_at_utc,
        previous_entry_hash=original.previous_entry_hash,
        entry_hash=original.entry_hash,
    )

    tampered = service.verify_journal()
    assert tampered.valid is False
    assert "entry hash mismatch" in tampered.reason


def test_production_mode_rejects_test_backend() -> None:
    with pytest.raises(VaultProductionReadinessError, match="production capability floor"):
        VaultService(
            InMemoryVaultBackend(),
            InMemoryVaultCatalog(),
            policy=VaultPolicy(require_production_backend=True),
        )
