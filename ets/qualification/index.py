"""Qualification publication index and roadmap-governance contract for HQP-5."""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ets.qualification.hardware import HardwareQualificationReport
from ets.qualification.verifier import (
    HardwareQualificationVerification,
    VerificationOutcome,
)

_SHA256_RE = r"^[0-9a-f]{64}$"
_COMMIT_RE = r"^[0-9a-f]{40,64}$"
_CLAIM_BOUNDARY: Literal[
    "bounded_qualification_publication_not_truth_completeness_compliance_safety_or_ga_proof"
] = (
    "bounded_qualification_publication_not_truth_completeness_compliance_safety_or_ga_proof"
)


class StrictIndexModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class PublicationState(StrEnum):
    ACTIVE = "active"
    HISTORICAL = "historical"
    WITHDRAWN = "withdrawn"


class IndexedDisposition(StrEnum):
    QUALIFIED = "qualified"
    QUALIFIED_WITH_DEVIATION = "qualified_with_deviation"
    FAILED = "failed"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class PendingQualificationState(StrEnum):
    NOT_TESTED = "not_tested"
    QUALIFICATION_IN_PROGRESS = "qualification_in_progress"
    LAB_TESTED = "lab_tested"


class QualificationProfileReference(StrictIndexModel):
    profile_id: str = Field(min_length=3, max_length=256)
    profile_version: str = Field(min_length=1, max_length=128)
    profile_digest_sha256: str = Field(pattern=_SHA256_RE)
    profile_path: str = Field(min_length=1, max_length=1024)


class IndexedDeviceIdentity(StrictIndexModel):
    device_id: str = Field(min_length=1, max_length=256)
    manufacturer: str = Field(min_length=1, max_length=256)
    model: str = Field(min_length=1, max_length=256)
    hardware_revision: str = Field(min_length=1, max_length=256)
    serial_or_asset_id: str | None = Field(default=None, max_length=256)
    identity_digest_sha256: str = Field(pattern=_SHA256_RE)


class IndexedBuildIdentity(StrictIndexModel):
    repository: str = Field(min_length=1, max_length=512)
    commit_sha: str = Field(pattern=_COMMIT_RE)
    artifact_digest_sha256: str = Field(pattern=_SHA256_RE)
    configuration_digest_sha256: str = Field(pattern=_SHA256_RE)
    sbom_artifact_id: str | None = Field(default=None, max_length=256)


class RetainedPackageReference(StrictIndexModel):
    run_id: str = Field(min_length=1, max_length=256)
    run_digest_sha256: str = Field(pattern=_SHA256_RE)
    report_id: str = Field(min_length=1, max_length=256)
    report_digest_sha256: str = Field(pattern=_SHA256_RE)
    package_digest_sha256: str = Field(pattern=_SHA256_RE)
    retention_locator: str = Field(min_length=1, max_length=2048)
    evidence_object_ids: tuple[str, ...] = Field(min_length=1)
    artifact_ids: tuple[str, ...] = Field(min_length=1)
    deviation_ids: tuple[str, ...] = ()


class IndependentVerificationReference(StrictIndexModel):
    verification_id: str = Field(min_length=1, max_length=256)
    verification_digest_sha256: str = Field(pattern=_SHA256_RE)
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_build_digest_sha256: str = Field(pattern=_SHA256_RE)
    outcome: Literal["valid", "invalid", "indeterminate"]
    eligible_for_claimed_disposition: bool
    independent_execution_context: Literal[True]


class ValidityWindow(StrictIndexModel):
    valid_from: datetime
    valid_until: datetime | None = None
    requalification_triggers: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_ordering(self) -> ValidityWindow:
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be later than valid_from")
        return self


class SupersessionReference(StrictIndexModel):
    superseded_by_claim_id: str = Field(min_length=1, max_length=256)
    effective_at: datetime
    reason: str = Field(min_length=1, max_length=4096)


