import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from pydantic import ValidationError

from ets.ranger.custody import (
    RangerBootCheckpoint,
    RangerCustodyConflict,
    RangerCustodyError,
    RangerCustodyIntegrityError,
    RangerCustodyLedger,
    RangerCustodyRecord,
    SQLiteRangerCustodyStore,
)
from ets.ranger.lifecycle import RangerLifecycleController
from ets.ranger.mobility import (
    ClockQuality,
    MotionVector,
    RangerDriveCommand,
    RangerMobilityController,
    RangerMobilityPolicy,
)
from ets.ranger.simulation import RangerMobilitySimulator

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
VEHICLE_ID = "ets-ranger:r0-001"
MISSION_ID = "mission-alpha"
BOOT_ID = "boot-1"
KEY_ID = "ranger-software-key-1"


def _key_hex() -> str:
    return Ed25519PrivateKey.generate().private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption(),
    ).hex()


def _source_events():
    controller = RangerMobilityController(
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        controller_id="operator-console-1",
        controller_session_id="controller-session-1",
        boot_id=BOOT_ID,
        policy=RangerMobilityPolicy(
            policy_id="ranger-r0-test",
            policy_version="1",
            max_linear_speed_mps=2.0,
            max_yaw_rate_rad_s=1.0,
            max_command_queue_age_ms=250,
            watchdog_timeout_ms=500,
            allow_reverse=True,
        ),
        local_clock_quality=ClockQuality.SYNCHRONIZED,
    )
    lifecycle = RangerLifecycleController(controller)
    armed = lifecycle.arm(
        now_monotonic_ns=1_000_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    command = RangerDriveCommand(
        command_id="cmd-1",
        command_sequence=1,
        mission_id=MISSION_ID,
        vehicle_id=VEHICLE_ID,
        controller_id="operator-console-1",
        controller_session_id="controller-session-1",
        issued_at_utc=NOW,
        source_clock_quality=ClockQuality.SYNCHRONIZED,
        deadman_asserted=True,
        requested_motion=MotionVector(linear_speed_mps=1.0, yaw_rate_rad_s=0.0),
    )
    mobility, transition = lifecycle.authorize(
        command,
        received_monotonic_ns=1_010_000_000,
        evaluated_monotonic_ns=1_020_000_000,
        evaluated_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    assert transition is None
    simulator = RangerMobilitySimulator(
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        boot_id=BOOT_ID,
        producer_id="simulator-1",
        simulation_session_id="simulation-session-1",
    )
    step = simulator.apply(mobility, step_duration_ms=100)
    return armed, mobility, step.actuator_response, step.simulated_result


def _ledger(path, key: str) -> tuple[SQLiteRangerCustodyStore, RangerCustodyLedger]:
    store = SQLiteRangerCustodyStore(path)
    ledger = RangerCustodyLedger(
        store,
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        boot_id=BOOT_ID,
        signing_key_id=KEY_ID,
        private_key_hex=key,
    )
    return store, ledger


def test_signed_chain_preserves_all_existing_source_profiles_and_recovers(tmp_path) -> None:
    path = tmp_path / "ranger-custody.sqlite3"
    key = _key_hex()
    store, ledger = _ledger(path, key)
    appended = [ledger.append(event) for event in _source_events()]

    assert [record.custody_sequence for record in appended] == [1, 2, 3, 4]
    assert [record.source_schema_version for record in appended] == [
        "ets.ranger.lifecycle-event.v1",
        "ets.ranger.mobility-event.v1",
        "ets.ranger.actuator-response.v1",
        "ets.ranger.simulated-result.v1",
    ]
    assert appended[0].previous_record_digest_sha256 == "0" * 64
    assert appended[-1].hardware_backed_key is False
    assert appended[-1].encrypted_at_rest is False
    assert appended[-1].physical_outcome_proven is False
    verification = ledger.verify_chain(appended, ledger.public_key_hex)
    assert verification.valid
    assert verification.record_count == 4
    assert verification.head_digest_sha256 == appended[-1].record_digest_sha256
    public_key_hex = ledger.public_key_hex
    store.close()

    reopened_store, reopened = _ledger(path, key)
    assert reopened.public_key_hex == public_key_hex
    assert reopened.list_records() == appended
    reopened_store.close()


def test_verifier_rejects_tampering_missing_duplicate_reordering_and_wrong_key(tmp_path) -> None:
    store, ledger = _ledger(tmp_path / "custody.sqlite3", _key_hex())
    records = [ledger.append(event) for event in _source_events()]

    tampered = records[1].model_copy(update={"signature_hex": "00" * 64})
    assert not ledger.verify_chain([records[0], tampered], ledger.public_key_hex).valid
    assert not ledger.verify_chain([records[0], records[2]], ledger.public_key_hex).valid
    assert not ledger.verify_chain([records[0], records[0]], ledger.public_key_hex).valid
    assert not ledger.verify_chain(list(reversed(records)), ledger.public_key_hex).valid

    wrong_private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(_key_hex()))
    wrong_public = wrong_private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    assert not ledger.verify_chain(records, wrong_public).valid
    store.close()


def test_source_mutation_with_retained_digest_fails_schema_validation(tmp_path) -> None:
    store, ledger = _ledger(tmp_path / "custody.sqlite3", _key_hex())
    record = ledger.append(_source_events()[1])
    changed_source = record.source_event.model_copy(update={"event_id": "mutated"})
    changed = record.model_copy(update={"source_event": changed_source})
    with pytest.raises(ValidationError, match="source_event_id"):
        type(record).model_validate(changed.model_dump())
    store.close()


def test_duplicate_source_and_stale_writer_fail_closed(tmp_path) -> None:
    path = tmp_path / "custody.sqlite3"
    key = _key_hex()
    store1, first = _ledger(path, key)
    store2, stale = _ledger(path, key)
    source = _source_events()[0]
    first.append(source)

    with pytest.raises(RangerCustodyConflict, match="sequence must be 2"):
        stale.append(source)
    with pytest.raises(RangerCustodyConflict, match="duplicate Ranger source"):
        first.append(source)
    store1.close()
    store2.close()


def test_identity_mismatch_is_rejected_before_signing(tmp_path) -> None:
    store, ledger = _ledger(tmp_path / "custody.sqlite3", _key_hex())
    foreign = _source_events()[0].model_copy(update={"mission_id": "other-mission"})
    with pytest.raises(RangerCustodyError, match="identity mismatch"):
        ledger.append(foreign)
    assert ledger.list_records() == []
    store.close()


def test_corrupted_retained_json_is_rejected_on_recovery(tmp_path) -> None:
    path = tmp_path / "custody.sqlite3"
    key = _key_hex()
    store, ledger = _ledger(path, key)
    ledger.append(_source_events()[0])
    store.close()

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE ranger_custody_records SET record_json = ? WHERE custody_sequence = 1",
        ('{"corrupted":true}',),
    )
    connection.commit()
    connection.close()

    corrupted = SQLiteRangerCustodyStore(path)
    with pytest.raises(RangerCustodyIntegrityError, match="stored Ranger custody record"):
        RangerCustodyLedger(
            corrupted,
            vehicle_id=VEHICLE_ID,
            mission_id=MISSION_ID,
            boot_id=BOOT_ID,
            signing_key_id=KEY_ID,
            private_key_hex=key,
        )
    corrupted.close()


