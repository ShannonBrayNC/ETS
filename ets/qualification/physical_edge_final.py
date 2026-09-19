"""Wave 1 Edge Compact R0 final HQP package and publication gate.

This module closes the implementation boundary after R0.15. It assembles the selected
physical phase-evidence chain, retains the R0.16 source-to-proof operator trace, binds
the resulting HQP-1 package to an off-DUT HQP-2 result, and produces the exact HQP-5
qualification-index claim that is eligible for publication.

Nothing in this module executes physical stimuli, generates phase evidence, or upgrades
the deliberately weak Edge Compact R0 trust posture.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.qualification.hardware import QualificationDisposition
from ets.qualification.physical_edge import (
    EdgeCompactR0BenchManifest,
    readiness_issues,
)
from ets.qualification.profile import FinalQualificationState
from ets.qualification.verifier import (
    HardwareQualificationVerification,
    VerificationOutcome,
)

_SHA256_RE = r"^[0-9a-f]{64}$"
_R0_FINAL_CLAIM_BOUNDARY: Literal[
    "edge_compact_r0_final_package_requires_physical_phase_evidence_hqp2_and_hqp5"
] = "edge_compact_r0_final_package_requires_physical_phase_evidence_hqp2_and_hqp5"
_R0_LIMITATIONS = (
    "identity_profile=software_volume",
    "hardware_attested=false",
    "secure_boot_verified=false",
    "hardware_key_protection=false",
    "Qualification applies only to the exact retained DUT/build/profile/evidence package.",
)


class StrictFinalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class R0PhaseId(StrEnum):
    R0_1 = "r0_1"
    R0_2 = "r0_2"
    R0_3 = "r0_3"
    R0_4 = "r0_4"
    R0_5 = "r0_5"
    R0_6 = "r0_6"
    R0_7 = "r0_7"
    R0_8 = "r0_8"
    R0_9 = "r0_9"
    R0_10 = "r0_10"
    R0_11 = "r0_11"
    R0_12 = "r0_12"
    R0_13 = "r0_13"
    R0_14 = "r0_14"
    R0_15 = "r0_15"


_REQUIRED_PHASE_ORDER: tuple[R0PhaseId, ...] = tuple(R0PhaseId)


class BuildTransitionKind(StrEnum):
    UNCHANGED = "unchanged"
    VALID_UPGRADE = "valid_upgrade"
    ROLLBACK_RECOVERY = "rollback_recovery"
    RECOVERY_REBUILD = "recovery_rebuild"


class HistoricalRunState(StrEnum):
    FAILED = "failed"
    INVALID = "invalid"
    SUPERSEDED = "superseded"


class R0PhaseEvidenceSelection(StrictFinalModel):
    schema_version: Literal["ets.edge-compact-r0-phase-selection.v1"] = (
        "ets.edge-compact-r0-phase-selection.v1"
    )
    phase_id: R0PhaseId
    evaluation_id: str = Field(min_length=1, max_length=256)
    evaluation_schema_version: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    evaluation_sha256: str = Field(pattern=_SHA256_RE)
    predecessor_evaluation_id: str | None = Field(default=None, max_length=256)
    phase_passed: Literal[True] = True
    disposition: Literal["phase_evidence_only"] = "phase_evidence_only"
    claim_boundary: str = Field(min_length=1, max_length=512)
    source_build_sha: str = Field(min_length=7, max_length=128)
    resulting_build_sha: str = Field(min_length=7, max_length=128)
    source_configuration_digest: str = Field(pattern=_SHA256_RE)
    resulting_configuration_digest: str = Field(pattern=_SHA256_RE)
    build_transition: BuildTransitionKind = BuildTransitionKind.UNCHANGED
    transition_binding_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    identity_before: str = Field(min_length=1, max_length=256)
    identity_after: str = Field(min_length=1, max_length=256)
    identity_transition_binding_sha256: str | None = Field(
        default=None,
        pattern=_SHA256_RE,
    )
    local_checkpoint_before: int | None = Field(default=None, ge=0)
    local_checkpoint_after: int | None = Field(default=None, ge=0)
    upstream_checkpoint_before: int | None = Field(default=None, ge=0)
    upstream_checkpoint_after: int | None = Field(default=None, ge=0)
    prior_history_preserved: Literal[True] = True
    logical_loss_or_duplication_observed: Literal[False] = False
    artifact_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: tuple[str, ...] = ()
    verifier_receipt_sha256: tuple[str, ...] = ()
    external_observation_required: bool
    independent_verification_required: bool
    issues: tuple[str, ...] = ()

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "phase selection evaluated_at")

    @model_validator(mode="after")
    def validate_selection(self) -> R0PhaseEvidenceSelection:
        if self.issues:
            raise ValueError("selected passing phase cannot retain blocking issues")
        if self.external_observation_required and not self.observer_receipt_sha256:
            raise ValueError("phase requires at least one independent observer receipt")
        if self.independent_verification_required and not self.verifier_receipt_sha256:
            raise ValueError("phase requires at least one independent verifier receipt")
        if self.build_transition is BuildTransitionKind.UNCHANGED:
            if self.source_build_sha != self.resulting_build_sha:
                raise ValueError("unchanged phase cannot change build")
            if self.source_configuration_digest != self.resulting_configuration_digest:
                raise ValueError("unchanged phase cannot change configuration")
            if self.transition_binding_sha256 is not None:
                raise ValueError("unchanged phase cannot carry build-transition binding")
        elif self.transition_binding_sha256 is None:
            raise ValueError("build transition requires retained transition binding")
        if self.identity_before != self.identity_after:
            if self.identity_transition_binding_sha256 is None:
                raise ValueError("identity change requires explicit transition binding")
        elif self.identity_transition_binding_sha256 is not None:
            raise ValueError("unchanged identity cannot carry identity-transition binding")
        if (
            self.local_checkpoint_before is not None
            and self.local_checkpoint_after is not None
            and self.local_checkpoint_after < self.local_checkpoint_before
        ):
            raise ValueError("local checkpoint cannot regress inside a selected phase")
        if (
            self.upstream_checkpoint_before is not None
            and self.upstream_checkpoint_after is not None
            and self.upstream_checkpoint_after < self.upstream_checkpoint_before
        ):
            raise ValueError("upstream checkpoint cannot regress inside a selected phase")
        return self


class R0OperatorSourceToProofTrace(StrictFinalModel):
    schema_version: Literal["ets.edge-compact-r0-operator-trace.v1"] = (
        "ets.edge-compact-r0-operator-trace.v1"
    )
    trace_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    source_observation_id: str = Field(min_length=1, max_length=256)
    source_artifact_sha256: str = Field(pattern=_SHA256_RE)
    ingress_receipt_sha256: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    evidence_object_id: str = Field(min_length=1, max_length=512)
    evidence_object_sha256: str = Field(pattern=_SHA256_RE)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    export_bundle_sha256: str = Field(pattern=_SHA256_RE)
    independent_verification_sha256: str = Field(pattern=_SHA256_RE)
    reviewer_id: str = Field(min_length=1, max_length=256)
    reviewed_at: datetime
    independently_reviewed: Literal[True] = True
    hidden_manual_reconstruction_required: Literal[False] = False
    trace_commitment_sha256: str = Field(pattern=_SHA256_RE)

    @field_validator("reviewed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "operator trace reviewed_at")

    @model_validator(mode="after")
    def verify_trace_commitment(self) -> R0OperatorSourceToProofTrace:
        expected = canonical_sha256(
            self.model_dump(mode="json", exclude={"trace_commitment_sha256"})
        )
        if self.trace_commitment_sha256 != expected:
            raise ValueError("operator trace commitment does not match canonical trace")
        return self


class R0HistoricalRunReference(StrictFinalModel):
    schema_version: Literal["ets.edge-compact-r0-historical-run.v1"] = (
        "ets.edge-compact-r0-historical-run.v1"
    )
    run_id: str = Field(min_length=1, max_length=256)
    state: HistoricalRunState
    package_sha256: str = Field(pattern=_SHA256_RE)
    reason: str = Field(min_length=1, max_length=2048)
    superseded_by_run_id: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def validate_supersession(self) -> R0HistoricalRunReference:
        if self.state is HistoricalRunState.SUPERSEDED:
            if self.superseded_by_run_id is None:
                raise ValueError("superseded historical run requires successor run ID")
        elif self.superseded_by_run_id is not None:
            raise ValueError("only superseded historical runs may name successor")
        return self


class R0HqpPackageBinding(StrictFinalModel):
    schema_version: Literal["ets.edge-compact-r0-hqp-binding.v1"] = (
        "ets.edge-compact-r0-hqp-binding.v1"
    )
    profile_id: str = Field(min_length=1, max_length=256)
    profile_version: str = Field(min_length=1, max_length=128)
    profile_digest_sha256: str = Field(pattern=_SHA256_RE)
    run_id: str = Field(min_length=1, max_length=256)
    run_digest_sha256: str = Field(pattern=_SHA256_RE)
    report_id: str = Field(min_length=1, max_length=256)
    report_digest_sha256: str = Field(pattern=_SHA256_RE)
    run_package_locator: str = Field(min_length=1, max_length=2048)
    qualification_report_locator: str = Field(min_length=1, max_length=2048)
    artifact_manifest_digest_sha256: str = Field(pattern=_SHA256_RE)
    evidence_object_ids: tuple[str, ...] = Field(min_length=1)
    hqp_input_package_sha256: str = Field(pattern=_SHA256_RE)

    @model_validator(mode="after")
    def require_unique_evidence(self) -> R0HqpPackageBinding:
        if len(self.evidence_object_ids) != len(set(self.evidence_object_ids)):
            raise ValueError("HQP Evidence Object IDs must be unique")
        return self


class Wave1R0PackageManifest(StrictFinalModel):
    schema_version: Literal["ets.edge-compact-r0-final-package.v1"] = (
        "ets.edge-compact-r0-final-package.v1"
    )
    package_id: str = Field(min_length=1, max_length=256)
    created_at: datetime
    qualification_class: Literal["EDGE_COMPACT_R0"] = "EDGE_COMPACT_R0"
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    manufacturer: str = Field(min_length=1, max_length=256)
    model: str = Field(min_length=1, max_length=256)
    hardware_revision: str = Field(min_length=1, max_length=256)
    firmware: dict[str, str]
    runtime_id: str = Field(min_length=1, max_length=512)
    final_build_sha: str = Field(min_length=7, max_length=128)
    final_artifact_digest: str = Field(pattern=_SHA256_RE)
    final_configuration_digest: str = Field(pattern=_SHA256_RE)
    identity_profile: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    secure_boot_verified: Literal[False] = False
    hardware_key_protection: Literal[False] = False
    phases: tuple[R0PhaseEvidenceSelection, ...] = Field(min_length=15, max_length=15)
    operator_trace: R0OperatorSourceToProofTrace
    historical_runs: tuple[R0HistoricalRunReference, ...] = ()
    hqp: R0HqpPackageBinding
    limitations: tuple[str, ...] = _R0_LIMITATIONS
    package_root_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "edge_compact_r0_final_package_requires_physical_phase_evidence_hqp2_and_hqp5"
    ] = _R0_FINAL_CLAIM_BOUNDARY

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "final package created_at")

    @model_validator(mode="after")
    def validate_package(self) -> Wave1R0PackageManifest:
        if tuple(item.phase_id for item in self.phases) != _REQUIRED_PHASE_ORDER:
            raise ValueError("final package must contain R0.1 through R0.15 in order")
        if self.operator_trace.manifest_id != self.manifest_id:
            raise ValueError("operator trace manifest binding mismatch")
        if self.operator_trace.asset_id != self.asset_id:
            raise ValueError("operator trace asset binding mismatch")

        previous: R0PhaseEvidenceSelection | None = None
        for index, phase in enumerate(self.phases):
            if phase.manifest_id != self.manifest_id or phase.asset_id != self.asset_id:
                raise ValueError(f"{phase.phase_id.value} is bound to another DUT")
            if index == 0:
                if phase.predecessor_evaluation_id is not None:
                    raise ValueError("R0.1 cannot declare predecessor phase")
            else:
                assert previous is not None
                if phase.predecessor_evaluation_id != previous.evaluation_id:
                    raise ValueError(
                        f"{phase.phase_id.value} predecessor evaluation binding mismatch"
                    )
                if phase.source_build_sha != previous.resulting_build_sha:
                    raise ValueError(
                        f"{phase.phase_id.value} source build breaks cross-phase continuity"
                    )
                if (
                    phase.source_configuration_digest
                    != previous.resulting_configuration_digest
                ):
                    raise ValueError(
                        f"{phase.phase_id.value} source configuration breaks continuity"
                    )
                if phase.identity_before != previous.identity_after:
                    raise ValueError(
                        f"{phase.phase_id.value} identity-before breaks continuity"
                    )
                if (
                    previous.local_checkpoint_after is not None
                    and phase.local_checkpoint_before is not None
                    and phase.local_checkpoint_before < previous.local_checkpoint_after
                ):
                    raise ValueError(
                        f"{phase.phase_id.value} local checkpoint regressed between phases"
                    )
                if (
                    previous.upstream_checkpoint_after is not None
                    and phase.upstream_checkpoint_before is not None
                    and phase.upstream_checkpoint_before
                    < previous.upstream_checkpoint_after
                ):
                    raise ValueError(
                        f"{phase.phase_id.value} upstream checkpoint regressed between phases"
                    )
            previous = phase

        final_phase = self.phases[-1]
        if final_phase.resulting_build_sha != self.final_build_sha:
            raise ValueError("final build does not match R0.15 resulting build")
        if final_phase.resulting_configuration_digest != self.final_configuration_digest:
            raise ValueError("final configuration does not match R0.15")
        if self.limitations != _R0_LIMITATIONS:
            raise ValueError("R0 final limitations must remain canonical")

        expected_root = canonical_sha256(
            self.model_dump(mode="json", exclude={"package_root_sha256"})
        )
        if self.package_root_sha256 != expected_root:
            raise ValueError("package_root_sha256 does not match canonical package")
        return self


class QualificationIndexProfileBinding(StrictFinalModel):
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)


class QualificationIndexDutBinding(StrictFinalModel):
    manufacturer: str = Field(min_length=1)
    model: str = Field(min_length=1)
    hardware_revision: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    firmware: dict[str, str]
    signer_profile: str = Field(min_length=1)


class QualificationIndexBuildBinding(StrictFinalModel):
    source_revision: str = Field(min_length=1)
    artifact_digest: str = Field(min_length=1)
    configuration_digest: str = Field(min_length=1)


class QualificationIndexEvidenceBinding(StrictFinalModel):
    run_package: str = Field(min_length=1)
    qualification_report: str = Field(min_length=1)
    artifact_manifest_digest: str = Field(min_length=1)
    evidence_object_ids: tuple[str, ...]


class QualificationIndexVerifierBinding(StrictFinalModel):
    identity: str = Field(min_length=1)
    result: str = Field(min_length=1)
    result_digest: str = Field(min_length=1)
    disposition_eligible: bool


class QualificationIndexValidity(StrictFinalModel):
    effective_at: datetime | None
    expires_at: datetime | None

    @field_validator("effective_at", "expires_at")
    @classmethod
    def require_optional_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _require_timezone(value, "qualification index validity timestamp")


class QualificationIndexSupersession(StrictFinalModel):
    supersedes: str | None
    superseded_by: str | None


class QualificationIndexClaimV1(StrictFinalModel):
    claim_id: str = Field(min_length=1)
    product: str = Field(min_length=1)
    qualification_class: str = Field(min_length=1)
    capability_maturity: str = Field(min_length=1)
    qualification_state: FinalQualificationState
    profile: QualificationIndexProfileBinding
    dut: QualificationIndexDutBinding
    build: QualificationIndexBuildBinding
    evidence: QualificationIndexEvidenceBinding
    verifier: QualificationIndexVerifierBinding
    limitations: tuple[str, ...]
    validity: QualificationIndexValidity
    supersession: QualificationIndexSupersession


class Wave1R0PublicationReceipt(StrictFinalModel):
    schema_version: Literal["ets.edge-compact-r0-publication-receipt.v1"] = (
        "ets.edge-compact-r0-publication-receipt.v1"
    )
    claim_id: str = Field(min_length=1, max_length=256)
    qualification_state: FinalQualificationState
    registry_locator: str = Field(min_length=1, max_length=2048)
    registry_artifact_sha256: str = Field(pattern=_SHA256_RE)
    published_at: datetime
    package_root_sha256: str = Field(pattern=_SHA256_RE)
    hqp2_verification_digest_sha256: str = Field(pattern=_SHA256_RE)
    publication_observer_sha256: str = Field(pattern=_SHA256_RE)

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "publication receipt timestamp")


class Wave1R0FinalDisposition(StrictFinalModel):
    schema_version: Literal["ets.edge-compact-r0-final-disposition.v1"] = (
        "ets.edge-compact-r0-final-disposition.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    package_id: str = Field(min_length=1, max_length=256)
    package_root_sha256: str = Field(pattern=_SHA256_RE)
    hqp2_verification_id: str = Field(min_length=1, max_length=256)
    hqp2_verification_digest_sha256: str = Field(pattern=_SHA256_RE)
    index_claim_id: str = Field(min_length=1, max_length=256)
    phase_chain_valid: bool
    operator_trace_valid: bool
    hqp_package_binding_valid: bool
    hqp2_independent_and_valid: bool
    hqp2_disposition_eligible: bool
    trust_posture_preserved: bool
    index_claim_valid: bool
    publication_receipt_valid: bool
    qualification_state: FinalQualificationState
    wave1_r0_publication_gate_passed: bool
    issues: tuple[str, ...]
    claim_boundary: Literal[
        "edge_compact_r0_final_package_requires_physical_phase_evidence_hqp2_and_hqp5"
    ] = _R0_FINAL_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "final disposition timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> Wave1R0FinalDisposition:
        expected = (
            self.phase_chain_valid
            and self.operator_trace_valid
            and self.hqp_package_binding_valid
            and self.hqp2_independent_and_valid
            and self.hqp2_disposition_eligible
            and self.trust_posture_preserved
            and self.index_claim_valid
            and self.publication_receipt_valid
            and self.qualification_state
            in {
                FinalQualificationState.QUALIFIED,
                FinalQualificationState.QUALIFIED_WITH_DEVIATION,
            }
            and not self.issues
        )
        if self.wave1_r0_publication_gate_passed != expected:
            raise ValueError(
                "wave1_r0_publication_gate_passed must match final gate components"
            )
        return self


def build_operator_trace(
    *,
    trace_id: str,
    manifest_id: str,
    asset_id: str,
    source_observation_id: str,
    source_artifact_sha256: str,
    ingress_receipt_sha256: str,
    event_id: str,
    evidence_object_id: str,
    evidence_object_sha256: str,
    proof_artifact_sha256: str,
    export_bundle_sha256: str,
    independent_verification_sha256: str,
    reviewer_id: str,
    reviewed_at: datetime,
) -> R0OperatorSourceToProofTrace:
    payload: dict[str, Any] = {
        "schema_version": "ets.edge-compact-r0-operator-trace.v1",
        "trace_id": trace_id,
        "manifest_id": manifest_id,
        "asset_id": asset_id,
        "source_observation_id": source_observation_id,
        "source_artifact_sha256": source_artifact_sha256,
        "ingress_receipt_sha256": ingress_receipt_sha256,
        "event_id": event_id,
        "evidence_object_id": evidence_object_id,
        "evidence_object_sha256": evidence_object_sha256,
        "proof_artifact_sha256": proof_artifact_sha256,
        "export_bundle_sha256": export_bundle_sha256,
        "independent_verification_sha256": independent_verification_sha256,
        "reviewer_id": reviewer_id,
        "reviewed_at": _json_datetime(reviewed_at),
        "independently_reviewed": True,
        "hidden_manual_reconstruction_required": False,
    }
    digest = canonical_sha256(payload)
    validation_payload = dict(payload)
    validation_payload["reviewed_at"] = reviewed_at
    validation_payload["trace_commitment_sha256"] = digest
    return R0OperatorSourceToProofTrace.model_validate(validation_payload)


def build_phase_selection_from_json(
    raw: bytes,
    *,
    phase_id: R0PhaseId,
    predecessor_evaluation_id: str | None,
    source_build_sha: str,
    resulting_build_sha: str,
    source_configuration_digest: str,
    resulting_configuration_digest: str,
    build_transition: BuildTransitionKind,
    transition_binding_sha256: str | None,
    identity_before: str,
    identity_after: str,
    identity_transition_binding_sha256: str | None,
    artifact_sha256: tuple[str, ...],
    observer_receipt_sha256: tuple[str, ...] = (),
    verifier_receipt_sha256: tuple[str, ...] = (),
    external_observation_required: bool = False,
    independent_verification_required: bool = False,
    local_checkpoint_before: int | None = None,
    local_checkpoint_after: int | None = None,
    upstream_checkpoint_before: int | None = None,
    upstream_checkpoint_after: int | None = None,
) -> R0PhaseEvidenceSelection:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("phase evaluation must be a JSON object")
    number = phase_id.value.split("_", maxsplit=1)[1]
    pass_key = f"r0_{number}_passed"
    if parsed.get(pass_key) is not True:
        raise ValueError(f"{phase_id.value} evaluation does not retain a PASS")
    issues_raw = parsed.get("issues", [])
    if not isinstance(issues_raw, list):
        raise ValueError("phase evaluation issues must be an array")
    evaluated_at_raw = parsed.get("evaluated_at")
    if not isinstance(evaluated_at_raw, str):
        raise ValueError("phase evaluation requires evaluated_at")
    return R0PhaseEvidenceSelection(
        phase_id=phase_id,
        evaluation_id=_require_string(parsed, "evaluation_id"),
        evaluation_schema_version=_require_string(parsed, "schema_version"),
        manifest_id=_require_string(parsed, "manifest_id"),
        asset_id=_require_string(parsed, "asset_id"),
        evaluated_at=_parse_datetime(evaluated_at_raw),
        evaluation_sha256=canonical_sha256(parsed),
        predecessor_evaluation_id=predecessor_evaluation_id,
        source_build_sha=source_build_sha,
        resulting_build_sha=resulting_build_sha,
        source_configuration_digest=source_configuration_digest,
        resulting_configuration_digest=resulting_configuration_digest,
        build_transition=build_transition,
        transition_binding_sha256=transition_binding_sha256,
        identity_before=identity_before,
        identity_after=identity_after,
        identity_transition_binding_sha256=identity_transition_binding_sha256,
        local_checkpoint_before=local_checkpoint_before,
        local_checkpoint_after=local_checkpoint_after,
        upstream_checkpoint_before=upstream_checkpoint_before,
        upstream_checkpoint_after=upstream_checkpoint_after,
        artifact_sha256=artifact_sha256,
        observer_receipt_sha256=observer_receipt_sha256,
        verifier_receipt_sha256=verifier_receipt_sha256,
        external_observation_required=external_observation_required,
        independent_verification_required=independent_verification_required,
        issues=tuple(str(item) for item in issues_raw),
        claim_boundary=_require_string(parsed, "claim_boundary"),
        disposition=_require_phase_disposition(parsed),
    )


def assemble_wave1_r0_package(
    manifest: EdgeCompactR0BenchManifest,
    *,
    phases: tuple[R0PhaseEvidenceSelection, ...],
    operator_trace: R0OperatorSourceToProofTrace,
    historical_runs: tuple[R0HistoricalRunReference, ...],
    hqp: R0HqpPackageBinding,
    runtime_id: str,
    final_build_sha: str,
    final_artifact_digest: str,
    final_configuration_digest: str,
    created_at: datetime,
) -> Wave1R0PackageManifest:
    blockers = readiness_issues(manifest)
    if blockers:
        raise ValueError("bench manifest is not ready: " + "; ".join(blockers))
    asset_id = manifest.dut.asset_id
    manufacturer = manifest.dut.manufacturer
    model = manifest.dut.model
    revision = manifest.dut.hardware_revision
    if not all((asset_id, manufacturer, model, revision)):
        raise ValueError("final package requires complete named-DUT identity")
    payload: dict[str, Any] = {
        "schema_version": "ets.edge-compact-r0-final-package.v1",
        "package_id": (
            "edge-r0-final-"
            + canonical_sha256(
                {
                    "manifest_id": manifest.manifest_id,
                    "asset_id": asset_id,
                    "phase_digests": [item.evaluation_sha256 for item in phases],
                    "hqp_run": hqp.run_digest_sha256,
                }
            )[:24]
        ),
        "created_at": _json_datetime(created_at),
        "qualification_class": "EDGE_COMPACT_R0",
        "manifest_id": manifest.manifest_id,
        "asset_id": asset_id,
        "manufacturer": manufacturer,
        "model": model,
        "hardware_revision": revision,
        "firmware": manifest.dut.firmware,
        "runtime_id": runtime_id,
        "final_build_sha": final_build_sha,
        "final_artifact_digest": final_artifact_digest,
        "final_configuration_digest": final_configuration_digest,
        "identity_profile": "software_volume",
        "hardware_attested": False,
        "secure_boot_verified": False,
        "hardware_key_protection": False,
        "phases": [item.model_dump(mode="json") for item in phases],
        "operator_trace": operator_trace.model_dump(mode="json"),
        "historical_runs": [item.model_dump(mode="json") for item in historical_runs],
        "hqp": hqp.model_dump(mode="json"),
        "limitations": list(_R0_LIMITATIONS),
        "claim_boundary": _R0_FINAL_CLAIM_BOUNDARY,
    }
    root_digest = canonical_sha256(payload)
    validation_payload = dict(payload)
    validation_payload["created_at"] = created_at
    validation_payload["phases"] = phases
    validation_payload["operator_trace"] = operator_trace
    validation_payload["historical_runs"] = historical_runs
    validation_payload["hqp"] = hqp
    validation_payload["limitations"] = _R0_LIMITATIONS
    validation_payload["package_root_sha256"] = root_digest
    return Wave1R0PackageManifest.model_validate(validation_payload)


def build_qualification_index_claim(
    package: Wave1R0PackageManifest,
    verification: HardwareQualificationVerification,
    *,
    capability_maturity: str,
    verification_result_locator: str,
    effective_at: datetime,
    expires_at: datetime | None = None,
    supersedes: str | None = None,
) -> QualificationIndexClaimV1:
    state = _eligible_index_state(verification)
    claim_id = f"edge-r0-{package.package_root_sha256[:24]}"
    return QualificationIndexClaimV1(
        claim_id=claim_id,
        product="ETS Edge",
        qualification_class=package.qualification_class,
        capability_maturity=capability_maturity,
        qualification_state=state,
        profile=QualificationIndexProfileBinding(
            profile_id=package.hqp.profile_id,
            profile_version=package.hqp.profile_version,
        ),
        dut=QualificationIndexDutBinding(
            manufacturer=package.manufacturer,
            model=package.model,
            hardware_revision=package.hardware_revision,
            asset_id=package.asset_id,
            firmware=package.firmware,
            signer_profile=package.identity_profile,
        ),
        build=QualificationIndexBuildBinding(
            source_revision=package.final_build_sha,
            artifact_digest=package.final_artifact_digest,
            configuration_digest=package.final_configuration_digest,
        ),
        evidence=QualificationIndexEvidenceBinding(
            run_package=package.hqp.run_package_locator,
            qualification_report=package.hqp.qualification_report_locator,
            artifact_manifest_digest=package.hqp.artifact_manifest_digest_sha256,
            evidence_object_ids=package.hqp.evidence_object_ids,
        ),
        verifier=QualificationIndexVerifierBinding(
            identity=verification.verifier_id,
            result=verification_result_locator,
            result_digest=verification.verification_digest_sha256,
            disposition_eligible=verification.eligible_for_claimed_disposition,
        ),
        limitations=package.limitations,
        validity=QualificationIndexValidity(
            effective_at=effective_at,
            expires_at=expires_at,
        ),
        supersession=QualificationIndexSupersession(
            supersedes=supersedes,
            superseded_by=None,
        ),
    )


def evaluate_wave1_r0_publication(
    package: Wave1R0PackageManifest,
    verification: HardwareQualificationVerification,
    claim: QualificationIndexClaimV1,
    publication: Wave1R0PublicationReceipt,
    *,
    evaluated_at: datetime,
) -> Wave1R0FinalDisposition:
    issues: list[str] = []

    phase_chain_valid = tuple(item.phase_id for item in package.phases) == (
        _REQUIRED_PHASE_ORDER
    )
    if not phase_chain_valid:
        issues.append("final package phase chain is incomplete")

    operator_trace_valid = (
        package.operator_trace.independently_reviewed
        and not package.operator_trace.hidden_manual_reconstruction_required
    )
    if not operator_trace_valid:
        issues.append("R0.16 operator source-to-proof trace is incomplete")

    hqp_package_binding_valid = True
    if verification.profile_id != package.hqp.profile_id:
        issues.append("HQP-2 profile ID does not match final package")
        hqp_package_binding_valid = False
    if verification.profile_version != package.hqp.profile_version:
        issues.append("HQP-2 profile version does not match final package")
        hqp_package_binding_valid = False
    if verification.profile_digest_sha256 != package.hqp.profile_digest_sha256:
        issues.append("HQP-2 profile digest does not match final package")
        hqp_package_binding_valid = False
    if verification.run_id != package.hqp.run_id:
        issues.append("HQP-2 run ID does not match final package")
        hqp_package_binding_valid = False
    if verification.run_digest_sha256 != package.hqp.run_digest_sha256:
        issues.append("HQP-2 run digest does not match final package")
        hqp_package_binding_valid = False
    if verification.report_id != package.hqp.report_id:
        issues.append("HQP-2 report ID does not match final package")
        hqp_package_binding_valid = False
    if verification.report_digest_sha256 != package.hqp.report_digest_sha256:
        issues.append("HQP-2 report digest does not match final package")
        hqp_package_binding_valid = False

    hqp2_valid = (
        verification.outcome is VerificationOutcome.VALID
        and verification.independent_execution_context
        and not verification.missing_artifact_ids
        and not verification.mismatched_artifact_ids
        and not verification.invalid_evidence_object_ids
    )
    if not hqp2_valid:
        issues.append("R0.17 HQP-2 result is not independently valid")

    hqp2_eligible = verification.eligible_for_claimed_disposition
    if not hqp2_eligible:
        issues.append("HQP-2 did not mark claimed disposition eligible")

    trust_posture_preserved = (
        package.identity_profile == "software_volume"
        and package.hardware_attested is False
        and package.secure_boot_verified is False
        and package.hardware_key_protection is False
        and package.limitations == _R0_LIMITATIONS
    )
    if not trust_posture_preserved:
        issues.append("final package escalates the R0 trust posture")

    expected_state: FinalQualificationState | None = None
    try:
        expected_state = _eligible_index_state(verification)
    except ValueError as exc:
        issues.append(str(exc))

    index_claim_valid = True
    if claim.claim_id != publication.claim_id:
        issues.append("publication receipt references another index claim")
        index_claim_valid = False
    if claim.qualification_class != package.qualification_class:
        issues.append("index qualification class mismatch")
        index_claim_valid = False
    if claim.dut.asset_id != package.asset_id:
        issues.append("index DUT asset mismatch")
        index_claim_valid = False
    if claim.profile.profile_id != package.hqp.profile_id:
        issues.append("index profile ID mismatch")
        index_claim_valid = False
    if claim.profile.profile_version != package.hqp.profile_version:
        issues.append("index profile version mismatch")
        index_claim_valid = False
    if claim.build.source_revision != package.final_build_sha:
        issues.append("index build SHA mismatch")
        index_claim_valid = False
    if claim.build.artifact_digest != package.final_artifact_digest:
        issues.append("index artifact digest mismatch")
        index_claim_valid = False
    if claim.build.configuration_digest != package.final_configuration_digest:
        issues.append("index configuration digest mismatch")
        index_claim_valid = False
    if claim.verifier.result_digest != verification.verification_digest_sha256:
        issues.append("index verifier digest mismatch")
        index_claim_valid = False
    if claim.limitations != package.limitations:
        issues.append("index limitations differ from final package")
        index_claim_valid = False
    if expected_state is None or claim.qualification_state is not expected_state:
        issues.append("index qualification state does not match HQP-2 disposition")
        index_claim_valid = False

    publication_valid = (
        publication.package_root_sha256 == package.package_root_sha256
        and publication.hqp2_verification_digest_sha256
        == verification.verification_digest_sha256
        and publication.qualification_state is claim.qualification_state
        and publication.published_at >= package.created_at
    )
    if not publication_valid:
        issues.append("HQP-5 publication receipt does not bind final package/result")

    qualification_state = (
        expected_state
        if expected_state is not None
        else FinalQualificationState.FAILED
    )
    passed = (
        phase_chain_valid
        and operator_trace_valid
        and hqp_package_binding_valid
        and hqp2_valid
        and hqp2_eligible
        and trust_posture_preserved
        and index_claim_valid
        and publication_valid
        and qualification_state
        in {
            FinalQualificationState.QUALIFIED,
            FinalQualificationState.QUALIFIED_WITH_DEVIATION,
        }
        and not issues
    )
    seed = {
        "package_root_sha256": package.package_root_sha256,
        "verification_digest": verification.verification_digest_sha256,
        "claim_id": claim.claim_id,
        "publication_digest": publication.registry_artifact_sha256,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    return Wave1R0FinalDisposition(
        evaluation_id=f"edge-r0-final-{canonical_sha256(seed)[:24]}",
        evaluated_at=evaluated_at,
        package_id=package.package_id,
        package_root_sha256=package.package_root_sha256,
        hqp2_verification_id=verification.verification_id,
        hqp2_verification_digest_sha256=verification.verification_digest_sha256,
        index_claim_id=claim.claim_id,
        phase_chain_valid=phase_chain_valid,
        operator_trace_valid=operator_trace_valid,
        hqp_package_binding_valid=hqp_package_binding_valid,
        hqp2_independent_and_valid=hqp2_valid,
        hqp2_disposition_eligible=hqp2_eligible,
        trust_posture_preserved=trust_posture_preserved,
        index_claim_valid=index_claim_valid,
        publication_receipt_valid=publication_valid,
        qualification_state=qualification_state,
        wave1_r0_publication_gate_passed=passed,
        issues=tuple(issues),
    )


def render_wave1_r0_summary(
    package: Wave1R0PackageManifest,
    result: Wave1R0FinalDisposition,
) -> str:
    lines = [
        f"Wave 1 Edge Compact R0 package: {package.package_id}",
        f"DUT: {package.manufacturer} {package.model} rev {package.hardware_revision}",
        f"Asset: {package.asset_id}",
        f"Build: {package.final_build_sha}",
        f"Qualification state: {result.qualification_state.value}",
        (
            "Publication gate passed: "
            + str(result.wave1_r0_publication_gate_passed).lower()
        ),
        "Trust posture:",
        "- identity_profile=software_volume",
        "- hardware_attested=false",
        "- secure_boot_verified=false",
        "- hardware_key_protection=false",
        "Bounded claim:",
        (
            "- The exact retained DUT/build/profile survived the selected physical R0 "
            "qualification corpus and the resulting package was independently verified."
        ),
        "- This result does not establish hardware-attested identity.",
        f"Package root: {package.package_root_sha256}",
        f"HQP-2 verification digest: {result.hqp2_verification_digest_sha256}",
        f"HQP-5 claim: {result.index_claim_id}",
    ]
    if result.issues:
        lines.append("Issues:")
        lines.extend(f"- {item}" for item in result.issues)
    return "\n".join(lines) + "\n"


def _eligible_index_state(
    verification: HardwareQualificationVerification,
) -> FinalQualificationState:
    if verification.outcome is not VerificationOutcome.VALID:
        raise ValueError("HQP-2 outcome is not valid")
    if not verification.independent_execution_context:
        raise ValueError("HQP-2 result is not independent")
    if not verification.eligible_for_claimed_disposition:
        raise ValueError("HQP-2 disposition is not eligible")
    if verification.claimed_disposition == QualificationDisposition.QUALIFIED.value:
        return FinalQualificationState.QUALIFIED
    if (
        verification.claimed_disposition
        == QualificationDisposition.QUALIFIED_WITH_DEVIATION.value
    ):
        return FinalQualificationState.QUALIFIED_WITH_DEVIATION
    raise ValueError("HQP-2 claimed disposition is not publishable as qualified")


def _require_string(value: Mapping[str, Any], key: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"phase evaluation requires string field {key}")
    return raw


def _require_phase_disposition(
    value: Mapping[str, Any],
) -> Literal["phase_evidence_only"]:
    raw = value.get("disposition")
    if raw != "phase_evidence_only":
        raise ValueError("selected phase must retain disposition=phase_evidence_only")
    return "phase_evidence_only"


def _json_datetime(value: datetime) -> str:
    normalized = _require_timezone(value, "canonical datetime")
    return normalized.isoformat().replace("+00:00", "Z")


def _require_timezone(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone offset")
    return value.astimezone(UTC)


def _parse_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return _require_timezone(datetime.fromisoformat(normalized), "timestamp")


def _write_json(path: Path, value: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_json_model(path: Path, model: type[BaseModel]) -> BaseModel:
    return model.model_validate_json(path.read_bytes())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ETS Wave 1 Edge Compact R0 final publication evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser("evaluate-publication")
    evaluate_parser.add_argument("--package", type=Path, required=True)
    evaluate_parser.add_argument("--hqp2-verification", type=Path, required=True)
    evaluate_parser.add_argument("--index-claim", type=Path, required=True)
    evaluate_parser.add_argument("--publication-receipt", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)
    evaluate_parser.add_argument("--summary", type=Path)

    args = parser.parse_args(argv)
    if args.command == "evaluate-publication":
        package = Wave1R0PackageManifest.model_validate_json(args.package.read_bytes())
        verification = HardwareQualificationVerification.model_validate_json(
            args.hqp2_verification.read_bytes()
        )
        claim = QualificationIndexClaimV1.model_validate_json(
            args.index_claim.read_bytes()
        )
        publication = Wave1R0PublicationReceipt.model_validate_json(
            args.publication_receipt.read_bytes()
        )
        result = evaluate_wave1_r0_publication(
            package,
            verification,
            claim,
            publication,
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        if args.summary is not None:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.summary.write_text(
                render_wave1_r0_summary(package, result),
                encoding="utf-8",
            )
        return 0 if result.wave1_r0_publication_gate_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
