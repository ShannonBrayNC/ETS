import sqlite3
from datetime import UTC, datetime

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
    RangerCustodyConflict,
    RangerCustodyError,
    RangerCustodyIntegrityError,
    RangerCustodyLedger,
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
