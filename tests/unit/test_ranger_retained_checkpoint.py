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

from ets.ranger.custody import RangerCustodyLedger, SQLiteRangerCustodyStore
from ets.ranger.lifecycle import (
    RangerLifecycleEvent,
    RangerLifecycleKind,
    RangerLifecycleResult,
)
from ets.ranger.mobility import ClockQuality, SafetyMode
from ets.ranger.retained_checkpoint import (
    RangerCheckpointConflict,
    RangerCheckpointError,
    RangerCheckpointIntegrityError,
    RangerCheckpointRegistry,
    SQLiteRangerCheckpointStore,
)

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
VEHICLE_ID = "ets-ranger:r0-001"
MISSION_ID = "mission-alpha"
RANGER_KEY_ID = "ranger-software-key-1"
REGISTRY_ID = "ets-verifier:ranger-registry-1"
REGISTRY_KEY_ID = "registry-software-key-1"


def _private_key_hex() -> str:
    return (
        Ed25519PrivateKey.generate()
        .private_bytes(
            Encoding.Raw,
            PrivateFormat.Raw,
            NoEncryption(),
        )
        .hex()
    )


def _public_key_hex(private_key_hex: str) -> str:
    private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    return private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _boot_ledger(
    path: Path,
    *,
    ranger_key: str,
    boot_id: str,
    boot_sequence: int,
    previous_boot_id: str | None = None,
    previous_head: str | None = None,
    mission_id: str = MISSION_ID,
) -> tuple[SQLiteRangerCustodyStore, RangerCustodyLedger]:
    store = SQLiteRangerCustodyStore(path)
    ledger = RangerCustodyLedger(
        store,
        vehicle_id=VEHICLE_ID,
        mission_id=mission_id,
        boot_id=boot_id,
        signing_key_id=RANGER_KEY_ID,
        private_key_hex=ranger_key,
    )
    ledger.append_boot_checkpoint(
        checkpoint_id=f"boot-checkpoint-{boot_sequence}",
        boot_sequence=boot_sequence,
        started_at_utc=NOW + timedelta(minutes=boot_sequence),
        clock_quality=ClockQuality.SYNCHRONIZED,
        clock_source="authenticated-ntp-candidate",
        clock_uncertainty_ms=25,
        previous_boot_id=previous_boot_id,
        previous_custody_head_digest_sha256=previous_head,
    )
    return store, ledger


def _lifecycle_event(*, boot_id: str, event_id: str) -> RangerLifecycleEvent:
    return RangerLifecycleEvent(
        event_id=event_id,
        lifecycle_sequence=1,
        lifecycle_kind=RangerLifecycleKind.ARM,
        transition_result=RangerLifecycleResult.APPLIED,
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        controller_id="operator-console-1",
        controller_session_id="controller-session-1",
        boot_id=boot_id,
        occurred_at_utc=NOW,
        occurred_monotonic_ns=1_000_000_000,
        local_clock_quality=ClockQuality.SYNCHRONIZED,
        mode_before=SafetyMode.DISARMED,
        mode_after=SafetyMode.ARMED,
        hardware_estop_asserted=False,
        operator_rearm_required=False,
    )


def _registry(
    path: Path,
    *,
    ranger_key: str,
    registry_key: str,
) -> tuple[SQLiteRangerCheckpointStore, RangerCheckpointRegistry]:
    store = SQLiteRangerCheckpointStore(path)
    registry = RangerCheckpointRegistry(
        store,
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        ranger_signing_key_id=RANGER_KEY_ID,
        ranger_public_key_hex=_public_key_hex(ranger_key),
        registry_id=REGISTRY_ID,
        registry_signing_key_id=REGISTRY_KEY_ID,
        registry_private_key_hex=registry_key,
    )
    return store, registry


