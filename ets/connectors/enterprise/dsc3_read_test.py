"""Fail-closed contract for scheduled, read-only DSC 3 configuration tests."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DSC3_READ_TEST_SCHEMA_VERSION: Literal["ets.microsoft.dsc3.read_test.v1"] = (
    "ets.microsoft.dsc3.read_test.v1"
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROOF_OF_CONCEPT_RESOURCE_NAMES = frozenset({"microsoft.windows/registry"})

AssessmentVerdict = Literal["compliant", "drift", "unknown"]
AssessmentReason = Literal[
    "structured_test_compliant",
    "structured_test_drift",
    "never_observed",
    "missed_or_dead_checker",
    "stale_checker",
    "process_failed",
    "structured_output_missing",
    "observation_binding_mismatch",
]


class StrictDscModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ComponentPinV1(StrictDscModel):
    """One immutable executable, resource, adapter, schema, or dependency pin."""

    name: str = Field(min_length=1, max_length=256)
    version: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=1024)
    sha256: str = Field(min_length=64, max_length=64)
    qualification: Literal["supported", "proof_of_concept"] = "supported"

    @field_validator("name", "version", "source")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("component pin text cannot be blank")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return normalized


class Dsc3RuntimePinsV1(StrictDscModel):
    """Complete runtime inventory required to reproduce a standalone DSC 3 test."""

    os_name: str = Field(min_length=1, max_length=128)
    os_version: str = Field(min_length=1, max_length=128)
    os_architecture: Literal["x86_64", "arm64"]
    dsc_executable: ComponentPinV1
    resources: tuple[ComponentPinV1, ...] = Field(min_length=1)
    adapters: tuple[ComponentPinV1, ...]
    schemas: tuple[ComponentPinV1, ...] = Field(min_length=1)
    dependencies: tuple[ComponentPinV1, ...]

    @model_validator(mode="after")
    def reject_duplicate_pins(self) -> Dsc3RuntimePinsV1:
        pins = (
            ("dsc_executable", self.dsc_executable),
            *(("resource", item) for item in self.resources),
            *(("adapter", item) for item in self.adapters),
            *(("schema", item) for item in self.schemas),
            *(("dependency", item) for item in self.dependencies),
        )
        identities = [(kind, item.name) for kind, item in pins]
        if len(identities) != len(set(identities)):
            raise ValueError("runtime pins cannot contain duplicate component names within a class")
        return self


class Dsc3SchedulerV1(StrictDscModel):
    """Owned scheduling and freshness policy for a non-resident DSC 3 worker."""

    scheduler_name: str = Field(min_length=1, max_length=256)
    execution_identity: str = Field(min_length=1, max_length=512)
    interval_seconds: int = Field(ge=60)
    timeout_seconds: int = Field(ge=1)
    overlap_policy: Literal["skip_if_running"]
    reboot_policy: Literal["run_when_available", "wait_for_next_interval"]
    freshness_threshold_seconds: int = Field(ge=60)

    @model_validator(mode="after")
    def validate_timing_policy(self) -> Dsc3SchedulerV1:
        if self.timeout_seconds >= self.interval_seconds:
            raise ValueError("timeout_seconds must be shorter than interval_seconds")
        if self.freshness_threshold_seconds < self.interval_seconds + self.timeout_seconds:
            raise ValueError(
                "freshness threshold must cover at least one interval plus the run timeout"
            )
        return self


class Dsc3ReadTestProfileV1(StrictDscModel):
    """Pre-deployment contract for one scheduled DSC 3 configuration test."""

    schema_version: Literal["ets.microsoft.dsc3.read_test.v1"] = DSC3_READ_TEST_SCHEMA_VERSION
    profile_id: str = Field(min_length=1, max_length=256)
    environment: Literal["disposable_qualification", "production"]
    execution_mode: Literal["standalone_dsc3"]
    operation: Literal["config_test"]
    resident_lcm_present: Literal[False]
    desired_configuration_sha256: str = Field(min_length=64, max_length=64)
    scheduler: Dsc3SchedulerV1
    runtime: Dsc3RuntimePinsV1

    @field_validator("desired_configuration_sha256")
    @classmethod
    def validate_configuration_digest(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("desired configuration digest must be a SHA-256 value")
        return normalized

    @model_validator(mode="after")
    def exclude_proof_of_concept_resources_from_production(self) -> Dsc3ReadTestProfileV1:
        has_poc_resource = any(
            item.qualification == "proof_of_concept"
            or item.name.casefold() in _PROOF_OF_CONCEPT_RESOURCE_NAMES
            for item in self.runtime.resources
        )
        if self.environment == "production" and has_poc_resource:
            raise ValueError("proof-of-concept DSC resources are excluded from production")
        return self


class Dsc3ResourceTestResultV1(StrictDscModel):
    resource_name: str = Field(min_length=1, max_length=256)
    in_desired_state: bool
    differing_properties: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_differences(self) -> Dsc3ResourceTestResultV1:
        if self.in_desired_state and self.differing_properties:
            raise ValueError("a resource in desired state cannot list differing properties")
        if len(set(self.differing_properties)) != len(self.differing_properties):
            raise ValueError("differing properties cannot contain duplicates")
        return self


class Dsc3StructuredTestResultV1(StrictDscModel):
    """Normalized projection of the structured `dsc config test` result."""

    in_desired_state: bool
    resources: tuple[Dsc3ResourceTestResultV1, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_aggregate(self) -> Dsc3StructuredTestResultV1:
        if self.in_desired_state != all(item.in_desired_state for item in self.resources):
            raise ValueError("aggregate desired-state result must match all resource results")
        names = [item.resource_name for item in self.resources]
        if len(names) != len(set(names)):
            raise ValueError("structured test output cannot contain duplicate resources")
        return self


class Dsc3RunObservationV1(StrictDscModel):
    """Process and structured-output evidence retained for one worker invocation."""

    profile_id: str = Field(min_length=1, max_length=256)
    desired_configuration_sha256: str = Field(min_length=64, max_length=64)
    started_at_utc: datetime
    completed_at_utc: datetime
    process_exit_code: int
    structured_result: Dsc3StructuredTestResultV1 | None

    @field_validator("desired_configuration_sha256")
    @classmethod
    def validate_configuration_digest(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("desired configuration digest must be a SHA-256 value")
        return normalized

    @field_validator("started_at_utc", "completed_at_utc")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("DSC observation timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_run_interval(self) -> Dsc3RunObservationV1:
        if self.completed_at_utc < self.started_at_utc:
            raise ValueError("completed_at_utc cannot precede started_at_utc")
        return self


class Dsc3ReadTestAssessmentV1(StrictDscModel):
    profile_id: str
    verdict: AssessmentVerdict
    reason: AssessmentReason
    evaluated_at_utc: datetime
    observation_completed_at_utc: datetime | None = None
    last_successful_completed_at_utc: datetime | None = None
    observation_age_seconds: int | None = None


def assess_dsc3_read_test(
    profile: Dsc3ReadTestProfileV1,
    observation: Dsc3RunObservationV1 | None,
    *,
    evaluated_at_utc: datetime,
    last_successful_completed_at_utc: datetime | None = None,
) -> Dsc3ReadTestAssessmentV1:
    """Evaluate both process and structured output, preserving checker failure as unknown."""

    _require_aware(evaluated_at_utc, "evaluated_at_utc")
    if last_successful_completed_at_utc is not None:
        _require_aware(last_successful_completed_at_utc, "last_successful_completed_at_utc")
        if last_successful_completed_at_utc > evaluated_at_utc:
            raise ValueError("last successful completion cannot be in the future")

    if observation is None:
        reason: AssessmentReason = (
            "never_observed"
            if last_successful_completed_at_utc is None
            else "missed_or_dead_checker"
        )
        return _assessment(
            profile,
            verdict="unknown",
            reason=reason,
            evaluated_at_utc=evaluated_at_utc,
            last_successful_completed_at_utc=last_successful_completed_at_utc,
        )

    if observation.completed_at_utc > evaluated_at_utc:
        raise ValueError("observation completion cannot be in the future")
    age_seconds = int((evaluated_at_utc - observation.completed_at_utc).total_seconds())
    if age_seconds > profile.scheduler.freshness_threshold_seconds:
        return _assessment(
            profile,
            verdict="unknown",
            reason="stale_checker",
            observation=observation,
            evaluated_at_utc=evaluated_at_utc,
            last_successful_completed_at_utc=last_successful_completed_at_utc,
            observation_age_seconds=age_seconds,
        )
    expected_resources = {item.name for item in profile.runtime.resources}
    observed_resources = (
        {item.resource_name for item in observation.structured_result.resources}
        if observation.structured_result is not None
        else expected_resources
    )
    if (
        observation.profile_id != profile.profile_id
        or observation.desired_configuration_sha256 != profile.desired_configuration_sha256
        or observed_resources != expected_resources
    ):
        return _assessment(
            profile,
            verdict="unknown",
            reason="observation_binding_mismatch",
            observation=observation,
            evaluated_at_utc=evaluated_at_utc,
            last_successful_completed_at_utc=last_successful_completed_at_utc,
            observation_age_seconds=age_seconds,
        )
    if observation.process_exit_code != 0:
        return _assessment(
            profile,
            verdict="unknown",
            reason="process_failed",
            observation=observation,
            evaluated_at_utc=evaluated_at_utc,
            last_successful_completed_at_utc=last_successful_completed_at_utc,
            observation_age_seconds=age_seconds,
        )
    if observation.structured_result is None:
        return _assessment(
            profile,
            verdict="unknown",
            reason="structured_output_missing",
            observation=observation,
            evaluated_at_utc=evaluated_at_utc,
            last_successful_completed_at_utc=last_successful_completed_at_utc,
            observation_age_seconds=age_seconds,
        )
    if observation.structured_result.in_desired_state:
        return _assessment(
            profile,
            verdict="compliant",
            reason="structured_test_compliant",
            observation=observation,
            evaluated_at_utc=evaluated_at_utc,
            last_successful_completed_at_utc=last_successful_completed_at_utc,
            observation_age_seconds=age_seconds,
        )
    return _assessment(
        profile,
        verdict="drift",
        reason="structured_test_drift",
        observation=observation,
        evaluated_at_utc=evaluated_at_utc,
        last_successful_completed_at_utc=last_successful_completed_at_utc,
        observation_age_seconds=age_seconds,
    )


def _assessment(
    profile: Dsc3ReadTestProfileV1,
    *,
    verdict: AssessmentVerdict,
    reason: AssessmentReason,
    evaluated_at_utc: datetime,
    last_successful_completed_at_utc: datetime | None,
    observation: Dsc3RunObservationV1 | None = None,
    observation_age_seconds: int | None = None,
) -> Dsc3ReadTestAssessmentV1:
    return Dsc3ReadTestAssessmentV1(
        profile_id=profile.profile_id,
        verdict=verdict,
        reason=reason,
        evaluated_at_utc=evaluated_at_utc,
        observation_completed_at_utc=(
            observation.completed_at_utc if observation is not None else None
        ),
        last_successful_completed_at_utc=last_successful_completed_at_utc,
        observation_age_seconds=observation_age_seconds,
    )


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


__all__ = [
    "DSC3_READ_TEST_SCHEMA_VERSION",
    "ComponentPinV1",
    "Dsc3ReadTestAssessmentV1",
    "Dsc3ReadTestProfileV1",
    "Dsc3ResourceTestResultV1",
    "Dsc3RunObservationV1",
    "Dsc3RuntimePinsV1",
    "Dsc3SchedulerV1",
    "Dsc3StructuredTestResultV1",
    "assess_dsc3_read_test",
]
