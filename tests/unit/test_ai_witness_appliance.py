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
from pydantic import ValidationError

from ets.ai_witness.appliance import (
    ApplianceClockQuality,
    BootEvidence,
    ClockEvidence,
    FleetEnrollment,
    FleetEnrollmentExpectation,
    HardwareKeyEvidence,
    HardwareKeyPurpose,
    PCRMeasurement,
    RuntimeAdapterIdentity,
    RuntimeAuthMethod,
    TimeProtocol,
    TPMAttestationEvidence,
    UpdateManifest,
    UpdateTrustPolicy,
    assess_pilot_readiness,
    enrollment_payload,
    sha256_hex,
    update_manifest_payload,
    verify_fleet_enrollment,
    verify_update_manifest,
    verify_update_target,
)
from ets.ai_witness.durable_queue import (
    DuplicateWitnessRecord,
    EncryptedWitnessQueue,
    QueueIntegrityError,
)
from ets.ai_witness.models import AIWitnessEvent, DigestRef, ModelIdentity, WitnessEventKind
from ets.ai_witness.service import AIWitnessLedger
from ets.core.api import canonicalize

NOW = datetime(2026, 8, 21, 7, 0, tzinfo=UTC)
TARGET = b"appliance-image"


def private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def private_key_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption(),
    ).hex()


def public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def digest(text: str) -> DigestRef:
    raw = text.encode("utf-8")
    return DigestRef(digest=hashlib.sha256(raw).hexdigest(), byte_length=len(raw))


def signed_record():
    key = private_key()
    ledger = AIWitnessLedger(
        witness_id="ets-aiw:pilot-1",
        signing_key_id="tpm:witness-signing-1",
        private_key_hex=private_key_hex(key),
    )
    event = AIWitnessEvent(
        witness_id="ets-aiw:pilot-1",
        session_id="session-1",
        event_id="event-1",
        sequence=0,
        kind=WitnessEventKind.MODEL_REQUEST,
        workload_ref="svc:pilot",
        occurred_at=NOW,
        observed_at=NOW,
        model=ModelIdentity(provider="openai", model="gpt-test"),
        input_digests=(digest("sensitive prompt"),),
    )
    return ledger.record(event)


def hardware_key(
    purpose: HardwareKeyPurpose,
    key_id: str,
    *,
    non_exportable: bool = True,
    hardware_backed: bool = True,
) -> HardwareKeyEvidence:
    fingerprint = "d" * 64 if purpose is HardwareKeyPurpose.WITNESS_SIGNING else None
    return HardwareKeyEvidence(
        key_id=key_id,
        purpose=purpose,
        hardware_backed=hardware_backed,
        non_exportable=non_exportable,
        public_key_fingerprint_sha256=fingerprint,
        observed_at=NOW,
    )


def tpm_evidence(*, non_exportable: bool = True) -> TPMAttestationEvidence:
    return TPMAttestationEvidence(
        manufacturer="example-tpm",
        firmware_version="1.0",
        attestation_key_id="tpm:ak:1",
        attestation_key_fingerprint_sha256="1" * 64,
        attestation_key_non_exportable=non_exportable,
        pcrs=(PCRMeasurement(index=0, digest="2" * 64),),
        quote_digest_sha256="3" * 64,
        event_log_digest_sha256="4" * 64,
        qualifying_nonce_digest_sha256="5" * 64,
        observed_at=NOW,
    )


def boot_evidence() -> BootEvidence:
    return BootEvidence(
        boot_id="boot-1",
        firmware_vendor="example-firmware",
        secure_boot_enabled=True,
        measured_boot_enabled=True,
        tpm_event_log_present=True,
        kernel_measurement_present=True,
        observed_at=NOW,
    )


def clock_evidence() -> ClockEvidence:
    return ClockEvidence(
        source="time.example.test",
        protocol=TimeProtocol.NTS,
        authenticated_transport=True,
        quality=ApplianceClockQuality.SYNCHRONIZED,
        offset_ms=2.5,
        uncertainty_ms=10.0,
        last_sync_at=NOW - timedelta(seconds=30),
        observed_at=NOW,
    )


def adapter_identity() -> RuntimeAdapterIdentity:
    return RuntimeAdapterIdentity(
        adapter_id="openai-api",
        adapter_version="1.0",
        provider="openai",
        workload_ref="svc:pilot",
        auth_method=RuntimeAuthMethod.OAUTH2_WORKLOAD_IDENTITY,
        authenticated=True,
        peer_identity="spiffe://example/workload/pilot",
        tenant_id="tenant-1",
        workspace_id="workspace-1",
    )


def sign_enrollment(key: Ed25519PrivateKey) -> FleetEnrollment:
    provisional = FleetEnrollment(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        fleet_id="fleet-1",
        gateway_id="gateway-1",
        witness_id="ets-aiw:pilot-1",
        device_key_fingerprint_sha256="6" * 64,
        enrollment_nonce_digest_sha256="7" * 64,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        signing_key_id="gateway-enrollment-1",
        signature_hex="0" * 128,
    )
    signature = key.sign(canonicalize(enrollment_payload(provisional))).hex()
    return FleetEnrollment.model_validate(
        {**provisional.model_dump(), "signature_hex": signature}
    )