def test_registry_signs_baseline_and_same_boot_extension_then_recovers(
    tmp_path: Path,
) -> None:
    ranger_key = _private_key_hex()
    registry_key = _private_key_hex()
    ranger_store, ranger = _boot_ledger(
        tmp_path / "boot.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-1",
        boot_sequence=1,
    )
    registry_path = tmp_path / "registry.sqlite3"
    registry_store, registry = _registry(
        registry_path, ranger_key=ranger_key, registry_key=registry_key
    )

    baseline = registry.retain(ranger.list_records(), received_at_utc=NOW + timedelta(minutes=10))
    assert baseline.registry_sequence == 1
    assert baseline.previous_checkpoint_digest_sha256 == "0" * 64
    assert baseline.freshness_scope == "registry_baseline"
    assert baseline.retained_state_advanced is False
    assert baseline.ranger_chain_integrity_verified is True
    assert baseline.independent_external_custody_proven is False
    assert baseline.globally_current_state_proven is False
    assert baseline.trusted_time_proven is False
    assert baseline.complete_capture_proven is False
    assert baseline.semantic_truth_proven is False
    assert baseline.physical_outcome_proven is False

    ranger.append(_lifecycle_event(boot_id="boot-1", event_id="arm-1"))
    latest = registry.retain(ranger.list_records(), received_at_utc=NOW + timedelta(minutes=11))
    assert latest.registry_sequence == 2
    assert latest.previous_checkpoint_digest_sha256 == baseline.checkpoint_digest_sha256
    assert latest.custody_record_count == 2
    assert latest.freshness_scope == "newer_than_retained_checkpoint"

    checkpoint_verification = RangerCheckpointRegistry.verify_checkpoint_chain(
        registry.list_checkpoints(), registry.registry_public_key_hex
    )
    assert checkpoint_verification.valid
    assert checkpoint_verification.checkpoint_count == 2
    assert checkpoint_verification.latest_checkpoint_digest_sha256 == (
        latest.checkpoint_digest_sha256
    )
    assert checkpoint_verification.freshness_relative_to_retained_state is True

    presentation = RangerCheckpointRegistry.verify_presented_chain(
        ranger.list_records(),
        latest,
        ranger_public_key_hex=ranger.public_key_hex,
        registry_public_key_hex=registry.registry_public_key_hex,
    )
    assert presentation.valid
    assert presentation.stale is False

    truncated_presentation = RangerCheckpointRegistry.verify_presented_chain(
        ranger.list_records()[:1],
        latest,
        ranger_public_key_hex=ranger.public_key_hex,
        registry_public_key_hex=registry.registry_public_key_hex,
    )
    assert not truncated_presentation.valid
    assert truncated_presentation.stale

    duplicate = registry.retain(ranger.list_records(), received_at_utc=NOW + timedelta(minutes=11))
    assert duplicate == latest
    assert len(registry.list_checkpoints()) == 2
    registry_public_key_hex = registry.registry_public_key_hex
    registry_store.close()

    reopened_store, reopened = _registry(
        registry_path, ranger_key=ranger_key, registry_key=registry_key
    )
    assert reopened.registry_public_key_hex == registry_public_key_hex
    assert reopened.list_checkpoints() == [baseline, latest]
    reopened_store.close()
    ranger_store.close()


def test_adjacent_boot_advances_registry_and_stale_valid_replay_is_detected(
    tmp_path: Path,
) -> None:
    ranger_key = _private_key_hex()
    registry_key = _private_key_hex()
    first_store, first = _boot_ledger(
        tmp_path / "boot-1.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-1",
        boot_sequence=1,
    )
    first.append(_lifecycle_event(boot_id="boot-1", event_id="arm-1"))
    registry_store, registry = _registry(
        tmp_path / "registry.sqlite3",
        ranger_key=ranger_key,
        registry_key=registry_key,
    )
    registry.retain(first.list_records(), received_at_utc=NOW + timedelta(minutes=10))
    first_head = first.list_records()[-1].record_digest_sha256

    second_store, second = _boot_ledger(
        tmp_path / "boot-2.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-2",
        boot_sequence=2,
        previous_boot_id="boot-1",
        previous_head=first_head,
    )
    latest = registry.retain(second.list_records(), received_at_utc=NOW + timedelta(minutes=20))
    assert latest.boot_sequence == 2
    assert latest.previous_boot_id == "boot-1"
    assert latest.previous_custody_head_digest_sha256 == first_head

    stale = RangerCheckpointRegistry.verify_presented_chain(
        first.list_records(),
        latest,
        ranger_public_key_hex=first.public_key_hex,
        registry_public_key_hex=registry.registry_public_key_hex,
    )
    assert not stale.valid
    assert stale.stale
    assert "stale" in stale.reason

    current = RangerCheckpointRegistry.verify_presented_chain(
        second.list_records(),
        latest,
        ranger_public_key_hex=second.public_key_hex,
        registry_public_key_hex=registry.registry_public_key_hex,
    )
    assert current.valid

    with pytest.raises(RangerCheckpointConflict, match="stale"):
        registry.retain(first.list_records(), received_at_utc=NOW + timedelta(minutes=21))
    first_store.close()
    second_store.close()
    registry_store.close()


