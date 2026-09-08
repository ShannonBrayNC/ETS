import hashlib
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

from ets.ranger.authority_checkpoint import (
    RangerAuthorityCheckpointConflict,
    RangerAuthorityCheckpointError,
    RangerAuthorityCheckpointIntegrityError,
    RangerAuthorityCheckpointRegistry,
    SQLiteRangerAuthorityCheckpointStore,
)
from ets.ranger.authority_head import (
    RangerAuthorityHeadConflict,
    RangerAuthorityHeadError,
    RangerAuthorityHeadIntegrityError,
    RangerAuthorityHeadRegistry,
    SQLiteRangerAuthorityHeadStore,
)
from ets.ranger.custody import RangerCustodyLedger, SQLiteRangerCustodyStore
from ets.ranger.key_authority import (
    RangerKeyAuthorityLedger,
    RangerKeyBindingIntent,
    RangerKeyEventKind,
    RangerKeyRevocationReason,
    RangerSigningKeyDescriptor,
    SQLiteRangerKeyAuthorityStore,
    build_key_binding_request,
    key_binding_intent_bytes,
)
from ets.ranger.lifecycle import (
    RangerLifecycleEvent,
    RangerLifecycleKind,
    RangerLifecycleResult,
)
from ets.ranger.mobility import ClockQuality, SafetyMode

NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
VEHICLE_ID = "ets-ranger:r0-001"
TENANT_ID = "tenant-ranger-research"
WORKSPACE_ID = "workspace-r0"
MISSION_ID = "mission-alpha"
AUTHORITY_ID = "ets-identity-authority:ranger-research"
AUTHORITY_KEY_ID = "ranger-authority-software-key-1"
REGISTRY_ID = "ets-verifier:ranger-registry-1"
REGISTRY_KEY_ID = "registry-software-key-1"


def _private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def _private_key_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()


def _public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _descriptor(key: Ed25519PrivateKey, key_id: str) -> RangerSigningKeyDescriptor:
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return RangerSigningKeyDescriptor(
        signing_key_id=key_id,
        public_key_hex=public.hex(),
        public_key_fingerprint_sha256=hashlib.sha256(public).hexdigest(),
    )


