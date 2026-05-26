from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field


class ConsentEventType(StrEnum):
    REQUESTED = "consent.requested"
    GRANTED = "consent.granted"
    DENIED = "consent.denied"
    REVOKED = "consent.revoked"
    EXPIRED = "consent.expired"


class VerificationReasonCode(StrEnum):
    OK = "ok"
    MISSING_PROOF = "missing-proof"
    HASH_MISMATCH = "hash-mismatch"
    CONSENT_MISSING = "consent-missing"
    CONSENT_DENIED = "consent-denied"
    CONSENT_REVOKED = "consent-revoked"
    CONSENT_EXPIRED = "consent-expired"
    APPROVAL_REQUIRED = "approval-required"
    REPLAY_DETECTED = "replay-detected"
    UNKNOWN_SOURCE = "unknown-source"


class LanternVerificationStatus(StrEnum):
    PASSED = "passed"
    QUARANTINED = "quarantined"
    BLOCKED = "blocked"
    HOLD_FOR_APPROVAL = "hold-for-approval"


class LanternModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True, extra="forbid")


class ConsentEvent(LanternModel):
    event_type: ConsentEventType = Field(alias="eventType")
    consent_id: str = Field(alias="consentId", min_length=1)
    workspace_id: str = Field(alias="workspaceId", min_length=1)
    subject_id: str = Field(alias="subjectId", min_length=1)
    granted_to: str = Field(alias="grantedTo", min_length=1)
    scope: str = Field(min_length=1)
    source_event_id: str = Field(alias="sourceEventId", min_length=1)
    evidence_hash: str = Field(alias="evidenceHash", pattern=r"^[0-9a-f]{64}$")
    expires_at: datetime | None = Field(alias="expiresAt", default=None)
    created_at: datetime = Field(
        alias="createdAt",
        default_factory=lambda: datetime.now(UTC),
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        comparison_time = now or datetime.now(UTC)
        return self.expires_at <= comparison_time


class LanternProofBundle(LanternModel):
    proof_id: str = Field(alias="proofId", min_length=1)
    source_event_id: str = Field(alias="sourceEventId", min_length=1)
    artifact_hash: str = Field(alias="artifactHash", pattern=r"^[0-9a-f]{64}$")
    consent_event_id: str | None = Field(alias="consentEventId", default=None)
    approval_state: str = Field(alias="approvalState", default="not-required")
    merkle_inclusion_proof: dict[str, Any] = Field(
        alias="merkleInclusionProof",
        default_factory=dict,
    )
    verification_result: str | None = Field(alias="verificationResult", default=None)


class LanternVerificationResult(LanternModel):
    status: LanternVerificationStatus
    reason_code: VerificationReasonCode = Field(alias="reasonCode")
    message: str
    proof_id: str | None = Field(alias="proofId", default=None)
    consent_id: str | None = Field(alias="consentId", default=None)


APPROVAL_REQUIRED_STATES = {"required", "pending"}
CONSENT_REQUIRED_ACTIONS = {
    "customer-message",
    "publication",
    "property-operation",
    "vendor-coordination",
    "financial-action",
    "deployment",
    "data-export",
    "memory-write",
}


def verify_lantern_proof_bundle(
    *,
    source_event_id: str,
    evidence_hash: str,
    proof_bundle: LanternProofBundle | None,
    consent_event: ConsentEvent | None = None,
    action_type: str | None = None,
    source_is_registered: bool = True,
    replay_detected: bool = False,
    now: datetime | None = None,
) -> LanternVerificationResult:
    """Validate the Lantern proof, consent, and approval chain.

    This verifier intentionally performs only local deterministic checks. It does not claim to
    validate an external Merkle tree or remote transparency log endpoint. Those checks should wrap
    this function once the transport is available.
    """

    if not source_is_registered:
        return LanternVerificationResult(
            status=LanternVerificationStatus.QUARANTINED,
            reasonCode=VerificationReasonCode.UNKNOWN_SOURCE,
            message="Source system is not registered for Lantern handoff.",
        )

    if replay_detected:
        return LanternVerificationResult(
            status=LanternVerificationStatus.BLOCKED,
            reasonCode=VerificationReasonCode.REPLAY_DETECTED,
            message="Replay nonce or proof was already used.",
        )

    if proof_bundle is None:
        return LanternVerificationResult(
            status=LanternVerificationStatus.QUARANTINED,
            reasonCode=VerificationReasonCode.MISSING_PROOF,
            message="Cross-system Lantern item is missing an ETS proof bundle.",
        )

    if (
        proof_bundle.source_event_id != source_event_id
        or proof_bundle.artifact_hash != evidence_hash
    ):
        return LanternVerificationResult(
            status=LanternVerificationStatus.BLOCKED,
            reasonCode=VerificationReasonCode.HASH_MISMATCH,
            message="Proof bundle does not match the supplied source event or evidence hash.",
            proofId=proof_bundle.proof_id,
        )

    requires_consent = (
        action_type in CONSENT_REQUIRED_ACTIONS
        or proof_bundle.approval_state in APPROVAL_REQUIRED_STATES
    )
    if requires_consent and consent_event is None:
        return LanternVerificationResult(
            status=LanternVerificationStatus.HOLD_FOR_APPROVAL,
            reasonCode=VerificationReasonCode.CONSENT_MISSING,
            message="Action requires consent, but no consent event was supplied.",
            proofId=proof_bundle.proof_id,
        )

    if consent_event is not None:
        if (
            consent_event.evidence_hash != evidence_hash
            or consent_event.source_event_id != source_event_id
        ):
            return LanternVerificationResult(
                status=LanternVerificationStatus.BLOCKED,
                reasonCode=VerificationReasonCode.HASH_MISMATCH,
                message="Consent event does not match source event or evidence hash.",
                proofId=proof_bundle.proof_id,
                consentId=consent_event.consent_id,
            )
        if consent_event.event_type == ConsentEventType.DENIED:
            return LanternVerificationResult(
                status=LanternVerificationStatus.BLOCKED,
                reasonCode=VerificationReasonCode.CONSENT_DENIED,
                message="Consent was denied for this scope.",
                proofId=proof_bundle.proof_id,
                consentId=consent_event.consent_id,
            )
        if consent_event.event_type == ConsentEventType.REVOKED:
            return LanternVerificationResult(
                status=LanternVerificationStatus.BLOCKED,
                reasonCode=VerificationReasonCode.CONSENT_REVOKED,
                message="Consent was revoked for this scope.",
                proofId=proof_bundle.proof_id,
                consentId=consent_event.consent_id,
            )
        if consent_event.event_type == ConsentEventType.EXPIRED or consent_event.is_expired(now):
            return LanternVerificationResult(
                status=LanternVerificationStatus.BLOCKED,
                reasonCode=VerificationReasonCode.CONSENT_EXPIRED,
                message="Consent is expired for this scope.",
                proofId=proof_bundle.proof_id,
                consentId=consent_event.consent_id,
            )
        if requires_consent and consent_event.event_type != ConsentEventType.GRANTED:
            return LanternVerificationResult(
                status=LanternVerificationStatus.HOLD_FOR_APPROVAL,
                reasonCode=VerificationReasonCode.APPROVAL_REQUIRED,
                message="Consent has not yet been granted for this scope.",
                proofId=proof_bundle.proof_id,
                consentId=consent_event.consent_id,
            )

    return LanternVerificationResult(
        status=LanternVerificationStatus.PASSED,
        reasonCode=VerificationReasonCode.OK,
        message="Lantern proof, consent, and approval checks passed.",
        proofId=proof_bundle.proof_id,
        consentId=consent_event.consent_id if consent_event else None,
    )


class LanternConsentState(StrEnum):
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"
    MISSING = "missing"


class LanternVerificationCode(StrEnum):
    VALID = "valid"
    MISSING_PROOF = "missing-proof"
    HASH_MISMATCH = "hash-mismatch"
    CONSENT_REVOKED = "consent-revoked"
    CONSENT_DENIED = "consent-denied"
    CONSENT_EXPIRED = "consent-expired"
    APPROVAL_MISSING = "approval-missing"


@dataclass(frozen=True)
class LegacyLanternProofBundle:
    event_id: str
    source_system: str
    source_repo: str
    evidence_hash: str
    proof_evidence_hash: str
    proof_id: str | None
    consent_state: LanternConsentState
    approval_required: bool
    approval_granted: bool


@dataclass(frozen=True)
class LegacyLanternVerificationResult:
    accepted: bool
    code: LanternVerificationCode


def verify_legacy_lantern_proof_bundle(
    bundle: LegacyLanternProofBundle,
) -> LegacyLanternVerificationResult:
    if bundle.proof_id is None:
        return LegacyLanternVerificationResult(False, LanternVerificationCode.MISSING_PROOF)
    if bundle.proof_evidence_hash != bundle.evidence_hash:
        return LegacyLanternVerificationResult(False, LanternVerificationCode.HASH_MISMATCH)
    if bundle.consent_state == LanternConsentState.REVOKED:
        return LegacyLanternVerificationResult(False, LanternVerificationCode.CONSENT_REVOKED)
    if bundle.consent_state == LanternConsentState.DENIED:
        return LegacyLanternVerificationResult(False, LanternVerificationCode.CONSENT_DENIED)
    if bundle.consent_state == LanternConsentState.EXPIRED:
        return LegacyLanternVerificationResult(False, LanternVerificationCode.CONSENT_EXPIRED)
    if bundle.approval_required and not bundle.approval_granted:
        return LegacyLanternVerificationResult(False, LanternVerificationCode.APPROVAL_MISSING)
    return LegacyLanternVerificationResult(True, LanternVerificationCode.VALID)


_verification_module = cast(Any, types.ModuleType("ets.lantern.verification"))
_verification_module.LanternConsentState = LanternConsentState
_verification_module.LanternProofBundle = LegacyLanternProofBundle
_verification_module.LanternVerificationCode = LanternVerificationCode
_verification_module.verify_lantern_proof_bundle = verify_legacy_lantern_proof_bundle
sys.modules["ets.lantern.verification"] = _verification_module
