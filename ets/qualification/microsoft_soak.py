"""Cumulative Microsoft connector soak qualification for G2E-F.

This module evaluates retained operational-posture/proof probe artifacts. It does not collect
Microsoft data, mutate connector state, or participate in ETS cryptographic verification.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.connectors.enterprise.microsoft_health import MicrosoftOperationalPostureV1

MICROSOFT_SOAK_POLICY_SCHEMA_VERSION: Literal[
    "ets.qualification.microsoft_soak_policy.v1"
] = "ets.qualification.microsoft_soak_policy.v1"
MICROSOFT_SOAK_PROBE_SCHEMA_VERSION: Literal[
    "ets.qualification.microsoft_soak_probe.v1"
] = "ets.qualification.microsoft_soak_probe.v1"
MICROSOFT_SOAK_SUMMARY_SCHEMA_VERSION: Literal[
    "ets.qualification.microsoft_soak_summary.v1"
] = "ets.qualification.microsoft_soak_summary.v1"


class MicrosoftSoakQualificationError(ValueError):
    """Raised when retained soak evidence cannot be qualified safely."""


class StrictSoakModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MicrosoftSoakPolicyV1(StrictSoakModel):
    """Governed coverage requirements for one release-candidate soak."""

    schema_version: Literal["ets.qualification.microsoft_soak_policy.v1"] = (
        MICROSOFT_SOAK_POLICY_SCHEMA_VERSION
    )
    profile_id: str = Field(min_length=1, max_length=200)
    minimum_duration_seconds: int = Field(ge=259_200, le=1_209_600)
    minimum_probe_count: int = Field(ge=2, le=10_000)
    maximum_probe_interval_seconds: int = Field(ge=60, le=21_600)
    maximum_evaluation_age_seconds: int = Field(ge=0, le=3_600)
    required_health_state: Literal["healthy"] = "healthy"
    require_zero_terminal_failures: Literal[True] = True
    require_verified_proof_each_probe: Literal[True] = True
    require_final_healthy: Literal[True] = True


class MicrosoftSoakProbeV1(StrictSoakModel):
    """One sanitized short-lived probe retained independently of the live job."""

    schema_version: Literal["ets.qualification.microsoft_soak_probe.v1"] = (
        MICROSOFT_SOAK_PROBE_SCHEMA_VERSION
    )
    source_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    workflow_run_id: str = Field(min_length=1, max_length=100)
    collected_at_utc: datetime
    posture: MicrosoftOperationalPostureV1
    proof_reference: str = Field(min_length=1, max_length=500)
    proof_verification_valid: bool
    reusable_credential_retained: Literal[False] = False
    raw_source_payload_retained: Literal[False] = False

    @field_validator("collected_at_utc")
    @classmethod
    def normalize_collected_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Microsoft soak probe timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def preserve_operational_nonclaims(self) -> MicrosoftSoakProbeV1:
        posture = self.posture
        if posture.verification_claimed:
            raise ValueError("Microsoft operational posture cannot claim ETS verification")
        if posture.source_truth_claimed:
            raise ValueError("Microsoft operational posture cannot claim source truth")
        if posture.completeness_claimed:
            raise ValueError("Microsoft operational posture cannot claim source completeness")
        return self


class MicrosoftSoakSummaryV1(StrictSoakModel):
    """Deterministic aggregate over one immutable release-candidate soak window."""

    schema_version: Literal["ets.qualification.microsoft_soak_summary.v1"] = (
        MICROSOFT_SOAK_SUMMARY_SCHEMA_VERSION
    )
    policy_profile_id: str = Field(min_length=1, max_length=200)
    source_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    instance_id: str = Field(min_length=1, max_length=128)
    ets_tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=200)
    microsoft_tenant_id: str = Field(min_length=36, max_length=36)
    subscription_id: str = Field(min_length=1, max_length=200)
    operational_policy_profile_id: str = Field(min_length=1, max_length=200)
    started_at_utc: datetime
    ended_at_utc: datetime
    duration_seconds: int = Field(ge=0)
    probe_count: int = Field(ge=0)
    maximum_observed_probe_interval_seconds: int = Field(ge=0)
    healthy_probe_count: int = Field(ge=0)
    degraded_probe_count: int = Field(ge=0)
    failed_probe_count: int = Field(ge=0)
    proof_failure_count: int = Field(ge=0)
    terminal_failure_probe_count: int = Field(ge=0)
    qualified: bool
    blockers: tuple[str, ...]
    verification_claimed_by_soak: Literal[False] = False
    source_truth_claimed: Literal[False] = False
    source_completeness_claimed: Literal[False] = False

    @field_validator("started_at_utc", "ended_at_utc")
    @classmethod
    def normalize_summary_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Microsoft soak summary timestamps must be timezone-aware")
        return value.astimezone(UTC)


def summarize_microsoft_soak(
    probes: tuple[MicrosoftSoakProbeV1, ...],
    policy: MicrosoftSoakPolicyV1,
) -> MicrosoftSoakSummaryV1:
    """Evaluate retained probes without inventing a second operational-health algorithm."""

    if not probes:
        raise MicrosoftSoakQualificationError("Microsoft soak requires at least one probe")
    ordered = tuple(sorted(probes, key=lambda probe: probe.collected_at_utc))
    _require_unique_probe_times(ordered)
    reference = ordered[0]
    _validate_identity(reference, ordered[1:])
    _validate_probe_evaluation_age(ordered, policy)

    started = ordered[0].collected_at_utc
    ended = ordered[-1].collected_at_utc
    duration_seconds = max(0, int((ended - started).total_seconds()))
    intervals = tuple(
        int((current.collected_at_utc - previous.collected_at_utc).total_seconds())
        for previous, current in zip(ordered, ordered[1:], strict=False)
    )
    maximum_interval = max(intervals, default=0)
    health_counts = Counter(probe.posture.health.state for probe in ordered)
    proof_failures = sum(not probe.proof_verification_valid for probe in ordered)
    terminal_failure_probes = sum(
        probe.posture.terminal_failure_count > 0 for probe in ordered
    )

    blockers: list[str] = []
    if duration_seconds < policy.minimum_duration_seconds:
        blockers.append("soak duration is below policy")
    if len(ordered) < policy.minimum_probe_count:
        blockers.append("soak probe count is below policy")
    if maximum_interval > policy.maximum_probe_interval_seconds:
        blockers.append("soak probe interval exceeds policy")
    if health_counts["degraded"] > 0:
        blockers.append("one or more Microsoft operational probes were degraded")
    if health_counts["failed"] > 0:
        blockers.append("one or more Microsoft operational probes failed")
    if terminal_failure_probes > 0:
        blockers.append("one or more probes reported terminal synchronization failures")
    if proof_failures > 0:
        blockers.append("one or more soak proof verifications failed")
    if ordered[-1].posture.health.state != policy.required_health_state:
        blockers.append("final Microsoft operational posture is not healthy")

    return MicrosoftSoakSummaryV1(
        policy_profile_id=policy.profile_id,
        source_sha=reference.source_sha,
        image_digest=reference.image_digest,
        instance_id=reference.posture.instance_id,
        ets_tenant_id=reference.posture.ets_tenant_id,
        workspace_id=reference.posture.workspace_id,
        source_id=reference.posture.source_id,
        microsoft_tenant_id=reference.posture.microsoft_tenant_id,
        subscription_id=reference.posture.subscription_id,
        operational_policy_profile_id=reference.posture.policy_profile_id,
        started_at_utc=started,
        ended_at_utc=ended,
        duration_seconds=duration_seconds,
        probe_count=len(ordered),
        maximum_observed_probe_interval_seconds=maximum_interval,
        healthy_probe_count=health_counts["healthy"],
        degraded_probe_count=health_counts["degraded"],
        failed_probe_count=health_counts["failed"],
        proof_failure_count=proof_failures,
        terminal_failure_probe_count=terminal_failure_probes,
        qualified=not blockers,
        blockers=tuple(blockers),
    )


def _require_unique_probe_times(probes: tuple[MicrosoftSoakProbeV1, ...]) -> None:
    timestamps = [probe.collected_at_utc for probe in probes]
    if len(timestamps) != len(set(timestamps)):
        raise MicrosoftSoakQualificationError("Microsoft soak contains duplicate probe timestamps")


def _validate_identity(
    reference: MicrosoftSoakProbeV1,
    probes: tuple[MicrosoftSoakProbeV1, ...],
) -> None:
    expected = _identity(reference)
    for probe in probes:
        if _identity(probe) != expected:
            raise MicrosoftSoakQualificationError(
                "Microsoft soak probe identity changed within the qualification window"
            )


def _identity(probe: MicrosoftSoakProbeV1) -> tuple[str, ...]:
    posture = probe.posture
    return (
        probe.source_sha,
        probe.image_digest,
        posture.instance_id,
        posture.ets_tenant_id,
        posture.workspace_id,
        posture.source_id,
        posture.microsoft_tenant_id,
        posture.subscription_id,
        posture.policy_profile_id,
    )


def _validate_probe_evaluation_age(
    probes: tuple[MicrosoftSoakProbeV1, ...],
    policy: MicrosoftSoakPolicyV1,
) -> None:
    for probe in probes:
        age = abs(
            int((probe.collected_at_utc - probe.posture.evaluated_at_utc).total_seconds())
        )
        if age > policy.maximum_evaluation_age_seconds:
            raise MicrosoftSoakQualificationError(
                "Microsoft soak posture evaluation is too far from probe collection time"
            )
