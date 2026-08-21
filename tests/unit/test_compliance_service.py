import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.compliance import (
    AssessmentContext,
    AssessmentOutcome,
    AssessmentReport,
    ComplianceEvaluator,
    CompliancePolicy,
    ComplianceValidationError,
    ControlDefinition,
    ControlPack,
    EvidenceDisposition,
    EvidenceObservation,
    EvidenceRequirement,
    FrameworkReference,
    ObservationMethod,
    VerificationState,
)

NOW = datetime(2026, 8, 21, 8, 0, tzinfo=UTC)


def framework() -> FrameworkReference:
    return FrameworkReference(
        framework_id="synthetic.security",
        version="2026.1",
        authority="ETS test fixture",
        profile_id="baseline",
    )


def requirement(
    *,
    requirement_id: str = "r1",
    minimum: int = 1,
    max_age: int | None = 3600,
) -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id=requirement_id,
        description="Synthetic evidence requirement",
        evidence_types=("config.assertion",),
        source_systems=("synthetic-scanner",),
        methods=(ObservationMethod.TEST,),
        minimum_observations=minimum,
        max_age_seconds=max_age,
    )


def pack(*requirements: EvidenceRequirement) -> ControlPack:
    selected = requirements or (requirement(),)
    return ControlPack(
        pack_id="synthetic-baseline",
        pack_version="1",
        framework=framework(),
        controls=(
            ControlDefinition(
                control_id="SYN-1",
                title="Synthetic control",
                objective_id="SYN-1.a",
                requirements=tuple(selected),
            ),
        ),
    )


def observation(
    *,
    observation_id: str = "o1",
    requirement_id: str = "r1",
    disposition: EvidenceDisposition = EvidenceDisposition.SUPPORTS,
    verification: VerificationState = VerificationState.VERIFIED,
    observed_at: datetime = NOW - timedelta(minutes=5),
    evidence_type: str = "config.assertion",
    source_system: str = "synthetic-scanner",
    method: ObservationMethod = ObservationMethod.TEST,
    tenant_id: str = "tenant",
    workspace_id: str = "workspace",
    subject_ref: str = "system:demo",
    attributes: dict[str, str] | None = None,
) -> EvidenceObservation:
    digest = hashlib.sha256(observation_id.encode()).hexdigest()
    return EvidenceObservation(
        observation_id=observation_id,
        requirement_id=requirement_id,
        evidence_id=f"ev-{observation_id}",
        event_id=f"evt-{observation_id}",
        event_hash=digest,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        subject_ref=subject_ref,
        evidence_type=evidence_type,
        event_type="synthetic.config",
        source_system=source_system,
        observed_at_utc=observed_at,
        method=method,
        origin_ref="tool:synthetic",
        disposition=disposition,
        verification_state=verification,
        attributes=attributes or {},
    )


def context(*observations: EvidenceObservation, evaluated_at: datetime = NOW) -> AssessmentContext:
    return AssessmentContext(
        assessment_id="assessment-1",
        tenant_id="tenant",
        workspace_id="workspace",
        subject_ref="system:demo",
        evaluated_at_utc=evaluated_at,
        observations=tuple(observations),
    )


def only_result(report):
    return report.control_results[0].requirement_results[0]


def test_verified_current_support_satisfies_control() -> None:
    report = ComplianceEvaluator().evaluate(pack(), context(observation()))
    assert report.control_results[0].outcome is AssessmentOutcome.SATISFIED
    assert report.summary.satisfied == 1
    assert report.summary.total_controls == 1
    assert only_result(report).valid_until_utc == NOW + timedelta(minutes=55)


def test_missing_evidence_is_not_observed_not_failure() -> None:
    report = ComplianceEvaluator().evaluate(pack(), context())
    assert report.control_results[0].outcome is AssessmentOutcome.NOT_OBSERVED
    assert only_result(report).reason_codes == ("no_matching_evidence",)


def test_stale_evidence_is_unknown_and_explicit() -> None:
    old = observation(observed_at=NOW - timedelta(hours=2))
    report = ComplianceEvaluator().evaluate(pack(), context(old))
    result = only_result(report)
    assert result.outcome is AssessmentOutcome.UNKNOWN
    assert result.reason_codes == ("matching_evidence_stale",)
    assert result.stale_evidence_ids == ("ev-o1",)


def test_unverified_evidence_is_unknown() -> None:
    item = observation(verification=VerificationState.UNVERIFIED)
    report = ComplianceEvaluator().evaluate(pack(), context(item))
    result = only_result(report)
    assert result.outcome is AssessmentOutcome.UNKNOWN
    assert result.unverified_evidence_ids == ("ev-o1",)


