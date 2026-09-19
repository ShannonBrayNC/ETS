"""Wave 1 Edge Compact R0 recovery-media rebuild evidence.

R0.14 evaluates retained evidence created by an operator-controlled recovery-media
rebuild.  It never wipes disks, partitions media, installs software, restores keys,
or boots recovery media.
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
_CLAIM: Literal["r0_14_phase_evidence_not_a_physical_qualification_result"] = (
    "r0_14_phase_evidence_not_a_physical_qualification_result"
)
_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase13Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class IdentityRecoveryMode(StrEnum):
    RESTORE_EXISTING_IDENTITY = "restore_existing_identity"
    ROTATE_IDENTITY_WITH_BINDING = "rotate_identity_with_binding"


class RebuildProofSubject(StrEnum):
    PRE_REBUILD = "pre_rebuild"
    REATTACHED_RECORD = "reattached_record"


class EdgeR0RebuildPendingRecord(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-rebuild-pending-record.v1"] = (
        "ets.edge-compact-r0-rebuild-pending-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    local_proof_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM


class EdgeR0RebuildBaseline(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-rebuild-baseline.v1"] = (
        "ets.edge-compact-r0-rebuild-baseline.v1"
    )
    baseline_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase12_evaluation_id: str = Field(min_length=1, max_length=256)
    phase12_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    build_sha: str = Field(min_length=7, max_length=128)
    artifact_digest: str = Field(pattern=_SHA256_RE)
    configuration_digest: str = Field(pattern=_SHA256_RE)
    runtime_version: str = Field(min_length=1, max_length=128)
    data_schema_version: str = Field(min_length=1, max_length=128)
    device_identity_id: str = Field(min_length=1, max_length=256)
    signing_key_id: str = Field(min_length=1, max_length=256)
    identity_material_commitment_sha256: str = Field(pattern=_SHA256_RE)
    identity_profile: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    secure_boot_verified: Literal[False] = False
    hardware_key_protection: Literal[False] = False
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
    pending_records: tuple[EdgeR0RebuildPendingRecord, ...] = Field(min_length=1)
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "rebuild-baseline timestamp")

    @model_validator(mode="after")
    def validate_baseline(self) -> EdgeR0RebuildBaseline:
        if self.storage_used_bytes >= self.storage_high_watermark_used_bytes:
            raise ValueError("R0.14 baseline exceeds the R0.8 storage boundary")
        ids = [record.record_id for record in self.pending_records]
        events = [record.event_id for record in self.pending_records]
        keys = [record.idempotency_key for record in self.pending_records]
        if len(ids) != len(set(ids)):
            raise ValueError("rebuild pending record IDs must be unique")
        if len(events) != len(set(events)):
            raise ValueError("rebuild pending event IDs must be unique")
        if len(keys) != len(set(keys)):
            raise ValueError("rebuild pending idempotency keys must be unique")
        if len(self.representative_proof_sha256) != len(
            set(self.representative_proof_sha256)
        ):
            raise ValueError("representative proof digests must be unique")
        return self


class EdgeR0RecoveryMedia(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-recovery-media.v1"] = (
        "ets.edge-compact-r0-recovery-media.v1"
    )
    media_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    prepared_at: datetime
    source_provenance_sha256: str = Field(pattern=_SHA256_RE)
    image_build_sha: str = Field(min_length=7, max_length=128)
    image_artifact_digest: str = Field(pattern=_SHA256_RE)
    image_digest: str = Field(pattern=_SHA256_RE)
    configuration_template_digest: str = Field(pattern=_SHA256_RE)
    expected_runtime_version: str = Field(min_length=1, max_length=128)
    expected_data_schema_version: str = Field(min_length=1, max_length=128)
    independently_verified: Literal[True] = True
    verification_receipt_sha256: str = Field(pattern=_SHA256_RE)
    operator_approved: Literal[True] = True
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM

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
    target_device_id: str = Field(min_length=1, max_length=256)
    target_matches_manifest: bool
    media_image_digest: str = Field(pattern=_SHA256_RE)
    media_boot_receipt_sha256: str = Field(pattern=_SHA256_RE)
    filesystem_creation_receipt_sha256: str = Field(pattern=_SHA256_RE)
    installed_build_sha: str = Field(min_length=7, max_length=128)
    installed_artifact_digest: str = Field(pattern=_SHA256_RE)
    installed_configuration_digest: str = Field(pattern=_SHA256_RE)
    installed_runtime_version: str = Field(min_length=1, max_length=128)
    installed_data_schema_version: str = Field(min_length=1, max_length=128)
    resulting_boot_id: str = Field(min_length=1, max_length=128)
    service_healthy: bool
    independently_observed: bool
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    operator_abort_available: Literal[True] = True
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "rebuild-observation timestamp")

    @model_validator(mode="after")
    def validate_duration(self) -> EdgeR0RebuildObservation:
        if self.completed_at <= self.started_at:
            raise ValueError("rebuild observation must have positive duration")
        return self


class EdgeR0IdentityRecovery(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-identity-recovery.v1"] = (
        "ets.edge-compact-r0-identity-recovery.v1"
    )
    identity_recovery_id: str = Field(min_length=1, max_length=256)
    rebuild_id: str = Field(min_length=1, max_length=256)
    mode: IdentityRecoveryMode
    prior_device_identity_id: str = Field(min_length=1, max_length=256)
    prior_signing_key_id: str = Field(min_length=1, max_length=256)
    resulting_device_identity_id: str = Field(min_length=1, max_length=256)
    resulting_signing_key_id: str = Field(min_length=1, max_length=256)
    recovery_material_commitment_sha256: str | None = Field(
        default=None, pattern=_SHA256_RE
    )
    continuity_receipt_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    old_to_new_binding_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    upstream_enrollment_updated: bool
    historical_identity_attribution_preserved: bool
    identity_profile: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    secure_boot_verified: Literal[False] = False
    hardware_key_protection: Literal[False] = False
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM

    @model_validator(mode="after")
    def validate_mode_shape(self) -> EdgeR0IdentityRecovery:
        same_identity = (
            self.prior_device_identity_id == self.resulting_device_identity_id
            and self.prior_signing_key_id == self.resulting_signing_key_id
        )
        if self.mode is IdentityRecoveryMode.RESTORE_EXISTING_IDENTITY:
            if not same_identity:
                raise ValueError("restore mode requires the prior identity and key")
            if self.recovery_material_commitment_sha256 is None:
                raise ValueError("restore mode requires recovery-material commitment")
            if self.continuity_receipt_sha256 is None:
                raise ValueError("restore mode requires continuity receipt")
            if self.old_to_new_binding_sha256 is not None:
                raise ValueError("restore mode cannot carry an old-to-new binding")
            if self.upstream_enrollment_updated:
                raise ValueError("restore mode cannot claim identity enrollment rotation")
        else:
            if same_identity:
                raise ValueError("rotation mode requires a new identity and signing key")
            if self.old_to_new_binding_sha256 is None:
                raise ValueError("rotation mode requires an old-to-new binding")
            if not self.upstream_enrollment_updated:
                raise ValueError("rotation mode requires explicit enrollment update")
        return self


class EdgeR0ReattachedRecord(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-reattached-record.v1"] = (
        "ets.edge-compact-r0-reattached-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    authoritative_local_present: bool
    final_upstream_commit_count: int = Field(ge=0, le=32)
    final_upstream_event_id: str | None = Field(default=None, max_length=256)
    final_proof_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    invented_upstream_acknowledgement: bool
    observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM

    @model_validator(mode="after")
    def validate_commit_shape(self) -> EdgeR0ReattachedRecord:
        if self.final_upstream_commit_count > 0:
            if self.final_upstream_event_id is None or self.final_proof_sha256 is None:
                raise ValueError("committed reattached record requires event and proof")
        elif self.final_upstream_event_id is not None or self.final_proof_sha256 is not None:
            raise ValueError("zero commits cannot carry final event/proof")
        return self


class EdgeR0Reattachment(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-reattachment.v1"] = (
        "ets.edge-compact-r0-reattachment.v1"
    )
    reattachment_id: str = Field(min_length=1, max_length=256)
    rebuild_id: str = Field(min_length=1, max_length=256)
    completed_at: datetime
    historical_record_commitment_sha256: str = Field(pattern=_SHA256_RE)
    pre_rebuild_log_head_observed: bool
    pre_rebuild_log_head_sha256: str = Field(pattern=_SHA256_RE)
    local_history_restored: bool
    local_history_limitation: str | None = Field(default=None, max_length=512)
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
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM

    @field_validator("completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "reattachment timestamp")

    @model_validator(mode="after")
    def validate_records(self) -> EdgeR0Reattachment:
        ids = [record.record_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("reattachment record IDs must be unique")
        if not self.local_history_restored and not self.local_history_limitation:
            raise ValueError("omitted local history requires an explicit limitation")
        return self


class EdgeR0RebuildProofReceipt(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-rebuild-proof-receipt.v1"] = (
        "ets.edge-compact-r0-rebuild-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    subject_kind: RebuildProofSubject
    subject_id: str = Field(min_length=1, max_length=256)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "rebuild-proof timestamp")


class EdgeR0RebuildCanary(StrictPhase13Model):
    schema_version: Literal["ets.edge-compact-r0-rebuild-canary.v1"] = (
        "ets.edge-compact-r0-rebuild-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    rebuild_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    device_identity_id: str = Field(min_length=1, max_length=256)
    build_sha: str = Field(min_length=7, max_length=128)
    configuration_digest: str = Field(pattern=_SHA256_RE)
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    synchronized: bool
    verified_at: datetime
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.14 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0RebuildCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("rebuild canary request SHA-256 must match content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("rebuild canary verification cannot precede capture")
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
    evaluated_at: datetime
    recovery_media_valid: bool
    rebuild_observed: bool
    identity_recovery_valid: bool
    trust_posture_preserved: bool
    historical_evidence_preserved: bool
    checkpoints_non_regressing: bool
    upstream_reattachment_valid: bool
    prior_phase_boundaries_preserved: bool
    independent_verification_complete: bool
    post_rebuild_canary_valid: bool
    r0_14_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _DISPOSITION
    claim_boundary: Literal[
        "r0_14_phase_evidence_not_a_physical_qualification_result"
    ] = _CLAIM

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.14 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase13Evaluation:
        expected = (
            self.recovery_media_valid
            and self.rebuild_observed
            and self.identity_recovery_valid
            and self.trust_posture_preserved
            and self.historical_evidence_preserved
            and self.checkpoints_non_regressing
            and self.upstream_reattachment_valid
            and self.prior_phase_boundaries_preserved
            and self.independent_verification_complete
            and self.post_rebuild_canary_valid
            and not self.issues
        )
        if self.r0_14_passed != expected:
            raise ValueError("r0_14_passed must match component results and issues")
        return self


def evaluate_r0_14(
    manifest: EdgeCompactR0BenchManifest,
    phase12: EdgeR0Phase12Evaluation,
    baseline: EdgeR0RebuildBaseline,
    media: EdgeR0RecoveryMedia,
    rebuild: EdgeR0RebuildObservation,
    identity: EdgeR0IdentityRecovery,
    reattachment: EdgeR0Reattachment,
    proofs: tuple[EdgeR0RebuildProofReceipt, ...],
    canary: EdgeR0RebuildCanary,
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

    recovery_media_valid = media.baseline_id == baseline.baseline_id
    if not recovery_media_valid:
        issues.append("R0.14: recovery media references another baseline")
    media_fields = (
        (rebuild.media_image_digest, media.image_digest, "image digest"),
        (rebuild.installed_build_sha, media.image_build_sha, "build"),
        (rebuild.installed_artifact_digest, media.image_artifact_digest, "artifact"),
        (
            rebuild.installed_configuration_digest,
            media.configuration_template_digest,
            "configuration",
        ),
        (
            rebuild.installed_runtime_version,
            media.expected_runtime_version,
            "runtime version",
        ),
        (
            rebuild.installed_data_schema_version,
            media.expected_data_schema_version,
            "data schema",
        ),
    )
    for observed, expected, label in media_fields:
        if observed != expected:
            issues.append(f"R0.14: recovery-media {label} mismatch")
            recovery_media_valid = False

    rebuild_observed = True
    if rebuild.baseline_id != baseline.baseline_id or rebuild.media_id != media.media_id:
        issues.append("R0.14: rebuild observation binding mismatch")
        rebuild_observed = False
    if rebuild.started_at < media.prepared_at:
        issues.append("R0.14: rebuild began before recovery media was prepared")
        rebuild_observed = False
    if not rebuild.target_matches_manifest:
        issues.append("R0.14: recovery targeted an unverified device")
        rebuild_observed = False
    if not rebuild.independently_observed:
        issues.append("R0.14: rebuild was not independently observed")
        rebuild_observed = False
    if not rebuild.service_healthy:
        issues.append("R0.14: rebuilt service is not healthy")
        rebuild_observed = False

    identity_recovery_valid = True
    if identity.rebuild_id != rebuild.rebuild_id:
        issues.append("R0.14: identity recovery references another rebuild")
        identity_recovery_valid = False
    if identity.prior_device_identity_id != baseline.device_identity_id:
        issues.append("R0.14: prior device identity binding mismatch")
        identity_recovery_valid = False
    if identity.prior_signing_key_id != baseline.signing_key_id:
        issues.append("R0.14: prior signing-key binding mismatch")
        identity_recovery_valid = False
    if identity.mode is IdentityRecoveryMode.RESTORE_EXISTING_IDENTITY:
        if (
            identity.recovery_material_commitment_sha256
            != baseline.identity_material_commitment_sha256
        ):
            issues.append("R0.14: identity recovery-material commitment mismatch")
            identity_recovery_valid = False
    elif not identity.historical_identity_attribution_preserved:
        issues.append("R0.14: identity rotation lost historical attribution")
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
    historical_evidence_preserved = True
    if (
        reattachment.historical_record_commitment_sha256
        != baseline.historical_record_commitment_sha256
    ):
        issues.append("R0.14: historical record commitment changed")
        historical_evidence_preserved = False
    if not reattachment.pre_rebuild_log_head_observed:
        issues.append("R0.14: pre-rebuild log head was not observed")
        historical_evidence_preserved = False
    if reattachment.pre_rebuild_log_head_sha256 != baseline.log_head_sha256:
        issues.append("R0.14: pre-rebuild log-head digest changed")
        historical_evidence_preserved = False

    checkpoints_non_regressing = (
        reattachment.local_checkpoint_index >= baseline.local_checkpoint_index
        and reattachment.upstream_checkpoint_index >= baseline.upstream_checkpoint_index
    )
    if reattachment.local_checkpoint_index < baseline.local_checkpoint_index:
        issues.append("R0.14: local checkpoint regressed")
    if reattachment.upstream_checkpoint_index < baseline.upstream_checkpoint_index:
        issues.append("R0.14: upstream checkpoint regressed")

    pending = {record.record_id: record for record in baseline.pending_records}
    recovered = {record.record_id: record for record in reattachment.records}
    missing = sorted(set(pending) - set(recovered))
    unknown = sorted(set(recovered) - set(pending))
    upstream_reattachment_valid = not missing and not unknown
    if missing:
        issues.append(f"R0.14: pending records missing after rebuild: {missing}")
    if unknown:
        issues.append(f"R0.14: unknown records appeared after rebuild: {unknown}")
    for record_id in sorted(set(pending) & set(recovered)):
        before, after = pending[record_id], recovered[record_id]
        if not after.authoritative_local_present:
            issues.append(f"R0.14: authoritative record disappeared: {record_id}")
            upstream_reattachment_valid = False
        if after.event_id != before.event_id or after.idempotency_key != before.idempotency_key:
            issues.append(f"R0.14: record identity changed during reattachment: {record_id}")
            upstream_reattachment_valid = False
        if (
            after.final_upstream_commit_count != 1
            or after.final_upstream_event_id != before.event_id
        ):
            issues.append(f"R0.14: record did not reconcile exactly once: {record_id}")
            upstream_reattachment_valid = False
        if after.invented_upstream_acknowledgement:
            issues.append(f"R0.14: invented upstream acknowledgement: {record_id}")
            upstream_reattachment_valid = False

    queue = reattachment.final_queue_state
    prior_phase_boundaries_preserved = (
        reattachment.storage_used_bytes < baseline.storage_high_watermark_used_bytes
        and reattachment.network_connected
        and reattachment.time_quality is TimeQuality.TRUSTED_SYNCHRONIZED
        and reattachment.software_state_unambiguous
        and queue.queue_depth == 0
        and queue.queue_bytes == 0
        and queue.pending == 0
        and queue.in_flight == 0
        and queue.retryable_failure == 0
        and queue.terminal_failure == 0
    )
    if not prior_phase_boundaries_preserved:
        issues.append("R0.14: one or more prior-phase guardrails were not restored")

    proof_map: dict[tuple[RebuildProofSubject, str], EdgeR0RebuildProofReceipt] = {}
    for proof in proofs:
        key = (proof.subject_kind, proof.subject_id)
        if key in proof_map:
            issues.append(f"R0.14: duplicate proof receipt: {proof.subject_id}")
        proof_map[key] = proof
    verifier_host = manifest.verifier.verifier_host_id
    independent_verification_complete = True
    for digest in baseline.representative_proof_sha256:
        receipt = proof_map.get((RebuildProofSubject.PRE_REBUILD, digest))
        if receipt is None:
            issues.append(f"R0.14: missing pre-rebuild proof verification: {digest}")
            independent_verification_complete = False
        elif (
            receipt.proof_artifact_sha256 != digest
            or not receipt.inclusion_valid
            or not receipt.independent_execution_context
            or verifier_host is None
            or receipt.verifier_host_id != verifier_host
        ):
            issues.append(f"R0.14: pre-rebuild proof failed verification: {digest}")
            independent_verification_complete = False
    for record_id, record in recovered.items():
        receipt = proof_map.get((RebuildProofSubject.REATTACHED_RECORD, record_id))
        if receipt is None:
            issues.append(f"R0.14: missing reattached-record proof: {record_id}")
            independent_verification_complete = False
        elif (
            receipt.proof_artifact_sha256 != record.final_proof_sha256
            or not receipt.inclusion_valid
            or not receipt.independent_execution_context
            or verifier_host is None
            or receipt.verifier_host_id != verifier_host
        ):
            issues.append(f"R0.14: reattached record failed verification: {record_id}")
            independent_verification_complete = False

    canary_valid = True
    if canary.rebuild_id != rebuild.rebuild_id or canary.captured_at < reattachment.completed_at:
        issues.append("R0.14: post-rebuild canary binding or ordering is invalid")
        canary_valid = False
    if canary.device_identity_id != identity.resulting_device_identity_id:
        issues.append("R0.14: canary is bound to the wrong recovered identity")
        canary_valid = False
    if canary.build_sha != rebuild.installed_build_sha:
        issues.append("R0.14: canary is bound to the wrong recovered build")
        canary_valid = False
    if canary.configuration_digest != rebuild.installed_configuration_digest:
        issues.append("R0.14: canary is bound to the wrong recovered configuration")
        canary_valid = False
    if (
        not canary.synchronized
        or not canary.inclusion_valid
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
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        recovery_media_valid
        and rebuild_observed
        and identity_recovery_valid
        and trust_posture_preserved
        and historical_evidence_preserved
        and checkpoints_non_regressing
        and upstream_reattachment_valid
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
        evaluated_at=evaluated_at,
        recovery_media_valid=recovery_media_valid,
        rebuild_observed=rebuild_observed,
        identity_recovery_valid=identity_recovery_valid,
        trust_posture_preserved=trust_posture_preserved,
        historical_evidence_preserved=historical_evidence_preserved,
        checkpoints_non_regressing=checkpoints_non_regressing,
        upstream_reattachment_valid=upstream_reattachment_valid,
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
    evaluate_parser.add_argument("--recovery-media", type=Path, required=True)
    evaluate_parser.add_argument("--rebuild", type=Path, required=True)
    evaluate_parser.add_argument("--identity-recovery", type=Path, required=True)
    evaluate_parser.add_argument("--reattachment", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    result = evaluate_r0_14(
        load_manifest(args.manifest.read_bytes()),
        load_phase12_evaluation(args.phase12_evaluation.read_bytes()),
        EdgeR0RebuildBaseline.model_validate_json(args.baseline.read_bytes()),
        EdgeR0RecoveryMedia.model_validate_json(args.recovery_media.read_bytes()),
        EdgeR0RebuildObservation.model_validate_json(args.rebuild.read_bytes()),
        EdgeR0IdentityRecovery.model_validate_json(args.identity_recovery.read_bytes()),
        EdgeR0Reattachment.model_validate_json(args.reattachment.read_bytes()),
        tuple(
            EdgeR0RebuildProofReceipt.model_validate_json(path.read_bytes())
            for path in args.proof_receipt
        ),
        EdgeR0RebuildCanary.model_validate_json(args.canary.read_bytes()),
        evaluated_at=(
            _parse_datetime(args.evaluated_at)
            if args.evaluated_at is not None
            else datetime.now(UTC)
        ),
    )
    _write_json(args.output, result)
    return 0 if result.r0_14_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
