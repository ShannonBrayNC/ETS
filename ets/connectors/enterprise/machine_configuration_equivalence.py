"""Fail-closed acceptance contract for DSC migration equivalence evidence."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MACHINE_CONFIGURATION_EQUIVALENCE_SCHEMA_VERSION: Literal[
    "ets.microsoft.machine_configuration_equivalence.v1"
] = "ets.microsoft.machine_configuration_equivalence.v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

ScenarioName = Literal[
    "initial_application",
    "recurring_drift",
    "correction",
    "errors",
    "reporting",
]
RuntimeName = Literal["legacy_lcm", "machine_configuration"]
Classification = Literal["pass", "accepted_difference", "fail", "inconclusive"]

MANDATORY_SCENARIOS: tuple[ScenarioName, ...] = (
    "initial_application",
    "recurring_drift",
    "correction",
    "errors",
    "reporting",
)

ArtifactRole = Literal[
    "legacy_source",
    "original_mof",
    "recompiled_mof",
    "legacy_module_bundle",
    "lcm_metaconfiguration",
    "replacement_assignment",
    "replacement_package",
]

MANDATORY_ARTIFACT_ROLES: frozenset[str] = frozenset(
    {
        "legacy_source",
        "original_mof",
        "recompiled_mof",
        "legacy_module_bundle",
        "lcm_metaconfiguration",
        "replacement_assignment",
        "replacement_package",
    }
)


class StrictEquivalenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RetainedArtifactV1(StrictEquivalenceModel):
    role: ArtifactRole
    uri: str = Field(min_length=1, max_length=2048)
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=1)

    @field_validator("uri")
    @classmethod
    def reject_blank_uri(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("artifact URI cannot be blank")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        return _validate_sha256(value, "artifact digest")


class RuntimePinV1(StrictEquivalenceModel):
    os_name: str = Field(min_length=1, max_length=128)
    os_version: str = Field(min_length=1, max_length=128)
    engine_name: str = Field(min_length=1, max_length=256)
    engine_version: str = Field(min_length=1, max_length=128)
    agent_or_lcm_version: str = Field(min_length=1, max_length=128)

    @field_validator(
        "os_name", "os_version", "engine_name", "engine_version", "agent_or_lcm_version"
    )
    @classmethod
    def reject_blank_pin(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("runtime pins cannot be blank")
        return value


class WriterBoundaryV1(StrictEquivalenceModel):
    legacy_writer_identity: str = Field(min_length=1, max_length=512)
    replacement_writer_identity: str = Field(min_length=1, max_length=512)
    simultaneous_writers_prohibited: Literal[True]
    guest_telemetry_required_for_correction: Literal[True]


class MachineConfigurationEquivalenceProfileV1(StrictEquivalenceModel):
    """Pinned pre-execution profile for one legacy-to-replacement control."""

    schema_version: Literal[
        "ets.microsoft.machine_configuration_equivalence.v1"
    ] = MACHINE_CONFIGURATION_EQUIVALENCE_SCHEMA_VERSION
    profile_id: str = Field(min_length=1, max_length=256)
    control_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=512)
    environment: Literal["disposable_qualification"]
    legacy_runtime: RuntimePinV1
    replacement_runtime: RuntimePinV1
    writer_boundary: WriterBoundaryV1
    retained_artifacts: tuple[RetainedArtifactV1, ...]
    retirement_deadline: Literal["2027-09-30"] = "2027-09-30"

    @model_validator(mode="after")
    def require_complete_artifact_set(self) -> MachineConfigurationEquivalenceProfileV1:
        roles = [artifact.role for artifact in self.retained_artifacts]
        if len(roles) != len(set(roles)):
            raise ValueError("retained artifact roles cannot be duplicated")
        if set(roles) != MANDATORY_ARTIFACT_ROLES:
            missing = sorted(MANDATORY_ARTIFACT_ROLES.difference(roles))
            unexpected = sorted(set(roles).difference(MANDATORY_ARTIFACT_ROLES))
            raise ValueError(
                f"retained artifact set is incomplete: missing={missing}, unexpected={unexpected}"
            )
        return self


class ScenarioObservationV1(StrictEquivalenceModel):
    profile_id: str = Field(min_length=1, max_length=256)
    control_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=512)
    runtime: RuntimeName
    scenario: ScenarioName
    observed_at_utc: datetime
    active_writer_identity: str = Field(min_length=1, max_length=512)
    other_active_writer_identities: tuple[str, ...] = ()
    outcome: Literal[
        "applied",
        "compliant",
        "drift_detected",
        "corrected",
        "error",
        "reported",
        "unavailable",
    ]
    state_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    error_code: str | None = Field(default=None, min_length=1, max_length=256)
    report_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    guest_telemetry_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    evidence_sha256: str = Field(min_length=64, max_length=64)

    @field_validator(
        "state_sha256", "report_sha256", "guest_telemetry_sha256", "evidence_sha256"
    )
    @classmethod
    def validate_digests(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_sha256(value, "observation digest")

    @field_validator("observed_at_utc")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        _require_aware(value, "observed_at_utc")
        return value

    @model_validator(mode="after")
    def validate_outcome_shape(self) -> ScenarioObservationV1:
        if self.outcome == "error" and self.error_code is None:
            raise ValueError("error outcomes require an error code")
        if self.outcome != "error" and self.error_code is not None:
            raise ValueError("non-error outcomes cannot carry an error code")
        if len(self.other_active_writer_identities) != len(
            set(self.other_active_writer_identities)
        ):
            raise ValueError("other active writer identities cannot be duplicated")
        if self.active_writer_identity in self.other_active_writer_identities:
            raise ValueError("active writer cannot also be listed as another writer")
        return self


class AcceptedDifferenceV1(StrictEquivalenceModel):
    scenario: ScenarioName
    approval_id: str = Field(min_length=1, max_length=256)
    approved_by: str = Field(min_length=1, max_length=512)
    rationale: str = Field(min_length=1, max_length=4096)
    approved_at_utc: datetime
    expires_at_utc: datetime
    legacy_evidence_sha256: str = Field(min_length=64, max_length=64)
    replacement_evidence_sha256: str = Field(min_length=64, max_length=64)

    @field_validator("legacy_evidence_sha256", "replacement_evidence_sha256")
    @classmethod
    def validate_digests(cls, value: str) -> str:
        return _validate_sha256(value, "accepted-difference evidence digest")

    @field_validator("approved_at_utc", "expires_at_utc")
    @classmethod
    def require_aware_times(cls, value: datetime) -> datetime:
        _require_aware(value, "accepted-difference timestamp")
        return value

    @model_validator(mode="after")
    def require_future_expiry(self) -> AcceptedDifferenceV1:
        if self.expires_at_utc <= self.approved_at_utc:
            raise ValueError("accepted-difference approval must expire after approval")
        if not self.rationale.strip():
            raise ValueError("accepted-difference rationale cannot be blank")
        return self


class EquivalenceCaseV1(StrictEquivalenceModel):
    legacy: ScenarioObservationV1
    replacement: ScenarioObservationV1
    accepted_difference: AcceptedDifferenceV1 | None = None

    @model_validator(mode="after")
    def validate_pair(self) -> EquivalenceCaseV1:
        if self.legacy.runtime != "legacy_lcm":
            raise ValueError("legacy observation must use the legacy_lcm runtime")
        if self.replacement.runtime != "machine_configuration":
            raise ValueError(
                "replacement observation must use the machine_configuration runtime"
            )
        if self.legacy.scenario != self.replacement.scenario:
            raise ValueError("equivalence observations must cover the same scenario")
        if (
            self.accepted_difference is not None
            and self.accepted_difference.scenario != self.legacy.scenario
        ):
            raise ValueError("accepted difference must bind to the compared scenario")
        return self


class ScenarioClassificationV1(StrictEquivalenceModel):
    scenario: ScenarioName
    classification: Classification
    reason: str


class EquivalenceSuiteResultV1(StrictEquivalenceModel):
    profile_id: str
    classification: Classification
    scenario_results: tuple[ScenarioClassificationV1, ...]
    missing_scenarios: tuple[ScenarioName, ...]
    evaluated_at_utc: datetime


def classify_equivalence_case(
    profile: MachineConfigurationEquivalenceProfileV1,
    case: EquivalenceCaseV1,
    *,
    evaluated_at_utc: datetime,
) -> ScenarioClassificationV1:
    """Classify one paired observation without inferring absent evidence."""

    _require_aware(evaluated_at_utc, "evaluated_at_utc")
    scenario = case.legacy.scenario
    observations = (case.legacy, case.replacement)
    for observation in observations:
        if observation.observed_at_utc > evaluated_at_utc:
            return _result(scenario, "inconclusive", "future_observation")
        if (
            observation.profile_id != profile.profile_id
            or observation.control_id != profile.control_id
            or observation.target_id != profile.target_id
        ):
            return _result(scenario, "inconclusive", "observation_binding_mismatch")

    expected_writers = (
        profile.writer_boundary.legacy_writer_identity,
        profile.writer_boundary.replacement_writer_identity,
    )
    for observation, expected_writer in zip(observations, expected_writers, strict=True):
        if (
            observation.active_writer_identity != expected_writer
            or observation.other_active_writer_identities
        ):
            return _result(scenario, "fail", "single_writer_boundary_violated")

    if any(observation.outcome == "unavailable" for observation in observations):
        return _result(scenario, "inconclusive", "runtime_evidence_unavailable")
    if scenario == "correction" and any(
        observation.guest_telemetry_sha256 is None for observation in observations
    ):
        return _result(scenario, "inconclusive", "guest_correction_telemetry_missing")
    if scenario == "reporting" and any(
        observation.report_sha256 is None for observation in observations
    ):
        return _result(scenario, "inconclusive", "report_evidence_missing")

    legacy_semantics = _semantic_result(case.legacy)
    replacement_semantics = _semantic_result(case.replacement)
    if legacy_semantics == replacement_semantics:
        return _result(scenario, "pass", "observable_semantics_match")

    approval = case.accepted_difference
    if approval is None:
        return _result(scenario, "fail", "unapproved_behavior_difference")
    if (
        approval.legacy_evidence_sha256 != case.legacy.evidence_sha256
        or approval.replacement_evidence_sha256 != case.replacement.evidence_sha256
    ):
        return _result(scenario, "fail", "accepted_difference_evidence_mismatch")
    if not (approval.approved_at_utc <= evaluated_at_utc < approval.expires_at_utc):
        return _result(scenario, "fail", "accepted_difference_not_current")
    return _result(scenario, "accepted_difference", "reviewed_difference_is_exact_bound")


def classify_equivalence_suite(
    profile: MachineConfigurationEquivalenceProfileV1,
    cases: tuple[EquivalenceCaseV1, ...],
    *,
    evaluated_at_utc: datetime,
) -> EquivalenceSuiteResultV1:
    """Require one comparison for every migration behavior in MIG-01."""

    _require_aware(evaluated_at_utc, "evaluated_at_utc")
    scenario_names = [case.legacy.scenario for case in cases]
    if len(scenario_names) != len(set(scenario_names)):
        raise ValueError("equivalence suite scenarios cannot be duplicated")
    results = tuple(
        classify_equivalence_case(profile, case, evaluated_at_utc=evaluated_at_utc)
        for case in cases
    )
    missing = tuple(
        scenario for scenario in MANDATORY_SCENARIOS if scenario not in scenario_names
    )
    if missing:
        overall: Classification = "inconclusive"
    else:
        classifications = {result.classification for result in results}
        if "fail" in classifications:
            overall = "fail"
        elif "inconclusive" in classifications:
            overall = "inconclusive"
        elif "accepted_difference" in classifications:
            overall = "accepted_difference"
        else:
            overall = "pass"
    return EquivalenceSuiteResultV1(
        profile_id=profile.profile_id,
        classification=overall,
        scenario_results=results,
        missing_scenarios=missing,
        evaluated_at_utc=evaluated_at_utc,
    )


def _semantic_result(observation: ScenarioObservationV1) -> tuple[str | None, ...]:
    return (
        observation.outcome,
        observation.state_sha256,
        observation.error_code,
        observation.report_sha256,
    )


def _result(
    scenario: ScenarioName, classification: Classification, reason: str
) -> ScenarioClassificationV1:
    return ScenarioClassificationV1(
        scenario=scenario,
        classification=classification,
        reason=reason,
    )


def _validate_sha256(value: str, description: str) -> str:
    normalized = value.lower()
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{description} must be 64 lowercase hexadecimal characters")
    return normalized


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


__all__ = [
    "MACHINE_CONFIGURATION_EQUIVALENCE_SCHEMA_VERSION",
    "MANDATORY_ARTIFACT_ROLES",
    "MANDATORY_SCENARIOS",
    "AcceptedDifferenceV1",
    "EquivalenceCaseV1",
    "EquivalenceSuiteResultV1",
    "MachineConfigurationEquivalenceProfileV1",
    "RetainedArtifactV1",
    "RuntimePinV1",
    "ScenarioClassificationV1",
    "ScenarioObservationV1",
    "WriterBoundaryV1",
    "classify_equivalence_case",
    "classify_equivalence_suite",
]
