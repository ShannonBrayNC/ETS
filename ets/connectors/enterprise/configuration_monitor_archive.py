"""Fail-closed archive gate for configuration-monitor baseline replacement."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONFIGURATION_MONITOR_ARCHIVE_SCHEMA_VERSION: Literal[
    "ets.microsoft.configuration_monitor_archive.v1"
] = "ets.microsoft.configuration_monitor_archive.v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

BaselineDecision = Literal["repair", "approved_standard"]
GateVerdict = Literal["allowed", "blocked", "emergency_exception"]
GateReason = Literal[
    "archive_verified",
    "request_binding_mismatch",
    "baseline_unchanged",
    "archive_missing",
    "archive_binding_mismatch",
    "archive_too_old",
    "archive_bytes_missing",
    "archive_digest_mismatch",
    "emergency_approval_missing",
    "emergency_approval_binding_mismatch",
    "emergency_approval_expired",
    "emergency_approval_not_independent",
    "emergency_approval_recorded",
]


class StrictArchiveModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ServiceEvaluationLimitsV1(StrictArchiveModel):
    """Versioned service limits used to validate the monitor schedule."""

    documentation_url: str = Field(min_length=1, max_length=1024)
    documented_at_utc: datetime
    minimum_evaluation_interval_seconds: int = Field(ge=60)
    maximum_evaluations_per_day: int = Field(ge=1)
    result_retention_seconds: int = Field(ge=60)

    @field_validator("documentation_url")
    @classmethod
    def reject_blank_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("service-limit documentation URL cannot be blank")
        return value

    @field_validator("documented_at_utc")
    @classmethod
    def require_aware_documentation_time(cls, value: datetime) -> datetime:
        _require_aware(value, "documented_at_utc")
        return value


class MonitorEvaluationPolicyV1(StrictArchiveModel):
    evaluation_interval_seconds: int = Field(ge=60)
    scheduled_evaluations_per_day: int = Field(ge=1)
    archive_lookback_seconds: int = Field(ge=60)
    polling_interval_seconds: int = Field(ge=1)
    freshness_source: Literal["evaluation_completed_at"]
    polling_establishes_freshness: Literal[False]


class ConfigurationMonitorArchiveProfileV1(StrictArchiveModel):
    """Pre-deployment contract for one configuration-monitor archive gate."""

    schema_version: Literal["ets.microsoft.configuration_monitor_archive.v1"] = (
        CONFIGURATION_MONITOR_ARCHIVE_SCHEMA_VERSION
    )
    profile_id: str = Field(min_length=1, max_length=256)
    tenant_id: str = Field(min_length=1, max_length=256)
    monitor_id: str = Field(min_length=1, max_length=512)
    archive_max_age_seconds: int = Field(ge=1)
    request_authorities: tuple[str, ...] = Field(min_length=1)
    emergency_approval_authorities: tuple[str, ...] = Field(min_length=1)
    required_monitor_fields: tuple[str, ...] = Field(min_length=1)
    required_run_fields: tuple[str, ...] = Field(min_length=1)
    required_result_fields: tuple[str, ...] = Field(min_length=1)
    required_drift_fields: tuple[str, ...] = Field(min_length=1)
    service_limits: ServiceEvaluationLimitsV1
    evaluation_policy: MonitorEvaluationPolicyV1

    @model_validator(mode="after")
    def validate_profile(self) -> ConfigurationMonitorArchiveProfileV1:
        _require_unique_nonblank(self.request_authorities, "request authorities")
        _require_unique_nonblank(
            self.emergency_approval_authorities, "emergency approval authorities"
        )
        if set(self.request_authorities) & set(self.emergency_approval_authorities):
            raise ValueError("emergency approval authority must be separate from request authority")
        for field_set, label in (
            (self.required_monitor_fields, "monitor fields"),
            (self.required_run_fields, "run fields"),
            (self.required_result_fields, "result fields"),
            (self.required_drift_fields, "drift fields"),
        ):
            _require_unique_nonblank(field_set, label)

        policy = self.evaluation_policy
        limits = self.service_limits
        if policy.evaluation_interval_seconds < limits.minimum_evaluation_interval_seconds:
            raise ValueError("evaluation cadence is faster than the documented service limit")
        if policy.scheduled_evaluations_per_day > limits.maximum_evaluations_per_day:
            raise ValueError("scheduled evaluations exceed the documented daily quota")
        maximum_by_interval = 86_400 // policy.evaluation_interval_seconds
        if policy.scheduled_evaluations_per_day > maximum_by_interval:
            raise ValueError("scheduled evaluation count is inconsistent with the interval")
        if policy.archive_lookback_seconds > limits.result_retention_seconds:
            raise ValueError("archive lookback exceeds documented result retention")
        return self


class ArchivedObjectV1(StrictArchiveModel):
    logical_name: Literal[
        "monitor_definition",
        "prior_baseline",
        "parameters",
        "proposed_baseline",
        "decision_record",
    ]
    path: str = Field(min_length=1, max_length=1024)
    byte_length: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)

    @field_validator("path")
    @classmethod
    def reject_blank_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("archive path cannot be blank")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _validate_sha256(value, "archive object digest")


class ArchivePageV1(StrictArchiveModel):
    page_number: int = Field(ge=1)
    path: str = Field(min_length=1, max_length=1024)
    record_count: int = Field(ge=0)
    byte_length: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)
    next_cursor_sha256: str | None = Field(default=None, min_length=64, max_length=64)

    @field_validator("path")
    @classmethod
    def reject_blank_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("archive page path cannot be blank")
        return value

    @field_validator("sha256", "next_cursor_sha256")
    @classmethod
    def validate_digests(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_sha256(value, "archive page digest")


class PaginatedArchiveV1(StrictArchiveModel):
    collection: Literal["runs", "results", "drifts"]
    exported_fields: tuple[str, ...] = Field(min_length=1)
    total_record_count: int = Field(ge=0)
    expected_page_count: int = Field(ge=1)
    pages: tuple[ArchivePageV1, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def verify_complete_pagination(self) -> PaginatedArchiveV1:
        _require_unique_nonblank(self.exported_fields, f"{self.collection} fields")
        if len(self.pages) != self.expected_page_count:
            raise ValueError(f"{self.collection} archive is missing one or more pages")
        if [page.page_number for page in self.pages] != list(
            range(1, self.expected_page_count + 1)
        ):
            raise ValueError(f"{self.collection} archive pages must be complete and ordered")
        if sum(page.record_count for page in self.pages) != self.total_record_count:
            raise ValueError(f"{self.collection} page counts do not match the total")
        paths = [page.path for page in self.pages]
        if len(paths) != len(set(paths)):
            raise ValueError(f"{self.collection} archive page paths must be unique")
        if any(page.next_cursor_sha256 is None for page in self.pages[:-1]):
            raise ValueError(f"non-final {self.collection} pages require a continuation cursor")
        if self.pages[-1].next_cursor_sha256 is not None:
            raise ValueError(f"final {self.collection} page cannot retain a continuation cursor")
        return self


class ConfigurationMonitorArchiveV1(StrictArchiveModel):
    schema_version: Literal["ets.microsoft.configuration_monitor_archive.v1"] = (
        CONFIGURATION_MONITOR_ARCHIVE_SCHEMA_VERSION
    )
    profile_id: str = Field(min_length=1, max_length=256)
    tenant_id: str = Field(min_length=1, max_length=256)
    monitor_id: str = Field(min_length=1, max_length=512)
    prior_baseline_sha256: str = Field(min_length=64, max_length=64)
    proposed_baseline_sha256: str = Field(min_length=64, max_length=64)
    decision: BaselineDecision
    decision_record_sha256: str = Field(min_length=64, max_length=64)
    last_evaluation_completed_at_utc: datetime
    export_started_at_utc: datetime
    export_completed_at_utc: datetime
    monitor_fields: tuple[str, ...] = Field(min_length=1)
    objects: tuple[ArchivedObjectV1, ...] = Field(min_length=5, max_length=5)
    collections: tuple[PaginatedArchiveV1, ...] = Field(min_length=3, max_length=3)

    @field_validator(
        "prior_baseline_sha256", "proposed_baseline_sha256", "decision_record_sha256"
    )
    @classmethod
    def validate_digests(cls, value: str) -> str:
        return _validate_sha256(value, "baseline archive digest")

    @field_validator(
        "last_evaluation_completed_at_utc",
        "export_started_at_utc",
        "export_completed_at_utc",
    )
    @classmethod
    def require_aware_times(cls, value: datetime) -> datetime:
        _require_aware(value, "archive timestamp")
        return value

    @model_validator(mode="after")
    def verify_archive_shape(self) -> ConfigurationMonitorArchiveV1:
        if self.prior_baseline_sha256 == self.proposed_baseline_sha256:
            raise ValueError("prior and proposed baseline digests must differ")
        if not (
            self.last_evaluation_completed_at_utc
            <= self.export_started_at_utc
            <= self.export_completed_at_utc
        ):
            raise ValueError("archive timestamps must follow the retained evaluation")
        _require_unique_nonblank(self.monitor_fields, "monitor fields")
        logical_names = [item.logical_name for item in self.objects]
        required_objects = {
            "monitor_definition",
            "prior_baseline",
            "parameters",
            "proposed_baseline",
            "decision_record",
        }
        if set(logical_names) != required_objects:
            raise ValueError(
                "archive requires definition, prior/proposed baselines, parameters, and decision"
            )
        object_digests = {item.logical_name: item.sha256 for item in self.objects}
        if object_digests["prior_baseline"] != self.prior_baseline_sha256:
            raise ValueError("prior baseline bytes must bind to the prior baseline digest")
        if object_digests["proposed_baseline"] != self.proposed_baseline_sha256:
            raise ValueError("proposed baseline bytes must bind to the proposed baseline digest")
        if object_digests["decision_record"] != self.decision_record_sha256:
            raise ValueError("decision record bytes must bind to the decision digest")
        paths = [item.path for item in self.objects]
        paths.extend(page.path for group in self.collections for page in group.pages)
        if len(paths) != len(set(paths)):
            raise ValueError("every archived object and page requires a unique path")
        collection_names = [item.collection for item in self.collections]
        if set(collection_names) != {"runs", "results", "drifts"}:
            raise ValueError("archive requires runs, results, and drifts collections")
        return self


class BaselineReplacementRequestV1(StrictArchiveModel):
    request_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    tenant_id: str = Field(min_length=1, max_length=256)
    monitor_id: str = Field(min_length=1, max_length=512)
    requestor_identity: str = Field(min_length=1, max_length=512)
    prior_baseline_sha256: str = Field(min_length=64, max_length=64)
    proposed_baseline_sha256: str = Field(min_length=64, max_length=64)
    decision: BaselineDecision
    decision_record_sha256: str = Field(min_length=64, max_length=64)
    requested_at_utc: datetime
    emergency: bool = False

    @field_validator(
        "prior_baseline_sha256", "proposed_baseline_sha256", "decision_record_sha256"
    )
    @classmethod
    def validate_digests(cls, value: str) -> str:
        return _validate_sha256(value, "baseline replacement digest")

    @field_validator("requested_at_utc")
    @classmethod
    def require_aware_request_time(cls, value: datetime) -> datetime:
        _require_aware(value, "requested_at_utc")
        return value


class EmergencyArchiveApprovalV1(StrictArchiveModel):
    approval_id: str = Field(min_length=1, max_length=256)
    request_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    tenant_id: str = Field(min_length=1, max_length=256)
    monitor_id: str = Field(min_length=1, max_length=512)
    approver_identity: str = Field(min_length=1, max_length=512)
    prior_baseline_sha256: str = Field(min_length=64, max_length=64)
    proposed_baseline_sha256: str = Field(min_length=64, max_length=64)
    decision: BaselineDecision
    decision_record_sha256: str = Field(min_length=64, max_length=64)
    archive_exception: Literal[True]
    reason: str = Field(min_length=1, max_length=2048)
    approved_at_utc: datetime
    expires_at_utc: datetime

    @field_validator(
        "prior_baseline_sha256", "proposed_baseline_sha256", "decision_record_sha256"
    )
    @classmethod
    def validate_digests(cls, value: str) -> str:
        return _validate_sha256(value, "emergency approval digest")

    @field_validator("approved_at_utc", "expires_at_utc")
    @classmethod
    def require_aware_approval_times(cls, value: datetime) -> datetime:
        _require_aware(value, "emergency approval timestamp")
        return value

    @field_validator("reason")
    @classmethod
    def reject_blank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("emergency approval reason cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> EmergencyArchiveApprovalV1:
        if self.expires_at_utc <= self.approved_at_utc:
            raise ValueError("emergency approval expiry must follow approval")
        return self


class BaselineReplacementAssessmentV1(StrictArchiveModel):
    request_id: str
    verdict: GateVerdict
    reason: GateReason
    evaluated_at_utc: datetime
    archive_completed_at_utc: datetime | None = None
    emergency_approval_id: str | None = None


def assess_baseline_replacement(
    profile: ConfigurationMonitorArchiveProfileV1,
    request: BaselineReplacementRequestV1,
    archive: ConfigurationMonitorArchiveV1 | None,
    *,
    archive_bytes: Mapping[str, bytes],
    evaluated_at_utc: datetime,
    emergency_approval: EmergencyArchiveApprovalV1 | None = None,
) -> BaselineReplacementAssessmentV1:
    """Permit replacement only after exact archive bytes verify, or a bounded exception."""

    _require_aware(evaluated_at_utc, "evaluated_at_utc")
    if request.requested_at_utc > evaluated_at_utc:
        raise ValueError("replacement request cannot be in the future")
    if (
        request.profile_id != profile.profile_id
        or request.tenant_id != profile.tenant_id
        or request.monitor_id != profile.monitor_id
        or request.requestor_identity not in profile.request_authorities
    ):
        return _assessment(request, "blocked", "request_binding_mismatch", evaluated_at_utc)
    if request.prior_baseline_sha256 == request.proposed_baseline_sha256:
        return _assessment(request, "blocked", "baseline_unchanged", evaluated_at_utc)

    if archive is not None:
        binding_matches = (
            archive.profile_id == request.profile_id
            and archive.tenant_id == request.tenant_id
            and archive.monitor_id == request.monitor_id
            and archive.prior_baseline_sha256 == request.prior_baseline_sha256
            and archive.proposed_baseline_sha256 == request.proposed_baseline_sha256
            and archive.decision == request.decision
            and archive.decision_record_sha256 == request.decision_record_sha256
            and archive.export_completed_at_utc <= request.requested_at_utc
            and archive.monitor_fields == profile.required_monitor_fields
            and _collection_fields(archive, "runs") == profile.required_run_fields
            and _collection_fields(archive, "results") == profile.required_result_fields
            and _collection_fields(archive, "drifts") == profile.required_drift_fields
        )
        if not binding_matches:
            return _assessment(
                request,
                "blocked",
                "archive_binding_mismatch",
                evaluated_at_utc,
                archive=archive,
            )
        age = int((request.requested_at_utc - archive.export_completed_at_utc).total_seconds())
        evaluation_age = int(
            (
                request.requested_at_utc - archive.last_evaluation_completed_at_utc
            ).total_seconds()
        )
        if (
            age > profile.archive_max_age_seconds
            or evaluation_age > profile.evaluation_policy.archive_lookback_seconds
        ):
            return _assessment(
                request,
                "blocked",
                "archive_too_old",
                evaluated_at_utc,
                archive=archive,
            )
        for item in _archive_files(archive):
            payload = archive_bytes.get(item.path)
            if payload is None:
                return _assessment(
                    request,
                    "blocked",
                    "archive_bytes_missing",
                    evaluated_at_utc,
                    archive=archive,
                )
            digest_matches = hashlib.sha256(payload).hexdigest() == item.sha256
            if len(payload) != item.byte_length or not digest_matches:
                return _assessment(
                    request,
                    "blocked",
                    "archive_digest_mismatch",
                    evaluated_at_utc,
                    archive=archive,
                )
        return _assessment(
            request, "allowed", "archive_verified", evaluated_at_utc, archive=archive
        )

    if not request.emergency:
        return _assessment(request, "blocked", "archive_missing", evaluated_at_utc)
    if emergency_approval is None:
        return _assessment(
            request, "blocked", "emergency_approval_missing", evaluated_at_utc
        )
    if emergency_approval.approver_identity == request.requestor_identity:
        return _assessment(
            request,
            "blocked",
            "emergency_approval_not_independent",
            evaluated_at_utc,
            emergency_approval=emergency_approval,
        )
    if (
        emergency_approval.approver_identity not in profile.emergency_approval_authorities
        or emergency_approval.request_id != request.request_id
        or emergency_approval.profile_id != request.profile_id
        or emergency_approval.tenant_id != request.tenant_id
        or emergency_approval.monitor_id != request.monitor_id
        or emergency_approval.prior_baseline_sha256 != request.prior_baseline_sha256
        or emergency_approval.proposed_baseline_sha256 != request.proposed_baseline_sha256
        or emergency_approval.decision != request.decision
        or emergency_approval.decision_record_sha256 != request.decision_record_sha256
        or emergency_approval.approved_at_utc > request.requested_at_utc
    ):
        return _assessment(
            request,
            "blocked",
            "emergency_approval_binding_mismatch",
            evaluated_at_utc,
            emergency_approval=emergency_approval,
        )
    if evaluated_at_utc > emergency_approval.expires_at_utc:
        return _assessment(
            request,
            "blocked",
            "emergency_approval_expired",
            evaluated_at_utc,
            emergency_approval=emergency_approval,
        )
    return _assessment(
        request,
        "emergency_exception",
        "emergency_approval_recorded",
        evaluated_at_utc,
        emergency_approval=emergency_approval,
    )


def _collection_fields(
    archive: ConfigurationMonitorArchiveV1, collection: str
) -> tuple[str, ...]:
    return next(
        item.exported_fields for item in archive.collections if item.collection == collection
    )


def _archive_files(
    archive: ConfigurationMonitorArchiveV1,
) -> tuple[ArchivedObjectV1 | ArchivePageV1, ...]:
    return (*archive.objects, *(page for group in archive.collections for page in group.pages))


def _assessment(
    request: BaselineReplacementRequestV1,
    verdict: GateVerdict,
    reason: GateReason,
    evaluated_at_utc: datetime,
    *,
    archive: ConfigurationMonitorArchiveV1 | None = None,
    emergency_approval: EmergencyArchiveApprovalV1 | None = None,
) -> BaselineReplacementAssessmentV1:
    return BaselineReplacementAssessmentV1(
        request_id=request.request_id,
        verdict=verdict,
        reason=reason,
        evaluated_at_utc=evaluated_at_utc,
        archive_completed_at_utc=(archive.export_completed_at_utc if archive else None),
        emergency_approval_id=(emergency_approval.approval_id if emergency_approval else None),
    )


def _validate_sha256(value: str, label: str) -> str:
    normalized = value.lower()
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{label} must be 64 lowercase hexadecimal characters")
    return normalized


def _require_unique_nonblank(values: tuple[str, ...], label: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{label} cannot contain blank values")
    if len(values) != len(set(values)):
        raise ValueError(f"{label} cannot contain duplicates")


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


__all__ = [
    "CONFIGURATION_MONITOR_ARCHIVE_SCHEMA_VERSION",
    "ArchivePageV1",
    "ArchivedObjectV1",
    "BaselineReplacementAssessmentV1",
    "BaselineReplacementRequestV1",
    "ConfigurationMonitorArchiveProfileV1",
    "ConfigurationMonitorArchiveV1",
    "EmergencyArchiveApprovalV1",
    "MonitorEvaluationPolicyV1",
    "PaginatedArchiveV1",
    "ServiceEvaluationLimitsV1",
    "assess_baseline_replacement",
]