def test_registry_rejects_truncation_fork_and_skipped_boot(tmp_path: Path) -> None:
    ranger_key = _private_key_hex()
    registry_key = _private_key_hex()
    first_store, first = _boot_ledger(
        tmp_path / "first.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-1",
        boot_sequence=1,
    )
    first.append(_lifecycle_event(boot_id="boot-1", event_id="arm-original"))
    registry_store, registry = _registry(
        tmp_path / "registry.sqlite3",
        ranger_key=ranger_key,
        registry_key=registry_key,
    )
    registry.retain(first.list_records(), received_at_utc=NOW + timedelta(minutes=10))

    with pytest.raises(RangerCheckpointConflict, match="truncated"):
        registry.retain(first.list_records()[:1], received_at_utc=NOW + timedelta(minutes=11))

    fork_store, fork = _boot_ledger(
        tmp_path / "fork.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-1",
        boot_sequence=1,
    )
    fork.append(_lifecycle_event(boot_id="boot-1", event_id="arm-fork"))
    with pytest.raises(RangerCheckpointConflict, match="custody head fork"):
        registry.retain(fork.list_records(), received_at_utc=NOW + timedelta(minutes=12))

    fork.append(_lifecycle_event(boot_id="boot-1", event_id="arm-fork-extension"))
    with pytest.raises(RangerCheckpointConflict, match="does not extend"):
        registry.retain(fork.list_records(), received_at_utc=NOW + timedelta(minutes=12))

    skipped_store, skipped = _boot_ledger(
        tmp_path / "skipped.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-3",
        boot_sequence=3,
        previous_boot_id="boot-1",
        previous_head=first.list_records()[-1].record_digest_sha256,
    )
    with pytest.raises(RangerCheckpointConflict, match="advance exactly once"):
        registry.retain(skipped.list_records(), received_at_utc=NOW + timedelta(minutes=13))
    first_store.close()
    fork_store.close()
    skipped_store.close()
    registry_store.close()


def test_registry_rejects_wrong_ranger_key_identity_time_and_self_witness(
    tmp_path: Path,
) -> None:
    ranger_key = _private_key_hex()
    registry_key = _private_key_hex()
    ranger_store, ranger = _boot_ledger(
        tmp_path / "ranger.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-1",
        boot_sequence=1,
    )
    registry_store, registry = _registry(
        tmp_path / "registry.sqlite3",
        ranger_key=ranger_key,
        registry_key=registry_key,
    )
    with pytest.raises(RangerCheckpointError, match="timezone-aware"):
        registry.retain(ranger.list_records(), received_at_utc=datetime(2026, 9, 7))

    foreign_store, foreign = _boot_ledger(
        tmp_path / "foreign.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-1",
        boot_sequence=1,
        mission_id="mission-foreign",
    )
    with pytest.raises(RangerCheckpointError, match="identity"):
        registry.retain(foreign.list_records(), received_at_utc=NOW + timedelta(minutes=10))

    wrong_key_store, wrong_key = _boot_ledger(
        tmp_path / "wrong-key.sqlite3",
        ranger_key=_private_key_hex(),
        boot_id="boot-1",
        boot_sequence=1,
    )
    with pytest.raises(RangerCheckpointError, match="custody chain is invalid"):
        registry.retain(wrong_key.list_records(), received_at_utc=NOW + timedelta(minutes=10))

    self_store = SQLiteRangerCheckpointStore(tmp_path / "self.sqlite3")
    with pytest.raises(RangerCheckpointError, match="must be distinct"):
        RangerCheckpointRegistry(
            self_store,
            vehicle_id=VEHICLE_ID,
            mission_id=MISSION_ID,
            ranger_signing_key_id=RANGER_KEY_ID,
            ranger_public_key_hex=_public_key_hex(ranger_key),
            registry_id=REGISTRY_ID,
            registry_signing_key_id=REGISTRY_KEY_ID,
            registry_private_key_hex=ranger_key,
        )
    ranger_store.close()
    foreign_store.close()
    wrong_key_store.close()
    registry_store.close()
    self_store.close()