def enrollment_expectation() -> FleetEnrollmentExpectation:
    return FleetEnrollmentExpectation(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        fleet_id="fleet-1",
        gateway_id="gateway-1",
        witness_id="ets-aiw:pilot-1",
        device_key_fingerprint_sha256="6" * 64,
        enrollment_nonce_digest_sha256="7" * 64,
        signing_key_id="gateway-enrollment-1",
    )


def sign_update(
    key: Ed25519PrivateKey,
    *,
    release_sequence: int = 3,
    metadata_version: int = 3,
    expires_at: datetime | None = None,
) -> UpdateManifest:
    provisional = UpdateManifest(
        release_sequence=release_sequence,
        release_version="1.1.0",
        target_sha256=sha256_hex(TARGET),
        target_size_bytes=len(TARGET),
        metadata_version=metadata_version,
        expires_at=expires_at or NOW + timedelta(days=1),
        signing_key_id="update-root-1",
        signature_hex="0" * 128,
    )
    signature = key.sign(canonicalize(update_manifest_payload(provisional))).hex()
    return UpdateManifest.model_validate(
        {**provisional.model_dump(), "signature_hex": signature}
    )


def update_policy() -> UpdateTrustPolicy:
    return UpdateTrustPolicy(
        signing_key_id="update-root-1",
        current_release_sequence=2,
        current_metadata_version=2,
    )


def test_pilot_readiness_passes_with_required_evidence() -> None:
    result = assess_pilot_readiness(
        tpm=tpm_evidence(),
        evidence_signing_key=hardware_key(
            HardwareKeyPurpose.WITNESS_SIGNING,
            "tpm:witness-signing-1",
        ),
        queue_sealing_key=hardware_key(
            HardwareKeyPurpose.QUEUE_SEALING,
            "tpm:queue-sealing-1",
        ),
        boot=boot_evidence(),
        clock=clock_evidence(),
        adapter=adapter_identity(),
        enrollment_verified=True,
    )
    assert result.ready
    assert result.violations == ()
    assert result.warnings == ()


def test_pilot_readiness_rejects_exportable_key_and_insecure_boot() -> None:
    boot = boot_evidence().model_copy(update={"secure_boot_enabled": False})
    result = assess_pilot_readiness(
        tpm=tpm_evidence(),
        evidence_signing_key=hardware_key(
            HardwareKeyPurpose.WITNESS_SIGNING,
            "tpm:witness-signing-1",
            non_exportable=False,
        ),
        queue_sealing_key=hardware_key(
            HardwareKeyPurpose.QUEUE_SEALING,
            "tpm:queue-sealing-1",
        ),
        boot=boot,
        clock=clock_evidence(),
        adapter=adapter_identity(),
        enrollment_verified=True,
    )
    assert not result.ready
    assert "hardware key tpm:witness-signing-1 is exportable" in result.violations
    assert "UEFI Secure Boot is not enabled" in result.violations


def test_pilot_readiness_rejects_reused_signing_and_sealing_key() -> None:
    shared_id = "tpm:shared-key"
    result = assess_pilot_readiness(
        tpm=tpm_evidence(),
        evidence_signing_key=hardware_key(HardwareKeyPurpose.WITNESS_SIGNING, shared_id),
        queue_sealing_key=hardware_key(HardwareKeyPurpose.QUEUE_SEALING, shared_id),
        boot=boot_evidence(),
        clock=clock_evidence(),
        adapter=adapter_identity(),
        enrollment_verified=True,
    )
    assert not result.ready
    assert "Witness signing and queue sealing must use distinct keys" in result.violations


def test_nts_clock_requires_authenticated_transport() -> None:
    with pytest.raises(ValidationError):
        ClockEvidence(
            source="time.example.test",
            protocol=TimeProtocol.NTS,
            authenticated_transport=False,
            quality=ApplianceClockQuality.SYNCHRONIZED,
            offset_ms=0.0,
            uncertainty_ms=1.0,
            last_sync_at=NOW,
            observed_at=NOW,
        )


def test_runtime_adapter_must_be_authenticated() -> None:
    payload = adapter_identity().model_dump(mode="json")
    payload["authenticated"] = False
    with pytest.raises(ValidationError):
        RuntimeAdapterIdentity.model_validate(payload)


def test_fleet_enrollment_is_signed_scoped_and_time_bounded() -> None:
    key = private_key()
    enrollment = sign_enrollment(key)
    expected = enrollment_expectation()
    assert verify_fleet_enrollment(
        enrollment,
        public_key_hex(key),
        expected=expected,
        now=NOW,
    )
    assert not verify_fleet_enrollment(
        enrollment,
        public_key_hex(private_key()),
        expected=expected,
        now=NOW,
    )
    assert not verify_fleet_enrollment(
        enrollment,
        public_key_hex(key),
        expected=expected,
        now=NOW + timedelta(hours=2),
    )


