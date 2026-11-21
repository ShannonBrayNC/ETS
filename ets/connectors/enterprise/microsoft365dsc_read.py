"""Fail-closed contract for a read-only Microsoft365DSC resource slice."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

M365DSC_READ_SCHEMA_VERSION: Literal["ets.microsoft.m365dsc.read.v1"] = (
    "ets.microsoft.m365dsc.read.v1"
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")

AssessmentVerdict = Literal["compliant", "drift", "unknown"]
AssessmentReason = Literal[
    "test_and_native_readback_agree",
    "test_reports_drift_and_native_readback_agrees",
    "never_observed",
    "stale_observation",
    "collection_authority_revoked",
    "unsupported_resource",
    "collector_failed",
    "native_readback_unavailable",
    "observation_binding_mismatch",
    "test_and_native_readback_disagree",
]


class StrictM365DscModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ComponentPinV1(StrictM365DscModel):
    name: str = Field(min_length=1, max_length=256)
    version: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=1024)
    sha256: str = Field(min_length=64, max_length=64)

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


class WindowsPowerShellLcmBridgeV1(StrictM365DscModel):
    """Explicit compatibility boundary; PowerShell 7 remains the owning runtime."""

    mode: Literal["windows_powershell_lcm_compatibility_only"]
    powershell7_executable: ComponentPinV1
    windows_powershell_version: str = Field(min_length=1, max_length=64)


class M365DscRuntimePinsV1(StrictM365DscModel):
    os_name: str = Field(min_length=1, max_length=128)
    os_version: str = Field(min_length=1, max_length=128)
    powershell_edition: Literal["Core"]
    powershell_version: str = Field(min_length=1, max_length=64)
    microsoft365dsc_module: ComponentPinV1
    dependencies: tuple[ComponentPinV1, ...]
    uses_windows_powershell_lcm: bool = False
    lcm_bridge: WindowsPowerShellLcmBridgeV1 | None = None

    @model_validator(mode="after")
    def validate_runtime(self) -> M365DscRuntimePinsV1:
        version = _parse_version(self.powershell_version)
        if version < (7, 6, 0):
            raise ValueError("Microsoft365DSC read profile requires PowerShell 7.6.0 or newer")
        if self.uses_windows_powershell_lcm != (self.lcm_bridge is not None):
            raise ValueError("Windows PowerShell LCM use requires an explicit PS7 bridge record")
        names = [self.microsoft365dsc_module.name, *(item.name for item in self.dependencies)]
        if len(names) != len(set(names)):
            raise ValueError("runtime component pins cannot be duplicated")
        return self


class ReadAuthorityV1(StrictM365DscModel):
    collector_identity: str = Field(min_length=1, max_length=512)
    get_test_permissions: tuple[str, ...] = Field(min_length=1)
    write_permissions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_read_only(self) -> ReadAuthorityV1:
        _validate_read_permissions(self.get_test_permissions)
        if self.write_permissions:
            raise ValueError("Microsoft365DSC Get/Test authority cannot include write permissions")
        return self


class NativeReadbackV1(StrictM365DscModel):
    reader_identity: str = Field(min_length=1, max_length=512)
    workload: str = Field(min_length=1, max_length=256)
    api_version: str = Field(min_length=1, max_length=128)
    endpoint_family: str = Field(min_length=1, max_length=1024)
    read_permissions: tuple[str, ...] = Field(min_length=1)
    observed_property: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def enforce_native_read_only(self) -> NativeReadbackV1:
        _validate_read_permissions(self.read_permissions)
        return self


class M365DscResourceSliceV1(StrictM365DscModel):
    resource_name: str = Field(min_length=1, max_length=256)
    module_name: str = Field(min_length=1, max_length=256)
    module_version: str = Field(min_length=1, max_length=128)
    workload: str = Field(min_length=1, max_length=256)
    target_property: str = Field(min_length=1, max_length=512)
    qualification: Literal["supported"]
    allowed_operations: tuple[Literal["Get", "Test"], ...]

    @model_validator(mode="after")
    def require_get_and_test_only(self) -> M365DscResourceSliceV1:
        if self.allowed_operations != ("Get", "Test"):
            raise ValueError("resource slice must allow exactly ordered Get and Test operations")
        return self


class FrozenQualifiedProfileV1(StrictM365DscModel):
    profile_id: str = Field(min_length=1, max_length=256)
    profile_sha256: str = Field(min_length=64, max_length=64)
    module_version: str = Field(min_length=1, max_length=128)
    status: Literal["frozen"]

    @field_validator("profile_sha256")
    @classmethod
    def validate_profile_digest(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("frozen profile digest must be a SHA-256 value")
        return normalized


class M365DscReadProfileV1(StrictM365DscModel):
    """Pre-deployment contract for one supported Microsoft365DSC property."""

    schema_version: Literal["ets.microsoft.m365dsc.read.v1"] = M365DSC_READ_SCHEMA_VERSION
    profile_id: str = Field(min_length=1, max_length=256)
    environment: Literal["disposable_qualification", "production"]
    tenant_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=512)
    desired_property_sha256: str = Field(min_length=64, max_length=64)
    freshness_threshold_seconds: int = Field(ge=60)
    runtime: M365DscRuntimePinsV1
    authority: ReadAuthorityV1
    resource: M365DscResourceSliceV1
    native_readback: NativeReadbackV1
    frozen_predecessors: tuple[FrozenQualifiedProfileV1, ...] = ()

    @field_validator("desired_property_sha256")
    @classmethod
    def validate_desired_digest(cls, value: str) -> str:
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("desired property digest must be a SHA-256 value")
        return normalized

    @model_validator(mode="after")
    def validate_profile_bindings(self) -> M365DscReadProfileV1:
        module = self.runtime.microsoft365dsc_module
        if (
            self.resource.module_name != module.name
            or self.resource.module_version != module.version
        ):
            raise ValueError("resource slice must bind to the pinned Microsoft365DSC module")
        if self.native_readback.workload != self.resource.workload:
            raise ValueError("native read-back must bind to the resource workload")
        if self.native_readback.reader_identity == self.authority.collector_identity:
            raise ValueError("native read-back requires an identity separate from the collector")
        predecessor_ids = [item.profile_id for item in self.frozen_predecessors]
        if self.profile_id in predecessor_ids or len(predecessor_ids) != len(set(predecessor_ids)):
            raise ValueError("frozen predecessor profile IDs must be unique and historical")
        return self


class M365DscReadObservationV1(StrictM365DscModel):
    profile_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=512)
    desired_property_sha256: str = Field(min_length=64, max_length=64)
    collector_identity: str = Field(min_length=1, max_length=512)
    reader_identity: str = Field(min_length=1, max_length=512)
    collected_at_utc: datetime
    collector_outcome: Literal["success", "authority_revoked", "unsupported", "runtime_failure"]
    test_in_desired_state: bool | None = None
    native_readback_outcome: Literal["success", "authority_revoked", "unsupported", "failure"]
    native_property_sha256: str | None = Field(default=None, min_length=64, max_length=64)

    @field_validator("desired_property_sha256", "native_property_sha256")
    @classmethod
    def validate_digests(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.lower()
        if _SHA256_PATTERN.fullmatch(normalized) is None:
            raise ValueError("observation digests must be SHA-256 values")
        return normalized

    @field_validator("collected_at_utc")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        _require_aware(value, "collected_at_utc")
        return value

    @model_validator(mode="after")
    def validate_outcome_shape(self) -> M365DscReadObservationV1:
        if self.collector_outcome == "success" and self.test_in_desired_state is None:
            raise ValueError("successful collection requires a Test result")
        if self.collector_outcome != "success" and self.test_in_desired_state is not None:
            raise ValueError("failed collection cannot carry a Test result")
        if self.native_readback_outcome == "success" and self.native_property_sha256 is None:
            raise ValueError("successful native read-back requires a property digest")
        if self.native_readback_outcome != "success" and self.native_property_sha256 is not None:
            raise ValueError("failed native read-back cannot carry a property digest")
        return self


class M365DscReadAssessmentV1(StrictM365DscModel):
    profile_id: str
    verdict: AssessmentVerdict
    reason: AssessmentReason
    evaluated_at_utc: datetime
    observation_collected_at_utc: datetime | None = None
    observation_age_seconds: int | None = None


def assess_m365dsc_read(
    profile: M365DscReadProfileV1,
    observation: M365DscReadObservationV1 | None,
    *,
    evaluated_at_utc: datetime,
) -> M365DscReadAssessmentV1:
    """Require both Microsoft365DSC Test and an independent workload-native read."""

    _require_aware(evaluated_at_utc, "evaluated_at_utc")
    if observation is None:
        return _assessment(profile, "unknown", "never_observed", evaluated_at_utc)
    if observation.collected_at_utc > evaluated_at_utc:
        raise ValueError("observation collection cannot be in the future")
    age = int((evaluated_at_utc - observation.collected_at_utc).total_seconds())
    if age > profile.freshness_threshold_seconds:
        return _assessment(
            profile, "unknown", "stale_observation", evaluated_at_utc, observation, age
        )
    if (
        observation.profile_id != profile.profile_id
        or observation.target_id != profile.target_id
        or observation.desired_property_sha256 != profile.desired_property_sha256
        or observation.collector_identity != profile.authority.collector_identity
        or observation.reader_identity != profile.native_readback.reader_identity
    ):
        return _assessment(
            profile, "unknown", "observation_binding_mismatch", evaluated_at_utc, observation, age
        )
    if observation.collector_outcome == "authority_revoked":
        return _assessment(
            profile, "unknown", "collection_authority_revoked", evaluated_at_utc, observation, age
        )
    if observation.collector_outcome == "unsupported":
        return _assessment(
            profile, "unknown", "unsupported_resource", evaluated_at_utc, observation, age
        )
    if observation.collector_outcome != "success":
        return _assessment(
            profile, "unknown", "collector_failed", evaluated_at_utc, observation, age
        )
    if observation.native_readback_outcome != "success":
        return _assessment(
            profile, "unknown", "native_readback_unavailable", evaluated_at_utc, observation, age
        )
    native_matches = observation.native_property_sha256 == profile.desired_property_sha256
    if observation.test_in_desired_state != native_matches:
        return _assessment(
            profile,
            "unknown",
            "test_and_native_readback_disagree",
            evaluated_at_utc,
            observation,
            age,
        )
    if native_matches:
        return _assessment(
            profile,
            "compliant",
            "test_and_native_readback_agree",
            evaluated_at_utc,
            observation,
            age,
        )
    return _assessment(
        profile,
        "drift",
        "test_reports_drift_and_native_readback_agrees",
        evaluated_at_utc,
        observation,
        age,
    )


def _assessment(
    profile: M365DscReadProfileV1,
    verdict: AssessmentVerdict,
    reason: AssessmentReason,
    evaluated_at_utc: datetime,
    observation: M365DscReadObservationV1 | None = None,
    age: int | None = None,
) -> M365DscReadAssessmentV1:
    return M365DscReadAssessmentV1(
        profile_id=profile.profile_id,
        verdict=verdict,
        reason=reason,
        evaluated_at_utc=evaluated_at_utc,
        observation_collected_at_utc=(
            observation.collected_at_utc if observation is not None else None
        ),
        observation_age_seconds=age,
    )


def _validate_read_permissions(permissions: tuple[str, ...]) -> None:
    normalized = [item.strip() for item in permissions]
    if any(not item for item in normalized):
        raise ValueError("read permissions cannot be blank")
    if len(normalized) != len(set(normalized)):
        raise ValueError("read permissions cannot be duplicated")
    if any(
        "readwrite" in item.casefold() or item.casefold().startswith("write")
        for item in normalized
    ):
        raise ValueError("read authority cannot include write-capable permissions")


def _parse_version(value: str) -> tuple[int, int, int]:
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("PowerShell version must be an exact semantic version")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


__all__ = [
    "M365DSC_READ_SCHEMA_VERSION",
    "ComponentPinV1",
    "FrozenQualifiedProfileV1",
    "M365DscReadAssessmentV1",
    "M365DscReadObservationV1",
    "M365DscReadProfileV1",
    "M365DscResourceSliceV1",
    "M365DscRuntimePinsV1",
    "NativeReadbackV1",
    "ReadAuthorityV1",
    "WindowsPowerShellLcmBridgeV1",
    "assess_m365dsc_read",
]