class RoadmapBinding(StrictIndexModel):
    roadmap_path: str = Field(min_length=1, max_length=1024)
    product: str = Field(min_length=1, max_length=256)
    capability_maturity: str = Field(min_length=1, max_length=256)
    qualification_language: str = Field(min_length=1, max_length=512)
    capability_maturity_is_independent: Literal[True]


class QualificationClaim(StrictIndexModel):
    claim_id: str = Field(min_length=3, max_length=256)
    publication_state: PublicationState
    disposition: IndexedDisposition
    claim_text: str = Field(min_length=1, max_length=4096)
    profile: QualificationProfileReference
    device: IndexedDeviceIdentity
    build: IndexedBuildIdentity
    package: RetainedPackageReference
    verification: IndependentVerificationReference
    limitations: tuple[str, ...] = Field(min_length=1)
    validity: ValidityWindow
    supersession: SupersessionReference | None = None
    roadmap: RoadmapBinding
    source_issue_refs: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_publication_semantics(self) -> QualificationClaim:
        if self.disposition in {
            IndexedDisposition.QUALIFIED,
            IndexedDisposition.QUALIFIED_WITH_DEVIATION,
        }:
            if self.verification.outcome != VerificationOutcome.VALID.value:
                raise ValueError("positive qualification claim requires valid HQP-2 verification")
            if not self.verification.eligible_for_claimed_disposition:
                raise ValueError("positive qualification claim must be verifier-eligible")
            if self.publication_state is PublicationState.WITHDRAWN:
                raise ValueError("withdrawn result cannot remain a positive active claim")

        if self.disposition is IndexedDisposition.SUPERSEDED:
            if self.supersession is None:
                raise ValueError("superseded disposition requires supersession metadata")
            if self.publication_state is PublicationState.ACTIVE:
                raise ValueError("superseded result cannot remain active")
        elif self.supersession is not None:
            raise ValueError("supersession metadata is only valid for superseded disposition")

        if self.disposition is IndexedDisposition.EXPIRED:
            if self.validity.valid_until is None:
                raise ValueError("expired disposition requires a validity end")
            if self.publication_state is PublicationState.ACTIVE:
                raise ValueError("expired result cannot remain active")

        if (
            self.disposition is IndexedDisposition.QUALIFIED_WITH_DEVIATION
            and not self.package.deviation_ids
        ):
            raise ValueError("qualified_with_deviation requires retained deviation identifiers")
        return self


class PendingQualificationTarget(StrictIndexModel):
    target_id: str = Field(min_length=3, max_length=256)
    product: str = Field(min_length=1, max_length=256)
    target_class_id: str = Field(min_length=1, max_length=128)
    profile_id: str = Field(min_length=3, max_length=256)
    profile_version: str = Field(min_length=1, max_length=128)
    profile_path: str = Field(min_length=1, max_length=1024)
    qualification_state: PendingQualificationState
    physical_exit_gate: str = Field(min_length=1, max_length=4096)
    tracking_issue: str = Field(min_length=1, max_length=256)
    roadmap_status: str = Field(min_length=1, max_length=256)
    non_claims: tuple[str, ...] = Field(min_length=1)


class QualificationIndex(StrictIndexModel):
    schema_version: Literal["ets.hardware-qualification-index.v1"]
    index_id: str = Field(min_length=3, max_length=256)
    status_date: date
    public_index: Literal[True]
    published_claims: tuple[QualificationClaim, ...] = ()
    pending_targets: tuple[PendingQualificationTarget, ...] = ()
    claim_boundary: Literal[
        "bounded_qualification_publication_not_truth_completeness_compliance_safety_or_ga_proof"
    ] = _CLAIM_BOUNDARY

    @model_validator(mode="after")
    def enforce_unique_records(self) -> QualificationIndex:
        claim_ids = tuple(item.claim_id for item in self.published_claims)
        target_ids = tuple(item.target_id for item in self.pending_targets)
        _require_unique(claim_ids, "qualification claim identifiers")
        _require_unique(target_ids, "pending qualification target identifiers")
        return self


def load_qualification_index(raw: bytes) -> QualificationIndex:
    return QualificationIndex.model_validate_json(raw)


