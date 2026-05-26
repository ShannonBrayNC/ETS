from ets.lantern.verification import (
    LanternConsentState,
    LanternProofBundle,
    LanternVerificationCode,
    verify_lantern_proof_bundle,
)

HASH = "c" * 64


def make_bundle(**overrides):
    values = {
        "event_id": "evt-1",
        "source_system": "opshelm",
        "source_repo": "ShannonBrayNC/OpsHelm",
        "evidence_hash": HASH,
        "proof_evidence_hash": HASH,
        "proof_id": "proof-1",
        "consent_state": LanternConsentState.GRANTED,
        "approval_required": True,
        "approval_granted": True,
    }
    values.update(overrides)
    return LanternProofBundle(**values)


def test_valid_bundle_is_accepted():
    result = verify_lantern_proof_bundle(make_bundle())

    assert result.accepted is True
    assert result.code == LanternVerificationCode.VALID


def test_missing_proof_is_rejected():
    result = verify_lantern_proof_bundle(make_bundle(proof_id=None))

    assert result.accepted is False
    assert result.code == LanternVerificationCode.MISSING_PROOF


def test_hash_mismatch_is_rejected():
    result = verify_lantern_proof_bundle(make_bundle(proof_evidence_hash="d" * 64))

    assert result.accepted is False
    assert result.code == LanternVerificationCode.HASH_MISMATCH


def test_revoked_consent_is_rejected():
    result = verify_lantern_proof_bundle(
        make_bundle(consent_state=LanternConsentState.REVOKED)
    )

    assert result.accepted is False
    assert result.code == LanternVerificationCode.CONSENT_REVOKED


def test_missing_required_approval_is_rejected():
    result = verify_lantern_proof_bundle(make_bundle(approval_granted=False))

    assert result.accepted is False
    assert result.code == LanternVerificationCode.APPROVAL_MISSING
