from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from ets.core.canonical_json import canonical_sha256


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


class LanternRecommendationKind(StrEnum):
    SOFTWARE_CHANGE = "software-change"
    PROCESS_CHANGE = "process-change"
    DOCUMENTATION_CHANGE = "documentation-change"
    INVESTIGATION = "investigation"


class LanternRecommendationStatus(StrEnum):
    OPEN = "open"
    ROUTED = "routed"
    IN_REVIEW = "in-review"
    BLOCKED = "blocked"
    CLOSED = "closed"


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


class LanternArtifactHash(LanternModel):
    artifact_id: str = Field(alias="artifactId", min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    kind: str = Field(min_length=1)


class LanternSupportAnalysisRequest(LanternModel):
    lantern_event_id: str = Field(alias="lanternEventId", min_length=1)
    event_type: str = Field(alias="eventType", min_length=1)
    source_system: str = Field(alias="sourceSystem", min_length=1)
    workspace_id: str = Field(alias="workspaceId", min_length=1)
    ticket_ref: str = Field(alias="ticketRef", min_length=1)
    artifact_hashes: list[LanternArtifactHash] = Field(alias="artifactHashes", min_length=1)
    requested_outputs: list[str] = Field(alias="requestedOutputs", min_length=1)
    approval_state: str = Field(alias="approvalState", default="required")
    consent_id: str | None = Field(alias="consentId", default=None)
    correlation_id: str | None = Field(alias="correlationId", default=None)


class LanternOutputArtifact(LanternModel):
    artifact_hash: str = Field(alias="artifactHash", pattern=r"^[0-9a-f]{64}$")
    approval_required: bool = Field(alias="approvalRequired")
    approval_state: str = Field(alias="approvalState")
    source_artifact_ids: list[str] = Field(alias="sourceArtifactIds")


class LanternTechnicalFinding(LanternModel):
    code: str
    summary: str
    evidence_hash: str = Field(alias="evidenceHash", pattern=r"^[0-9a-f]{64}$")


class LanternRecommendedAction(LanternModel):
    action_type: str = Field(alias="actionType")
    summary: str
    approval_required: bool = Field(alias="approvalRequired")


class LanternKBCandidate(LanternModel):
    title: str
    evidence_hash: str = Field(alias="evidenceHash", pattern=r"^[0-9a-f]{64}$")
    reuse_scope: str = Field(alias="reuseScope")
    approval_required: bool = Field(alias="approvalRequired")


class LanternMemoryObservation(LanternModel):
    observation_type: str = Field(alias="type")
    summary: str
    evidence_hash: str = Field(alias="evidenceHash", pattern=r"^[0-9a-f]{64}$")


class LanternSupportOutputs(LanternModel):
    customer_summary: LanternOutputArtifact | None = Field(alias="customerSummary", default=None)
    internal_summary: LanternOutputArtifact | None = Field(alias="internalSummary", default=None)
    technical_findings: list[LanternTechnicalFinding] = Field(
        alias="technicalFindings",
        default_factory=list,
    )
    recommended_actions: list[LanternRecommendedAction] = Field(
        alias="recommendedActions",
        default_factory=list,
    )
    kb_candidates: list[LanternKBCandidate] = Field(alias="kbCandidates", default_factory=list)


class LanternSupportAnalysisResponse(LanternModel):
    lantern_event_id: str = Field(alias="lanternEventId")
    status: LanternVerificationStatus
    reason_code: VerificationReasonCode = Field(alias="reasonCode")
    proof_bundle_url: str = Field(alias="proofBundleUrl")
    outputs: LanternSupportOutputs
    metrics: dict[str, int]
    memory_observations: list[LanternMemoryObservation] = Field(alias="memoryObservations")


class LanternRecommendationNote(LanternModel):
    author: str = Field(min_length=1)
    note: str = Field(min_length=1)
    created_at: datetime = Field(alias="createdAt", default_factory=lambda: datetime.now(UTC))


class LanternRecommendation(LanternModel):
    recommendation_id: str = Field(alias="recommendationId", min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    item_type: LanternRecommendationKind = Field(alias="itemType")
    priority: str = Field(min_length=1)
    source: str = Field(min_length=1)
    status: LanternRecommendationStatus
    owner_repo: str = Field(alias="ownerRepo", min_length=1)
    suggested_sprint_bucket: str = Field(alias="suggestedSprintBucket", min_length=1)
    related_refs: list[str] = Field(alias="relatedRefs", default_factory=list)
    tracking_issue_url: str | None = Field(alias="trackingIssueUrl", default=None)
    duplicate_key: str = Field(alias="duplicateKey", min_length=1)
    approval_required: bool = Field(alias="approvalRequired", default=False)
    review_notes: list[LanternRecommendationNote] = Field(
        alias="reviewNotes",
        default_factory=list,
    )


class LanternSprintCandidate(LanternModel):
    recommendation_id: str = Field(alias="recommendationId")
    title: str
    owner_repo: str = Field(alias="ownerRepo")
    suggested_sprint_bucket: str = Field(alias="suggestedSprintBucket")
    priority: str
    tracking_issue_url: str | None = Field(alias="trackingIssueUrl", default=None)


class LanternRecommendationExport(LanternModel):
    owner_repo: str = Field(alias="ownerRepo")
    generated_at: datetime = Field(alias="generatedAt")
    recommendations: list[LanternRecommendation]
    sprint_candidates: list[LanternSprintCandidate] = Field(alias="sprintCandidates")


class LanternRecommendationUpdateRequest(LanternModel):
    status: LanternRecommendationStatus | None = None
    tracking_issue_url: str | None = Field(alias="trackingIssueUrl", default=None)
    note: str | None = None
    author: str = "christina"


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


CUSTOMER_FACING_OUTPUTS = {"customer_summary", "recommended_actions", "kb_candidates"}


def default_ets_recommendations() -> list[LanternRecommendation]:
    return [
        _default_recommendation(
            recommendation_id="ets-rec-phase2-hosted-readiness",
            title="Finish hosted ETS explorer and API readiness path",
            summary="Complete the hosted Phase 2 path for explorer/API deployment readiness.",
            item_type=LanternRecommendationKind.SOFTWARE_CHANGE,
            priority="P2",
            source="github:ShannonBrayNC/ETS#34",
            suggested_sprint_bucket="hosted-readiness",
            related_refs=["https://github.com/ShannonBrayNC/ETS/issues/34"],
            tracking_issue_url="https://github.com/ShannonBrayNC/ETS/issues/34",
        ),
        _default_recommendation(
            recommendation_id="ets-rec-distributed-trust-validation",
            title="Plan distributed ETS validation without premature consensus scope",
            summary=(
                "Keep Phase 3 distributed validation scoped to root exchange and "
                "divergence detection."
            ),
            item_type=LanternRecommendationKind.INVESTIGATION,
            priority="P3",
            source="github:ShannonBrayNC/ETS#35",
            suggested_sprint_bucket="distributed-validation",
            related_refs=["https://github.com/ShannonBrayNC/ETS/issues/35"],
            tracking_issue_url="https://github.com/ShannonBrayNC/ETS/issues/35",
        ),
        _default_recommendation(
            recommendation_id="ets-rec-dissertation-artifacts",
            title="Fill missing dissertation chapter artifacts",
            summary=(
                "Add the remaining prospectus, literature review, formal foundations, "
                "evaluation, and contribution artifacts."
            ),
            item_type=LanternRecommendationKind.DOCUMENTATION_CHANGE,
            priority="P3",
            source="github:ShannonBrayNC/ETS#51-55",
            suggested_sprint_bucket="dissertation-artifacts",
            related_refs=[
                "https://github.com/ShannonBrayNC/ETS/issues/51",
                "https://github.com/ShannonBrayNC/ETS/issues/52",
                "https://github.com/ShannonBrayNC/ETS/issues/53",
                "https://github.com/ShannonBrayNC/ETS/issues/54",
                "https://github.com/ShannonBrayNC/ETS/issues/55",
            ],
            tracking_issue_url=None,
        ),
    ]


def _default_recommendation(
    *,
    recommendation_id: str,
    title: str,
    summary: str,
    item_type: LanternRecommendationKind,
    priority: str,
    source: str,
    suggested_sprint_bucket: str,
    related_refs: list[str],
    tracking_issue_url: str | None,
) -> LanternRecommendation:
    owner_repo = "ShannonBrayNC/ETS"
    return LanternRecommendation(
        recommendationId=recommendation_id,
        title=title,
        summary=summary,
        itemType=item_type,
        priority=priority,
        source=source,
        status=LanternRecommendationStatus.OPEN,
        ownerRepo=owner_repo,
        suggestedSprintBucket=suggested_sprint_bucket,
        relatedRefs=related_refs,
        trackingIssueUrl=tracking_issue_url,
        duplicateKey=recommendation_duplicate_key(owner_repo, item_type, title),
        approvalRequired=False,
    )


def recommendation_duplicate_key(owner_repo: str, item_type: str, title: str) -> str:
    return canonical_sha256(
        {
            "ownerRepo": owner_repo.lower(),
            "itemType": item_type,
            "title": title.strip().lower(),
        }
    )


def build_recommendation_export(
    recommendations: list[LanternRecommendation],
    *,
    owner_repo: str = "ShannonBrayNC/ETS",
    generated_at: datetime | None = None,
) -> LanternRecommendationExport:
    actionable = [
        recommendation
        for recommendation in recommendations
        if recommendation.status
        in {
            LanternRecommendationStatus.OPEN,
            LanternRecommendationStatus.ROUTED,
            LanternRecommendationStatus.IN_REVIEW,
        }
    ]
    return LanternRecommendationExport(
        ownerRepo=owner_repo,
        generatedAt=generated_at or datetime.now(UTC),
        recommendations=recommendations,
        sprintCandidates=[
            LanternSprintCandidate(
                recommendationId=recommendation.recommendation_id,
                title=recommendation.title,
                ownerRepo=recommendation.owner_repo,
                suggestedSprintBucket=recommendation.suggested_sprint_bucket,
                priority=recommendation.priority,
                trackingIssueUrl=recommendation.tracking_issue_url,
            )
            for recommendation in actionable
        ],
    )


def update_recommendation(
    recommendation: LanternRecommendation,
    request: LanternRecommendationUpdateRequest,
) -> LanternRecommendation:
    notes = list(recommendation.review_notes)
    if request.note is not None:
        notes.append(LanternRecommendationNote(author=request.author, note=request.note))
    return recommendation.model_copy(
        update={
            "status": request.status or recommendation.status,
            "tracking_issue_url": request.tracking_issue_url
            if request.tracking_issue_url is not None
            else recommendation.tracking_issue_url,
            "review_notes": notes,
        }
    )


def build_lantern_support_analysis(
    request: LanternSupportAnalysisRequest,
) -> LanternSupportAnalysisResponse:
    """Build a deterministic Lantern support-intelligence envelope.

    ETS does not generate natural-language support advice here. It creates the stable adapter
    envelope that downstream systems can fill, verify, approve, and reuse.
    """

    source_ids = [artifact.artifact_id for artifact in request.artifact_hashes]
    output_payload = {
        "lanternEventId": request.lantern_event_id,
        "sourceSystem": request.source_system,
        "ticketRef": request.ticket_ref,
        "artifactHashes": [
            artifact.model_dump(mode="json", by_alias=True)
            for artifact in request.artifact_hashes
        ],
    }
    approval_required = (
        request.approval_state in APPROVAL_REQUIRED_STATES
        or bool(CUSTOMER_FACING_OUTPUTS.intersection(request.requested_outputs))
    )
    customer_summary = (
        _support_output_artifact(
            request,
            "customer_summary",
            source_ids,
            approval_required=True,
        )
        if "customer_summary" in request.requested_outputs
        else None
    )
    internal_summary = (
        _support_output_artifact(
            request,
            "internal_summary",
            source_ids,
            approval_required=False,
        )
        if "internal_summary" in request.requested_outputs
        else None
    )
    finding_hash = canonical_sha256({**output_payload, "output": "technical_findings"})
    kb_hash = canonical_sha256({**output_payload, "output": "kb_candidates"})
    outputs = LanternSupportOutputs(
        customerSummary=customer_summary,
        internalSummary=internal_summary,
        technicalFindings=[
            LanternTechnicalFinding(
                code="lantern.support.finding.evidence-linked",
                summary="Support analysis is linked to registered ticket and artifact hashes.",
                evidenceHash=finding_hash,
            )
        ]
        if "technical_findings" in request.requested_outputs
        else [],
        recommendedActions=[
            LanternRecommendedAction(
                actionType="customer-message",
                summary="Hold customer-facing response for Christina approval.",
                approvalRequired=True,
            )
        ]
        if "recommended_actions" in request.requested_outputs
        else [],
        kbCandidates=[
            LanternKBCandidate(
                title=f"Reusable support pattern for {request.ticket_ref}",
                evidenceHash=kb_hash,
                reuseScope="internal-knowledge-base",
                approvalRequired=True,
            )
        ]
        if "kb_candidates" in request.requested_outputs
        else [],
    )
    memory_hash = canonical_sha256({**output_payload, "observation": "recurring_support_pattern"})
    status = (
        LanternVerificationStatus.HOLD_FOR_APPROVAL
        if approval_required
        else LanternVerificationStatus.PASSED
    )
    reason_code = (
        VerificationReasonCode.APPROVAL_REQUIRED
        if approval_required
        else VerificationReasonCode.OK
    )
    return LanternSupportAnalysisResponse(
        lanternEventId=request.lantern_event_id,
        status=status,
        reasonCode=reason_code,
        proofBundleUrl=f"/api/v1/bundles/{request.lantern_event_id}",
        outputs=outputs,
        metrics={
            "artifact_count": len(request.artifact_hashes),
            "requested_output_count": len(request.requested_outputs),
            "approval_gated_output_count": _approval_gated_output_count(outputs),
        },
        memoryObservations=[
            LanternMemoryObservation(
                type="recurring_support_pattern",
                summary="Support request is available for SignalForge memory correlation.",
                evidenceHash=memory_hash,
            )
        ],
    )


def _support_output_artifact(
    request: LanternSupportAnalysisRequest,
    output_name: str,
    source_ids: list[str],
    *,
    approval_required: bool,
) -> LanternOutputArtifact:
    return LanternOutputArtifact(
        artifactHash=canonical_sha256(
            {
                "lanternEventId": request.lantern_event_id,
                "ticketRef": request.ticket_ref,
                "output": output_name,
                "sourceArtifacts": source_ids,
            }
        ),
        approvalRequired=approval_required,
        approvalState=request.approval_state if approval_required else "not-required",
        sourceArtifactIds=source_ids,
    )


def _approval_gated_output_count(outputs: LanternSupportOutputs) -> int:
    count = 0
    output_artifacts = [outputs.customer_summary, outputs.internal_summary]
    count += sum(1 for output in output_artifacts if output and output.approval_required)
    count += sum(1 for action in outputs.recommended_actions if action.approval_required)
    count += sum(1 for candidate in outputs.kb_candidates if candidate.approval_required)
    return count


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
