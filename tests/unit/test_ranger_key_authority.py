import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from pydantic import ValidationError

from ets.ranger.custody import RangerCustodyLedger, SQLiteRangerCustodyStore
from ets.ranger.key_authority import (
    RangerKeyAuthorityConflict,
    RangerKeyAuthorityError,
    RangerKeyAuthorityIntegrityError,
    RangerKeyAuthorityLedger,
    RangerKeyAuthorizationReason,
    RangerKeyBindingIntent,
    RangerKeyEventKind,
    RangerKeyRevocationReason,
    RangerSigningKeyDescriptor,
    SQLiteRangerKeyAuthorityStore,
    build_key_binding_request,
    key_binding_intent_bytes,
)
from ets.ranger.mobility import ClockQuality

NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
VEHICLE_ID = "ets-ranger:r0-001"
TENANT_ID = "tenant-ranger-research"
WORKSPACE_ID = "workspace-r0"
MISSION_ID = "mission-alpha"
AUTHORITY_ID = "ets-identity-authority:ranger-research"
AUTHORITY_KEY_ID = "ranger-authority-software-key-1"


def _private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def _private_key_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()


def _public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _descriptor(key: Ed25519PrivateKey, key_id: str) -> RangerSigningKeyDescriptor:
    public = bytes.fromhex(_public_key_hex(key))
    import hashlib

    return RangerSigningKeyDescriptor(
        signing_key_id=key_id,
        public_key_hex=public.hex(),
        public_key_fingerprint_sha256=hashlib.sha256(public).hexdigest(),
    )


def _intent(
    *,
    request_id: str,
    kind: RangerKeyEventKind,
    subject: RangerSigningKeyDescriptor,
    effective_boot_sequence: int,
    replacement: RangerSigningKeyDescriptor | None = None,
    revocation_reason: RangerKeyRevocationReason | None = None,
    minutes: int = 0,
) -> RangerKeyBindingIntent:
    return RangerKeyBindingIntent(
        request_id=request_id,
        event_kind=kind,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        effective_boot_sequence=effective_boot_sequence,
        subject_key=subject,
        replacement_key=replacement,
        revocation_reason=revocation_reason,
        recorded_at_utc=NOW + timedelta(minutes=minutes),
        clock_quality=ClockQuality.SYNCHRONIZED,
        clock_source="authenticated-time-candidate",
        clock_uncertainty_ms=25,
    )


def _signed_request(
    intent: RangerKeyBindingIntent,
    *,
    subject_signer: Ed25519PrivateKey | None = None,
    replacement_signer: Ed25519PrivateKey | None = None,
):
    payload = key_binding_intent_bytes(intent)
    return build_key_binding_request(
        intent,
        subject_key_proof_signature_hex=(
            None if subject_signer is None else subject_signer.sign(payload).hex()
        ),
        replacement_key_proof_signature_hex=(
            None if replacement_signer is None else replacement_signer.sign(payload).hex()
        ),
    )


def _ledger(
    path: Path,
    authority_key: Ed25519PrivateKey,
) -> tuple[SQLiteRangerKeyAuthorityStore, RangerKeyAuthorityLedger]:
    store = SQLiteRangerKeyAuthorityStore(path)
    ledger = RangerKeyAuthorityLedger(
        store,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        authority_id=AUTHORITY_ID,
        authority_signing_key_id=AUTHORITY_KEY_ID,
        authority_private_key_hex=_private_key_hex(authority_key),
    )
    return store, ledger


def _enroll(
    ledger: RangerKeyAuthorityLedger,
    ranger_key: Ed25519PrivateKey,
    descriptor: RangerSigningKeyDescriptor,
):
    intent = _intent(
        request_id="key-request-enroll-1",
        kind=RangerKeyEventKind.ENROLL,
        subject=descriptor,
        effective_boot_sequence=1,
    )
    return ledger.append(_signed_request(intent, subject_signer=ranger_key))


def _boot_ledger(
    path: Path,
    *,
    ranger_key: Ed25519PrivateKey,
    descriptor: RangerSigningKeyDescriptor,
    boot_id: str,
    boot_sequence: int,
    previous_boot_id: str | None = None,
    previous_head: str | None = None,
) -> tuple[SQLiteRangerCustodyStore, RangerCustodyLedger]:
    store = SQLiteRangerCustodyStore(path)
    ledger = RangerCustodyLedger(
        store,
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        boot_id=boot_id,
        signing_key_id=descriptor.signing_key_id,
        private_key_hex=_private_key_hex(ranger_key),
    )
    ledger.append_boot_checkpoint(
        checkpoint_id=f"boot-checkpoint-{boot_sequence}",
        boot_sequence=boot_sequence,
        started_at_utc=NOW + timedelta(hours=boot_sequence),
        clock_quality=ClockQuality.SYNCHRONIZED,
        clock_source="authenticated-time-candidate",
        clock_uncertainty_ms=25,
        previous_boot_id=previous_boot_id,
        previous_custody_head_digest_sha256=previous_head,
    )
    return store, ledger


