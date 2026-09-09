from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from ets.ranger import timed_retained_receipts as target
from ets.ranger.authority_checkpoint import (
    RangerAuthorityBoundCheckpoint,
    RangerAuthorityCheckpointChainVerification,
)
from ets.ranger.authority_head import (
    RangerAuthorityHeadChainVerification,
    RangerRetainedAuthorityHead,
)
from ets.ranger.governance import (
    RangerGovernanceSubjectKind,
    build_trusted_time_attestation,
)

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
VEHICLE_ID = "ets-ranger:r0-001"
TENANT_ID = "tenant-ranger-research"
WORKSPACE_ID = "workspace-r0"
MISSION_ID = "mission-alpha"
AUTHORITY_ID = "ets-identity-authority:ranger-research"
AUTHORITY_KEY_ID = "ranger-authority-software-key-1"
REGISTRY_ID = "ets-verifier:ranger-registry-1"
REGISTRY_KEY_ID = "registry-software-key-1"
TIME_SOURCE_ID = "ets-time:ranger-configured-1"
TIME_KEY_ID = "time-software-key-1"


def _private_key_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()


def _public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _authority_head() -> RangerRetainedAuthorityHead:
    return RangerRetainedAuthorityHead(
        registry_sequence=1,
        previous_checkpoint_digest_sha256="0" * 64,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        authority_event_count=1,
        authority_history_head_digest_sha256="1" * 64,
        authority_id=AUTHORITY_ID,
        authority_signing_key_id=AUTHORITY_KEY_ID,
        authority_public_key_fingerprint_sha256="2" * 64,
        received_at_utc=NOW,
        registry_id=REGISTRY_ID,
        registry_signing_key_id=REGISTRY_KEY_ID,
        registry_public_key_fingerprint_sha256="3" * 64,
        authority_history_integrity_verified=True,
        retained_state_advanced=False,
        freshness_scope="registry_baseline",
        checkpoint_digest_sha256="a" * 64,
        signature_hex="b" * 128,
    )


def _authority_checkpoint() -> RangerAuthorityBoundCheckpoint:
    return RangerAuthorityBoundCheckpoint(
        registry_sequence=1,
        previous_checkpoint_digest_sha256="0" * 64,
        vehicle_id=VEHICLE_ID,
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        mission_id=MISSION_ID,
        boot_id="boot-1",
        boot_sequence=1,
        custody_record_count=1,
        custody_head_digest_sha256="4" * 64,
        ranger_signing_key_id="ranger-key-1",
        ranger_public_key_fingerprint_sha256="5" * 64,
        previous_boot_id=None,
        previous_custody_head_digest_sha256=None,
        authority_head_registry_sequence=1,
        authority_head_checkpoint_digest_sha256="a" * 64,
        authority_event_count=1,
        authority_history_head_digest_sha256="1" * 64,
        authority_id=AUTHORITY_ID,
        authority_signing_key_id=AUTHORITY_KEY_ID,
        authority_public_key_fingerprint_sha256="2" * 64,
        received_at_utc=NOW,
        registry_id=REGISTRY_ID,
        registry_signing_key_id=REGISTRY_KEY_ID,
        registry_public_key_fingerprint_sha256="3" * 64,
        ranger_chain_integrity_verified=True,
        authority_history_integrity_verified=True,
        authority_relative_key_standing_verified=True,
        authority_history_current_relative_to_registry=True,
        ranger_state_advanced=False,
        authority_state_advanced=False,
        freshness_scope="registry_baseline",
        checkpoint_digest_sha256="c" * 64,
        signature_hex="d" * 128,
    )


def _authority_head_chain_result(
    receipt: RangerRetainedAuthorityHead,
    *,
    valid: bool = True,
) -> RangerAuthorityHeadChainVerification:
    return RangerAuthorityHeadChainVerification(
        valid=valid,
        checkpoint_count=1,
        latest_checkpoint_digest_sha256=(
            receipt.checkpoint_digest_sha256 if valid else None
        ),
        latest_authority_event_count=receipt.authority_event_count if valid else None,
        latest_authority_history_head_digest_sha256=(
            receipt.authority_history_head_digest_sha256 if valid else None
        ),
        freshness_relative_to_retained_state=valid,
        reason="ok" if valid else "synthetic chain failure",
    )


