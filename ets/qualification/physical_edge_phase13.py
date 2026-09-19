"""Wave 1 Edge Compact R0 recovery-media rebuild evidence.

R0.14 evaluates rebuild from independently verified recovery media after deliberate
software-volume loss/replacement. It preserves explicit R0 trust posture, identity
restore-or-rotate semantics, historical proof verifiability and upstream reattachment.
The evaluator never performs destructive recovery actions.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.qualification.physical_edge import (
    EdgeCompactR0BenchManifest,
    load_manifest,
    readiness_issues,
)
from ets.qualification.physical_edge_phase3 import EdgeSyncStatusEvidence
from ets.qualification.physical_edge_phase10 import TimeQuality
from ets.qualification.physical_edge_phase12 import EdgeR0Phase12Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE13_CLAIM_BOUNDARY: Literal[
    "r0_14_phase_evidence_not_a_physical_qualification_result"
] = "r0_14_phase_evidence_not_a_physical_qualification_result"
_PHASE13_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase13Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class IdentityRecoveryMode(StrEnum):
    RESTORE_EXISTING_IDENTITY = "restore_existing_identity"
    ROTATE_IDENTITY_WITH_BINDING = "rotate_identity_with_binding"


class LocalHistoryMode(StrEnum):
    RESTORED = "restored"
    NOT_RESTORED = "not_restored"


class RecoveryProofSubject(StrEnum):
    PRE_REBUILD = "pre_rebuild"
    REATTACHED_RECORD = "reattached_record"


class EdgeR0PreRebuildRecord(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-pre-rebuild-record.v1"] = (
        "ets.edge-compact-r0-pre-rebuild-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    original_identity_id: str = Field(min_length=1, max_length=256)
    upstream_acceptance_sha256: str = Field(pattern=_SHA256_RE)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    local_authoritative_present: Literal[True] = True
    synchronized_before_rebuild: Literal[True] = True
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY


class EdgeR0RecoveryBaseline(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-recovery-baseline.v1"] = (
        "ets.edge-compact-r0-recovery-baseline.v1"
    )
    baseline_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase12_evaluation_id: str = Field(min_length=1, max_length=256)
    phase12_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    current_build_sha: str = Field(min_length=7, max_length=128)
    current_artifact_digest: str = Field(pattern=_SHA256_RE)
    current_configuration_digest: str = Field(pattern=_SHA256_RE)
    current_version: str = Field(min_length=1, max_length=128)
    current_data_schema_version: str = Field(min_length=1, max_length=128)
    current_runtime_id: str = Field(min_length=1, max_length=256)
    device_identity_id: str = Field(min_length=1, max_length=256)
    signing_key_id: str = Field(min_length=1, max_length=256)
    identity_material_commitment_sha256: str = Field(pattern=_SHA256_RE)
    hardware_attested: Literal[False] = False
    secure_boot_verified: Literal[False] = False
    hardware_key_protection: Literal[False] = False
    identity_profile: Literal["software_volume"] = "software_volume"
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    log_head_sha256: str = Field(pattern=_SHA256_RE)
    historical_record_commitment_sha256: str = Field(pattern=_SHA256_RE)
    queue_state: EdgeSyncStatusEvidence
    storage_used_bytes: int = Field(ge=0)
    storage_high_watermark_used_bytes: int = Field(gt=0)
    network_connected: Literal[True] = True
    time_quality: Literal[TimeQuality.TRUSTED_SYNCHRONIZED] = (
        TimeQuality.TRUSTED_SYNCHRONIZED
    )
    synchronized_records: tuple[EdgeR0PreRebuildRecord, ...] = Field(min_length=1)
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    off_dut_evidence_copy_sha256: str = Field(pattern=_SHA256_RE)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "recovery-baseline timestamp")

    @model_validator(mode="after")
    def validate_baseline(self) -> EdgeR0RecoveryBaseline:
        if self.storage_used_bytes >= self.storage_high_watermark_used_bytes:
            raise ValueError("R0.14 baseline exceeds the R0.8 storage boundary")
        ids = [record.record_id for record in self.synchronized_records]
        event_ids = [record.event_id for record in self.synchronized_records]
        idem = [record.idempotency_key for record in self.synchronized_records]
        if len(ids) != len(set(ids)):
            raise ValueError("pre-rebuild record IDs must be unique")
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("pre-rebuild event IDs must be unique")
        if len(idem) != len(set(idem)):
            raise ValueError("pre-rebuild idempotency keys must be unique")
        for record in self.synchronized_records:
            if record.original_identity_id != self.device_identity_id:
                raise ValueError("pre-rebuild record identity must match baseline identity")
        return self


class EdgeR0RecoveryMedia(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-recovery-media.v1"] = (
        "ets.edge-compact-r0-recovery-media.v1"
    )
    media_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    prepared_at: datetime
    target_asset_id: str = Field(min_length=1, max_length=256)
    image_build_sha: str = Field(min_length=7, max_length=128)
    image_artifact_digest: str = Field(pattern=_SHA256_RE)
    image_configuration_digest: str = Field(pattern=_SHA256_RE)
    media_image_digest: str = Field(pattern=_SHA256_RE)
    configuration_template_digest: str = Field(pattern=_SHA256_RE)
    expected_version: str = Field(min_length=1, max_length=128)
    expected_data_schema_version: str = Field(min_length=1, max_length=128)
    expected_runtime_id: str = Field(min_length=1, max_length=256)
    source_provenance: str = Field(min_length=1, max_length=1024)
    media_creation_receipt_sha256: str = Field(pattern=_SHA256_RE)
    independent_verification_sha256: str = Field(pattern=_SHA256_RE)
    independently_verified: Literal[True] = True
    operator_approved: Literal[True] = True
    evaluator_executes_recovery: Literal[False] = False
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY

    @field_validator("prepared_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "recovery-media timestamp")


class EdgeR0RebuildObservation(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-rebuild-observation.v1"] = (
        "ets.edge-compact-r0-rebuild-observation.v1"
    )
    rebuild_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    media_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    target_asset_id: str = Field(min_length=1, max_length=256)
    target_storage_id: str = Field(min_length=1, max_length=256)
    observed_media_image_digest: str = Field(pattern=_SHA256_RE)
    media_boot_receipt_sha256: str = Field(pattern=_SHA256_RE)
    partition_filesystem_result_sha256: str = Field(pattern=_SHA256_RE)
    partition_filesystem_success: bool
    installed_build_sha: str = Field(min_length=7, max_length=128)
    installed_artifact_digest: str = Field(pattern=_SHA256_RE)
    installed_configuration_digest: str = Field(pattern=_SHA256_RE)
    installed_version: str = Field(min_length=1, max_length=128)
    installed_data_schema_version: str = Field(min_length=1, max_length=128)
    installed_runtime_id: str = Field(min_length=1, max_length=256)
    resulting_boot_id: str = Field(min_length=1, max_length=128)
    service_healthy: bool
    build_independently_identified: bool
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    external_observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    independently_observed: bool
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "rebuild-observation timestamp")

    @model_validator(mode="after")
    def validate_rebuild(self) -> EdgeR0RebuildObservation:
        if self.completed_at <= self.started_at:
            raise ValueError("rebuild observation must have positive duration")
        return self


class EdgeR0IdentityRecoveryEvidence(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-identity-recovery.v1"] = (
        "ets.edge-compact-r0-identity-recovery.v1"
    )
    identity_recovery_id: str = Field(min_length=1, max_length=256)
    rebuild_id: str = Field(min_length=1, max_length=256)
    mode: IdentityRecoveryMode
    observed_at: datetime
    pre_device_identity_id: str = Field(min_length=1, max_length=256)
    pre_signing_key_id: str = Field(min_length=1, max_length=256)
    post_device_identity_id: str = Field(min_length=1, max_length=256)
    post_signing_key_id: str = Field(min_length=1, max_length=256)
    recovery_material_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    continuity_binding_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    old_to_new_binding_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    upstream_enrollment_updated: bool
    historical_identity_attribution_preserved: bool
    post_recovery_identity_attribution_correct: bool
    hardware_attested: Literal[False] = False
    secure_boot_verified: Literal[False] = False
    hardware_key_protection: Literal[False] = False
    identity_profile: Literal["software_volume"] = "software_volume"
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "identity-recovery timestamp")

    @model_validator(mode="after")
    def validate_mode(self) -> EdgeR0IdentityRecoveryEvidence:
        if self.mode is IdentityRecoveryMode.RESTORE_EXISTING_IDENTITY:
            if self.post_device_identity_id != self.pre_device_identity_id:
                raise ValueError("restored device identity must equal pre-rebuild identity")
            if self.post_signing_key_id != self.pre_signing_key_id:
                raise ValueError("restored signing key must equal pre-rebuild signing key")
            if self.recovery_material_sha256 is None:
                raise ValueError("identity restore requires recovery material commitment")
            if self.continuity_binding_sha256 is None:
                raise ValueError("identity restore requires continuity binding")
            if self.old_to_new_binding_sha256 is not None:
                raise ValueError("identity restore cannot carry old-to-new rotation binding")
            if self.upstream_enrollment_updated:
                raise ValueError("identity restore must not claim rotation enrollment update")
        else:
            if self.post_device_identity_id == self.pre_device_identity_id:
                raise ValueError("rotated device identity must differ from prior identity")
            if self.post_signing_key_id == self.pre_signing_key_id:
                raise ValueError("rotated signing key must differ from prior signing key")
            if self.old_to_new_binding_sha256 is None:
                raise ValueError("identity rotation requires old-to-new binding")
            if not self.upstream_enrollment_updated:
                raise ValueError("identity rotation requires upstream enrollment update")
        return self


class EdgeR0ReattachedRecord(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-reattached-record.v1"] = (
        "ets.edge-compact-r0-reattached-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    original_identity_id: str = Field(min_length=1, max_length=256)
    upstream_record_present: bool
    final_upstream_commit_count: int = Field(ge=0, le=32)
    final_upstream_event_id: str | None = Field(default=None, max_length=256)
    upstream_acceptance_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    proof_artifact_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    authoritative_local_present_after_rebuild: bool
    local_marked_synchronized: bool
    replayed_as_new_logical_event: bool
    invented_upstream_acknowledgement: bool
    reattachment_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_commit_shape(self) -> EdgeR0ReattachedRecord:
        fields = (
            self.final_upstream_event_id,
            self.upstream_acceptance_sha256,
            self.proof_artifact_sha256,
        )
        if self.final_upstream_commit_count > 0:
            if any(value is None for value in fields):
                raise ValueError("reattached committed record requires event/acceptance/proof")
        elif any(value is not None for value in fields):
            raise ValueError("zero reattached commits cannot carry final commit fields")
        if self.local_marked_synchronized and self.final_upstream_commit_count != 1:
            raise ValueError("local synchronized state requires one upstream commit")
        return self


class EdgeR0RecoveryReattachment(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-recovery-reattachment.v1"] = (
        "ets.edge-compact-r0-recovery-reattachment.v1"
    )
    reattachment_id: str = Field(min_length=1, max_length=256)
    rebuild_id: str = Field(min_length=1, max_length=256)
    identity_recovery_id: str = Field(min_length=1, max_length=256)
    reattached_at: datetime
    local_history_mode: LocalHistoryMode
    local_history_limitation_explicit: bool
    restored_local_history_commitment_sha256: str | None = Field(
        default=None,
        pattern=_SHA256_RE,
    )
    upstream_historical_commitment_verified: bool
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    records: tuple[EdgeR0ReattachedRecord, ...] = Field(min_length=1)
    final_queue_state: EdgeSyncStatusEvidence
    storage_used_bytes: int = Field(ge=0)
    network_connected: bool
    time_quality: TimeQuality
    software_state_unambiguous: bool
    reconciliation_commitment_sha256: str = Field(pattern=_SHA256_RE)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY

    @field_validator("reattached_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "recovery-reattachment timestamp")

    @model_validator(mode="after")
    def validate_history_mode(self) -> EdgeR0RecoveryReattachment:
        if self.local_history_mode is LocalHistoryMode.RESTORED:
            if self.restored_local_history_commitment_sha256 is None:
                raise ValueError("restored local history requires a retained commitment")
        else:
            if self.restored_local_history_commitment_sha256 is not None:
                raise ValueError("non-restored local history cannot carry restored commitment")
            if not self.local_history_limitation_explicit:
                raise ValueError("missing local history must be explicitly disclosed")
        ids = [record.record_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("reattached record IDs must be unique")
        return self


class EdgeR0RecoveryProofReceipt(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-recovery-proof-receipt.v1"] = (
        "ets.edge-compact-r0-recovery-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    subject_kind: RecoveryProofSubject
    subject_id: str = Field(min_length=1, max_length=256)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "recovery-proof timestamp")


class EdgeR0RecoveryCanary(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-recovery-canary.v1"] = (
        "ets.edge-compact-r0-recovery-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    reattachment_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    identity_recovery_mode: IdentityRecoveryMode
    post_rebuild_identity_id: str = Field(min_length=1, max_length=256)
    rebuilt_build_sha: str = Field(min_length=7, max_length=128)
    rebuilt_configuration_digest: str = Field(pattern=_SHA256_RE)
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    synchronized: bool
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.14 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0RecoveryCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("recovery canary payload SHA-256 must match content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("recovery canary verification cannot precede capture")
        return self


class EdgeR0Phase13Evaluation(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-phase13-evaluation.v1"] = (
        "ets.edge-compact-r0-phase13-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase12_evaluation_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    media_id: str = Field(min_length=1, max_length=256)
    rebuild_id: str = Field(min_length=1, max_length=256)
    identity_recovery_id: str = Field(min_length=1, max_length=256)
    reattachment_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    media_provenance_valid: bool
    rebuild_target_valid: bool
    rebuilt_software_valid: bool
    identity_recovery_valid: bool
    trust_posture_preserved: bool
    historical_evidence_preserved: bool
    upstream_reattachment_valid: bool
    checkpoints_consistent: bool
    no_logical_replay_or_invented_ack: bool
    prior_phase_boundaries_preserved: bool
    independent_verification_complete: bool
    post_rebuild_canary_valid: bool
    r0_14_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE13_DISPOSITION
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE13_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.14 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase13Evaluation:
        expected = (
            self.media_provenance_valid
            and self.rebuild_target_valid
            and self.rebuilt_software_valid
            and self.identity_recovery_valid
            and self.trust_posture_preserved
            and self.historical_evidence_preserved
            and self.upstream_reattachment_valid
            and self.checkpoints_consistent
            and self.no_logical_replay_or_invented_ack
            and self.prior_phase_boundaries_preserved
            and self.independent_verification_complete
            and self.post_rebuild_canary_valid
            and not self.issues
        )
        if self.r0_14_passed != expected:
            raise ValueError("r0_14_passed must match component results and issues")
        return self


def build_recovery_reattachment_commitment(
    records: tuple[EdgeR0ReattachedRecord, ...],
) -> str:
    value = [
        {
            "record_id": record.record_id,
            "event_id": record.event_id,
            "idempotency_key": record.idempotency_key,
            "original_identity_id": record.original_identity_id,
            "upstream_record_present": record.upstream_record_present,
            "final_upstream_commit_count": record.final_upstream_commit_count,
            "final_upstream_event_id": record.final_upstream_event_id,
            "upstream_acceptance_sha256": record.upstream_acceptance_sha256,
            "proof_artifact_sha256": record.proof_artifact_sha256,
            "authoritative_local_present_after_rebuild": (
                record.authoritative_local_present_after_rebuild
            ),
            "local_marked_synchronized": record.local_marked_synchronized,
            "replayed_as_new_logical_event": record.replayed_as_new_logical_event,
            "invented_upstream_acknowledgement": (
                record.invented_upstream_acknowledgement
            ),
        }
        for record in sorted(records, key=lambda item: item.record_id)
    ]
    return canonical_sha256(value)


def evaluate_r0_14(
    manifest: EdgeCompactR0BenchManifest,
    phase12: EdgeR0Phase12Evaluation,
    baseline: EdgeR0RecoveryBaseline,
    media: EdgeR0RecoveryMedia,
    rebuild: EdgeR0RebuildObservation,
    identity: EdgeR0IdentityRecoveryEvidence,
    reattachment: EdgeR0RecoveryReattachment,
    proofs: tuple[EdgeR0RecoveryProofReceipt, ...],
    canary: EdgeR0RecoveryCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase13Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.14: bench manifest not ready: {blocker}")
    if not phase12.r0_13_passed:
        issues.append("R0.14: R0.13 did not pass")
    if phase12.manifest_id != manifest.manifest_id or phase12.asset_id != asset_id:
        issues.append("R0.14: R0.13 evaluation is bound to another DUT")

    if baseline.manifest_id != manifest.manifest_id or baseline.asset_id != asset_id:
        issues.append("R0.14: baseline is bound to another DUT")
    if baseline.phase12_evaluation_id != phase12.evaluation_id:
        issues.append("R0.14: baseline references another R0.13 evaluation")
    if baseline.phase12_evaluation_sha256 != canonical_sha256(
        phase12.model_dump(mode="json")
    ):
        issues.append("R0.14: R0.13 digest binding mismatch")

    media_provenance_valid = True
    if media.baseline_id != baseline.baseline_id:
        issues.append("R0.14: recovery media references another baseline")
        media_provenance_valid = False
    if media.target_asset_id != baseline.asset_id:
        issues.append("R0.14: recovery media targets another hardware asset")
        media_provenance_valid = False
    if media.prepared_at < baseline.captured_at:
        issues.append("R0.14: recovery media was prepared before retained baseline")
        media_provenance_valid = False

    rebuild_target_valid = True
    if rebuild.baseline_id != baseline.baseline_id:
        issues.append("R0.14: rebuild references another baseline")
        rebuild_target_valid = False
    if rebuild.media_id != media.media_id:
        issues.append("R0.14: rebuild references another recovery medium")
        rebuild_target_valid = False
    if rebuild.target_asset_id != baseline.asset_id:
        issues.append("R0.14: rebuild targeted another hardware asset")
        rebuild_target_valid = False
    if rebuild.observed_media_image_digest != media.media_image_digest:
        issues.append("R0.14: observed recovery-media digest mismatch")
        rebuild_target_valid = False
    if not rebuild.partition_filesystem_success:
        issues.append("R0.14: rebuild storage preparation did not succeed")
        rebuild_target_valid = False
    if not rebuild.independently_observed:
        issues.append("R0.14: rebuild lacks independent observation")
        rebuild_target_valid = False

    rebuilt_software_valid = True
    software_fields = (
        (rebuild.installed_build_sha, media.image_build_sha, "build"),
        (
            rebuild.installed_artifact_digest,
            media.image_artifact_digest,
            "artifact digest",
        ),
        (
            rebuild.installed_configuration_digest,
            media.image_configuration_digest,
            "configuration digest",
        ),
        (rebuild.installed_version, media.expected_version, "version"),
        (
            rebuild.installed_data_schema_version,
            media.expected_data_schema_version,
            "data schema version",
        ),
        (rebuild.installed_runtime_id, media.expected_runtime_id, "runtime"),
    )
    for observed, expected, label in software_fields:
        if observed != expected:
            issues.append(f"R0.14: rebuilt {label} mismatch")
            rebuilt_software_valid = False
    if not rebuild.service_healthy:
        issues.append("R0.14: rebuilt service is not healthy")
        rebuilt_software_valid = False
    if not rebuild.build_independently_identified:
        issues.append("R0.14: rebuilt software was not independently identified")
        rebuilt_software_valid = False

    identity_recovery_valid = True
    if identity.rebuild_id != rebuild.rebuild_id:
        issues.append("R0.14: identity recovery references another rebuild")
        identity_recovery_valid = False
    if identity.pre_device_identity_id != baseline.device_identity_id:
        issues.append("R0.14: pre-rebuild device identity binding mismatch")
        identity_recovery_valid = False
    if identity.pre_signing_key_id != baseline.signing_key_id:
        issues.append("R0.14: pre-rebuild signing-key binding mismatch")
        identity_recovery_valid = False
    if not identity.historical_identity_attribution_preserved:
        issues.append("R0.14: historical identity attribution was not preserved")
        identity_recovery_valid = False
    if not identity.post_recovery_identity_attribution_correct:
        issues.append("R0.14: post-recovery identity attribution is incorrect")
        identity_recovery_valid = False

    if identity.mode is IdentityRecoveryMode.RESTORE_EXISTING_IDENTITY:
        if identity.post_device_identity_id != baseline.device_identity_id:
            issues.append("R0.14: restored device identity differs from baseline")
            identity_recovery_valid = False
        if identity.post_signing_key_id != baseline.signing_key_id:
            issues.append("R0.14: restored signing key differs from baseline")
            identity_recovery_valid = False
        if identity.recovery_material_sha256 != baseline.identity_material_commitment_sha256:
            issues.append("R0.14: restored identity material commitment mismatch")
            identity_recovery_valid = False
        if identity.continuity_binding_sha256 is None:
            issues.append("R0.14: restored identity lacks continuity binding")
            identity_recovery_valid = False
    else:
        if identity.post_device_identity_id == baseline.device_identity_id:
            issues.append("R0.14: rotated device identity did not change")
            identity_recovery_valid = False
        if identity.post_signing_key_id == baseline.signing_key_id:
            issues.append("R0.14: rotated signing key did not change")
            identity_recovery_valid = False
        if identity.old_to_new_binding_sha256 is None:
            issues.append("R0.14: identity rotation lacks old-to-new binding")
            identity_recovery_valid = False
        if not identity.upstream_enrollment_updated:
            issues.append("R0.14: identity rotation lacks upstream enrollment update")
            identity_recovery_valid = False

    trust_posture_preserved = (
        identity.identity_profile == "software_volume"
        and identity.hardware_attested is False
        and identity.secure_boot_verified is False
        and identity.hardware_key_protection is False
    )
    if not trust_posture_preserved:
        issues.append("R0.14: R0 trust posture changed unexpectedly")

    if reattachment.rebuild_id != rebuild.rebuild_id:
        issues.append("R0.14: reattachment references another rebuild")
    if reattachment.identity_recovery_id != identity.identity_recovery_id:
        issues.append("R0.14: reattachment references another identity recovery")

    historical_evidence_preserved = reattachment.upstream_historical_commitment_verified
    if not reattachment.upstream_historical_commitment_verified:
        issues.append("R0.14: upstream historical commitment was not verified")
    if reattachment.local_history_mode is LocalHistoryMode.RESTORED:
        if (
            reattachment.restored_local_history_commitment_sha256
            != baseline.historical_record_commitment_sha256
        ):
            issues.append("R0.14: restored local historical commitment mismatch")
            historical_evidence_preserved = False
    elif not reattachment.local_history_limitation_explicit:
        issues.append("R0.14: absent local history limitation was not disclosed")
        historical_evidence_preserved = False

    baseline_by_id = {
        record.record_id: record for record in baseline.synchronized_records
    }
    recovered_by_id = {record.record_id: record for record in reattachment.records}
    baseline_ids = set(baseline_by_id)
    recovered_ids = set(recovered_by_id)
    missing = sorted(baseline_ids - recovered_ids)
    unknown = sorted(recovered_ids - baseline_ids)
    upstream_reattachment_valid = not missing and not unknown
    no_logical_replay_or_invented_ack = not missing and not unknown
    if missing:
        issues.append(f"R0.14: reattachment missing records: {missing}")
    if unknown:
        issues.append(f"R0.14: reattachment contains unknown records: {unknown}")

    for record_id in sorted(baseline_ids & recovered_ids):
        before = baseline_by_id[record_id]
        after = recovered_by_id[record_id]
        if after.event_id != before.event_id:
            issues.append(f"R0.14: reattached event ID changed: {record_id}")
            upstream_reattachment_valid = False
        if after.idempotency_key != before.idempotency_key:
            issues.append(f"R0.14: reattached idempotency key changed: {record_id}")
            upstream_reattachment_valid = False
        if after.original_identity_id != before.original_identity_id:
            issues.append(f"R0.14: historical identity attribution changed: {record_id}")
            upstream_reattachment_valid = False
        if not after.upstream_record_present:
            issues.append(f"R0.14: upstream synchronized record missing: {record_id}")
            upstream_reattachment_valid = False
        if after.final_upstream_commit_count != 1:
            issues.append(
                f"R0.14: expected one existing logical upstream commit: {record_id}"
            )
            upstream_reattachment_valid = False
        if after.final_upstream_event_id != before.event_id:
            issues.append(f"R0.14: upstream event binding changed: {record_id}")
            upstream_reattachment_valid = False
        if after.upstream_acceptance_sha256 != before.upstream_acceptance_sha256:
            issues.append(f"R0.14: upstream acceptance digest changed: {record_id}")
            upstream_reattachment_valid = False
        if after.proof_artifact_sha256 != before.proof_artifact_sha256:
            issues.append(f"R0.14: reattached proof digest changed: {record_id}")
            upstream_reattachment_valid = False
        if after.replayed_as_new_logical_event:
            issues.append(f"R0.14: synchronized record was replayed as new: {record_id}")
            no_logical_replay_or_invented_ack = False
        if after.invented_upstream_acknowledgement:
            issues.append(f"R0.14: invented upstream acknowledgement: {record_id}")
            no_logical_replay_or_invented_ack = False
        if reattachment.local_history_mode is LocalHistoryMode.RESTORED:
            if not after.authoritative_local_present_after_rebuild:
                issues.append(f"R0.14: restored local record missing: {record_id}")
                upstream_reattachment_valid = False
            if not after.local_marked_synchronized:
                issues.append(f"R0.14: restored record not marked synchronized: {record_id}")
                upstream_reattachment_valid = False

    expected_reattachment = build_recovery_reattachment_commitment(
        reattachment.records
    )
    if reattachment.reconciliation_commitment_sha256 != expected_reattachment:
        issues.append("R0.14: reattachment commitment mismatch")
        upstream_reattachment_valid = False

    checkpoints_consistent = (
        reattachment.upstream_checkpoint_index >= baseline.upstream_checkpoint_index
        and (
            reattachment.local_history_mode is LocalHistoryMode.NOT_RESTORED
            or reattachment.local_checkpoint_index >= baseline.local_checkpoint_index
        )
    )
    if reattachment.upstream_checkpoint_index < baseline.upstream_checkpoint_index:
        issues.append("R0.14: upstream checkpoint regressed")
    if (
        reattachment.local_history_mode is LocalHistoryMode.RESTORED
        and reattachment.local_checkpoint_index < baseline.local_checkpoint_index
    ):
        issues.append("R0.14: restored local checkpoint regressed")

    final_queue = reattachment.final_queue_state
    prior_phase_boundaries_preserved = (
        reattachment.storage_used_bytes < baseline.storage_high_watermark_used_bytes
        and reattachment.network_connected
        and reattachment.time_quality is TimeQuality.TRUSTED_SYNCHRONIZED
        and reattachment.software_state_unambiguous
        and final_queue.queue_depth == 0
        and final_queue.queue_bytes == 0
        and final_queue.pending == 0
        and final_queue.in_flight == 0
        and final_queue.retryable_failure == 0
        and final_queue.terminal_failure == 0
    )
    if reattachment.storage_used_bytes >= baseline.storage_high_watermark_used_bytes:
        issues.append("R0.14: R0.8 storage boundary crossed")
    if not reattachment.network_connected:
        issues.append("R0.14: R0.10 network boundary crossed")
    if reattachment.time_quality is not TimeQuality.TRUSTED_SYNCHRONIZED:
        issues.append("R0.14: R0.11 trusted-time boundary not restored")
    if not reattachment.software_state_unambiguous:
        issues.append("R0.14: R0.12/R0.13 software state is ambiguous")
    if (
        final_queue.queue_depth != 0
        or final_queue.queue_bytes != 0
        or final_queue.pending != 0
        or final_queue.in_flight != 0
        or final_queue.retryable_failure != 0
        or final_queue.terminal_failure != 0
    ):
        issues.append("R0.14: final queue did not reconcile cleanly")

    proof_keys: dict[tuple[RecoveryProofSubject, str], EdgeR0RecoveryProofReceipt] = {}
    for proof_receipt in proofs:
        key = (proof_receipt.subject_kind, proof_receipt.subject_id)
        if key in proof_keys:
            issues.append(
                "R0.14: duplicate proof receipt for "
                f"{proof_receipt.subject_kind.value}:{proof_receipt.subject_id}"
            )
            continue
        proof_keys[key] = proof_receipt

    verifier_host = manifest.verifier.verifier_host_id
    independent_verification_complete = True

    for proof_digest in baseline.representative_proof_sha256:
        pre_receipt = proof_keys.get((RecoveryProofSubject.PRE_REBUILD, proof_digest))
        if pre_receipt is None:
            issues.append(
                f"R0.14: missing pre-rebuild proof verification: {proof_digest}"
            )
            independent_verification_complete = False
            continue
        if pre_receipt.proof_artifact_sha256 != proof_digest:
            issues.append(f"R0.14: pre-rebuild proof digest mismatch: {proof_digest}")
            independent_verification_complete = False
        if (
            not pre_receipt.inclusion_valid
            or not pre_receipt.independent_execution_context
            or verifier_host is None
            or pre_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.14: pre-rebuild proof failed independent verification: {proof_digest}"
            )
            independent_verification_complete = False

    for record_id in sorted(baseline_ids):
        final_record = recovered_by_id.get(record_id)
        if final_record is None or final_record.final_upstream_commit_count != 1:
            independent_verification_complete = False
            continue
        record_receipt = proof_keys.get(
            (RecoveryProofSubject.REATTACHED_RECORD, record_id)
        )
        if record_receipt is None:
            issues.append(f"R0.14: missing reattached-record proof receipt: {record_id}")
            independent_verification_complete = False
            continue
        if record_receipt.proof_artifact_sha256 != final_record.proof_artifact_sha256:
            issues.append(f"R0.14: reattached-record proof digest mismatch: {record_id}")
            independent_verification_complete = False
        if (
            not record_receipt.inclusion_valid
            or not record_receipt.independent_execution_context
            or verifier_host is None
            or record_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.14: reattached record failed independent verification: {record_id}"
            )
            independent_verification_complete = False

    canary_valid = True
    if canary.reattachment_id != reattachment.reattachment_id:
        issues.append("R0.14: canary references another reattachment")
        canary_valid = False
    if canary.captured_at < reattachment.reattached_at:
        issues.append("R0.14: canary predates completed reattachment")
        canary_valid = False
    if canary.identity_recovery_mode is not identity.mode:
        issues.append("R0.14: canary identity-recovery mode mismatch")
        canary_valid = False
    if canary.post_rebuild_identity_id != identity.post_device_identity_id:
        issues.append("R0.14: canary is not bound to post-rebuild identity")
        canary_valid = False
    if canary.rebuilt_build_sha != rebuild.installed_build_sha:
        issues.append("R0.14: canary is not bound to rebuilt build")
        canary_valid = False
    if canary.rebuilt_configuration_digest != rebuild.installed_configuration_digest:
        issues.append("R0.14: canary is not bound to rebuilt configuration")
        canary_valid = False
    if not canary.synchronized:
        issues.append("R0.14: post-rebuild canary did not synchronize")
        canary_valid = False
    if (
        not canary.inclusion_valid
        or not canary.independent_execution_context
        or verifier_host is None
        or canary.verifier_host_id != verifier_host
    ):
        issues.append("R0.14: post-rebuild canary did not independently verify")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase12_evaluation_id": phase12.evaluation_id,
        "baseline_id": baseline.baseline_id,
        "media_id": media.media_id,
        "rebuild_id": rebuild.rebuild_id,
        "identity_recovery_id": identity.identity_recovery_id,
        "reattachment_id": reattachment.reattachment_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        media_provenance_valid
        and rebuild_target_valid
        and rebuilt_software_valid
        and identity_recovery_valid
        and trust_posture_preserved
        and historical_evidence_preserved
        and upstream_reattachment_valid
        and checkpoints_consistent
        and no_logical_replay_or_invented_ack
        and prior_phase_boundaries_preserved
        and independent_verification_complete
        and canary_valid
        and not issues
    )
    return EdgeR0Phase13Evaluation(
        evaluation_id=f"edge-r0-phase13-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase12_evaluation_id=phase12.evaluation_id,
        baseline_id=baseline.baseline_id,
        media_id=media.media_id,
        rebuild_id=rebuild.rebuild_id,
        identity_recovery_id=identity.identity_recovery_id,
        reattachment_id=reattachment.reattachment_id,
        evaluated_at=evaluated_at,
        media_provenance_valid=media_provenance_valid,
        rebuild_target_valid=rebuild_target_valid,
        rebuilt_software_valid=rebuilt_software_valid,
        identity_recovery_valid=identity_recovery_valid,
        trust_posture_preserved=trust_posture_preserved,
        historical_evidence_preserved=historical_evidence_preserved,
        upstream_reattachment_valid=upstream_reattachment_valid,
        checkpoints_consistent=checkpoints_consistent,
        no_logical_replay_or_invented_ack=no_logical_replay_or_invented_ack,
        prior_phase_boundaries_preserved=prior_phase_boundaries_preserved,
        independent_verification_complete=independent_verification_complete,
        post_rebuild_canary_valid=canary_valid,
        r0_14_passed=passed,
        issues=tuple(issues),
    )


def load_phase12_evaluation(raw: bytes) -> EdgeR0Phase12Evaluation:
    return EdgeR0Phase12Evaluation.model_validate_json(raw)


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ETS Wave 1 Edge Compact R0 R0.14 recovery-media evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser("evaluate-r0-14")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase12-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--baseline", type=Path, required=True)
    evaluate_parser.add_argument("--media", type=Path, required=True)
    evaluate_parser.add_argument("--rebuild", type=Path, required=True)
    evaluate_parser.add_argument("--identity-recovery", type=Path, required=True)
    evaluate_parser.add_argument("--reattachment", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-14":
        result = evaluate_r0_14(
            load_manifest(args.manifest.read_bytes()),
            load_phase12_evaluation(args.phase12_evaluation.read_bytes()),
            EdgeR0RecoveryBaseline.model_validate_json(args.baseline.read_bytes()),
            EdgeR0RecoveryMedia.model_validate_json(args.media.read_bytes()),
            EdgeR0RebuildObservation.model_validate_json(args.rebuild.read_bytes()),
            EdgeR0IdentityRecoveryEvidence.model_validate_json(
                args.identity_recovery.read_bytes()
            ),
            EdgeR0RecoveryReattachment.model_validate_json(
                args.reattachment.read_bytes()
            ),
            tuple(
                EdgeR0RecoveryProofReceipt.model_validate_json(path.read_bytes())
                for path in args.proof_receipt
            ),
            EdgeR0RecoveryCanary.model_validate_json(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_14_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