def test_enrollment_is_dual_signed_persisted_and_authorizes_boot(tmp_path: Path) -> None:
    authority_key = _private_key()
    ranger_key = _private_key()
    descriptor = _descriptor(ranger_key, "ranger-custody-key-1")
    path = tmp_path / "key-authority.sqlite3"
    store, ledger = _ledger(path, authority_key)
    event = _enroll(ledger, ranger_key, descriptor)

    assert event.authority_sequence == 1
    assert event.previous_event_digest_sha256 == "0" * 64
    assert event.request.intent_digest_sha256
    assert event.operational_device_authorization_proven is False
    assert event.hardware_identity_proven is False
    assert event.globally_current_history_proven is False
    verification = ledger.verify_history(ledger.list_events(), ledger.authority_public_key_hex)
    assert verification.valid
    assert verification.event_count == 1
    assert verification.latest_signing_key_id == descriptor.signing_key_id

    decision = ledger.authorize_key(
        ledger.list_events(),
        ledger.authority_public_key_hex,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        boot_sequence=1,
        signing_key_id=descriptor.signing_key_id,
        public_key_fingerprint_sha256=descriptor.public_key_fingerprint_sha256,
    )
    assert decision.allowed
    assert decision.reason is RangerKeyAuthorizationReason.AUTHORIZED
    assert decision.authority_relative_key_standing
    assert decision.operational_device_authorization_proven is False
    assert decision.globally_current_history_proven is False
    authority_public_key_hex = ledger.authority_public_key_hex
    store.close()

    reopened_store, reopened = _ledger(path, authority_key)
    assert reopened.authority_public_key_hex == authority_public_key_hex
    assert reopened.list_events() == [event]
    reopened_store.close()


