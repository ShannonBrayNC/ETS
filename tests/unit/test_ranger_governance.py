"""Focused tests for Ranger authenticated-administration and trusted-time evidence."""

import hashlib
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from ets.ranger.governance import (
    RangerAdministrativeApproval,
    RangerGovernanceError,
    RangerGovernanceSubjectKind,
    RangerTrustedTimeAttestation,
    build_administrative_approval,
    build_trusted_time_attestation,
    verify_administrative_approval,
    verify_governed_key_binding_request,
    verify_retained_receipt_time,
    verify_trusted_time_attestation,
)
from ets.ranger.key_authority import (
    RangerKeyBindingIntent,
    RangerKeyBindingRequest,
    RangerKeyEventKind,
    RangerSigningKeyDescriptor,
    build_key_binding_request,
    key_binding_intent_bytes,
)
from ets.ranger.mobility import ClockQuality


def _private_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()


def _public_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _request(request_id: str = "request-001") -> RangerKeyBindingRequest:
    ranger_key = Ed25519PrivateKey.generate()
    public_bytes = ranger_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    descriptor = RangerSigningKeyDescriptor(
        signing_key_id="ranger-key-001",
        public_key_hex=public_bytes.hex(),
        public_key_fingerprint_sha256=hashlib.sha256(public_bytes).hexdigest(),
    )
    intent = RangerKeyBindingIntent(
        request_id=request_id,
        event_kind=RangerKeyEventKind.ENROLL,
        vehicle_id="ets-ranger:test-unit",
        tenant_id="tenant-test",
        workspace_id="workspace-test",
        effective_boot_sequence=1,
        subject_key=descriptor,
        recorded_at_utc=datetime(2026, 9, 8, 20, 0, tzinfo=UTC),
        clock_quality=ClockQuality.SYNCHRONIZED,
        clock_source="test-local-clock",
        clock_uncertainty_ms=25,
    )
    signature = ranger_key.sign(key_binding_intent_bytes(intent)).hex()
    return build_key_binding_request(intent, subject_key_proof_signature_hex=signature)


def _approval(
    request: RangerKeyBindingRequest,
    admin_key: Ed25519PrivateKey,
) -> RangerAdministrativeApproval:
    return build_administrative_approval(
        request,
        approval_id="approval-001",
        administrator_id="ranger-admin:test",
        administrator_signing_key_id="admin-key-001",
        administrator_private_key_hex=_private_hex(admin_key),
    )


def _time_attestation(
    subject_digest: str,
    time_key: Ed25519PrivateKey,
) -> RangerTrustedTimeAttestation:
    return build_trusted_time_attestation(
        attestation_id="time-001",
        subject_kind=RangerGovernanceSubjectKind.ADMINISTRATIVE_APPROVAL,
        subject_digest_sha256=subject_digest,
        observed_at_utc=datetime(2026, 9, 8, 20, 1, tzinfo=UTC),
        uncertainty_ms=50,
        time_source_id="time-authority:test",
        time_signing_key_id="time-key-001",
        time_private_key_hex=_private_hex(time_key),
    )


def test_governed_request_verifies_admin_and_time_evidence() -> None:
    request = _request()
    admin_key = Ed25519PrivateKey.generate()
    time_key = Ed25519PrivateKey.generate()
    approval = _approval(request, admin_key)
    attestation = _time_attestation(approval.approval_digest_sha256, time_key)

    approval_result = verify_administrative_approval(
        request, approval, _public_hex(admin_key)
    )
    time_result = verify_trusted_time_attestation(attestation, _public_hex(time_key))
    result = verify_governed_key_binding_request(
        request,
        approval,
        attestation,
        administrator_public_key_hex=_public_hex(admin_key),
        time_public_key_hex=_public_hex(time_key),
    )

    assert approval_result.valid
    assert approval_result.authenticated_administration_proven
    assert time_result.valid
    assert time_result.trusted_time_proven
    assert result.valid
    assert result.authenticated_administration_proven
    assert result.trusted_time_proven
    assert not result.authority_acceptance_proven