def validate_claim_against_evidence(
    claim: QualificationClaim,
    report: HardwareQualificationReport,
    verification: HardwareQualificationVerification,
) -> None:
    """Cross-check one published index record against HQP-1/HQP-2 evidence."""

    if report.profile.profile_id != claim.profile.profile_id:
        raise ValueError("claim profile_id does not match HQP-1 report")
    if report.profile.profile_version != claim.profile.profile_version:
        raise ValueError("claim profile_version does not match HQP-1 report")
    if report.profile.profile_digest_sha256 != claim.profile.profile_digest_sha256:
        raise ValueError("claim profile digest does not match HQP-1 report")
    if report.device_id != claim.device.device_id:
        raise ValueError("claim device_id does not match HQP-1 report")
    if report.hardware_revision != claim.device.hardware_revision:
        raise ValueError("claim hardware revision does not match HQP-1 report")
    if report.commit_sha != claim.build.commit_sha:
        raise ValueError("claim build commit does not match HQP-1 report")
    if report.run_id != claim.package.run_id:
        raise ValueError("claim run_id does not match HQP-1 report")
    if report.run_digest_sha256 != claim.package.run_digest_sha256:
        raise ValueError("claim run digest does not match HQP-1 report")
    if report.report_id != claim.package.report_id:
        raise ValueError("claim report_id does not match HQP-1 report")
    if report.report_digest_sha256 != claim.package.report_digest_sha256:
        raise ValueError("claim report digest does not match HQP-1 report")
    if report.final_disposition.value != claim.disposition.value:
        raise ValueError("claim disposition does not match HQP-1 report")

    if verification.verification_id != claim.verification.verification_id:
        raise ValueError("claim verification_id does not match HQP-2 result")
    if verification.verification_digest_sha256 != claim.verification.verification_digest_sha256:
        raise ValueError("claim verification digest does not match HQP-2 result")
    if verification.verifier_id != claim.verification.verifier_id:
        raise ValueError("claim verifier_id does not match HQP-2 result")
    if verification.verifier_build_digest_sha256 != claim.verification.verifier_build_digest_sha256:
        raise ValueError("claim verifier build digest does not match HQP-2 result")
    if verification.outcome.value != claim.verification.outcome:
        raise ValueError("claim verification outcome does not match HQP-2 result")
    if (
        verification.eligible_for_claimed_disposition
        != claim.verification.eligible_for_claimed_disposition
    ):
        raise ValueError("claim verifier eligibility does not match HQP-2 result")


def render_qualification_index(index: QualificationIndex) -> str:
    payload = {
        "index_id": index.index_id,
        "status_date": index.status_date.isoformat(),
        "published_claim_count": len(index.published_claims),
        "pending_target_count": len(index.pending_targets),
        "published_claims": [
            {
                "claim_id": item.claim_id,
                "product": item.roadmap.product,
                "disposition": item.disposition.value,
                "publication_state": item.publication_state.value,
                "device_id": item.device.device_id,
                "profile_id": item.profile.profile_id,
                "profile_version": item.profile.profile_version,
            }
            for item in index.published_claims
        ],
        "pending_targets": [
            {
                "target_id": item.target_id,
                "product": item.product,
                "qualification_state": item.qualification_state.value,
                "profile_id": item.profile_id,
                "profile_version": item.profile_version,
            }
            for item in index.pending_targets
        ],
        "claim_boundary": index.claim_boundary,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _require_unique(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


__all__ = [
    "IndexedBuildIdentity",
    "IndexedDeviceIdentity",
    "IndexedDisposition",
    "IndependentVerificationReference",
    "PendingQualificationState",
    "PendingQualificationTarget",
    "PublicationState",
    "QualificationClaim",
    "QualificationIndex",
    "QualificationProfileReference",
    "RetainedPackageReference",
    "RoadmapBinding",
    "SupersessionReference",
    "ValidityWindow",
    "load_qualification_index",
    "render_qualification_index",
    "validate_claim_against_evidence",
]