def _authority(
    path: Path, authority_key: Ed25519PrivateKey
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


def _append_enrollment(
    authority: RangerKeyAuthorityLedger,
    ranger_key: Ed25519PrivateKey,
    descriptor: RangerSigningKeyDescriptor,
) -> None:
    intent = _intent(
        request_id="key-request-enroll-1",
        kind=RangerKeyEventKind.ENROLL,
        subject=descriptor,
        effective_boot_sequence=1,
    )
    authority.append(
        build_key_binding_request(
            intent,
            subject_key_proof_signature_hex=ranger_key.sign(key_binding_intent_bytes(intent)).hex(),
        )
    )


def _append_rotation(
    authority: RangerKeyAuthorityLedger,
    old_key: Ed25519PrivateKey,
    old: RangerSigningKeyDescriptor,
    new_key: Ed25519PrivateKey,
    new: RangerSigningKeyDescriptor,
    *,
    request_id: str = "key-request-rotate-2",
) -> None:
    intent = _intent(
        request_id=request_id,
        kind=RangerKeyEventKind.ROTATE,
        subject=old,
        replacement=new,
        effective_boot_sequence=2,
        minutes=1,
    )
    payload = key_binding_intent_bytes(intent)
    authority.append(
        build_key_binding_request(
            intent,
            subject_key_proof_signature_hex=old_key.sign(payload).hex(),
            replacement_key_proof_signature_hex=new_key.sign(payload).hex(),
        )
    )


def _append_revocation(
    authority: RangerKeyAuthorityLedger,
    subject: RangerSigningKeyDescriptor,
    *,
    effective_boot_sequence: int,
    request_id: str,
    minutes: int,
) -> None:
    intent = _intent(
        request_id=request_id,
        kind=RangerKeyEventKind.REVOKE,
        subject=subject,
        effective_boot_sequence=effective_boot_sequence,
        revocation_reason=RangerKeyRevocationReason.COMPROMISE_SUSPECTED,
        minutes=minutes,
    )
    authority.append(build_key_binding_request(intent))


def _authority_head_registry(
    path: Path,
    *,
    authority: RangerKeyAuthorityLedger,
    registry_key: Ed25519PrivateKey,
) -> tuple[SQLiteRangerAuthorityHeadStore, RangerAuthorityHeadRegistry]:
    store = SQLiteRangerAuthorityHeadStore(path)
    registry = RangerAuthorityHeadRegistry(
        store,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        authority_id=AUTHORITY_ID,
        authority_signing_key_id=AUTHORITY_KEY_ID,
        authority_public_key_hex=authority.authority_public_key_hex,
        registry_id=REGISTRY_ID,
        registry_signing_key_id=REGISTRY_KEY_ID,
        registry_private_key_hex=_private_key_hex(registry_key),
    )
    return store, registry


def _checkpoint_registry(
    path: Path,
    *,
    authority_heads: RangerAuthorityHeadRegistry,
    registry_key: Ed25519PrivateKey,
) -> tuple[SQLiteRangerAuthorityCheckpointStore, RangerAuthorityCheckpointRegistry]:
    store = SQLiteRangerAuthorityCheckpointStore(path)
    registry = RangerAuthorityCheckpointRegistry(
        store,
        authority_head_registry=authority_heads,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        mission_id=MISSION_ID,
        registry_id=REGISTRY_ID,
        registry_signing_key_id=REGISTRY_KEY_ID,
        registry_private_key_hex=_private_key_hex(registry_key),
    )
    return store, registry


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


def _lifecycle_event(*, boot_id: str, event_id: str, sequence: int = 1) -> RangerLifecycleEvent:
    return RangerLifecycleEvent(
        event_id=event_id,
        lifecycle_sequence=sequence,
        lifecycle_kind=RangerLifecycleKind.ARM,
        transition_result=RangerLifecycleResult.APPLIED,
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        controller_id="operator-console-1",
        controller_session_id="controller-session-1",
        boot_id=boot_id,
        occurred_at_utc=NOW + timedelta(seconds=sequence),
        occurred_monotonic_ns=sequence * 1_000_000_000,
        local_clock_quality=ClockQuality.SYNCHRONIZED,
        mode_before=SafetyMode.DISARMED,
        mode_after=SafetyMode.ARMED,
        hardware_estop_asserted=False,
        operator_rearm_required=False,
    )


def test_authority_head_retains_extension_detects_replay_and_recovers(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    ranger_key = _private_key()
    replacement_key = _private_key()
    ranger = _descriptor(ranger_key, "ranger-custody-key-1")
    replacement = _descriptor(replacement_key, "ranger-custody-key-2")
    authority_store, authority = _authority(tmp_path / "authority.sqlite3", authority_key)
    _append_enrollment(authority, ranger_key, ranger)
    registry_key = _private_key()
    head_path = tmp_path / "authority-heads.sqlite3"
    head_store, heads = _authority_head_registry(
        head_path, authority=authority, registry_key=registry_key
    )

    with pytest.raises(RangerAuthorityHeadError, match="timezone-aware"):
        heads.retain(authority.list_events(), received_at_utc=datetime(2026, 9, 8))
    baseline = heads.retain(authority.list_events(), received_at_utc=NOW + timedelta(minutes=10))
    assert baseline.registry_sequence == 1
    assert baseline.freshness_scope == "registry_baseline"
    assert baseline.independent_external_custody_proven is False
    assert baseline.globally_current_history_proven is False
    assert heads.retain(authority.list_events(), received_at_utc=NOW + timedelta(minutes=10)) == (
        baseline
    )

    _append_rotation(authority, ranger_key, ranger, replacement_key, replacement)
    latest = heads.retain(authority.list_events(), received_at_utc=NOW + timedelta(minutes=11))
    assert latest.registry_sequence == 2
    assert latest.authority_event_count == 2
    assert latest.retained_state_advanced
    verified = RangerAuthorityHeadRegistry.verify_checkpoint_chain(
        heads.list_checkpoints(), heads.registry_public_key_hex
    )
    assert verified.valid
    assert verified.latest_authority_event_count == 2

    current = RangerAuthorityHeadRegistry.verify_presented_history(
        authority.list_events(),
        latest,
        authority_public_key_hex=authority.authority_public_key_hex,
        registry_public_key_hex=heads.registry_public_key_hex,
    )
    stale = RangerAuthorityHeadRegistry.verify_presented_history(
        authority.list_events()[:1],
        latest,
        authority_public_key_hex=authority.authority_public_key_hex,
        registry_public_key_hex=heads.registry_public_key_hex,
    )
    assert current.valid
    assert not stale.valid and stale.stale
    _append_revocation(
        authority,
        replacement,
        effective_boot_sequence=3,
        request_id="key-request-revoke-3",
        minutes=2,
    )
    ahead = RangerAuthorityHeadRegistry.verify_presented_history(
        authority.list_events(),
        latest,
        authority_public_key_hex=authority.authority_public_key_hex,
        registry_public_key_hex=heads.registry_public_key_hex,
    )
    assert not ahead.valid and not ahead.stale
    assert "ahead" in ahead.reason

    registry_public_key_hex = heads.registry_public_key_hex
    head_store.close()
    reopened_store, reopened = _authority_head_registry(
        head_path, authority=authority, registry_key=registry_key
    )
    assert reopened.registry_public_key_hex == registry_public_key_hex
    assert reopened.list_checkpoints() == [baseline, latest]
    reopened_store.close()
    authority_store.close()


def test_authority_head_rejects_rollback_fork_nonprefix_and_tampering(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    old_key = _private_key()
    new_key = _private_key()
    alternate_key = _private_key()
    old = _descriptor(old_key, "ranger-custody-key-1")
    new = _descriptor(new_key, "ranger-custody-key-2")
    alternate = _descriptor(alternate_key, "ranger-custody-key-alternate")
    authority_store, authority = _authority(tmp_path / "authority.sqlite3", authority_key)
    _append_enrollment(authority, old_key, old)
    _append_rotation(authority, old_key, old, new_key, new)

    fork_store, fork = _authority(tmp_path / "fork.sqlite3", authority_key)
    _append_enrollment(fork, old_key, old)
    _append_rotation(
        fork,
        old_key,
        old,
        alternate_key,
        alternate,
        request_id="key-request-rotate-alternate",
    )
    _append_revocation(
        fork,
        alternate,
        effective_boot_sequence=3,
        request_id="key-request-revoke-alternate",
        minutes=2,
    )

    registry_key = _private_key()
    head_store, heads = _authority_head_registry(
        tmp_path / "heads.sqlite3", authority=authority, registry_key=registry_key
    )
    latest = heads.retain(authority.list_events(), received_at_utc=NOW + timedelta(minutes=10))
    with pytest.raises(RangerAuthorityHeadConflict, match="stale"):
        heads.retain(authority.list_events()[:1], received_at_utc=NOW + timedelta(minutes=11))
    with pytest.raises(RangerAuthorityHeadConflict, match="fork"):
        heads.retain(fork.list_events()[:2], received_at_utc=NOW + timedelta(minutes=11))
    with pytest.raises(RangerAuthorityHeadConflict, match="does not extend"):
        heads.retain(fork.list_events(), received_at_utc=NOW + timedelta(minutes=11))

    tampered = latest.model_copy(update={"signature_hex": "00" * 64})
    assert not RangerAuthorityHeadRegistry.verify_checkpoint_chain(
        [tampered], heads.registry_public_key_hex
    ).valid
    assert not RangerAuthorityHeadRegistry.verify_checkpoint_chain(
        [latest], _public_key_hex(_private_key())
    ).valid
    head_store.close()
    fork_store.close()
    authority_store.close()


def test_authority_head_store_detects_stale_writer_and_index_tampering(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    ranger_key = _private_key()
    ranger = _descriptor(ranger_key, "ranger-custody-key-1")
    authority_store, authority = _authority(tmp_path / "authority.sqlite3", authority_key)
    _append_enrollment(authority, ranger_key, ranger)
    registry_key = _private_key()
    path = tmp_path / "heads.sqlite3"
    first_store, first = _authority_head_registry(
        path, authority=authority, registry_key=registry_key
    )
    stale_store, stale = _authority_head_registry(
        path, authority=authority, registry_key=registry_key
    )
    first.retain(authority.list_events(), received_at_utc=NOW + timedelta(minutes=10))
    with pytest.raises(RangerAuthorityHeadConflict, match="history changed"):
        stale.retain(authority.list_events(), received_at_utc=NOW + timedelta(minutes=10))
    first_store.close()
    stale_store.close()

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE ranger_retained_authority_heads SET authority_event_count = 99 "
        "WHERE registry_sequence = 1"
    )
    connection.commit()
    connection.close()
    corrupted = SQLiteRangerAuthorityHeadStore(path)
    with pytest.raises(RangerAuthorityHeadIntegrityError, match="index metadata"):
        corrupted.list_checkpoints()
    corrupted.close()
    authority_store.close()


def test_bound_registry_tracks_ranger_and_authority_advancement_and_recovers(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    ranger_key = _private_key()
    replacement_key = _private_key()
    ranger = _descriptor(ranger_key, "ranger-custody-key-1")
    replacement = _descriptor(replacement_key, "ranger-custody-key-2")
    authority_store, authority = _authority(tmp_path / "authority.sqlite3", authority_key)
    _append_enrollment(authority, ranger_key, ranger)
    ranger_store, boot = _boot_ledger(
        tmp_path / "boot.sqlite3",
        ranger_key=ranger_key,
        descriptor=ranger,
        boot_id="boot-1",
        boot_sequence=1,
    )
    registry_key = _private_key()
    head_path = tmp_path / "authority-heads.sqlite3"
    checkpoint_path = tmp_path / "checkpoints.sqlite3"
    head_store, heads = _authority_head_registry(
        head_path, authority=authority, registry_key=registry_key
    )
    checkpoint_store, checkpoints = _checkpoint_registry(
        checkpoint_path, authority_heads=heads, registry_key=registry_key
    )

    with pytest.raises(RangerAuthorityCheckpointError, match="timezone-aware"):
        checkpoints.retain(
            boot.list_records(),
            authority.list_events(),
            received_at_utc=datetime(2026, 9, 8),
        )
    baseline = checkpoints.retain(
        boot.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=10),
    )
    assert baseline.freshness_scope == "registry_baseline"
    assert not baseline.ranger_state_advanced
    assert not baseline.authority_state_advanced
    assert baseline.authority_relative_key_standing_verified
    assert baseline.operational_device_authorization_proven is False

    boot.append(_lifecycle_event(boot_id="boot-1", event_id="arm-1"))
    ranger_advanced = checkpoints.retain(
        boot.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=11),
    )
    assert ranger_advanced.freshness_scope == "ranger_state_advanced"

    _append_rotation(authority, ranger_key, ranger, replacement_key, replacement)
    authority_advanced = checkpoints.retain(
        boot.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=12),
    )
    assert authority_advanced.freshness_scope == "authority_state_advanced"
    assert not authority_advanced.ranger_state_advanced
    assert authority_advanced.authority_state_advanced

    structural = RangerAuthorityCheckpointRegistry.verify_checkpoint_chain(
        checkpoints.list_checkpoints(), checkpoints.registry_public_key_hex
    )
    bound = RangerAuthorityCheckpointRegistry.verify_bound_checkpoint_chain(
        checkpoints.list_checkpoints(),
        heads.list_checkpoints(),
        authority.list_events(),
        registry_public_key_hex=checkpoints.registry_public_key_hex,
        authority_public_key_hex=authority.authority_public_key_hex,
    )
    presentation = RangerAuthorityCheckpointRegistry.verify_presented_chain(
        boot.list_records(),
        authority_advanced,
        heads.list_checkpoints(),
        authority.list_events(),
        registry_public_key_hex=checkpoints.registry_public_key_hex,
        authority_public_key_hex=authority.authority_public_key_hex,
    )
    assert structural.valid and not structural.authority_bindings_verified
    assert bound.valid and bound.authority_bindings_verified
    assert presentation.valid
    assert (
        checkpoints.retain(
            boot.list_records(),
            authority.list_events(),
            received_at_utc=NOW + timedelta(minutes=12),
        )
        == authority_advanced
    )

    checkpoint_store.close()
    head_store.close()
    reopened_head_store, reopened_heads = _authority_head_registry(
        head_path, authority=authority, registry_key=registry_key
    )
    reopened_checkpoint_store, reopened = _checkpoint_registry(
        checkpoint_path, authority_heads=reopened_heads, registry_key=registry_key
    )
    assert reopened.list_checkpoints() == [baseline, ranger_advanced, authority_advanced]
    reopened_checkpoint_store.close()
    reopened_head_store.close()
    ranger_store.close()
    authority_store.close()


def test_authorized_rotation_binds_adjacent_boot_and_detects_stale_replay(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    old_key = _private_key()
    new_key = _private_key()
    old = _descriptor(old_key, "ranger-custody-key-1")
    new = _descriptor(new_key, "ranger-custody-key-2")
    authority_store, authority = _authority(tmp_path / "authority.sqlite3", authority_key)
    _append_enrollment(authority, old_key, old)
    first_store, first = _boot_ledger(
        tmp_path / "boot-1.sqlite3",
        ranger_key=old_key,
        descriptor=old,
        boot_id="boot-1",
        boot_sequence=1,
    )
    first_head = first.list_records()[-1].record_digest_sha256
    registry_key = _private_key()
    head_store, heads = _authority_head_registry(
        tmp_path / "heads.sqlite3", authority=authority, registry_key=registry_key
    )
    checkpoint_store, checkpoints = _checkpoint_registry(
        tmp_path / "checkpoints.sqlite3",
        authority_heads=heads,
        registry_key=registry_key,
    )
    checkpoints.retain(
        first.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=10),
    )

    _append_rotation(authority, old_key, old, new_key, new)
    second_store, second = _boot_ledger(
        tmp_path / "boot-2.sqlite3",
        ranger_key=new_key,
        descriptor=new,
        boot_id="boot-2",
        boot_sequence=2,
        previous_boot_id="boot-1",
        previous_head=first_head,
    )
    heads.retain(authority.list_events(), received_at_utc=NOW + timedelta(minutes=20))
    with pytest.raises(RangerAuthorityCheckpointConflict, match="predates"):
        checkpoints.retain(
            second.list_records(),
            authority.list_events(),
            received_at_utc=NOW + timedelta(minutes=19),
        )
    latest = checkpoints.retain(
        second.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=20),
    )
    assert latest.freshness_scope == "ranger_and_authority_state_advanced"
    assert latest.ranger_signing_key_id == new.signing_key_id
    assert latest.authority_event_count == 2

    stale = RangerAuthorityCheckpointRegistry.verify_presented_chain(
        first.list_records(),
        latest,
        heads.list_checkpoints(),
        authority.list_events(),
        registry_public_key_hex=checkpoints.registry_public_key_hex,
        authority_public_key_hex=authority.authority_public_key_hex,
    )
    current = RangerAuthorityCheckpointRegistry.verify_presented_chain(
        second.list_records(),
        latest,
        heads.list_checkpoints(),
        authority.list_events(),
        registry_public_key_hex=checkpoints.registry_public_key_hex,
        authority_public_key_hex=authority.authority_public_key_hex,
    )
    assert not stale.valid and stale.stale
    assert current.valid
    with pytest.raises(RangerAuthorityCheckpointConflict, match="stale"):
        checkpoints.retain(
            first.list_records(),
            authority.list_events(),
            received_at_utc=NOW + timedelta(minutes=21),
        )
    second_store.close()
    first_store.close()
    checkpoint_store.close()
    head_store.close()
    authority_store.close()