def test_tampered_unsigned_index_metadata_is_rejected_on_recovery(tmp_path) -> None:
    path = tmp_path / "custody.sqlite3"
    key = _key_hex()
    store, ledger = _ledger(path, key)
    ledger.append(_source_events()[0])
    store.close()

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE ranger_custody_records SET source_event_id = ? WHERE custody_sequence = 1",
        ("forged-index-identity",),
    )
    connection.commit()
    connection.close()

    corrupted = SQLiteRangerCustodyStore(path)
    with pytest.raises(RangerCustodyIntegrityError, match="index metadata"):
        corrupted.list_records()
    corrupted.close()


def test_recovery_rejects_wrong_key_or_chain_identity(tmp_path) -> None:
    path = tmp_path / "custody.sqlite3"
    key = _key_hex()
    store, ledger = _ledger(path, key)
    ledger.append(_source_events()[0])
    store.close()

    wrong_key_store = SQLiteRangerCustodyStore(path)
    with pytest.raises(RangerCustodyIntegrityError, match="custody chain is invalid"):
        RangerCustodyLedger(
            wrong_key_store,
            vehicle_id=VEHICLE_ID,
            mission_id=MISSION_ID,
            boot_id=BOOT_ID,
            signing_key_id=KEY_ID,
            private_key_hex=_key_hex(),
        )
    wrong_key_store.close()

    wrong_boot_store = SQLiteRangerCustodyStore(path)
    with pytest.raises(RangerCustodyIntegrityError, match="identity or signing key mismatch"):
        RangerCustodyLedger(
            wrong_boot_store,
            vehicle_id=VEHICLE_ID,
            mission_id=MISSION_ID,
            boot_id="boot-2",
            signing_key_id=KEY_ID,
            private_key_hex=key,
        )
    wrong_boot_store.close()