def test_rotation_requires_both_proofs_and_authorizes_cross_boot_continuity(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    old_key = _private_key()
    new_key = _private_key()
    old = _descriptor(old_key, "ranger-custody-key-1")
    new = _descriptor(new_key, "ranger-custody-key-2")
    store, authority = _ledger(tmp_path / "authority.sqlite3", authority_key)
    _enroll(authority, old_key, old)
    rotation_intent = _intent(
        request_id="key-request-rotate-2",
        kind=RangerKeyEventKind.ROTATE,
        subject=old,
        replacement=new,
        effective_boot_sequence=2,
        minutes=1,
    )
    with pytest.raises(RangerKeyAuthorityError, match="subject-key possession proof"):
        authority.append(
            _signed_request(
                rotation_intent,
                subject_signer=_private_key(),
                replacement_signer=new_key,
            )
        )
    rotation = authority.append(
        _signed_request(
            rotation_intent,
            subject_signer=old_key,
            replacement_signer=new_key,
        )
    )
    assert rotation.authority_sequence == 2

    old_at_one = authority.authorize_key(
        authority.list_events(),
        authority.authority_public_key_hex,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        boot_sequence=1,
        signing_key_id=old.signing_key_id,
        public_key_fingerprint_sha256=old.public_key_fingerprint_sha256,
    )
    old_at_two = authority.authorize_key(
        authority.list_events(),
        authority.authority_public_key_hex,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        boot_sequence=2,
        signing_key_id=old.signing_key_id,
        public_key_fingerprint_sha256=old.public_key_fingerprint_sha256,
    )
    new_at_one = authority.authorize_key(
        authority.list_events(),
        authority.authority_public_key_hex,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        boot_sequence=1,
        signing_key_id=new.signing_key_id,
        public_key_fingerprint_sha256=new.public_key_fingerprint_sha256,
    )
    assert old_at_one.allowed
    assert old_at_two.reason is RangerKeyAuthorizationReason.SUPERSEDED_CREDENTIAL
    assert new_at_one.reason is RangerKeyAuthorizationReason.CREDENTIAL_NOT_YET_ACTIVE

    old_store, first = _boot_ledger(
        tmp_path / "boot-1.sqlite3",
        ranger_key=old_key,
        descriptor=old,
        boot_id="boot-1",
        boot_sequence=1,
    )
    first_head = first.list_records()[-1].record_digest_sha256
    new_store, second = _boot_ledger(
        tmp_path / "boot-2.sqlite3",
        ranger_key=new_key,
        descriptor=new,
        boot_id="boot-2",
        boot_sequence=2,
        previous_boot_id="boot-1",
        previous_head=first_head,
    )
    continuity = authority.verify_boot_continuity(
        first.list_records(),
        second.list_records(),
        authority.list_events(),
        authority.authority_public_key_hex,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
    )
    assert continuity.valid
    assert continuity.key_rotation_authorized
    assert continuity.authority_relative_key_standing
    assert continuity.operational_device_authorization_proven is False
    assert continuity.globally_current_history_proven is False
    old_store.close()
    new_store.close()
    store.close()


def test_revocation_blocks_validly_signed_future_boot_but_not_prior_history(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    ranger_key = _private_key()
    descriptor = _descriptor(ranger_key, "ranger-custody-key-1")
    store, authority = _ledger(tmp_path / "authority.sqlite3", authority_key)
    _enroll(authority, ranger_key, descriptor)
    revoke_intent = _intent(
        request_id="key-request-revoke-2",
        kind=RangerKeyEventKind.REVOKE,
        subject=descriptor,
        effective_boot_sequence=2,
        revocation_reason=RangerKeyRevocationReason.COMPROMISE_SUSPECTED,
        minutes=1,
    )
    authority.append(_signed_request(revoke_intent))

    before = authority.authorize_key(
        authority.list_events(),
        authority.authority_public_key_hex,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        boot_sequence=1,
        signing_key_id=descriptor.signing_key_id,
        public_key_fingerprint_sha256=descriptor.public_key_fingerprint_sha256,
    )
    revoked = authority.authorize_key(
        authority.list_events(),
        authority.authority_public_key_hex,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        boot_sequence=2,
        signing_key_id=descriptor.signing_key_id,
        public_key_fingerprint_sha256=descriptor.public_key_fingerprint_sha256,
    )
    assert before.allowed
    assert not revoked.allowed
    assert revoked.reason is RangerKeyAuthorizationReason.REVOKED

    first_store, first = _boot_ledger(
        tmp_path / "boot-1.sqlite3",
        ranger_key=ranger_key,
        descriptor=descriptor,
        boot_id="boot-1",
        boot_sequence=1,
    )
    second_store, second = _boot_ledger(
        tmp_path / "boot-2.sqlite3",
        ranger_key=ranger_key,
        descriptor=descriptor,
        boot_id="boot-2",
        boot_sequence=2,
        previous_boot_id="boot-1",
        previous_head=first.list_records()[-1].record_digest_sha256,
    )
    assert RangerCustodyLedger.verify_chain(
        second.list_records(), descriptor.public_key_hex
    ).valid
    continuity = authority.verify_boot_continuity(
        first.list_records(),
        second.list_records(),
        authority.list_events(),
        authority.authority_public_key_hex,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
    )
    assert not continuity.valid
    assert "revoked" in continuity.reason
    first_store.close()
    second_store.close()
    store.close()


def test_verifier_rejects_tampering_reordering_missing_events_and_wrong_authority(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    old_key = _private_key()
    new_key = _private_key()
    old = _descriptor(old_key, "ranger-custody-key-1")
    new = _descriptor(new_key, "ranger-custody-key-2")
    store, authority = _ledger(tmp_path / "authority.sqlite3", authority_key)
    first = _enroll(authority, old_key, old)
    intent = _intent(
        request_id="key-request-rotate-2",
        kind=RangerKeyEventKind.ROTATE,
        subject=old,
        replacement=new,
        effective_boot_sequence=2,
        minutes=1,
    )
    second = authority.append(
        _signed_request(intent, subject_signer=old_key, replacement_signer=new_key)
    )
    history = [first, second]

    tampered = second.model_copy(update={"authority_signature_hex": "00" * 64})
    assert not authority.verify_history(
        [first, tampered], authority.authority_public_key_hex
    ).valid
    assert not authority.verify_history([second], authority.authority_public_key_hex).valid
    assert not authority.verify_history(
        list(reversed(history)), authority.authority_public_key_hex
    ).valid
    wrong_authority = _public_key_hex(_private_key())
    assert not authority.verify_history(history, wrong_authority).valid

    foreign_intent = first.request.intent.model_copy(update={"vehicle_id": "ets-ranger:other"})
    foreign_request = first.request.model_copy(update={"intent": foreign_intent})
    foreign = first.model_copy(update={"request": foreign_request})
    assert not authority.verify_history([foreign], authority.authority_public_key_hex).valid
    store.close()


def test_store_rejects_stale_writer_and_tampered_unsigned_index(tmp_path: Path) -> None:
    path = tmp_path / "authority.sqlite3"
    authority_key = _private_key()
    ranger_key = _private_key()
    descriptor = _descriptor(ranger_key, "ranger-custody-key-1")
    store1, first = _ledger(path, authority_key)
    store2, stale = _ledger(path, authority_key)
    intent = _intent(
        request_id="key-request-enroll-1",
        kind=RangerKeyEventKind.ENROLL,
        subject=descriptor,
        effective_boot_sequence=1,
    )
    request = _signed_request(intent, subject_signer=ranger_key)
    first.append(request)
    with pytest.raises(RangerKeyAuthorityConflict, match="history changed"):
        stale.append(request)
    store1.close()
    store2.close()

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE ranger_key_authority_events SET request_id = ? WHERE authority_sequence = 1",
        ("forged-request-id",),
    )
    connection.commit()
    connection.close()
    tampered_store = SQLiteRangerKeyAuthorityStore(path)
    with pytest.raises(RangerKeyAuthorityIntegrityError, match="index"):
        tampered_store.list_events()
    tampered_store.close()


def test_open_ledger_rejects_live_history_tampering(tmp_path: Path) -> None:
    path = tmp_path / "authority.sqlite3"
    authority_key = _private_key()
    ranger_key = _private_key()
    descriptor = _descriptor(ranger_key, "ranger-custody-key-1")
    store, authority = _ledger(path, authority_key)
    _enroll(authority, ranger_key, descriptor)

    connection = sqlite3.connect(path)
    row = connection.execute(
        "SELECT event_json FROM ranger_key_authority_events WHERE authority_sequence = 1"
    ).fetchone()
    assert row is not None
    event = authority.list_events()[0]
    tampered = event.model_copy(update={"authority_signature_hex": "00" * 64})
    connection.execute(
        "UPDATE ranger_key_authority_events SET event_json = ? WHERE authority_sequence = 1",
        (tampered.model_dump_json(),),
    )
    connection.commit()
    connection.close()

    rotation_key = _private_key()
    rotation = _descriptor(rotation_key, "ranger-custody-key-2")
    intent = _intent(
        request_id="key-request-rotate-after-tamper",
        kind=RangerKeyEventKind.ROTATE,
        subject=descriptor,
        replacement=rotation,
        effective_boot_sequence=2,
    )
    with pytest.raises(RangerKeyAuthorityConflict, match="history changed"):
        authority.append(
            _signed_request(
                intent,
                subject_signer=ranger_key,
                replacement_signer=rotation_key,
            )
        )
    store.close()


def test_schema_rejects_false_clock_precision_and_malformed_transition() -> None:
    key = _private_key()
    descriptor = _descriptor(key, "ranger-custody-key-1")
    with pytest.raises(ValidationError, match="unknown clock quality"):
        RangerKeyBindingIntent(
            request_id="key-request-enroll-1",
            event_kind=RangerKeyEventKind.ENROLL,
            vehicle_id=VEHICLE_ID,
            tenant_id=TENANT_ID,
            workspace_id=WORKSPACE_ID,
            effective_boot_sequence=1,
            subject_key=descriptor,
            recorded_at_utc=NOW,
            clock_quality=ClockQuality.UNKNOWN,
            clock_source="local-clock",
            clock_uncertainty_ms=1,
        )
    with pytest.raises(ValidationError, match="rotation requires a replacement"):
        _intent(
            request_id="key-request-rotate-bad",
            kind=RangerKeyEventKind.ROTATE,
            subject=descriptor,
            effective_boot_sequence=2,
        )


@pytest.mark.parametrize("reuse", ["identifier", "public_key"])
def test_rotation_rejects_reused_key_identity_component(
    tmp_path: Path, reuse: str
) -> None:
    authority_key = _private_key()
    old_key = _private_key()
    old = _descriptor(old_key, "ranger-custody-key-1")
    store, authority = _ledger(tmp_path / "authority.sqlite3", authority_key)
    _enroll(authority, old_key, old)

    if reuse == "identifier":
        replacement_key = _private_key()
        replacement = _descriptor(replacement_key, old.signing_key_id)
        match = "key identifier"
    else:
        replacement_key = old_key
        replacement = _descriptor(replacement_key, "ranger-custody-key-alias")
        match = "public key"
    intent = _intent(
        request_id=f"key-request-rotate-reused-{reuse}",
        kind=RangerKeyEventKind.ROTATE,
        subject=old,
        replacement=replacement,
        effective_boot_sequence=2,
    )
    with pytest.raises(RangerKeyAuthorityConflict, match=match):
        authority.append(
            _signed_request(
                intent,
                subject_signer=old_key,
                replacement_signer=replacement_key,
            )
        )
    store.close()
