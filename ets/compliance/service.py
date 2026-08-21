"""Deterministic policy-bound ETS Compliance evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta

from ets.compliance.models import (
    AssessmentContext,
    AssessmentOutcome,
    AssessmentReport,
    AssessmentSummary,
    CompliancePolicy,
    ControlDefinition,
    ControlEvaluation,
    ControlPack,
    EvidenceDisposition,
    EvidenceObservation,
    EvidenceRequirement,
    RequirementEvaluation,
    VerificationState,
)
from ets.core.api import EvidenceEvent, canonical_sha256


class ComplianceValidationError(ValueError):
    """Raised when assessment inputs violate scope or temporal safety boundaries."""


class ComplianceEvaluator:
    """Evaluate control evidence without claiming certification or semantic truth."""

    def __init__(self, *, policy: CompliancePolicy | None = None) -> None:
        self.policy = policy or CompliancePolicy()

    def evaluate(self, pack: ControlPack, context: AssessmentContext) -> AssessmentReport:
        """Return a deterministic assessment report for one versioned control pack."""

        self._validate_context(context)
        observations = tuple(sorted(context.observations, key=lambda item: item.observation_id))
        results = tuple(
            self._evaluate_control(control, observations, context)
            for control in sorted(pack.controls, key=lambda item: item.control_id)
        )
        summary = AssessmentSummary(
            total_controls=len(results),
            satisfied=sum(item.outcome is AssessmentOutcome.SATISFIED for item in results),
            not_satisfied=sum(
                item.outcome is AssessmentOutcome.NOT_SATISFIED for item in results
            ),
            unknown=sum(item.outcome is AssessmentOutcome.UNKNOWN for item in results),
            not_observed=sum(
                item.outcome is AssessmentOutcome.NOT_OBSERVED for item in results
            ),
        )
        input_digest = canonical_sha256(
            {
                "pack": pack.model_dump(mode="json"),
                "policy": self.policy.model_dump(mode="json"),
                "context": {
                    **context.model_dump(mode="json", exclude={"observations"}),
                    "observations": [
                        item.model_dump(mode="json") for item in observations
                    ],
                },
            }
        )
        report = AssessmentReport(
            assessment_id=context.assessment_id,
            tenant_id=context.tenant_id,
            workspace_id=context.workspace_id,
            subject_ref=context.subject_ref,
            framework=pack.framework,
            pack_id=pack.pack_id,
            pack_version=pack.pack_version,
            policy_version=self.policy.policy_version,
            evaluated_at_utc=context.evaluated_at_utc,
            control_results=results,
            summary=summary,
            input_digest=input_digest,
            result_digest="0" * 64,
        )
        result_digest = canonical_sha256(
            report.model_dump(mode="json", exclude={"result_digest"})
        )
        return report.model_copy(update={"result_digest": result_digest})

    def verify_report(
        self,
        report: AssessmentReport,
        *,
        pack: ControlPack,
        context: AssessmentContext,
    ) -> bool:
        """Re-evaluate the same inputs and compare the complete deterministic report."""

        try:
            recomputed = self.evaluate(pack, context)
        except ComplianceValidationError:
            return False
        return recomputed == report

    @staticmethod
    def to_evidence_event(report: AssessmentReport) -> EvidenceEvent:
        """Project a minimized derived assessment result through the ETS Core contract."""

        metadata = {
            "compliance_assessment": {
                "schema_version": report.schema_version,
                "framework_id": report.framework.framework_id,
                "framework_version": report.framework.version,
                "pack_id": report.pack_id,
                "pack_version": report.pack_version,
                "policy_version": report.policy_version,
                "input_digest": report.input_digest,
                "summary": report.summary.model_dump(mode="json"),
                "claim_boundary": "policy_bound_evidence_evaluation_not_certification",
            }
        }
        return EvidenceEvent(
            event_id=f"comp:{report.assessment_id}",
            tenant_id=report.tenant_id,
            workspace_id=report.workspace_id,
            evidence_id=f"comp:{report.result_digest[:48]}",
            event_type="compliance.assessment",
            subject_ref=report.subject_ref,
            content_hash=report.result_digest,
            content_hash_alg="sha256",
            metadata=metadata,
            created_at_utc=report.evaluated_at_utc,
            source_system="ets-compliance",
            actor_id=None,
            correlation_id=report.assessment_id,
            external_refs=None,
            redaction_profile="none",
        )

    def _validate_context(self, context: AssessmentContext) -> None:
        for observation in context.observations:
            if observation.tenant_id != context.tenant_id:
                raise ComplianceValidationError(
                    "cross-tenant evidence is forbidden in one assessment context"
                )
            if observation.workspace_id != context.workspace_id:
                raise ComplianceValidationError(
                    "cross-workspace evidence is forbidden in one assessment context"
                )
            if observation.subject_ref != context.subject_ref:
                raise ComplianceValidationError(
                    "cross-subject evidence is forbidden in one assessment context"
                )
            allowed_future = context.evaluated_at_utc + timedelta(
                seconds=self.policy.max_future_skew_seconds
            )
            if observation.observed_at_utc > allowed_future:
                raise ComplianceValidationError(
                    "observation exceeds configured future-clock-skew allowance"
                )

    def _evaluate_control(
        self,
        control: ControlDefinition,
        observations: tuple[EvidenceObservation, ...],
        context: AssessmentContext,
    ) -> ControlEvaluation:
        requirement_results = tuple(
            self._evaluate_requirement(requirement, observations, context)
            for requirement in sorted(
                control.requirements, key=lambda item: item.requirement_id
            )
        )
        outcomes = {item.outcome for item in requirement_results}
        if AssessmentOutcome.NOT_SATISFIED in outcomes:
            outcome = AssessmentOutcome.NOT_SATISFIED
            reasons = ("verified_contradiction",)
        elif AssessmentOutcome.UNKNOWN in outcomes:
            outcome = AssessmentOutcome.UNKNOWN
            reasons = ("one_or_more_requirements_unknown",)
        elif AssessmentOutcome.NOT_OBSERVED in outcomes:
            outcome = AssessmentOutcome.NOT_OBSERVED
            reasons = ("one_or_more_requirements_not_observed",)
        else:
            outcome = AssessmentOutcome.SATISFIED
            reasons = ("all_requirements_satisfied",)

        expiries = [
            item.valid_until_utc
            for item in requirement_results
            if item.valid_until_utc is not None
        ]
        valid_until = min(expiries) if expiries else None
        return ControlEvaluation(
            control_id=control.control_id,
            outcome=outcome,
            reason_codes=reasons,
            requirement_results=requirement_results,
            valid_until_utc=valid_until,
        )

    def _evaluate_requirement(
        self,
        requirement: EvidenceRequirement,
        observations: tuple[EvidenceObservation, ...],
        context: AssessmentContext,
    ) -> RequirementEvaluation:
        matching = tuple(
            item
            for item in observations
            if self._matches_requirement(item, requirement)
        )
        if not matching:
            return RequirementEvaluation(
                requirement_id=requirement.requirement_id,
                outcome=AssessmentOutcome.NOT_OBSERVED,
                reason_codes=("no_matching_evidence",),
                matched_observation_ids=(),
                supporting_evidence_ids=(),
                contradicting_evidence_ids=(),
                stale_evidence_ids=(),
                unverified_evidence_ids=(),
            )

        current: list[EvidenceObservation] = []
        stale: list[EvidenceObservation] = []
        for item in matching:
            if self._is_stale(item, requirement, context):
                stale.append(item)
            else:
                current.append(item)

        verified = [
            item for item in current if item.verification_state is VerificationState.VERIFIED
        ]
        unverified = [
            item for item in current if item.verification_state is not VerificationState.VERIFIED
        ]
        supports = [
            item for item in verified if item.disposition is EvidenceDisposition.SUPPORTS
        ]
        contradicts = [
            item
            for item in verified
            if item.disposition is EvidenceDisposition.CONTRADICTS
        ]
        indeterminate = [
            item
            for item in verified
            if item.disposition is EvidenceDisposition.INDETERMINATE
        ]

        if supports and contradicts:
            outcome = AssessmentOutcome.UNKNOWN
            reasons = ("conflicting_verified_evidence",)
        elif contradicts:
            outcome = AssessmentOutcome.NOT_SATISFIED
            reasons = ("verified_contradiction",)
        elif len(supports) >= requirement.minimum_observations:
            outcome = AssessmentOutcome.SATISFIED
            reasons = ("minimum_verified_support_met",)
        elif stale and not current:
            outcome = AssessmentOutcome.UNKNOWN
            reasons = ("matching_evidence_stale",)
        elif unverified and not verified:
            outcome = AssessmentOutcome.UNKNOWN
            reasons = ("matching_evidence_unverified",)
        elif indeterminate:
            outcome = AssessmentOutcome.UNKNOWN
            reasons = ("verified_evidence_indeterminate",)
        else:
            outcome = AssessmentOutcome.UNKNOWN
            reasons = ("insufficient_verified_support",)

        valid_until = self._valid_until(supports, requirement)
        return RequirementEvaluation(
            requirement_id=requirement.requirement_id,
            outcome=outcome,
            reason_codes=reasons,
            matched_observation_ids=tuple(item.observation_id for item in matching),
            supporting_evidence_ids=tuple(item.evidence_id for item in supports),
            contradicting_evidence_ids=tuple(item.evidence_id for item in contradicts),
            stale_evidence_ids=tuple(item.evidence_id for item in stale),
            unverified_evidence_ids=tuple(item.evidence_id for item in unverified),
            valid_until_utc=valid_until,
        )

    @staticmethod
    def _matches_requirement(
        observation: EvidenceObservation,
        requirement: EvidenceRequirement,
    ) -> bool:
        if observation.requirement_id != requirement.requirement_id:
            return False
        if observation.evidence_type not in requirement.evidence_types:
            return False
        if (
            requirement.source_systems
            and observation.source_system not in requirement.source_systems
        ):
            return False
        if requirement.methods and observation.method not in requirement.methods:
            return False
        return True

    @staticmethod
    def _is_stale(
        observation: EvidenceObservation,
        requirement: EvidenceRequirement,
        context: AssessmentContext,
    ) -> bool:
        if requirement.max_age_seconds is None:
            return False
        expires = observation.observed_at_utc + timedelta(
            seconds=requirement.max_age_seconds
        )
        return expires <= context.evaluated_at_utc

    @staticmethod
    def _valid_until(
        supports: list[EvidenceObservation],
        requirement: EvidenceRequirement,
    ) -> datetime | None:
        if not supports or requirement.max_age_seconds is None:
            return None
        if len(supports) < requirement.minimum_observations:
            return None
        expiries = sorted(
            (
                item.observed_at_utc + timedelta(seconds=requirement.max_age_seconds)
                for item in supports
            ),
            reverse=True,
        )
        return expiries[requirement.minimum_observations - 1]