def test_clock_qualified_checkpoint_links_consecutive_boot_chains(tmp_path) -> None:
    key = _key_hex()
    first_store, first = _ledger(tmp_path / "boot-1.sqlite3", key)
    first_checkpoint = first.append_boot_checkpoint(
        checkpoint_id="checkpoint-1",
        boot_sequence=1,
        started_at_utc=NOW,
        clock_quality=ClockQuality.SYNCHRONIZED,
        clock_source="authenticated-ntp-candidate",
        clock_uncertainty_ms=25,
    )
    first.append(_source_events()[0])

    second_store = SQLiteRangerCustodyStore(tmp_path / "boot-2.sqlite3")
    second = RangerCustodyLedger(
        second_store,
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        boot_id="boot-2",
        signing_key_id=KEY_ID,
        private_key_hex=key,
    )
    second_checkpoint = second.append_boot_checkpoint(
        checkpoint_id="checkpoint-2",
        boot_sequence=2,
        started_at_utc=NOW + timedelta(minutes=1),
        clock_quality=ClockQuality.ESTIMATED,
        clock_source="holdover-clock",
        clock_uncertainty_ms=750,
        previous_boot_id=BOOT_ID,
        previous_custody_head_digest_sha256=first.list_records()[-1].record_digest_sha256,
    )

    result = RangerCustodyLedger.verify_boot_continuity(
        first.list_records(), second.list_records(), first.public_key_hex
    )
    assert result.valid
    assert result.previous_boot_id == BOOT_ID
    assert result.current_boot_id == "boot-2"
    assert result.previous_head_digest_sha256 == first.list_records()[-1].record_digest_sha256
    assert isinstance(first_checkpoint.source_event, RangerBootCheckpoint)
    assert isinstance(second_checkpoint.source_event, RangerBootCheckpoint)
    assert second_checkpoint.source_event.trusted_time_proven is False
    assert second_checkpoint.source_event.external_head_witnessed is False
    assert second_checkpoint.source_event.complete_capture_proven is False
    first_store.close()
    second_store.close()