def test_revocation_is_retained_before_rejected_custody_and_preserves_prior_boot(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    ranger_key = _private_key()
    ranger = _descriptor(ranger_key, "ranger-custody-key-1")
    authority_store, authority = _authority(tmp_path / "authority.sqlite3", authority_key)
    _append_enrollment(authority, ranger_key, ranger)
    first_store, first = _boot_ledger(
        tmp_path / "boot-1.sqlite3",
        ranger_key=ranger_key,
        descriptor=ranger,
        boot_id="boot-1",
        boot_sequence=1,
    )
    registry_key = _private_key()
    head_store, heads = _authority_head_registry(
        tmp_path / "heads.sqlite3", authority=authority, registry_key=registry_key
    )
    checkpoint_store, checkpoints = _checkpoint_registry(
        tmp_path / "checkpoints.sqlite3",
        authority_heads=heads,
        registry_key=registry_key,
    )
    baseline = checkpoints.retain(
        first.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=10),
    )
    _append_revocation(
        authority,
        ranger,
        effective_boot_sequence=2,
        request_id="key-request-revoke-2",
        minutes=1,
    )
    second_store, second = _boot_ledger(
        tmp_path / "boot-2.sqlite3",
        ranger_key=ranger_key,
        descriptor=ranger,
        boot_id="boot-2",
        boot_sequence=2,
        previous_boot_id="boot-1",
        previous_head=first.list_records()[-1].record_digest_sha256,
    )
    with pytest.raises(RangerAuthorityCheckpointError, match="revoked"):
        checkpoints.retain(
            second.list_records(),
            authority.list_events(),
            received_at_utc=NOW + timedelta(minutes=20),
        )
    assert len(heads.list_checkpoints()) == 2
    assert heads.list_checkpoints()[-1].authority_event_count == 2
    assert checkpoints.list_checkpoints() == [baseline]

    rejected = RangerAuthorityCheckpointRegistry.verify_presented_chain(
        second.list_records(),
        baseline,
        heads.list_checkpoints(),
        authority.list_events(),
        registry_public_key_hex=checkpoints.registry_public_key_hex,
        authority_public_key_hex=authority.authority_public_key_hex,
    )
    historical = RangerAuthorityCheckpointRegistry.verify_presented_chain(
        first.list_records(),
        baseline,
        heads.list_checkpoints(),
        authority.list_events(),
        registry_public_key_hex=checkpoints.registry_public_key_hex,
        authority_public_key_hex=authority.authority_public_key_hex,
    )
    assert not rejected.valid
    assert "revoked" in rejected.reason
    assert historical.valid
    second_store.close()
    first_store.close()
    checkpoint_store.close()
    head_store.close()
    authority_store.close()


