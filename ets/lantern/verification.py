from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LanternConsentState(StrEnum):
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"
    NOT_REQUIRED = "not-required"


class LanternVerificationCode(StrEnum):
    VALID = "valid"
    MISSING_PROOF = "missing_proof"
    INVALID_PROOF = "invalid_proof"
    HASH_MISMATCH = "hash_mismatch"
    CONSENT_DENIED = "consent_denied"
    CONSENT_REVOKED = "consent_revoked"
    CONSENT_EXPIRED = "consent_expired"
    APPROVAL_MISSING = "approval_missing"
    SOURCE_UNTRUSTED = "source_untrusted"
    REPLAY_DETECTED = "replay_detected"
    TAMPERED_PAYLOAD = "tampered_payload"
    UNSUPPORTED_EVENT_TYPE = "unsupported_event_type"


@dataclass(frozen=True, slots=True)
class LanternProofBundle:
    event_id: str
    source_system: str
    source_repo: str
    evidence_hash: str
    proof_evidence_hash: str | None
    proof_id: str | None
    consent_state: LanternConsentState
    approval_required: bool
    approval_granted: bool
    source_trusted: bool = True
    replay_detected: bool = False
    supported_event_type: bool = True


@dataclass(frozen=True, slots=True)
class LanternVerificationResult:
    code: LanternVerificationCode
    accepted: bool
    reason: str


def verify_lantern_proof_bundle(bundle: LanternProofBundle) -> LanternVerificationResult:
    if not bundle.supported_event_type:
        return LanternVerificationResult(
            LanternVerificationCode.UNSUPPORTED_EVENT_TYPE,
            False,
            "The Lantern event type is not supported by this verifier.",
        )
    if not bundle.source_trusted:
        return LanternVerificationResult(
            LanternVerificationCode.SOURCE_UNTRUSTED,
            False,
            "The source system or repository is not trusted for Lantern handoff.",
        )
    if bundle.replay_detected:
        return LanternVerificationResult(
            LanternVerificationCode.REPLAY_DETECTED,
            False,
            "The handoff appears to reuse a previously observed event or nonce.",
        )
    if not bundle.proof_id or not bundle.proof_evidence_hash:
        return LanternVerificationResult(
            LanternVerificationCode.MISSING_PROOF,
            False,
            "The handoff is missing an ETS proof reference.",
        )
    if bundle.evidence_hash != bundle.proof_evidence_hash:
        return LanternVerificationResult(
            LanternVerificationCode.HASH_MISMATCH,
            False,
            "The payload evidence hash does not match the ETS proof hash.",
        )
    if bundle.consent_state == LanternConsentState.DENIED:
        return LanternVerificationResult(
            LanternVerificationCode.CONSENT_DENIED,
            False,
            "Consent was denied for the requested Lantern action.",
        )
    if bundle.consent_state == LanternConsentState.REVOKED:
        return LanternVerificationResult(
            LanternVerificationCode.CONSENT_REVOKED,
            False,
            "Consent was revoked for the requested Lantern action.",
        )
    if bundle.consent_state == LanternConsentState.EXPIRED:
        return LanternVerificationResult(
            LanternVerificationCode.CONSENT_EXPIRED,
            False,
            "Consent expired before the requested Lantern action could proceed.",
        )
    if bundle.approval_required and not bundle.approval_granted:
        return LanternVerificationResult(
            LanternVerificationCode.APPROVAL_MISSING,
            False,
            "Human approval is required before this Lantern action can proceed.",
        )
    return LanternVerificationResult(
        LanternVerificationCode.VALID,
        True,
        "The Lantern proof bundle is valid for intake.",
    )