def test_continuity_rejects_substituted_head_stale_time_and_boot_sequence(tmp_path) -> None:
    key = _key_hex()
    first_store, first = _ledger(tmp_path / "first.sqlite3", key)
    first.append_boot_checkpoint(
        checkpoint_id="checkpoint-1",
        boot_sequence=1,
        started_at_utc=NOW,
        clock_quality=ClockQuality.DEGRADED,
        clock_source="rtc",
        clock_uncertainty_ms=5_000,
    )

    def current_records(*, head: str, sequence: int, started_at: datetime):
        store = SQLiteRangerCustodyStore(
            tmp_path / f"current-{head[:4]}-{sequence}-{started_at.minute}.sqlite3"
        )
        ledger = RangerCustodyLedger(
            store,
            vehicle_id=VEHICLE_ID,
            mission_id=MISSION_ID,
            boot_id=f"boot-{sequence}",
            signing_key_id=KEY_ID,
            private_key_hex=key,
        )
        ledger.append_boot_checkpoint(
            checkpoint_id=f"checkpoint-{sequence}-{head[:4]}-{started_at.minute}",
            boot_sequence=sequence,
            started_at_utc=started_at,
            clock_quality=ClockQuality.SYNCHRONIZED,
            clock_source="ntp",
            clock_uncertainty_ms=10,
            previous_boot_id=BOOT_ID,
            previous_custody_head_digest_sha256=head,
        )
        records = ledger.list_records()
        store.close()
        return records

    expected_head = first.list_records()[-1].record_digest_sha256
    substituted = current_records(
        head="f" * 64, sequence=2, started_at=NOW + timedelta(seconds=1)
    )
    stale = current_records(head=expected_head, sequence=2, started_at=NOW)
    skipped = current_records(
        head=expected_head, sequence=3, started_at=NOW + timedelta(seconds=1)
    )

    assert not RangerCustodyLedger.verify_boot_continuity(
        first.list_records(), substituted, first.public_key_hex
    ).valid
    assert not RangerCustodyLedger.verify_boot_continuity(
        first.list_records(), stale, first.public_key_hex
    ).valid
    assert not RangerCustodyLedger.verify_boot_continuity(
        first.list_records(), skipped, first.public_key_hex
    ).valid
    first_store.close()


def test_checkpoint_requires_consistent_clock_and_predecessor_claims() -> None:
    common = {
        "checkpoint_id": "checkpoint",
        "vehicle_id": VEHICLE_ID,
        "mission_id": MISSION_ID,
        "boot_id": BOOT_ID,
        "started_at_utc": NOW,
        "clock_source": "local-clock",
    }
    with pytest.raises(ValidationError, match="cannot claim bounded uncertainty"):
        RangerBootCheckpoint(
            **common,
            boot_sequence=1,
            clock_quality=ClockQuality.UNKNOWN,
            clock_uncertainty_ms=1,
        )
    with pytest.raises(ValidationError, match="requires clock_uncertainty_ms"):
        RangerBootCheckpoint(
            **common,
            boot_sequence=1,
            clock_quality=ClockQuality.SYNCHRONIZED,
        )
    with pytest.raises(ValidationError, match="requires the previous boot and custody head"):
        RangerBootCheckpoint(
            **common,
            boot_sequence=2,
            clock_quality=ClockQuality.UNKNOWN,
            previous_boot_id="prior-boot",
        )


