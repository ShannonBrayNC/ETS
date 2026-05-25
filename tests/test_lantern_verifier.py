from datetime import datetime, timezone

from ets.lantern import (
    ConsentEvent,
    ConsentEventType,
    LanternProofBundle,
    LanternVerificationStatus,
    VerificationReasonCode,
    verify_lantern_proof_bundle,
)

HASH = "c" * 64


def make_proof(**overrides):
    values = {
        "proofId": "proof-1",
        "sourceEventId": "evt-1",
        "artifactHash": HASH,
        "consentEventId": "consent-1",
        "approvalState": "required",
        "merkleInclusionProof": {"leaf": HASH},
    }
    values.update(overrides)
    return LanternProofBundle(**values)


def make_consent(event_type=ConsentEventType.GRANTED, **overrides):
    values = {
        "eventType": event_type,
        "consentId": "consent-1",
        "workspaceId": "default",
        "subjectId": "human-owner",
        "grantedTo": "christina",
        "scope": "customer-message:ticket-12345",
        "sourceEventId": "evt-1",
        "evidenceHash": HASH,
        "createdAt": datetime(2026, 5, 25, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return ConsentEvent(**values)


def test_missing_proof_quarantines_item():
    result = verify_lantern_proof_bundle(
        source_event_id="evt-1",
        evidence_hash=HASH,
        proof_bundle=None,
        action_type="customer-message",
    )

    assert result.status == LanternVerificationStatus.QUARANTINED
    assert result.reason_code == VerificationReasonCode.MISSING_PROOF


def test_hash_mismatch_blocks_item():
    result = verify_lantern_proof_bundle(
        source_event_id="evt-1",
        evidence_hash=HASH,
        proof_bundle=make_proof(artifactHash="d" * 64),
        consent_event=make_consent(),
        action_type="customer-message",
    )

    assert result.status == LanternVerificationStatus.BLOCKED
    assert result.reason_code == VerificationReasonCode.HASH_MISMATCH


def test_granted_consent_passes():
    result = verify_lantern_proof_bundle(
        source_event_id="evt-1",
        evidence_hash=HASH,
        proof_bundle=make_proof(),
        consent_event=make_consent(),
        action_type="customer-message",
    )

    assert result.status == LanternVerificationStatus.PASSED
    assert result.reason_code == VerificationReasonCode.OK


def test_revoked_consent_blocks_item():
    result = verify_lantern_proof_bundle(
        source_event_id="evt-1",
        evidence_hash=HASH,
        proof_bundle=make_proof(),
        consent_event=make_consent(ConsentEventType.REVOKED),
        action_type="customer-message",
    )

    assert result.status == LanternVerificationStatus.BLOCKED
    assert result.reason_code == VerificationReasonCode.CONSENT_REVOKED


def test_unregistered_source_quarantines_item():
    result = verify_lantern_proof_bundle(
        source_event_id="evt-1",
        evidence_hash=HASH,
        proof_bundle=make_proof(),
        consent_event=make_consent(),
        source_is_registered=False,
    )

    assert result.status == LanternVerificationStatus.QUARANTINED
    assert result.reason_code == VerificationReasonCode.UNKNOWN_SOURCE