def test_bound_registry_rejects_truncation_fork_nonprefix_and_skipped_boot(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    ranger_key = _private_key()
    ranger = _descriptor(ranger_key, "ranger-custody-key-1")
    authority_store, authority = _authority(tmp_path / "authority.sqlite3", authority_key)
    _append_enrollment(authority, ranger_key, ranger)
    first_store, first = _boot_ledger(
        tmp_path / "boot-1.sqlite3",
        ranger_key=ranger_key,
        descriptor=ranger,
        boot_id="boot-1",
        boot_sequence=1,
    )
    first.append(_lifecycle_event(boot_id="boot-1", event_id="arm-original"))
    registry_key = _private_key()
    head_store, heads = _authority_head_registry(
        tmp_path / "heads.sqlite3", authority=authority, registry_key=registry_key
    )
    checkpoint_store, checkpoints = _checkpoint_registry(
        tmp_path / "checkpoints.sqlite3",
        authority_heads=heads,
        registry_key=registry_key,
    )
    checkpoints.retain(
        first.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=10),
    )
    with pytest.raises(RangerAuthorityCheckpointConflict, match="truncated"):
        checkpoints.retain(
            first.list_records()[:1],
            authority.list_events(),
            received_at_utc=NOW + timedelta(minutes=11),
        )

    fork_store, fork = _boot_ledger(
        tmp_path / "fork.sqlite3",
        ranger_key=ranger_key,
        descriptor=ranger,
        boot_id="boot-1",
        boot_sequence=1,
    )
    fork.append(_lifecycle_event(boot_id="boot-1", event_id="arm-fork"))
    with pytest.raises(RangerAuthorityCheckpointConflict, match="custody head fork"):
        checkpoints.retain(
            fork.list_records(),
            authority.list_events(),
            received_at_utc=NOW + timedelta(minutes=11),
        )
    fork.append(_lifecycle_event(boot_id="boot-1", event_id="arm-fork-extension", sequence=2))
    with pytest.raises(RangerAuthorityCheckpointConflict, match="does not extend"):
        checkpoints.retain(
            fork.list_records(),
            authority.list_events(),
            received_at_utc=NOW + timedelta(minutes=11),
        )

    skipped_store, skipped = _boot_ledger(
        tmp_path / "skipped.sqlite3",
        ranger_key=ranger_key,
        descriptor=ranger,
        boot_id="boot-3",
        boot_sequence=3,
        previous_boot_id="boot-1",
        previous_head=first.list_records()[-1].record_digest_sha256,
    )
    with pytest.raises(RangerAuthorityCheckpointConflict, match="advance exactly once"):
        checkpoints.retain(
            skipped.list_records(),
            authority.list_events(),
            received_at_utc=NOW + timedelta(minutes=11),
        )
    skipped_store.close()
    fork_store.close()
    first_store.close()
    checkpoint_store.close()
    head_store.close()
    authority_store.close()