def test_checkpoint_verification_rejects_tampering_order_and_wrong_key(
    tmp_path: Path,
) -> None:
    ranger_key = _private_key_hex()
    registry_key = _private_key_hex()
    ranger_store, ranger = _boot_ledger(
        tmp_path / "ranger.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-1",
        boot_sequence=1,
    )
    registry_store, registry = _registry(
        tmp_path / "registry.sqlite3",
        ranger_key=ranger_key,
        registry_key=registry_key,
    )
    baseline = registry.retain(ranger.list_records(), received_at_utc=NOW + timedelta(minutes=10))
    ranger.append(_lifecycle_event(boot_id="boot-1", event_id="arm-1"))
    latest = registry.retain(ranger.list_records(), received_at_utc=NOW + timedelta(minutes=11))

    tampered = latest.model_copy(update={"signature_hex": "00" * 64})
    assert not RangerCheckpointRegistry.verify_checkpoint_chain(
        [baseline, tampered], registry.registry_public_key_hex
    ).valid
    assert not RangerCheckpointRegistry.verify_checkpoint_chain(
        [baseline, baseline], registry.registry_public_key_hex
    ).valid
    assert not RangerCheckpointRegistry.verify_checkpoint_chain(
        list(reversed([baseline, latest])), registry.registry_public_key_hex
    ).valid
    assert not RangerCheckpointRegistry.verify_checkpoint_chain(
        [baseline, latest], _public_key_hex(_private_key_hex())
    ).valid

    bad_presentation = RangerCheckpointRegistry.verify_presented_chain(
        ranger.list_records(),
        tampered,
        ranger_public_key_hex=ranger.public_key_hex,
        registry_public_key_hex=registry.registry_public_key_hex,
    )
    assert not bad_presentation.valid
    assert "signature" in bad_presentation.reason
    ranger_store.close()
    registry_store.close()


def test_checkpoint_store_detects_stale_writer_and_unsigned_index_tampering(
    tmp_path: Path,
) -> None:
    ranger_key = _private_key_hex()
    registry_key = _private_key_hex()
    ranger_store, ranger = _boot_ledger(
        tmp_path / "ranger.sqlite3",
        ranger_key=ranger_key,
        boot_id="boot-1",
        boot_sequence=1,
    )
    path = tmp_path / "registry.sqlite3"
    first_store, first = _registry(path, ranger_key=ranger_key, registry_key=registry_key)
    stale_store, stale = _registry(path, ranger_key=ranger_key, registry_key=registry_key)
    first.retain(ranger.list_records(), received_at_utc=NOW + timedelta(minutes=10))

    with pytest.raises(RangerCheckpointConflict, match="registry sequence must be 2"):
        stale.retain(ranger.list_records(), received_at_utc=NOW + timedelta(minutes=10))
    first_store.close()
    stale_store.close()

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE ranger_retained_checkpoints SET boot_sequence = ? WHERE registry_sequence = 1",
        (99,),
    )
    connection.commit()
    connection.close()

    corrupted = SQLiteRangerCheckpointStore(path)
    with pytest.raises(RangerCheckpointIntegrityError, match="index metadata"):
        corrupted.list_checkpoints()
    corrupted.close()
    ranger_store.close()