def _authority_checkpoint_chain_result(
    receipt: RangerAuthorityBoundCheckpoint,
    *,
    valid: bool = True,
    authority_bindings_verified: bool = True,
) -> RangerAuthorityCheckpointChainVerification:
    return RangerAuthorityCheckpointChainVerification(
        valid=valid,
        checkpoint_count=1,
        latest_checkpoint_digest_sha256=(
            receipt.checkpoint_digest_sha256 if valid else None
        ),
        latest_boot_sequence=receipt.boot_sequence if valid else None,
        latest_authority_history_head_digest_sha256=(
            receipt.authority_history_head_digest_sha256 if valid else None
        ),
        authority_bindings_verified=authority_bindings_verified if valid else False,
        freshness_relative_to_retained_state=valid,
        reason="ok" if valid else "synthetic chain failure",
    )


def _time_attestation(
    key: Ed25519PrivateKey,
    *,
    subject_kind: RangerGovernanceSubjectKind,
    subject_digest_sha256: str,
    time_source_id: str = TIME_SOURCE_ID,
):
    return build_trusted_time_attestation(
        attestation_id="time-attestation-1",
        subject_kind=subject_kind,
        subject_digest_sha256=subject_digest_sha256,
        observed_at_utc=NOW + timedelta(minutes=1),
        uncertainty_ms=50,
        time_source_id=time_source_id,
        time_signing_key_id=TIME_KEY_ID,
        time_private_key_hex=_private_key_hex(key),
    )


def _patch_authority_head_chain(monkeypatch, receipt, *, valid: bool = True) -> None:
    result = _authority_head_chain_result(receipt, valid=valid)
    monkeypatch.setattr(
        target.RangerAuthorityHeadRegistry,
        "verify_checkpoint_chain",
        staticmethod(lambda checkpoints, public_key: result),
    )


def _patch_authority_checkpoint_chain(
    monkeypatch,
    receipt,
    *,
    valid: bool = True,
    authority_bindings_verified: bool = True,
) -> None:
    result = _authority_checkpoint_chain_result(
        receipt,
        valid=valid,
        authority_bindings_verified=authority_bindings_verified,
    )
    monkeypatch.setattr(
        target.RangerAuthorityCheckpointRegistry,
        "verify_checkpoint_chain",
        staticmethod(lambda checkpoints, public_key: result),
    )


def test_time_attested_authority_head_verifies(monkeypatch) -> None:
    receipt = _authority_head()
    _patch_authority_head_chain(monkeypatch, receipt)
    time_key = Ed25519PrivateKey.generate()
    attestation = _time_attestation(
        time_key,
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
    )

    result = target.verify_time_attested_authority_head(
        [receipt],
        attestation,
        registry_public_key_hex="11" * 32,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex=_public_key_hex(time_key),
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
    )

    assert result.valid
    assert result.receipt_chain_integrity_proven
    assert result.configured_registry_identity_proven
    assert result.registry_relative_freshness_proven
    assert result.trusted_time_proven
    assert result.configured_time_identity_proven
    assert result.receipt_local_time_trusted is False
    assert result.independent_external_custody_proven is False
    assert result.global_clock_correctness_proven is False


def test_time_attested_authority_checkpoint_verifies(monkeypatch) -> None:
    receipt = _authority_checkpoint()
    _patch_authority_checkpoint_chain(monkeypatch, receipt)
    time_key = Ed25519PrivateKey.generate()
    attestation = _time_attestation(
        time_key,
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
    )

    result = target.verify_time_attested_authority_checkpoint(
        [receipt],
        attestation,
        registry_public_key_hex="11" * 32,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex=_public_key_hex(time_key),
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
    )

    assert result.valid
    assert result.receipt_chain_integrity_proven
    assert result.authority_bindings_verified
    assert result.trusted_time_proven
    assert result.complete_capture_proven is False
    assert result.physical_outcome_proven is False