def test_comprehensive_verifier_rejects_checkpoint_and_authority_tampering(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    ranger_key = _private_key()
    ranger = _descriptor(ranger_key, "ranger-custody-key-1")
    authority_store, authority = _authority(tmp_path / "authority.sqlite3", authority_key)
    _append_enrollment(authority, ranger_key, ranger)
    ranger_store, boot = _boot_ledger(
        tmp_path / "boot.sqlite3",
        ranger_key=ranger_key,
        descriptor=ranger,
        boot_id="boot-1",
        boot_sequence=1,
    )
    registry_key = _private_key()
    head_store, heads = _authority_head_registry(
        tmp_path / "heads.sqlite3", authority=authority, registry_key=registry_key
    )
    checkpoint_store, checkpoints = _checkpoint_registry(
        tmp_path / "checkpoints.sqlite3",
        authority_heads=heads,
        registry_key=registry_key,
    )
    baseline = checkpoints.retain(
        boot.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=10),
    )
    boot.append(_lifecycle_event(boot_id="boot-1", event_id="arm-1"))
    latest = checkpoints.retain(
        boot.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=11),
    )
    tampered_checkpoint = latest.model_copy(update={"signature_hex": "00" * 64})
    tampered_head = heads.list_checkpoints()[0].model_copy(update={"signature_hex": "00" * 64})
    wrong_registry_key = _public_key_hex(_private_key())

    assert not RangerAuthorityCheckpointRegistry.verify_checkpoint_chain(
        [baseline, tampered_checkpoint], checkpoints.registry_public_key_hex
    ).valid
    assert not RangerAuthorityCheckpointRegistry.verify_checkpoint_chain(
        [latest, baseline], checkpoints.registry_public_key_hex
    ).valid
    assert not RangerAuthorityCheckpointRegistry.verify_checkpoint_chain(
        [baseline, latest], wrong_registry_key
    ).valid
    assert not RangerAuthorityCheckpointRegistry.verify_bound_checkpoint_chain(
        [baseline, latest],
        [tampered_head],
        authority.list_events(),
        registry_public_key_hex=checkpoints.registry_public_key_hex,
        authority_public_key_hex=authority.authority_public_key_hex,
    ).valid
    assert not RangerAuthorityCheckpointRegistry.verify_bound_checkpoint_chain(
        [baseline, latest],
        [],
        authority.list_events(),
        registry_public_key_hex=checkpoints.registry_public_key_hex,
        authority_public_key_hex=authority.authority_public_key_hex,
    ).valid
    ranger_store.close()
    checkpoint_store.close()
    head_store.close()
    authority_store.close()