def test_continuity_rejects_missing_checkpoint_identity_or_key_change(tmp_path) -> None:
    key = _key_hex()
    first_store, first = _ledger(tmp_path / "first.sqlite3", key)
    first.append_boot_checkpoint(
        checkpoint_id="checkpoint-1",
        boot_sequence=1,
        started_at_utc=NOW,
        clock_quality=ClockQuality.UNKNOWN,
        clock_source="unqualified-local-clock",
    )

    legacy_store, legacy = _ledger(tmp_path / "legacy.sqlite3", key)
    legacy.append(_source_events()[0])
    missing = RangerCustodyLedger.verify_boot_continuity(
        first.list_records(), legacy.list_records(), first.public_key_hex
    )
    assert not missing.valid
    assert "boot checkpoint" in missing.reason

    changed_store = SQLiteRangerCustodyStore(tmp_path / "changed.sqlite3")
    changed = RangerCustodyLedger(
        changed_store,
        vehicle_id=VEHICLE_ID,
        mission_id="other-mission",
        boot_id="boot-2",
        signing_key_id=KEY_ID,
        private_key_hex=key,
    )
    changed.append_boot_checkpoint(
        checkpoint_id="checkpoint-2",
        boot_sequence=2,
        started_at_utc=NOW + timedelta(seconds=1),
        clock_quality=ClockQuality.UNKNOWN,
        clock_source="unqualified-local-clock",
        previous_boot_id=BOOT_ID,
        previous_custody_head_digest_sha256=first.list_records()[-1].record_digest_sha256,
    )
    identity = RangerCustodyLedger.verify_boot_continuity(
        first.list_records(), changed.list_records(), first.public_key_hex
    )
    assert not identity.valid
    assert "identity changed" in identity.reason

    wrong_key = _key_hex()
    wrong_store = SQLiteRangerCustodyStore(tmp_path / "wrong-key.sqlite3")
    wrong = RangerCustodyLedger(
        wrong_store,
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        boot_id="boot-2",
        signing_key_id=KEY_ID,
        private_key_hex=wrong_key,
    )
    wrong.append_boot_checkpoint(
        checkpoint_id="checkpoint-wrong-key",
        boot_sequence=2,
        started_at_utc=NOW + timedelta(seconds=1),
        clock_quality=ClockQuality.UNKNOWN,
        clock_source="unqualified-local-clock",
        previous_boot_id=BOOT_ID,
        previous_custody_head_digest_sha256=first.list_records()[-1].record_digest_sha256,
    )
    key_result = RangerCustodyLedger.verify_boot_continuity(
        first.list_records(), wrong.list_records(), first.public_key_hex
    )
    assert not key_result.valid
    assert "current custody chain is invalid" in key_result.reason

    renamed_store = SQLiteRangerCustodyStore(tmp_path / "renamed-key.sqlite3")
    renamed = RangerCustodyLedger(
        renamed_store,
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        boot_id="boot-2",
        signing_key_id="renamed-software-key",
        private_key_hex=key,
    )
    renamed.append_boot_checkpoint(
        checkpoint_id="checkpoint-renamed-key",
        boot_sequence=2,
        started_at_utc=NOW + timedelta(seconds=1),
        clock_quality=ClockQuality.UNKNOWN,
        clock_source="unqualified-local-clock",
        previous_boot_id=BOOT_ID,
        previous_custody_head_digest_sha256=first.list_records()[-1].record_digest_sha256,
    )
    renamed_result = RangerCustodyLedger.verify_boot_continuity(
        first.list_records(), renamed.list_records(), first.public_key_hex
    )
    assert not renamed_result.valid
    assert "signing key identity changed" in renamed_result.reason
    first_store.close()
    legacy_store.close()
    changed_store.close()
    wrong_store.close()
    renamed_store.close()


def test_boot_checkpoint_must_be_first_and_signing_is_deterministic(tmp_path) -> None:
    key = _key_hex()
    first_store, first = _ledger(tmp_path / "first.sqlite3", key)
    first_record = first.append_boot_checkpoint(
        checkpoint_id="checkpoint-1",
        boot_sequence=1,
        started_at_utc=NOW,
        clock_quality=ClockQuality.SYNCHRONIZED,
        clock_source="ntp",
        clock_uncertainty_ms=20,
    )
    with pytest.raises(RangerCustodyConflict, match="must be the first"):
        first.append_boot_checkpoint(
            checkpoint_id="checkpoint-late",
            boot_sequence=1,
            started_at_utc=NOW,
            clock_quality=ClockQuality.UNKNOWN,
            clock_source="local",
        )

    late_checkpoint = RangerBootCheckpoint(
        checkpoint_id="checkpoint-direct-bypass",
        vehicle_id=VEHICLE_ID,
        mission_id=MISSION_ID,
        boot_id=BOOT_ID,
        boot_sequence=2,
        started_at_utc=NOW + timedelta(seconds=1),
        clock_quality=ClockQuality.UNKNOWN,
        clock_source="local",
        previous_boot_id="prior-boot",
        previous_custody_head_digest_sha256="f" * 64,
    )
    with pytest.raises(RangerCustodyConflict, match="must be the first"):
        first.append(late_checkpoint)

    misplaced_record = first_record.model_copy(update={"custody_sequence": 2})
    with pytest.raises(ValidationError, match="must be the first custody record"):
        RangerCustodyRecord.model_validate(misplaced_record.model_dump())

    replay_store, replay = _ledger(tmp_path / "replay.sqlite3", key)
    replay_record = replay.append_boot_checkpoint(
        checkpoint_id="checkpoint-1",
        boot_sequence=1,
        started_at_utc=NOW,
        clock_quality=ClockQuality.SYNCHRONIZED,
        clock_source="ntp",
        clock_uncertainty_ms=20,
    )
    assert replay_record == first_record
    first_store.close()
    replay_store.close()