def test_authority_head_rejects_wrong_time_subject(monkeypatch) -> None:
    receipt = _authority_head()
    _patch_authority_head_chain(monkeypatch, receipt)
    time_key = Ed25519PrivateKey.generate()
    attestation = _time_attestation(
        time_key,
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
    )

    result = target.verify_time_attested_authority_head(
        [receipt],
        attestation,
        registry_public_key_hex="11" * 32,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex=_public_key_hex(time_key),
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
    )

    assert not result.valid
    assert "kind" in result.reason or "target" in result.reason


def test_authority_head_rejects_wrong_time_digest(monkeypatch) -> None:
    receipt = _authority_head()
    _patch_authority_head_chain(monkeypatch, receipt)
    time_key = Ed25519PrivateKey.generate()
    attestation = _time_attestation(
        time_key,
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256="f" * 64,
    )

    result = target.verify_time_attested_authority_head(
        [receipt],
        attestation,
        registry_public_key_hex="11" * 32,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex=_public_key_hex(time_key),
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
    )

    assert not result.valid
    assert "digest" in result.reason


def test_authority_head_rejects_registry_identity_substitution(monkeypatch) -> None:
    receipt = _authority_head()
    _patch_authority_head_chain(monkeypatch, receipt)
    time_key = Ed25519PrivateKey.generate()
    attestation = _time_attestation(
        time_key,
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
    )

    result = target.verify_time_attested_authority_head(
        [receipt],
        attestation,
        registry_public_key_hex="11" * 32,
        expected_registry_id="ets-verifier:other-registry",
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex=_public_key_hex(time_key),
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
    )

    assert not result.valid
    assert "registry identity" in result.reason


def test_authority_checkpoint_rejects_time_identity_substitution(monkeypatch) -> None:
    receipt = _authority_checkpoint()
    _patch_authority_checkpoint_chain(monkeypatch, receipt)
    time_key = Ed25519PrivateKey.generate()
    attestation = _time_attestation(
        time_key,
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
        time_source_id="ets-time:other-source",
    )

    result = target.verify_time_attested_authority_checkpoint(
        [receipt],
        attestation,
        registry_public_key_hex="11" * 32,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex=_public_key_hex(time_key),
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
    )

    assert not result.valid
    assert "time authority identity" in result.reason


def test_authority_head_rejects_invalid_retained_chain(monkeypatch) -> None:
    receipt = _authority_head()
    _patch_authority_head_chain(monkeypatch, receipt, valid=False)
    time_key = Ed25519PrivateKey.generate()
    attestation = _time_attestation(
        time_key,
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
    )

    result = target.verify_time_attested_authority_head(
        [receipt],
        attestation,
        registry_public_key_hex="11" * 32,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex=_public_key_hex(time_key),
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
    )

    assert not result.valid
    assert "chain is invalid" in result.reason


def test_authority_checkpoint_requires_verified_authority_binding(monkeypatch) -> None:
    receipt = _authority_checkpoint()
    _patch_authority_checkpoint_chain(
        monkeypatch,
        receipt,
        authority_bindings_verified=False,
    )
    time_key = Ed25519PrivateKey.generate()
    attestation = _time_attestation(
        time_key,
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
    )

    result = target.verify_time_attested_authority_checkpoint(
        [receipt],
        attestation,
        registry_public_key_hex="11" * 32,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex=_public_key_hex(time_key),
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
    )

    assert not result.valid
    assert "does not terminate" in result.reason


def test_authority_head_rejects_wrong_time_key(monkeypatch) -> None:
    receipt = _authority_head()
    _patch_authority_head_chain(monkeypatch, receipt)
    time_key = Ed25519PrivateKey.generate()
    wrong_key = Ed25519PrivateKey.generate()
    attestation = _time_attestation(
        time_key,
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
    )

    result = target.verify_time_attested_authority_head(
        [receipt],
        attestation,
        registry_public_key_hex="11" * 32,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex=_public_key_hex(wrong_key),
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
    )

    assert not result.valid
    assert "fingerprint" in result.reason or "signature" in result.reason