def test_checkpoint_store_detects_stale_writer_and_index_tampering(
    tmp_path: Path,
) -> None:
    authority_key = _private_key()
    ranger_key = _private_key()
    ranger = _descriptor(ranger_key, "ranger-custody-key-1")
    authority_store, authority = _authority(tmp_path / "authority.sqlite3", authority_key)
    _append_enrollment(authority, ranger_key, ranger)
    ranger_store, boot = _boot_ledger(
        tmp_path / "boot.sqlite3",
        ranger_key=ranger_key,
        descriptor=ranger,
        boot_id="boot-1",
        boot_sequence=1,
    )
    registry_key = _private_key()
    head_store, heads = _authority_head_registry(
        tmp_path / "heads.sqlite3", authority=authority, registry_key=registry_key
    )
    path = tmp_path / "checkpoints.sqlite3"
    first_store, first = _checkpoint_registry(
        path, authority_heads=heads, registry_key=registry_key
    )
    stale_store, stale = _checkpoint_registry(
        path, authority_heads=heads, registry_key=registry_key
    )
    first.retain(
        boot.list_records(),
        authority.list_events(),
        received_at_utc=NOW + timedelta(minutes=10),
    )
    with pytest.raises(RangerAuthorityCheckpointConflict, match="history changed"):
        stale.retain(
            boot.list_records(),
            authority.list_events(),
            received_at_utc=NOW + timedelta(minutes=10),
        )
    first_store.close()
    stale_store.close()

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE ranger_authority_bound_checkpoints SET boot_sequence = 99 "
        "WHERE registry_sequence = 1"
    )
    connection.commit()
    connection.close()
    corrupted = SQLiteRangerAuthorityCheckpointStore(path)
    with pytest.raises(RangerAuthorityCheckpointIntegrityError, match="index metadata"):
        corrupted.list_checkpoints()
    corrupted.close()
    ranger_store.close()
    head_store.close()
    authority_store.close()
