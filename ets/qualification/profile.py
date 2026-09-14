"""Runtime model for the ETS Hardware Qualification Profile v1 descriptor.

The normative JSON Schema remains schemas/qualification/v1/hardware-qualification-profile.schema.json.
This module mirrors that contract so HQP-2 can validate a profile in a clean verifier process
without adding a second JSON-Schema dependency to the ETS runtime.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class QualificationState(StrEnum):
    NOT_TESTED = "not_tested"
    SIMULATED = "simulated"
    LAB_TESTED = "lab_tested"
    QUALIFICATION_IN_PROGRESS = "qualification_in_progress"
    QUALIFIED = "qualified"
    QUALIFIED_WITH_DEVIATION = "qualified_with_deviation"
    FAILED = "failed"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class EvidenceRequirementClass(StrEnum):
    DUT_IDENTITY = "dut_identity"
    ENVIRONMENT = "environment"
    BUILD_IDENTITY = "build_identity"
    OBSERVER_IDENTITY = "observer_identity"
    STARTING_STATE = "starting_state"
    STIMULUS = "stimulus"
    OBSERVATIONS = "observations"
    RESULTING_STATE = "resulting_state"
    VERIFIER_OUTPUT = "verifier_output"
    QUALIFICATION_REPORT = "qualification_report"


class VerifierCheckName(StrEnum):
    SCHEMA_CONFORMANCE = "schema_conformance"
    ARTIFACT_PRESENCE = "artifact_presence"
    DIGEST_VALIDITY = "digest_validity"
    SIGNATURE_VALIDITY = "signature_validity"
    EVIDENCE_OBJECT_BINDING = "evidence_object_binding"
    TEST_CASE_COMPLETION = "test_case_completion"
    OBSERVATION_RESULT_LINKAGE = "observation_result_linkage"
    DEVIATION_POLICY = "deviation_policy"
    DISPOSITION_POLICY = "disposition_policy"


class FinalQualificationState(StrEnum):
    LAB_TESTED = "lab_tested"
    QUALIFIED = "qualified"
    QUALIFIED_WITH_DEVIATION = "qualified_with_deviation"
    FAILED = "failed"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class FailurePolicy(StrEnum):
    FAIL = "fail"
    INVALIDATE = "invalidate"
    CONTINUE_FOR_DIAGNOSTICS = "continue_for_diagnostics"


class ParentProfile(StrictProfileModel):
    profile_id: str = Field(min_length=3)
    profile_version: str = Field(min_length=1)
    override_review_required: bool = True


class CapabilityBoundary(StrictProfileModel):
    capability_states_are_independent: Literal[True]
    qualification_states: tuple[QualificationState, ...] = Field(min_length=1)
    claim_statement: str = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_unique_states(self) -> CapabilityBoundary:
        _require_unique(self.qualification_states, "qualification_states")
        return self


class DeviceConstraints(StrictProfileModel):
    claim_critical_fields: tuple[str, ...] = Field(min_length=1)
    cross_revision_qualification_allowed: Literal[False]
    equivalence_profile_required: bool = True
    notes: str | None = None

    @model_validator(mode="after")
    def enforce_unique_fields(self) -> DeviceConstraints:
        _require_unique(self.claim_critical_fields, "claim_critical_fields")
        return self


class EvidenceRequirements(StrictProfileModel):
    evidence_object_binding_required: Literal[True]
    required_classes: tuple[EvidenceRequirementClass, ...] = Field(min_length=1)
    missing_required_evidence_policy: Literal["invalid", "failed"]
    external_artifacts_allowed: bool = False
    raw_artifact_digest_required: bool = True

    @model_validator(mode="after")
    def enforce_unique_classes(self) -> EvidenceRequirements:
        _require_unique(self.required_classes, "required_classes")
        return self


class VerifierRequirements(StrictProfileModel):
    independent_verification_required_for: tuple[
        Literal["qualified", "qualified_with_deviation"], ...
    ] = Field(min_length=1)
    immutable_verifier_identity_required: Literal[True]
    checks: tuple[VerifierCheckName, ...] = Field(min_length=1)
    dut_runtime_may_be_trusted: Literal[False]

    @model_validator(mode="after")
    def enforce_unique_requirements(self) -> VerifierRequirements:
        _require_unique(
            self.independent_verification_required_for,
            "independent_verification_required_for",
        )
        _require_unique(self.checks, "verifier checks")
        return self


class HardwareQualificationTestCase(StrictProfileModel):
    test_id: str = Field(min_length=2, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    required: bool
    depends_on: tuple[str, ...] = ()
    stimulus_class: str = Field(min_length=1)
    required_observations: tuple[str, ...] = Field(min_length=1)
    required_resulting_state: tuple[str, ...] = Field(min_length=1)
    pass_criteria: tuple[str, ...] = Field(min_length=1)
    failure_policy: FailurePolicy
    waivable: bool
    safety_boundary: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def enforce_unique_case_fields(self) -> HardwareQualificationTestCase:
        _require_unique(self.depends_on, f"{self.test_id} depends_on")
        _require_unique(
            self.required_observations,
            f"{self.test_id} required_observations",
        )
        _require_unique(
            self.required_resulting_state,
            f"{self.test_id} required_resulting_state",
        )
        return self


class DispositionPolicy(StrictProfileModel):
    allowed_final_states: tuple[FinalQualificationState, ...] = Field(min_length=1)
    missing_required_case_policy: Literal["failed", "invalid"]
    deviation_state: Literal["qualified_with_deviation"]
    non_waivable_failure_blocks_qualification: Literal[True]

    @model_validator(mode="after")
    def enforce_unique_final_states(self) -> DispositionPolicy:
        _require_unique(self.allowed_final_states, "allowed_final_states")
        return self


class ValidityPolicy(StrictProfileModel):
    requalify_on_claim_critical_change: Literal[True]
    supersession_must_be_explicit: Literal[True]
    historical_results_immutable: Literal[True]
    maximum_validity_days: int | None = Field(default=None, ge=1)
    additional_requalification_triggers: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_unique_triggers(self) -> ValidityPolicy:
        _require_unique(
            self.additional_requalification_triggers,
            "additional_requalification_triggers",
        )
        return self


class QualificationTraceability(StrictProfileModel):
    tracking_issue: str = Field(min_length=1)
    source_requirements: tuple[str, ...] = Field(min_length=1)
    authoritative_roadmap: str = Field(min_length=1)
    review_references: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_unique_traceability(self) -> QualificationTraceability:
        _require_unique(self.source_requirements, "source_requirements")
        _require_unique(self.review_references, "review_references")
        return self


class HardwareQualificationProfile(StrictProfileModel):
    schema_version: Literal["1.0"]
    base_profile: Literal["ets.hardware-qualification.v1"]
    profile_id: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9._-]+$")
    profile_version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    product_scope: tuple[str, ...] = Field(min_length=1)
    parent_profiles: tuple[ParentProfile, ...] = ()
    capability_boundary: CapabilityBoundary
    device_constraints: DeviceConstraints
    environment_dimensions: tuple[str, ...] = Field(min_length=1)
    evidence_requirements: EvidenceRequirements
    verifier_requirements: VerifierRequirements
    test_cases: tuple[HardwareQualificationTestCase, ...] = Field(min_length=1)
    disposition_policy: DispositionPolicy
    validity_policy: ValidityPolicy
    non_claims: tuple[str, ...] = Field(min_length=1)
    traceability: QualificationTraceability

    @model_validator(mode="after")
    def enforce_profile_integrity(self) -> HardwareQualificationProfile:
        _require_unique(self.product_scope, "product_scope")
        _require_unique(self.environment_dimensions, "environment_dimensions")
        _require_unique(self.non_claims, "non_claims")

        case_ids = [item.test_id for item in self.test_cases]
        _require_unique(tuple(case_ids), "test case identifiers")
        available = set(case_ids)
        for case in self.test_cases:
            missing = set(case.depends_on) - available
            if missing:
                raise ValueError(
                    f"{case.test_id} depends on unknown test cases: {sorted(missing)}"
                )
            if case.test_id in case.depends_on:
                raise ValueError(f"{case.test_id} cannot depend on itself")
        return self


def _require_unique(values: tuple[object, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} values must be unique")


__all__ = [
    "DispositionPolicy",
    "EvidenceRequirementClass",
    "EvidenceRequirements",
    "FailurePolicy",
    "FinalQualificationState",
    "HardwareQualificationProfile",
    "HardwareQualificationTestCase",
    "QualificationState",
    "VerifierCheckName",
    "VerifierRequirements",
]