def test_approval_rejects_different_request() -> None:
    original = _request("request-original")
    replacement = _request("request-replacement")
    admin_key = Ed25519PrivateKey.generate()
    approval = _approval(original, admin_key)

    result = verify_administrative_approval(replacement, approval, _public_hex(admin_key))

    assert not result.valid
    assert "request digest mismatch" in result.reason


def test_approval_rejects_wrong_administrator_key() -> None:
    request = _request()
    admin_key = Ed25519PrivateKey.generate()
    wrong_key = Ed25519PrivateKey.generate()
    approval = _approval(request, admin_key)

    result = verify_administrative_approval(request, approval, _public_hex(wrong_key))

    assert not result.valid
    assert "fingerprint mismatch" in result.reason


def test_approval_rejects_signature_tampering() -> None:
    request = _request()
    admin_key = Ed25519PrivateKey.generate()
    approval = _approval(request, admin_key).model_copy(
        update={"administrator_signature_hex": "00" * 64}
    )

    result = verify_administrative_approval(request, approval, _public_hex(admin_key))

    assert not result.valid
    assert "signature invalid" in result.reason


def test_governed_request_rejects_time_attestation_for_other_approval() -> None:
    request = _request()
    admin_key = Ed25519PrivateKey.generate()
    time_key = Ed25519PrivateKey.generate()
    approval = _approval(request, admin_key)
    attestation = _time_attestation("ab" * 32, time_key)

    result = verify_governed_key_binding_request(
        request,
        approval,
        attestation,
        administrator_public_key_hex=_public_hex(admin_key),
        time_public_key_hex=_public_hex(time_key),
    )

    assert not result.valid
    assert "different administrative approval" in result.reason


def test_time_attestation_rejects_wrong_time_key() -> None:
    time_key = Ed25519PrivateKey.generate()
    wrong_key = Ed25519PrivateKey.generate()
    attestation = build_trusted_time_attestation(
        attestation_id="time-002",
        subject_kind=RangerGovernanceSubjectKind.KEY_AUTHORITY_EVENT,
        subject_digest_sha256="cd" * 32,
        observed_at_utc=datetime(2026, 9, 8, 20, 2, tzinfo=UTC),
        uncertainty_ms=10,
        time_source_id="time-authority:test",
        time_signing_key_id="time-key-001",
        time_private_key_hex=_private_hex(time_key),
    )

    result = verify_trusted_time_attestation(attestation, _public_hex(wrong_key))

    assert not result.valid
    assert "fingerprint mismatch" in result.reason


def test_retained_receipt_time_binds_kind_and_digest() -> None:
    time_key = Ed25519PrivateKey.generate()
    digest = "ef" * 32
    attestation = build_trusted_time_attestation(
        attestation_id="time-retained-001",
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256=digest,
        observed_at_utc=datetime(2026, 9, 8, 20, 3, tzinfo=UTC),
        uncertainty_ms=75,
        time_source_id="time-authority:test",
        time_signing_key_id="time-key-001",
        time_private_key_hex=_private_hex(time_key),
    )

    valid = verify_retained_receipt_time(
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256=digest,
        time_attestation=attestation,
        time_public_key_hex=_public_hex(time_key),
    )
    wrong_kind = verify_retained_receipt_time(
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest_sha256=digest,
        time_attestation=attestation,
        time_public_key_hex=_public_hex(time_key),
    )

    assert valid.valid
    assert valid.trusted_time_proven
    assert not wrong_kind.valid
    assert "kind mismatch" in wrong_kind.reason


def test_time_builder_rejects_naive_datetime() -> None:
    time_key = Ed25519PrivateKey.generate()

    with pytest.raises(RangerGovernanceError, match="timezone-aware"):
        build_trusted_time_attestation(
            attestation_id="time-naive",
            subject_kind=RangerGovernanceSubjectKind.KEY_AUTHORITY_EVENT,
            subject_digest_sha256="12" * 32,
            observed_at_utc=datetime(2026, 9, 8, 20, 4),
            uncertainty_ms=10,
            time_source_id="time-authority:test",
            time_signing_key_id="time-key-001",
            time_private_key_hex=_private_hex(time_key),
        )
