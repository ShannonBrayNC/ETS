import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from pydantic import ValidationError

from ets.black_box import (
    BlackBoxObservation,
    BlackBoxPolicy,
    BlackBoxProductionReadinessError,
    BlackBoxRecorder,
    BlackBoxValidationError,
    InMemoryBlackBoxStore,
    SQLiteBlackBoxStore,
    SealReason,
    TriggerKind,
)

DEVICE = "ets-black-box:test-unit"
NOW = datetime(2026, 8, 21, 7, 0, tzinfo=UTC)


def key_hex() -> str:
    return Ed25519PrivateKey.generate().private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    ).hex()


def observation(
    i: int,
    *,
    boot_id: str = "boot-1",
    attributes: dict[str, object] | None = None,
) -> BlackBoxObservation:
    content = f"payload-{i}".encode()
    return BlackBoxObservation(
        device_id=DEVICE,
        boot_id=boot_id,
        observation_id=f"obs-{i}",
        source_system="controller:test",
        event_type="telemetry.sample",
        subject_ref="asset:test",
        observed_at_utc=NOW + timedelta(milliseconds=i),
        monotonic_ns=i + 1,
        content_hash_sha256=hashlib.sha256(content).hexdigest(),
        content_byte_length=len(content),
        attributes=attributes or {"sample": i},
    )


def recorder(
    store: InMemoryBlackBoxStore | SQLiteBlackBoxStore,
    key: str,
    *,
    pre: int = 3,
    post: int = 2,
    boot_id: str = "boot-1",
    boot_counter: int = 1,
) -> BlackBoxRecorder:
    return BlackBoxRecorder(
        store,
        device_id=DEVICE,
        signing_key_id="key-1",
        private_key_hex=key,
        boot_id=boot_id,
        boot_counter=boot_counter,
        policy=BlackBoxPolicy(pre_trigger_frames=pre, post_trigger_frames=post),
        clock=lambda: NOW + timedelta(seconds=30),
    )


def test_rolling_window_keeps_only_configured_pretrigger_frames() -> None:
    store = InMemoryBlackBoxStore()
    bb = recorder(store, key_hex(), pre=3)
    for i in range(5):
        bb.record(observation(i))
    assert [frame.sequence for frame in store.list_live_frames()] == [3, 4, 5]
    assert bb.status().sealed_segment_count == 0


def test_trigger_freezes_pre_window_and_auto_seals_post_window() -> None:
    store = InMemoryBlackBoxStore()
    bb = recorder(store, key_hex(), pre=3, post=2)
    for i in range(5):
        bb.record(observation(i))
    assert bb.trigger(trigger_id="incident-1", kind=TriggerKind.FAULT, reason="watchdog") is None
    bb.record(observation(5))
    bb.record(observation(6))
    segment = bb.list_segments()[0]
    assert [frame.sequence for frame in segment.frames] == [3, 4, 5, 6, 7]
    assert segment.manifest.trigger.trigger_sequence == 5
    assert segment.manifest.seal_reason == SealReason.POST_WINDOW_COMPLETE
    assert bb.verify_segment(segment, bb.public_key_hex).valid
    assert not bb.status().capture_active


def test_tampering_and_wrong_key_fail_verification() -> None:
    store = InMemoryBlackBoxStore()
    key = key_hex()
    bb = recorder(store, key, post=0)
    bb.record(observation(0))
    segment = bb.trigger(trigger_id="incident-1", kind=TriggerKind.SECURITY, reason="tamper")
    assert segment is not None
    wrong = recorder(InMemoryBlackBoxStore(), key_hex())
    assert not bb.verify_segment(segment, wrong.public_key_hex).valid
    frame = segment.frames[0]
    changed = frame.model_copy(update={"frame_hash": "0" * 64})
    tampered = segment.model_copy(update={"frames": (changed,)})
    assert not bb.verify_segment(tampered, bb.public_key_hex).valid


def test_digest_only_contract_rejects_raw_payload_fields() -> None:
    payload = observation(0).model_dump()
    payload["raw_payload"] = "secret bytes"
    with pytest.raises(ValidationError):
        BlackBoxObservation.model_validate(payload)


def test_monotonic_clock_must_increase_and_copied_models_are_revalidated() -> None:
    store = InMemoryBlackBoxStore()
    bb = recorder(store, key_hex())
    bb.record(observation(1))
    with pytest.raises(BlackBoxValidationError, match="monotonic_ns"):
        bb.record(observation(0))
    invalid = observation(2).model_copy(update={"device_id": "ets-edge:other"})
    with pytest.raises(ValidationError):
        bb.record(invalid)