def test_verified_contradiction_is_not_satisfied() -> None:
    item = observation(disposition=EvidenceDisposition.CONTRADICTS)
    report = ComplianceEvaluator().evaluate(pack(), context(item))
    assert report.control_results[0].outcome is AssessmentOutcome.NOT_SATISFIED
    assert only_result(report).contradicting_evidence_ids == ("ev-o1",)


def test_conflicting_verified_evidence_is_unknown() -> None:
    support = observation(observation_id="support")
    contradiction = observation(
        observation_id="contradiction",
        disposition=EvidenceDisposition.CONTRADICTS,
    )
    report = ComplianceEvaluator().evaluate(pack(), context(support, contradiction))
    result = only_result(report)
    assert result.outcome is AssessmentOutcome.UNKNOWN
    assert result.reason_codes == ("conflicting_verified_evidence",)


def test_minimum_observation_threshold_is_enforced() -> None:
    report = ComplianceEvaluator().evaluate(
        pack(requirement(minimum=2)),
        context(observation()),
    )
    assert only_result(report).outcome is AssessmentOutcome.UNKNOWN
    assert only_result(report).reason_codes == ("insufficient_verified_support",)


def test_requirement_filters_do_not_turn_mismatch_into_failure() -> None:
    wrong_source = observation(source_system="other-scanner")
    report = ComplianceEvaluator().evaluate(pack(), context(wrong_source))
    assert only_result(report).outcome is AssessmentOutcome.NOT_OBSERVED


def test_multiple_requirements_preserve_missing_requirement_state() -> None:
    report = ComplianceEvaluator().evaluate(
        pack(requirement(requirement_id="r1"), requirement(requirement_id="r2")),
        context(observation(requirement_id="r1")),
    )
    assert report.control_results[0].outcome is AssessmentOutcome.NOT_OBSERVED
    assert [item.outcome for item in report.control_results[0].requirement_results] == [
        AssessmentOutcome.SATISFIED,
        AssessmentOutcome.NOT_OBSERVED,
    ]


def test_cross_scope_evidence_fails_closed() -> None:
    with pytest.raises(ComplianceValidationError, match="cross-tenant"):
        ComplianceEvaluator().evaluate(
            pack(),
            context(observation(tenant_id="other-tenant")),
        )


def test_excessive_future_clock_skew_fails_closed() -> None:
    future = observation(observed_at=NOW + timedelta(minutes=10))
    evaluator = ComplianceEvaluator(
        policy=CompliancePolicy(max_future_skew_seconds=60)
    )
    with pytest.raises(ComplianceValidationError, match="future-clock-skew"):
        evaluator.evaluate(pack(), context(future))


def test_raw_or_sensitive_content_cannot_be_embedded() -> None:
    payload = observation().model_dump()
    payload["attributes"] = {"raw_payload": "secret bytes"}
    with pytest.raises(ValidationError, match="raw/sensitive"):
        EvidenceObservation.model_validate(payload)


def test_report_is_reproducible_and_tamper_detected() -> None:
    evaluator = ComplianceEvaluator()
    ctx = context(observation())
    report = evaluator.evaluate(pack(), ctx)
    assert evaluator.verify_report(report, pack=pack(), context=ctx)
    tampered = report.model_copy(
        update={"result_digest": "0" * 64}
    )
    assert not evaluator.verify_report(tampered, pack=pack(), context=ctx)


def test_input_order_does_not_change_deterministic_report() -> None:
    first = observation(observation_id="a")
    second = observation(observation_id="b")
    evaluator = ComplianceEvaluator()
    left = evaluator.evaluate(pack(requirement(minimum=2)), context(first, second))
    right = evaluator.evaluate(pack(requirement(minimum=2)), context(second, first))
    assert left == right


def test_core_projection_is_minimized_and_not_a_certification_claim() -> None:
    evaluator = ComplianceEvaluator()
    item = observation(attributes={"safe_label": "internal-detail"})
    report = evaluator.evaluate(pack(), context(item))
    event = evaluator.to_evidence_event(report)
    serialized = str(event.model_dump(mode="json"))
    assert event.content_hash == report.result_digest
    assert event.event_type == "compliance.assessment"
    assert "internal-detail" not in serialized
    assert "ev-o1" not in serialized
    assert "policy_bound_evidence_evaluation_not_certification" in serialized


def test_report_contract_has_no_blanket_score_or_certification_field() -> None:
    forbidden = {"score", "percentage", "certified", "certification", "compliant"}
    assert forbidden.isdisjoint(AssessmentReport.model_fields)
