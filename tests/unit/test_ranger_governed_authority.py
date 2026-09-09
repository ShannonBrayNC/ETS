import hashlib
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

from ets.core.canonical_json import canonical_sha256
from ets.ranger.governance import (
    RangerGovernanceSubjectKind,
    build_administrative_approval,
    build_trusted_time_attestation,
)
from ets.ranger.governed_authority import (
    RangerGovernedAuthorityAcceptance,
    RangerGovernedAuthorityError,
    build_governed_authority_acceptance,
    verify_governed_authority_acceptance,
)
from ets.ranger.key_authority import (
    RangerKeyAuthorityLedger,
    RangerKeyBindingIntent,
    RangerKeyEventKind,
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
AUTHORITY_ID = "ets-identity-authority:ranger-research"
AUTHORITY_KEY_ID = "ranger-authority-software-key-1"
ADMIN_ID = "ets-administrator:ranger-research"
ADMIN_KEY_ID = "ranger-admin-software-key-1"
TIME_SOURCE_ID = "ets-time:ranger-research"
TIME_KEY_ID = "ranger-time-software-key-1"


def _private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def _private_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()


def _public_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _descriptor(key: Ed25519PrivateKey, key_id: str) -> RangerSigningKeyDescriptor:
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return RangerSigningKeyDescriptor(
        signing_key_id=key_id,
        public_key_hex=public.hex(),
        public_key_fingerprint_sha256=hashlib.sha256(public).hexdigest(),
    )


def _governed_fixture(tmp_path: Path):
    authority_key = _private_key()
    ranger_key = _private_key()
    admin_key = _private_key()
    time_key = _private_key()

    store = SQLiteRangerKeyAuthorityStore(tmp_path / "authority.db")
    ledger = RangerKeyAuthorityLedger(
        store,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        authority_id=AUTHORITY_ID,
        authority_signing_key_id=AUTHORITY_KEY_ID,
        authority_private_key_hex=_private_hex(authority_key),
    )

    descriptor = _descriptor(ranger_key, "ranger-custody-key-1")
    intent = RangerKeyBindingIntent(
        request_id="enroll-1",
        event_kind=RangerKeyEventKind.ENROLL,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        effective_boot_sequence=1,
        subject_key=descriptor,
        recorded_at_utc=NOW - timedelta(seconds=5),
        clock_quality=ClockQuality.SYNCHRONIZED,
        clock_source="local-clock-observation",
        clock_uncertainty_ms=25,
    )
    request = build_key_binding_request(
        intent,
        subject_key_proof_signature_hex=ranger_key.sign(
            key_binding_intent_bytes(intent)
        ).hex(),
    )
    approval = build_administrative_approval(
        request,
        approval_id="approval-1",
        administrator_id=ADMIN_ID,
        administrator_signing_key_id=ADMIN_KEY_ID,
        administrator_private_key_hex=_private_hex(admin_key),
    )
    approval_time = build_trusted_time_attestation(
        attestation_id="time-approval-1",
        subject_kind=RangerGovernanceSubjectKind.ADMINISTRATIVE_APPROVAL,
        subject_digest_sha256=approval.approval_digest_sha256,
        observed_at_utc=NOW,
        uncertainty_ms=10,
        time_source_id=TIME_SOURCE_ID,
        time_signing_key_id=TIME_KEY_ID,
        time_private_key_hex=_private_hex(time_key),
    )

    event = ledger.append(request)
    event_time = build_trusted_time_attestation(
        attestation_id="time-event-1",
        subject_kind=RangerGovernanceSubjectKind.KEY_AUTHORITY_EVENT,
        subject_digest_sha256=event.event_digest_sha256,
        observed_at_utc=NOW + timedelta(seconds=1),
        uncertainty_ms=10,
        time_source_id=TIME_SOURCE_ID,
        time_signing_key_id=TIME_KEY_ID,
        time_private_key_hex=_private_hex(time_key),
    )

    return {
        "store": store,
        "ledger": ledger,
        "history": [event],
        "approval": approval,
        "approval_time": approval_time,
        "event_time": event_time,
        "authority_key": authority_key,
        "admin_key": admin_key,
        "time_key": time_key,
    }


def _build(case):
    return build_governed_authority_acceptance(
        case["history"],
        case["approval"],
        case["approval_time"],
        case["event_time"],
        authority_public_key_hex=_public_hex(case["authority_key"]),
        administrator_public_key_hex=_public_hex(case["admin_key"]),
        time_public_key_hex=_public_hex(case["time_key"]),
    )


def _verify(case, acceptance):
    return verify_governed_authority_acceptance(
        acceptance,
        case["history"],
        case["approval"],
        case["approval_time"],
        case["event_time"],
        authority_public_key_hex=_public_hex(case["authority_key"]),
        administrator_public_key_hex=_public_hex(case["admin_key"]),
        time_public_key_hex=_public_hex(case["time_key"]),
    )


def test_governed_authority_acceptance_composes_signed_proofs(tmp_path: Path) -> None:
    case = _governed_fixture(tmp_path)
    acceptance = _build(case)
    verification = _verify(case, acceptance)

    assert verification.valid
    assert verification.authority_history_integrity_proven
    assert verification.authority_acceptance_proven
    assert verification.authenticated_administration_proven
    assert verification.trusted_time_proven
    assert verification.approval_precedes_acceptance_proven
    assert acceptance.acceptance_digest_sha256 == canonical_sha256(
        acceptance.model_dump(mode="json", exclude={"acceptance_digest_sha256"})
    )
    assert not acceptance.operational_device_authorization_proven
    assert not acceptance.globally_current_history_proven
    assert not acceptance.global_clock_correctness_proven
    assert not acceptance.semantic_truth_proven
    assert not acceptance.physical_outcome_proven


def test_build_rejects_wrong_event_time_subject(tmp_path: Path) -> None:
    case = _governed_fixture(tmp_path)
    event = case["history"][-1]
    case["event_time"] = build_trusted_time_attestation(
        attestation_id="wrong-subject-kind",
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256=event.event_digest_sha256,
        observed_at_utc=NOW + timedelta(seconds=1),
        uncertainty_ms=10,
        time_source_id=TIME_SOURCE_ID,
        time_signing_key_id=TIME_KEY_ID,
        time_private_key_hex=_private_hex(case["time_key"]),
    )

    with pytest.raises(RangerGovernedAuthorityError, match="wrong subject kind"):
        _build(case)


def test_build_rejects_time_attestation_for_different_event(tmp_path: Path) -> None:
    case = _governed_fixture(tmp_path)
    wrong = build_trusted_time_attestation(
        attestation_id="wrong-event-time",
        subject_kind=RangerGovernanceSubjectKind.KEY_AUTHORITY_EVENT,
        subject_digest_sha256="a" * 64,
        observed_at_utc=NOW + timedelta(seconds=1),
        uncertainty_ms=10,
        time_source_id=TIME_SOURCE_ID,
        time_signing_key_id=TIME_KEY_ID,
        time_private_key_hex=_private_hex(case["time_key"]),
    )
    case["event_time"] = wrong

    with pytest.raises(RangerGovernedAuthorityError, match="different event"):
        _build(case)


def test_build_rejects_overlapping_time_intervals(tmp_path: Path) -> None:
    case = _governed_fixture(tmp_path)
    event = case["history"][-1]
    case["event_time"] = build_trusted_time_attestation(
        attestation_id="overlap",
        subject_kind=RangerGovernanceSubjectKind.KEY_AUTHORITY_EVENT,
        subject_digest_sha256=event.event_digest_sha256,
        observed_at_utc=NOW,
        uncertainty_ms=10,
        time_source_id=TIME_SOURCE_ID,
        time_signing_key_id=TIME_KEY_ID,
        time_private_key_hex=_private_hex(case["time_key"]),
    )

    with pytest.raises(RangerGovernedAuthorityError, match="overlap or invert"):
        _build(case)


def test_build_rejects_distinct_time_authority_identity(tmp_path: Path) -> None:
    case = _governed_fixture(tmp_path)
    event = case["history"][-1]
    case["event_time"] = build_trusted_time_attestation(
        attestation_id="other-time-source",
        subject_kind=RangerGovernanceSubjectKind.KEY_AUTHORITY_EVENT,
        subject_digest_sha256=event.event_digest_sha256,
        observed_at_utc=NOW + timedelta(seconds=1),
        uncertainty_ms=10,
        time_source_id="ets-time:other-source",
        time_signing_key_id=TIME_KEY_ID,
        time_private_key_hex=_private_hex(case["time_key"]),
    )

    with pytest.raises(RangerGovernedAuthorityError, match="one configured time authority"):
        _build(case)


def test_build_rejects_wrong_administrator_key(tmp_path: Path) -> None:
    case = _governed_fixture(tmp_path)
    wrong_admin = _private_key()

    with pytest.raises(RangerGovernedAuthorityError, match="administrator public key"):
        build_governed_authority_acceptance(
            case["history"],
            case["approval"],
            case["approval_time"],
            case["event_time"],
            authority_public_key_hex=_public_hex(case["authority_key"]),
            administrator_public_key_hex=_public_hex(wrong_admin),
            time_public_key_hex=_public_hex(case["time_key"]),
        )


def test_build_rejects_tampered_authority_history(tmp_path: Path) -> None:
    case = _governed_fixture(tmp_path)
    case["history"] = [
        case["history"][0].model_copy(update={"authority_signature_hex": "0" * 128})
    ]

    with pytest.raises(RangerGovernedAuthorityError, match="authority history invalid"):
        _build(case)


def test_verify_rejects_manifest_tampering(tmp_path: Path) -> None:
    case = _governed_fixture(tmp_path)
    acceptance = _build(case)
    tampered = RangerGovernedAuthorityAcceptance.model_validate(
        {
            **acceptance.model_dump(),
            "administrator_id": "ets-administrator:substituted",
        }
    )

    verification = _verify(case, tampered)
    assert not verification.valid
    assert "manifest does not match signed inputs" in verification.reason