def test_fleet_enrollment_rejects_scope_device_and_nonce_mismatch() -> None:
    key = private_key()
    enrollment = sign_enrollment(key)
    expected = enrollment_expectation()
    mismatches = (
        {"tenant_id": "tenant-2"},
        {"workspace_id": "workspace-2"},
        {"fleet_id": "fleet-2"},
        {"gateway_id": "gateway-2"},
        {"witness_id": "ets-aiw:pilot-2"},
        {"device_key_fingerprint_sha256": "8" * 64},
        {"enrollment_nonce_digest_sha256": "9" * 64},
        {"signing_key_id": "gateway-enrollment-2"},
    )
    for change in mismatches:
        mismatched = expected.model_copy(update=change)
        assert not verify_fleet_enrollment(
            enrollment,
            public_key_hex(key),
            expected=mismatched,
            now=NOW,
        )


def test_update_manifest_binds_signer_freshness_and_target() -> None:
    key = private_key()
    update = sign_update(key)
    policy = update_policy()
    assert verify_update_manifest(
        update,
        public_key_hex(key),
        policy=policy,
        now=NOW,
    )
    assert verify_update_target(update, TARGET)
    assert not verify_update_target(update, TARGET + b"-tampered")
    same_length_tamper = b"X" * len(TARGET)
    assert not verify_update_target(update, same_length_tamper)


def test_update_manifest_rejects_rollback_expiry_signer_and_tampering() -> None:
    key = private_key()
    policy = update_policy()

    release_rollback = sign_update(key, release_sequence=2, metadata_version=3)
    assert not verify_update_manifest(
        release_rollback,
        public_key_hex(key),
        policy=policy,
        now=NOW,
    )

    metadata_rollback = sign_update(key, release_sequence=3, metadata_version=2)
    assert not verify_update_manifest(
        metadata_rollback,
        public_key_hex(key),
        policy=policy,
        now=NOW,
    )

    update = sign_update(key)
    wrong_signer = policy.model_copy(update={"signing_key_id": "update-root-2"})
    assert not verify_update_manifest(
        update,
        public_key_hex(key),
        policy=wrong_signer,
        now=NOW,
    )

    tampered = update.model_copy(update={"target_sha256": "8" * 64})
    assert not verify_update_manifest(
        tampered,
        public_key_hex(key),
        policy=policy,
        now=NOW,
    )

    expired = sign_update(key, expires_at=NOW - timedelta(seconds=1))
    assert not verify_update_manifest(
        expired,
        public_key_hex(key),
        policy=policy,
        now=NOW,
    )


def test_encrypted_queue_survives_restart_and_hides_record_structure(tmp_path: Path) -> None:
    queue_path = tmp_path / "witness-queue.db"
    key_material = "9" * 64
    record = signed_record()
    with EncryptedWitnessQueue(
        queue_path,
        key_material_hex=key_material,
        key_id="tpm:sealed-queue-1",
    ) as queue:
        queue.enqueue(record)
        assert queue.depth() == 1

    database_bytes = queue_path.read_bytes()
    assert b"model_request" not in database_bytes

    with EncryptedWitnessQueue(
        queue_path,
        key_material_hex=key_material,
        key_id="tpm:sealed-queue-1",
    ) as reopened:
        assert reopened.peek() == (record,)
        assert reopened.ack(record.record_digest)
        assert reopened.depth() == 0


def test_encrypted_queue_rejects_duplicate_and_wrong_key(tmp_path: Path) -> None:
    queue_path = tmp_path / "witness-queue.db"
    record = signed_record()
    queue = EncryptedWitnessQueue(
        queue_path,
        key_material_hex="a" * 64,
        key_id="tpm:sealed-queue-1",
    )
    queue.enqueue(record)
    with pytest.raises(DuplicateWitnessRecord):
        queue.enqueue(record)
    queue.close()

    with pytest.raises(QueueIntegrityError):
        EncryptedWitnessQueue(
            queue_path,
            key_material_hex="b" * 64,
            key_id="tpm:sealed-queue-1",
        )


def test_encrypted_queue_detects_ciphertext_tampering(tmp_path: Path) -> None:
    queue_path = tmp_path / "witness-queue.db"
    key_material = "c" * 64
    record = signed_record()
    queue = EncryptedWitnessQueue(
        queue_path,
        key_material_hex=key_material,
        key_id="tpm:sealed-queue-1",
    )
    queue.enqueue(record)
    queue.close()

    db = sqlite3.connect(queue_path)
    row = db.execute("SELECT id, ciphertext FROM witness_queue LIMIT 1").fetchone()
    assert row is not None
    ciphertext = bytearray(row[1])
    ciphertext[-1] ^= 1
    db.execute(
        "UPDATE witness_queue SET ciphertext = ? WHERE id = ?",
        (bytes(ciphertext), row[0]),
    )
    db.commit()
    db.close()

    with EncryptedWitnessQueue(
        queue_path,
        key_material_hex=key_material,
        key_id="tpm:sealed-queue-1",
    ) as reopened:
        with pytest.raises(QueueIntegrityError):
            reopened.peek()