def test_oversized_observation_fails_before_signing() -> None:
    store = InMemoryBlackBoxStore()
    key = key_hex()
    bb = BlackBoxRecorder(
        store,
        device_id=DEVICE,
        signing_key_id="key-1",
        private_key_hex=key,
        boot_id="boot-1",
        boot_counter=1,
        policy=BlackBoxPolicy(
            pre_trigger_frames=3,
            post_trigger_frames=2,
            max_observation_bytes=1024,
        ),
    )
    rich = observation(0, attributes={f"k{i}": "x" * 100 for i in range(20)})
    with pytest.raises(BlackBoxValidationError, match="size limit"):
        bb.record(rich)
    assert bb.state.last_sequence == 0


def test_power_loss_imminent_force_seals_partial_window() -> None:
    store = InMemoryBlackBoxStore()
    bb = recorder(store, key_hex(), pre=2, post=5)
    for i in range(3):
        bb.record(observation(i))
    bb.trigger(trigger_id="power-1", kind=TriggerKind.POWER_LOSS, reason="brownout")
    bb.record(observation(3))
    segment = bb.force_seal(SealReason.POWER_LOSS_IMMINENT)
    assert segment.manifest.seal_reason == SealReason.POWER_LOSS_IMMINENT
    assert [frame.sequence for frame in segment.frames] == [2, 3, 4]
    assert bb.verify_segment(segment, bb.public_key_hex).valid


def test_sqlite_restart_recovers_active_trigger_and_completes_seal(tmp_path) -> None:
    path = tmp_path / "black-box.sqlite3"
    key = key_hex()
    store1 = SQLiteBlackBoxStore(path)
    bb1 = recorder(store1, key, pre=2, post=2)
    bb1.record(observation(0))
    bb1.record(observation(1))
    bb1.trigger(trigger_id="restart-1", kind=TriggerKind.WATCHDOG, reason="reset")
    bb1.record(observation(2))
    store1.close()

    store2 = SQLiteBlackBoxStore(path)
    bb2 = recorder(store2, key, pre=2, post=2, boot_id="boot-2", boot_counter=2)
    assert bb2.status().capture_active
    bb2.record(observation(3, boot_id="boot-2"))
    segments = bb2.list_segments()
    assert len(segments) == 1
    assert [frame.sequence for frame in segments[0].frames] == [1, 2, 3, 4]
    assert bb2.verify_segment(segments[0], bb2.public_key_hex).valid
    store2.close()


def test_boot_counter_rollback_and_boot_id_reuse_fail_closed() -> None:
    store = InMemoryBlackBoxStore()
    key = key_hex()
    recorder(store, key)
    with pytest.raises(BlackBoxValidationError, match="boot_id changed"):
        recorder(store, key, boot_id="boot-other", boot_counter=1)
    recorder(store, key, boot_id="boot-2", boot_counter=2)
    with pytest.raises(BlackBoxValidationError, match="rollback"):
        recorder(store, key, boot_id="boot-1", boot_counter=1)


def test_production_mode_rejects_reference_backends(tmp_path) -> None:
    key = key_hex()
    policy = BlackBoxPolicy(require_production_backend=True)
    with pytest.raises(BlackBoxProductionReadinessError):
        BlackBoxRecorder(
            InMemoryBlackBoxStore(),
            device_id=DEVICE,
            signing_key_id="key-1",
            private_key_hex=key,
            boot_id="boot-1",
            boot_counter=1,
            policy=policy,
        )
    sqlite = SQLiteBlackBoxStore(tmp_path / "prod.sqlite3")
    with pytest.raises(BlackBoxProductionReadinessError):
        BlackBoxRecorder(
            sqlite,
            device_id=DEVICE,
            signing_key_id="key-1",
            private_key_hex=key,
            boot_id="boot-1",
            boot_counter=1,
            policy=policy,
        )
    sqlite.close()


def test_core_projection_contains_manifest_not_frame_attributes() -> None:
    store = InMemoryBlackBoxStore()
    bb = recorder(store, key_hex(), post=0)
    bb.record(observation(0, attributes={"private_detail": "do-not-project"}))
    segment = bb.trigger(trigger_id="incident-1", kind=TriggerKind.MANUAL, reason="operator")
    assert segment is not None
    event = bb.to_evidence_event(segment, tenant_id="tenant", workspace_id="workspace")
    serialized = str(event.model_dump(mode="json"))
    assert event.content_hash == segment.manifest.segment_hash
    assert event.redaction_profile == "none"
    assert "private_detail" not in serialized
    assert "do-not-project" not in serialized
    assert "operator" not in serialized


def test_sequence_removal_invalidates_segment() -> None:
    store = InMemoryBlackBoxStore()
    bb = recorder(store, key_hex(), pre=3, post=1)
    for i in range(3):
        bb.record(observation(i))
    bb.trigger(trigger_id="incident-1", kind=TriggerKind.CRASH, reason="impact")
    bb.record(observation(3))
    segment = bb.list_segments()[0]
    removed = segment.model_copy(update={"frames": (segment.frames[0], *segment.frames[2:])})
    result = bb.verify_segment(removed, bb.public_key_hex)
    assert not result.valid
