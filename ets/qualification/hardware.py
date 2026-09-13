"""Cross-product ETS hardware qualification execution and report contracts.

HQP-1 turns the product-neutral HQP-0 profile into a machine-readable retained run package.
The package is intentionally product-neutral and does not participate in ETS runtime verification.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ets.core.canonical_json import canonical_sha256

_SHA256_RE = r"^[0-9a-f]{64}$"
_COMMIT_RE = r"^[0-9a-f]{40,64}$"
_CLAIM_BOUNDARY = (
    "bounded_hqp_execution_evidence_not_complete_observation_truth_compliance_safety_or_ga_proof"
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class TestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INVALID = "invalid"
    WAIVED = "waived"
    NOT_RUN = "not_run"


class QualificationDisposition(StrEnum):
    IN_PROGRESS = "in_progress"
    INVALID = "invalid"
    FAILED = "failed"
    LAB_TESTED = "lab_tested"
    QUALIFIED = "qualified"
    QUALIFIED_WITH_DEVIATION = "qualified_with_deviation"


class VerifierStatus(StrEnum):
    NOT_RUN = "not_run"
    VALID = "valid"
    INVALID = "invalid"


class DeviationKind(StrEnum):
    DEVIATION = "deviation"
    WAIVER = "waiver"


class ProfileBinding(StrictModel):
    profile_id: str = Field(min_length=3, max_length=256)
    profile_version: str = Field(min_length=1, max_length=128)
    profile_digest_sha256: str = Field(pattern=_SHA256_RE)


class DeviceIdentity(StrictModel):
    device_id: str = Field(min_length=1, max_length=256)
    manufacturer: str = Field(min_length=1, max_length=256)
    model: str = Field(min_length=1, max_length=256)
    hardware_revision: str = Field(min_length=1, max_length=256)
    serial_or_asset_id: str | None = Field(default=None, max_length=256)
    firmware: dict[str, str] = Field(default_factory=dict)
    identity_digest_sha256: str = Field(pattern=_SHA256_RE)


class QualificationEnvironment(StrictModel):
    environment_id: str = Field(min_length=1, max_length=256)
    dimensions: dict[str, str]
    environment_digest_sha256: str = Field(pattern=_SHA256_RE)


class BuildIdentity(StrictModel):
    repository: str = Field(min_length=1, max_length=512)
    commit_sha: str = Field(pattern=_COMMIT_RE)
    artifact_digest_sha256: str = Field(pattern=_SHA256_RE)
    configuration_digest_sha256: str = Field(pattern=_SHA256_RE)
    sbom_artifact_id: str | None = Field(default=None, max_length=256)


class ObserverIdentity(StrictModel):
    observer_id: str = Field(min_length=1, max_length=256)
    observer_kind: Literal["human", "machine", "composite"]
    role: str = Field(min_length=1, max_length=256)
    signing_identity: str | None = Field(default=None, max_length=512)


class ArtifactReference(StrictModel):
    artifact_id: str = Field(min_length=1, max_length=256)
    artifact_role: str = Field(min_length=1, max_length=256)
    media_type: str = Field(min_length=1, max_length=256)
    sha256: str = Field(pattern=_SHA256_RE)
    byte_length: int = Field(ge=0)
    retention_locator: str | None = Field(default=None, max_length=2048)
    redaction_state: Literal["none", "redacted", "withheld"] = "none"
    required: bool = True
    secret_material_embedded: Literal[False] = False
    private_key_embedded: Literal[False] = False


class StateReference(StrictModel):
    state_id: str = Field(min_length=1, max_length=256)
    canonical_digest_sha256: str = Field(pattern=_SHA256_RE)
    artifact_ids: tuple[str, ...] = ()


class StimulusRecord(StrictModel):
    stimulus_id: str = Field(min_length=1, max_length=256)
    test_id: str = Field(min_length=1, max_length=256)
    issued_at: datetime
    authority_reference: str = Field(min_length=1, max_length=512)
    stimulus_class: str = Field(min_length=1, max_length=256)
    canonical_digest_sha256: str = Field(pattern=_SHA256_RE)
    artifact_ids: tuple[str, ...] = ()


class ObservationRecord(StrictModel):
    observation_id: str = Field(min_length=1, max_length=256)
    test_id: str = Field(min_length=1, max_length=256)
    observer_id: str = Field(min_length=1, max_length=256)
    observed_at: datetime
    observation_class: str = Field(min_length=1, max_length=256)
    canonical_digest_sha256: str = Field(pattern=_SHA256_RE)
    artifact_ids: tuple[str, ...] = ()
    uncertainty_statement: str | None = Field(default=None, max_length=2048)


class ResultingStateRecord(StrictModel):
    resulting_state_id: str = Field(min_length=1, max_length=256)
    test_id: str = Field(min_length=1, max_length=256)
    observed_at: datetime
    canonical_digest_sha256: str = Field(pattern=_SHA256_RE)
    artifact_ids: tuple[str, ...] = ()


class EvidenceObjectReference(StrictModel):
    evidence_object_id: str = Field(min_length=1, max_length=512)
    evidence_class: str = Field(min_length=1, max_length=256)
    canonical_digest_sha256: str = Field(pattern=_SHA256_RE)
    artifact_ids: tuple[str, ...] = ()


class DeviationRecord(StrictModel):
    deviation_id: str = Field(min_length=1, max_length=256)
    kind: DeviationKind
    test_id: str | None = Field(default=None, max_length=256)
    rationale: str = Field(min_length=1, max_length=4096)
    approved_by: str = Field(min_length=1, max_length=256)
    approval_artifact_id: str = Field(min_length=1, max_length=256)
    affects_claim_scope: bool
    expires_at: datetime | None = None


class AssertionResult(StrictModel):
    assertion_id: str = Field(min_length=1, max_length=256)
    passed: bool
    reason: str = Field(min_length=1, max_length=2048)


class TestExecution(StrictModel):
    test_id: str = Field(min_length=1, max_length=256)
    required: bool
    status: TestStatus
    started_at: datetime
    completed_at: datetime | None = None
    starting_state_id: str = Field(min_length=1, max_length=256)
    stimulus_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    resulting_state_ids: tuple[str, ...]
    evidence_object_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...] = ()
    assertions: tuple[AssertionResult, ...]
    deviation_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_completed_timestamp_for_terminal_status(self) -> TestExecution:
        if self.status is not TestStatus.NOT_RUN and self.completed_at is None:
            raise ValueError("terminal test status requires completed_at")
        return self


class VerifierResult(StrictModel):
    status: VerifierStatus
    verifier_id: str | None = Field(default=None, max_length=256)
    verifier_build_digest_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    independent_execution_context: bool = False
    verification_digest_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    challenge_nonce: str | None = Field(default=None, max_length=512)
    reason: str = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def enforce_valid_verifier_identity(self) -> VerifierResult:
        if self.status is VerifierStatus.VALID:
            if not self.independent_execution_context:
                raise ValueError("valid verifier result must come from an independent context")
            if not self.verifier_id or not self.verifier_build_digest_sha256:
                raise ValueError("valid verifier result requires immutable verifier identity")
            if not self.verification_digest_sha256:
                raise ValueError("valid verifier result requires a verification digest")
        return self


class HardwareQualificationRun(StrictModel):
    schema_version: Literal["ets.hardware-qualification-run.v1"] = (
        "ets.hardware-qualification-run.v1"
    )
    run_id: str = Field(min_length=1, max_length=256)
    profile: ProfileBinding
    device: DeviceIdentity
    environment: QualificationEnvironment
    build: BuildIdentity
    observers: tuple[ObserverIdentity, ...]
    started_at: datetime
    completed_at: datetime | None = None
    starting_states: tuple[StateReference, ...]
    stimuli: tuple[StimulusRecord, ...]
    observations: tuple[ObservationRecord, ...]
    resulting_states: tuple[ResultingStateRecord, ...]
    artifacts: tuple[ArtifactReference, ...]
    evidence_objects: tuple[EvidenceObjectReference, ...]
    test_executions: tuple[TestExecution, ...]
    deviations: tuple[DeviationRecord, ...] = ()
    verifier_result: VerifierResult
    final_disposition: QualificationDisposition
    run_digest_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    credentials_embedded: Literal[False] = False
    private_keys_embedded: Literal[False] = False
    claim_boundary: Literal[
        "bounded_hqp_execution_evidence_not_complete_observation_truth_compliance_safety_or_ga_proof"
    ] = _CLAIM_BOUNDARY

    @model_validator(mode="after")
    def enforce_references_and_disposition(self) -> HardwareQualificationRun:
        observer_ids = _unique_ids(self.observers, "observer_id", "observer")
        state_ids = _unique_ids(self.starting_states, "state_id", "starting state")
        stimulus_ids = _unique_ids(self.stimuli, "stimulus_id", "stimulus")
        observation_ids = _unique_ids(self.observations, "observation_id", "observation")
        result_ids = _unique_ids(self.resulting_states, "resulting_state_id", "resulting state")
        artifact_ids = _unique_ids(self.artifacts, "artifact_id", "artifact")
        evidence_ids = _unique_ids(self.evidence_objects, "evidence_object_id", "Evidence Object")
        deviation_ids = _unique_ids(self.deviations, "deviation_id", "deviation")
        _unique_ids(self.test_executions, "test_id", "test execution")

        for observation in self.observations:
            _require_member(observation.observer_id, observer_ids, "observation observer")
            _require_members(observation.artifact_ids, artifact_ids, "observation artifact")
        for state in self.starting_states:
            _require_members(state.artifact_ids, artifact_ids, "starting-state artifact")
        for stimulus in self.stimuli:
            _require_members(stimulus.artifact_ids, artifact_ids, "stimulus artifact")
        for result in self.resulting_states:
            _require_members(result.artifact_ids, artifact_ids, "resulting-state artifact")
        for evidence in self.evidence_objects:
            _require_members(evidence.artifact_ids, artifact_ids, "Evidence Object artifact")
        for deviation in self.deviations:
            _require_member(deviation.approval_artifact_id, artifact_ids, "deviation approval artifact")

        for execution in self.test_executions:
            _require_member(execution.starting_state_id, state_ids, "test starting state")
            _require_members(execution.stimulus_ids, stimulus_ids, "test stimulus")
            _require_members(execution.observation_ids, observation_ids, "test observation")
            _require_members(execution.resulting_state_ids, result_ids, "test resulting state")
            _require_members(execution.evidence_object_ids, evidence_ids, "test Evidence Object")
            _require_members(execution.artifact_ids, artifact_ids, "test artifact")
            _require_members(execution.deviation_ids, deviation_ids, "test deviation")

        terminal = self.final_disposition is not QualificationDisposition.IN_PROGRESS
        if terminal and self.completed_at is None:
            raise ValueError("terminal qualification run requires completed_at")
        if terminal and self.run_digest_sha256 is None:
            raise ValueError("terminal qualification run must be sealed with run_digest_sha256")

        if self.run_digest_sha256 is not None:
            expected = canonical_sha256(
                self.model_dump(mode="json", exclude={"run_digest_sha256"})
            )
            if self.run_digest_sha256 != expected:
                raise ValueError("run_digest_sha256 does not match canonical run payload")

        if self.final_disposition in {
            QualificationDisposition.QUALIFIED,
            QualificationDisposition.QUALIFIED_WITH_DEVIATION,
        }:
            if self.verifier_result.status is not VerifierStatus.VALID:
                raise ValueError("qualified disposition requires a valid independent verifier")
            if not self.evidence_objects:
                raise ValueError("qualified disposition requires retained Evidence Object references")
            for execution in self.test_executions:
                if execution.required and execution.status not in {
                    TestStatus.PASSED,
                    TestStatus.WAIVED,
                }:
                    raise ValueError("qualified disposition requires every required case to pass/waive")
            if self.final_disposition is QualificationDisposition.QUALIFIED:
                if any(item.affects_claim_scope for item in self.deviations):
                    raise ValueError("claim-affecting deviation requires qualified_with_deviation")

        return self


class HardwareQualificationReport(StrictModel):
    schema_version: Literal["ets.hardware-qualification-report.v1"] = (
        "ets.hardware-qualification-report.v1"
    )
    report_id: str = Field(min_length=1, max_length=256)
    run_id: str = Field(min_length=1, max_length=256)
    run_digest_sha256: str = Field(pattern=_SHA256_RE)
    profile: ProfileBinding
    device_id: str = Field(min_length=1, max_length=256)
    hardware_revision: str = Field(min_length=1, max_length=256)
    commit_sha: str = Field(pattern=_COMMIT_RE)
    required_case_ids: tuple[str, ...]
    passed_case_ids: tuple[str, ...]
    failed_case_ids: tuple[str, ...]
    invalid_case_ids: tuple[str, ...]
    waived_case_ids: tuple[str, ...]
    not_run_case_ids: tuple[str, ...]
    deviation_ids: tuple[str, ...]
    evidence_object_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...]
    verifier_status: VerifierStatus
    verifier_result_digest_sha256: str = Field(pattern=_SHA256_RE)
    final_disposition: QualificationDisposition
    report_digest_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "bounded_hqp_execution_evidence_not_complete_observation_truth_compliance_safety_or_ga_proof"
    ] = _CLAIM_BOUNDARY

    @model_validator(mode="after")
    def verify_report_digest(self) -> HardwareQualificationReport:
        if self.final_disposition is QualificationDisposition.IN_PROGRESS:
            raise ValueError("qualification report cannot describe an in-progress run")
        expected = canonical_sha256(
            self.model_dump(mode="json", exclude={"report_digest_sha256"})
        )
        if self.report_digest_sha256 != expected:
            raise ValueError("report_digest_sha256 does not match canonical report payload")
        return self


def seal_qualification_run(
    run: HardwareQualificationRun,
    *,
    final_disposition: QualificationDisposition | None = None,
    completed_at: datetime | None = None,
) -> HardwareQualificationRun:
    """Seal a draft run, optionally applying its terminal disposition and completion time."""

    updates: dict[str, object] = {"run_digest_sha256": None}
    if final_disposition is not None:
        updates["final_disposition"] = final_disposition
    if completed_at is not None:
        updates["completed_at"] = completed_at
    candidate = run.model_copy(update=updates)
    digest_payload = candidate.model_dump(mode="json", exclude={"run_digest_sha256"})
    digest = canonical_sha256(digest_payload)
    validation_payload = candidate.model_dump(mode="python", exclude={"run_digest_sha256"})
    validation_payload["run_digest_sha256"] = digest
    return HardwareQualificationRun.model_validate(validation_payload)


def build_qualification_report(
    run: HardwareQualificationRun,
    *,
    report_id: str | None = None,
) -> HardwareQualificationReport:
    """Build the deterministic HQP report projection for a sealed terminal run."""

    if run.run_digest_sha256 is None:
        raise ValueError("qualification report requires a sealed run")
    if run.final_disposition is QualificationDisposition.IN_PROGRESS:
        raise ValueError("qualification report requires a terminal run")

    def ids_for(status: TestStatus) -> tuple[str, ...]:
        return tuple(item.test_id for item in run.test_executions if item.status is status)

    required_ids = tuple(item.test_id for item in run.test_executions if item.required)
    verifier_digest = canonical_sha256(run.verifier_result.model_dump(mode="json"))
    digest_payload: dict[str, object] = {
        "schema_version": "ets.hardware-qualification-report.v1",
        "report_id": report_id or f"{run.run_id}.report",
        "run_id": run.run_id,
        "run_digest_sha256": run.run_digest_sha256,
        "profile": run.profile.model_dump(mode="json"),
        "device_id": run.device.device_id,
        "hardware_revision": run.device.hardware_revision,
        "commit_sha": run.build.commit_sha,
        "required_case_ids": required_ids,
        "passed_case_ids": ids_for(TestStatus.PASSED),
        "failed_case_ids": ids_for(TestStatus.FAILED),
        "invalid_case_ids": ids_for(TestStatus.INVALID),
        "waived_case_ids": ids_for(TestStatus.WAIVED),
        "not_run_case_ids": ids_for(TestStatus.NOT_RUN),
        "deviation_ids": tuple(item.deviation_id for item in run.deviations),
        "evidence_object_ids": tuple(item.evidence_object_id for item in run.evidence_objects),
        "artifact_ids": tuple(item.artifact_id for item in run.artifacts),
        "verifier_status": run.verifier_result.status.value,
        "verifier_result_digest_sha256": verifier_digest,
        "final_disposition": run.final_disposition.value,
        "claim_boundary": _CLAIM_BOUNDARY,
    }
    report_digest = canonical_sha256(digest_payload)
    validation_payload = dict(digest_payload)
    validation_payload["profile"] = run.profile
    validation_payload["verifier_status"] = run.verifier_result.status
    validation_payload["final_disposition"] = run.final_disposition
    validation_payload["report_digest_sha256"] = report_digest
    return HardwareQualificationReport.model_validate(validation_payload)


def _unique_ids(items: tuple[StrictModel, ...], attribute: str, label: str) -> set[str]:
    values = [str(getattr(item, attribute)) for item in items]
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label} identifier")
    return set(values)


def _require_member(value: str, available: set[str], label: str) -> None:
    if value not in available:
        raise ValueError(f"unknown {label}: {value}")


def _require_members(values: tuple[str, ...], available: set[str], label: str) -> None:
    for value in values:
        _require_member(value, available, label)


__all__ = [
    "ArtifactReference",
    "BuildIdentity",
    "DeviationKind",
    "DeviationRecord",
    "DeviceIdentity",
    "EvidenceObjectReference",
    "HardwareQualificationReport",
    "HardwareQualificationRun",
    "ObservationRecord",
    "ObserverIdentity",
    "ProfileBinding",
    "QualificationDisposition",
    "QualificationEnvironment",
    "ResultingStateRecord",
    "StateReference",
    "StimulusRecord",
    "TestExecution",
    "TestStatus",
    "VerifierResult",
    "VerifierStatus",
    "build_qualification_report",
    "seal_qualification_run",
]
