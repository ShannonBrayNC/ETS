"""Wave 1 Edge Compact R0 failed-upgrade and rollback evidence.

R0.13 evaluates containment of one bounded failed upgrade and recovery to one
unambiguous supported build while preserving identity, evidence, pending-state
semantics and prior qualification boundaries. The evaluator never installs or rolls
back software.
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
from ets.qualification.physical_edge_phase11 import EdgeR0Phase11Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE12_CLAIM_BOUNDARY: Literal[
    "r0_13_phase_evidence_not_a_physical_qualification_result"
] = "r0_13_phase_evidence_not_a_physical_qualification_result"
_PHASE12_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase12Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class UpgradeFailureStage(StrEnum):
    PACKAGE_VALIDATION = "package_validation"
    PRE_MIGRATION = "pre_migration"
    MIGRATION = "migration"
    SERVICE_START = "service_start"
    POST_INSTALL_VALIDATION = "post_install_validation"


class MigrationFailureState(StrEnum):
    NOT_STARTED = "not_started"
    PARTIAL = "partial"
    COMPLETED = "completed"


class RecoveryMode(StrEnum):
    ROLLBACK_SOURCE = "rollback_source"
    APPROVED_RECOVERY_BUILD = "approved_recovery_build"


class RollbackProofSubject(StrEnum):
    PRE_FAILURE = "pre_failure"
    PENDING_RECORD = "pending_record"


class EdgeR0RollbackPendingRecord(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-rollback-pending-record.v1"] = (
        "ets.edge-compact-r0-rollback-pending-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    local_proof_sha256: str = Field(pattern=_SHA256_RE)
    local_authoritative: Literal[True] = True
    synchronized_before_failure: bool
    upstream_acceptance_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_sync_state(self) -> EdgeR0RollbackPendingRecord:
        if self.synchronized_before_failure:
            if self.upstream_acceptance_sha256 is None:
                raise ValueError("synchronized record requires upstream acceptance")
        elif self.upstream_acceptance_sha256 is not None:
            raise ValueError("pending record cannot carry upstream acceptance")
        return self


class EdgeR0RollbackBaseline(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-rollback-baseline.v1"] = (
        "ets.edge-compact-r0-rollback-baseline.v1"
    )
    baseline_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase11_evaluation_id: str = Field(min_length=1, max_length=256)
    phase11_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    source_build_sha: str = Field(min_length=7, max_length=128)
    source_artifact_digest: str = Field(pattern=_SHA256_RE)
    source_configuration_digest: str = Field(pattern=_SHA256_RE)
    source_version: str = Field(min_length=1, max_length=128)
    source_data_schema_version: str = Field(min_length=1, max_length=128)
    device_identity_id: str = Field(min_length=1, max_length=256)
    signing_key_id: str = Field(min_length=1, max_length=256)
    hardware_attested: Literal[False] = False
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
    pending_records: tuple[EdgeR0RollbackPendingRecord, ...] = Field(min_length=1)
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "rollback-baseline timestamp")

    @model_validator(mode="after")
    def validate_baseline(self) -> EdgeR0RollbackBaseline:
        if self.storage_used_bytes >= self.storage_high_watermark_used_bytes:
            raise ValueError("R0.13 baseline exceeds the R0.8 storage boundary")
        ids = [record.record_id for record in self.pending_records]
        events = [record.event_id for record in self.pending_records]
        idem = [record.idempotency_key for record in self.pending_records]
        if len(ids) != len(set(ids)):
            raise ValueError("rollback pending record IDs must be unique")
        if len(events) != len(set(events)):
            raise ValueError("rollback pending event IDs must be unique")
        if len(idem) != len(set(idem)):
            raise ValueError("rollback pending idempotency keys must be unique")
        pending_count = sum(
            not record.synchronized_before_failure for record in self.pending_records
        )
        if self.queue_state.pending < pending_count:
            raise ValueError("queue pending count cannot understate pending records")
        return self


class EdgeR0FailedUpgradeTarget(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-failed-upgrade-target.v1"] = (
        "ets.edge-compact-r0-failed-upgrade-target.v1"
    )
    target_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    prepared_at: datetime
    attempted_build_sha: str = Field(min_length=7, max_length=128)
    attempted_artifact_digest: str = Field(pattern=_SHA256_RE)
    attempted_configuration_digest: str = Field(pattern=_SHA256_RE)
    attempted_version: str = Field(min_length=1, max_length=128)
    attempted_data_schema_version: str = Field(min_length=1, max_length=128)
    package_digest: str = Field(pattern=_SHA256_RE)
    migration_plan_sha256: str = Field(pattern=_SHA256_RE)
    expected_failure_stage: UpgradeFailureStage
    package_verified: Literal[True] = True
    operator_approved: Literal[True] = True
    independent_package_verification_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @field_validator("prepared_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "failed-target timestamp")


class EdgeR0RecoveryPlan(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-recovery-plan.v1"] = (
        "ets.edge-compact-r0-recovery-plan.v1"
    )
    recovery_plan_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=256)
    prepared_at: datetime
    recovery_mode: RecoveryMode
    recovery_build_sha: str = Field(min_length=7, max_length=128)
    recovery_artifact_digest: str = Field(pattern=_SHA256_RE)
    recovery_configuration_digest: str = Field(pattern=_SHA256_RE)
    recovery_version: str = Field(min_length=1, max_length=128)
    recovery_data_schema_version: str = Field(min_length=1, max_length=128)
    recovery_package_digest: str = Field(pattern=_SHA256_RE)
    recovery_plan_sha256: str = Field(pattern=_SHA256_RE)
    independently_verified: Literal[True] = True
    operator_approved: Literal[True] = True
    verification_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @field_validator("prepared_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "recovery-plan timestamp")


class EdgeR0UpgradeFailureObservation(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-upgrade-failure.v1"] = (
        "ets.edge-compact-r0-upgrade-failure.v1"
    )
    failure_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    failed_at: datetime
    observed_failure_stage: UpgradeFailureStage
    process_exit_code: int
    migration_state: MigrationFailureState
    target_success_claimed: bool
    service_healthy_at_failure: bool
    observed_build_sha: str | None = Field(default=None, min_length=7, max_length=128)
    observed_data_schema_version: str | None = Field(default=None, max_length=128)
    installer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    controller_failure_receipt_sha256: str = Field(pattern=_SHA256_RE)
    independent_failure_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @field_validator("started_at", "failed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "upgrade-failure timestamp")

    @model_validator(mode="after")
    def validate_failure(self) -> EdgeR0UpgradeFailureObservation:
        if self.failed_at <= self.started_at:
            raise ValueError("failed upgrade must have positive duration")
        if self.process_exit_code == 0:
            raise ValueError("failed upgrade must retain a nonzero exit code")
        return self


class EdgeR0RollbackExecution(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-rollback-execution.v1"] = (
        "ets.edge-compact-r0-rollback-execution.v1"
    )
    rollback_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    failure_id: str = Field(min_length=1, max_length=256)
    recovery_plan_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    rollback_receipt_sha256: str = Field(pattern=_SHA256_RE)
    migration_recovery_success: bool
    migration_recovery_receipt_sha256: str = Field(pattern=_SHA256_RE)
    final_service_healthy: bool
    final_build_independently_identified: bool
    mixed_version_inventory_detected: bool
    final_build_sha: str = Field(min_length=7, max_length=128)
    final_artifact_digest: str = Field(pattern=_SHA256_RE)
    final_configuration_digest: str = Field(pattern=_SHA256_RE)
    final_version: str = Field(min_length=1, max_length=128)
    final_data_schema_version: str = Field(min_length=1, max_length=128)
    device_identity_id: str = Field(min_length=1, max_length=256)
    signing_key_id: str = Field(min_length=1, max_length=256)
    hardware_attested: Literal[False] = False
    preserved_historical_record_commitment_sha256: str = Field(pattern=_SHA256_RE)
    pre_failure_log_head_observed: bool
    pre_failure_log_head_sha256: str = Field(pattern=_SHA256_RE)
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    final_queue_state: EdgeSyncStatusEvidence
    storage_used_bytes: int = Field(ge=0)
    network_connected: bool
    time_quality: TimeQuality
    final_boot_id: str = Field(min_length=1, max_length=128)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "rollback-execution timestamp")

    @model_validator(mode="after")
    def validate_execution(self) -> EdgeR0RollbackExecution:
        if self.completed_at <= self.started_at:
            raise ValueError("rollback execution must have positive duration")
        return self


class EdgeR0RollbackRecoveredRecord(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-rollback-recovered-record.v1"] = (
        "ets.edge-compact-r0-rollback-recovered-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    authoritative_local_present: bool
    final_upstream_commit_count: int = Field(ge=0, le=32)
    final_upstream_event_id: str | None = Field(default=None, max_length=256)
    final_upstream_acceptance_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    final_proof_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    local_marked_synchronized: bool
    false_sync_ack_observed_during_failure: bool
    recovery_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_commit_shape(self) -> EdgeR0RollbackRecoveredRecord:
        fields = (
            self.final_upstream_event_id,
            self.final_upstream_acceptance_sha256,
            self.final_proof_sha256,
        )
        if self.final_upstream_commit_count > 0:
            if any(value is None for value in fields):
                raise ValueError("rollback record with commit requires event/acceptance/proof")
        elif any(value is not None for value in fields):
            raise ValueError("zero rollback commits cannot carry final commit fields")
        if self.local_marked_synchronized and self.final_upstream_commit_count != 1:
            raise ValueError("local synchronized state requires one final upstream commit")
        return self


class EdgeR0RollbackReconciliation(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-rollback-reconciliation.v1"] = (
        "ets.edge-compact-r0-rollback-reconciliation.v1"
    )
    reconciliation_id: str = Field(min_length=1, max_length=256)
    rollback_id: str = Field(min_length=1, max_length=256)
    reconciled_at: datetime
    records: tuple[EdgeR0RollbackRecoveredRecord, ...] = Field(min_length=1)
    reconciliation_commitment_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @field_validator("reconciled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "rollback-reconciliation timestamp")

    @model_validator(mode="after")
    def validate_records(self) -> EdgeR0RollbackReconciliation:
        ids = [record.record_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("rollback reconciliation record IDs must be unique")
        return self


class EdgeR0RollbackProofReceipt(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-rollback-proof-receipt.v1"] = (
        "ets.edge-compact-r0-rollback-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    subject_kind: RollbackProofSubject
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
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "rollback-proof timestamp")


class EdgeR0RollbackCanary(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-rollback-canary.v1"] = (
        "ets.edge-compact-r0-rollback-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    rollback_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    recovery_build_sha: str = Field(min_length=7, max_length=128)
    recovery_configuration_digest: str = Field(pattern=_SHA256_RE)
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.13 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0RollbackCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("rollback canary request SHA-256 must match content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("rollback canary verification cannot precede capture")
        return self


class EdgeR0Phase12Evaluation(StrictPhase12Model):
    schema_version: Literal["ets.edge-compact-r0-phase12-evaluation.v1"] = (
        "ets.edge-compact-r0-phase12-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase11_evaluation_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=256)
    failure_id: str = Field(min_length=1, max_length=256)
    rollback_id: str = Field(min_length=1, max_length=256)
    reconciliation_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    failure_observed: bool
    no_false_target_success: bool
    recovery_build_valid: bool
    identity_continuity_preserved: bool
    trust_posture_preserved: bool
    historical_evidence_preserved: bool
    pending_state_reconciled: bool
    checkpoints_non_regressing: bool
    no_ambiguous_half_upgrade: bool
    prior_phase_boundaries_preserved: bool
    independent_verification_complete: bool
    post_recovery_canary_valid: bool
    r0_13_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE12_DISPOSITION
    claim_boundary: Literal[
        "r0_13_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE12_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.13 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase12Evaluation:
        expected = (
            self.failure_observed
            and self.no_false_target_success
            and self.recovery_build_valid
            and self.identity_continuity_preserved
            and self.trust_posture_preserved
            and self.historical_evidence_preserved
            and self.pending_state_reconciled
            and self.checkpoints_non_regressing
            and self.no_ambiguous_half_upgrade
            and self.prior_phase_boundaries_preserved
            and self.independent_verification_complete
            and self.post_recovery_canary_valid
            and not self.issues
        )
        if self.r0_13_passed != expected:
            raise ValueError("r0_13_passed must match component results and issues")
        return self


def build_rollback_reconciliation_commitment(
    records: tuple[EdgeR0RollbackRecoveredRecord, ...],
) -> str:
    value = [
        {
            "record_id": record.record_id,
            "event_id": record.event_id,
            "idempotency_key": record.idempotency_key,
            "authoritative_local_present": record.authoritative_local_present,
            "final_upstream_commit_count": record.final_upstream_commit_count,
            "final_upstream_event_id": record.final_upstream_event_id,
            "final_upstream_acceptance_sha256": record.final_upstream_acceptance_sha256,
            "final_proof_sha256": record.final_proof_sha256,
            "local_marked_synchronized": record.local_marked_synchronized,
            "false_sync_ack_observed_during_failure": (
                record.false_sync_ack_observed_during_failure
            ),
        }
        for record in sorted(records, key=lambda item: item.record_id)
    ]
    return canonical_sha256(value)


def evaluate_r0_13(
    manifest: EdgeCompactR0BenchManifest,
    phase11: EdgeR0Phase11Evaluation,
    baseline: EdgeR0RollbackBaseline,
    target: EdgeR0FailedUpgradeTarget,
    recovery_plan: EdgeR0RecoveryPlan,
    failure: EdgeR0UpgradeFailureObservation,
    rollback: EdgeR0RollbackExecution,
    reconciliation: EdgeR0RollbackReconciliation,
    proofs: tuple[EdgeR0RollbackProofReceipt, ...],
    canary: EdgeR0RollbackCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase12Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.13: bench manifest not ready: {blocker}")
    if not phase11.r0_12_passed:
        issues.append("R0.13: R0.12 did not pass")
    if phase11.manifest_id != manifest.manifest_id or phase11.asset_id != asset_id:
        issues.append("R0.13: R0.12 evaluation is bound to another DUT")

    if baseline.manifest_id != manifest.manifest_id or baseline.asset_id != asset_id:
        issues.append("R0.13: baseline is bound to another DUT")
    if baseline.phase11_evaluation_id != phase11.evaluation_id:
        issues.append("R0.13: baseline references another R0.12 evaluation")
    if baseline.phase11_evaluation_sha256 != canonical_sha256(
        phase11.model_dump(mode="json")
    ):
        issues.append("R0.13: R0.12 digest binding mismatch")

    if target.baseline_id != baseline.baseline_id:
        issues.append("R0.13: failed target references another baseline")
    if recovery_plan.baseline_id != baseline.baseline_id:
        issues.append("R0.13: recovery plan references another baseline")
    if recovery_plan.target_id != target.target_id:
        issues.append("R0.13: recovery plan references another failed target")
    if target.attempted_build_sha == baseline.source_build_sha:
        issues.append("R0.13: failed target build equals source build")

    failure_observed = True
    if failure.baseline_id != baseline.baseline_id:
        issues.append("R0.13: failure observation references another baseline")
        failure_observed = False
    if failure.target_id != target.target_id:
        issues.append("R0.13: failure observation references another target")
        failure_observed = False
    if failure.started_at < target.prepared_at:
        issues.append("R0.13: failed upgrade began before target preparation")
        failure_observed = False
    if failure.observed_failure_stage is not target.expected_failure_stage:
        issues.append("R0.13: observed failure stage does not match declared profile")
        failure_observed = False

    no_false_target_success = not failure.target_success_claimed
    if failure.target_success_claimed:
        issues.append("R0.13: failed target was falsely claimed successful")

    recovery_build_valid = True
    if rollback.baseline_id != baseline.baseline_id:
        issues.append("R0.13: rollback references another baseline")
        recovery_build_valid = False
    if rollback.failure_id != failure.failure_id:
        issues.append("R0.13: rollback references another failure")
        recovery_build_valid = False
    if rollback.recovery_plan_id != recovery_plan.recovery_plan_id:
        issues.append("R0.13: rollback references another recovery plan")
        recovery_build_valid = False
    if rollback.started_at < failure.failed_at:
        issues.append("R0.13: rollback began before failed upgrade was observed")
        recovery_build_valid = False

    recovery_fields = (
        (rollback.final_build_sha, recovery_plan.recovery_build_sha, "build"),
        (
            rollback.final_artifact_digest,
            recovery_plan.recovery_artifact_digest,
            "artifact digest",
        ),
        (
            rollback.final_configuration_digest,
            recovery_plan.recovery_configuration_digest,
            "configuration digest",
        ),
        (rollback.final_version, recovery_plan.recovery_version, "version"),
        (
            rollback.final_data_schema_version,
            recovery_plan.recovery_data_schema_version,
            "data schema version",
        ),
    )
    for observed, expected, label in recovery_fields:
        if observed != expected:
            issues.append(f"R0.13: final recovery {label} mismatch")
            recovery_build_valid = False

    if recovery_plan.recovery_mode is RecoveryMode.ROLLBACK_SOURCE:
        source_fields = (
            (recovery_plan.recovery_build_sha, baseline.source_build_sha, "build"),
            (
                recovery_plan.recovery_artifact_digest,
                baseline.source_artifact_digest,
                "artifact digest",
            ),
            (
                recovery_plan.recovery_configuration_digest,
                baseline.source_configuration_digest,
                "configuration digest",
            ),
            (recovery_plan.recovery_version, baseline.source_version, "version"),
            (
                recovery_plan.recovery_data_schema_version,
                baseline.source_data_schema_version,
                "data schema version",
            ),
        )
        for recovered, source, label in source_fields:
            if recovered != source:
                issues.append(f"R0.13: source rollback {label} mismatch")
                recovery_build_valid = False

    if recovery_plan.recovery_build_sha == target.attempted_build_sha:
        issues.append("R0.13: recovery build must differ from failed target")
        recovery_build_valid = False
    if not rollback.migration_recovery_success:
        issues.append("R0.13: migration recovery did not succeed")
        recovery_build_valid = False
    if not rollback.final_service_healthy:
        issues.append("R0.13: recovered service is not healthy")
        recovery_build_valid = False
    if not rollback.final_build_independently_identified:
        issues.append("R0.13: final recovered build was not independently identified")
        recovery_build_valid = False

    identity_continuity_preserved = (
        rollback.device_identity_id == baseline.device_identity_id
        and rollback.signing_key_id == baseline.signing_key_id
    )
    if rollback.device_identity_id != baseline.device_identity_id:
        issues.append("R0.13: device identity changed unexpectedly")
    if rollback.signing_key_id != baseline.signing_key_id:
        issues.append("R0.13: signing key changed unexpectedly")

    trust_posture_preserved = (
        baseline.hardware_attested is False and rollback.hardware_attested is False
    )
    if not trust_posture_preserved:
        issues.append("R0.13: R0 trust posture changed unexpectedly")

    historical_evidence_preserved = True
    if (
        rollback.preserved_historical_record_commitment_sha256
        != baseline.historical_record_commitment_sha256
    ):
        issues.append("R0.13: historical record commitment changed")
        historical_evidence_preserved = False
    if not rollback.pre_failure_log_head_observed:
        issues.append("R0.13: pre-failure log head was not observed")
        historical_evidence_preserved = False
    if rollback.pre_failure_log_head_sha256 != baseline.log_head_sha256:
        issues.append("R0.13: pre-failure log-head digest changed")
        historical_evidence_preserved = False

    checkpoints_non_regressing = (
        rollback.local_checkpoint_index >= baseline.local_checkpoint_index
        and rollback.upstream_checkpoint_index >= baseline.upstream_checkpoint_index
    )
    if rollback.local_checkpoint_index < baseline.local_checkpoint_index:
        issues.append("R0.13: local checkpoint regressed")
    if rollback.upstream_checkpoint_index < baseline.upstream_checkpoint_index:
        issues.append("R0.13: upstream checkpoint regressed")

    no_ambiguous_half_upgrade = (
        not rollback.mixed_version_inventory_detected
        and rollback.final_build_independently_identified
        and rollback.final_service_healthy
        and rollback.migration_recovery_success
    )
    if rollback.mixed_version_inventory_detected:
        issues.append("R0.13: mixed-version inventory remains after rollback")
    if not no_ambiguous_half_upgrade:
        issues.append("R0.13: rollback left an ambiguous half-upgraded state")

    final_queue = rollback.final_queue_state
    prior_phase_boundaries_preserved = (
        rollback.storage_used_bytes < baseline.storage_high_watermark_used_bytes
        and rollback.network_connected
        and rollback.time_quality is TimeQuality.TRUSTED_SYNCHRONIZED
        and final_queue.queue_depth == 0
        and final_queue.queue_bytes == 0
        and final_queue.pending == 0
        and final_queue.in_flight == 0
        and final_queue.retryable_failure == 0
        and final_queue.terminal_failure == 0
    )
    if rollback.storage_used_bytes >= baseline.storage_high_watermark_used_bytes:
        issues.append("R0.13: R0.8 storage boundary crossed")
    if not rollback.network_connected:
        issues.append("R0.13: R0.10 network boundary crossed")
    if rollback.time_quality is not TimeQuality.TRUSTED_SYNCHRONIZED:
        issues.append("R0.13: R0.11 trusted-time boundary not restored")
    if (
        final_queue.queue_depth != 0
        or final_queue.queue_bytes != 0
        or final_queue.pending != 0
        or final_queue.in_flight != 0
        or final_queue.retryable_failure != 0
        or final_queue.terminal_failure != 0
    ):
        issues.append("R0.13: final queue did not reconcile cleanly")

    if reconciliation.rollback_id != rollback.rollback_id:
        issues.append("R0.13: reconciliation references another rollback")

    pending_by_id = {record.record_id: record for record in baseline.pending_records}
    recovered_by_id = {record.record_id: record for record in reconciliation.records}
    pending_ids = set(pending_by_id)
    recovered_ids = set(recovered_by_id)
    missing = sorted(pending_ids - recovered_ids)
    unknown = sorted(recovered_ids - pending_ids)
    pending_state_reconciled = not missing and not unknown
    if missing:
        issues.append(f"R0.13: pending records missing after rollback: {missing}")
    if unknown:
        issues.append(f"R0.13: unknown recovered records after rollback: {unknown}")

    for record_id in sorted(pending_ids & recovered_ids):
        before = pending_by_id[record_id]
        after = recovered_by_id[record_id]
        if not after.authoritative_local_present:
            issues.append(f"R0.13: authoritative pending record disappeared: {record_id}")
            pending_state_reconciled = False
        if after.event_id != before.event_id:
            issues.append(f"R0.13: pending event ID changed: {record_id}")
            pending_state_reconciled = False
        if after.idempotency_key != before.idempotency_key:
            issues.append(f"R0.13: pending idempotency key changed: {record_id}")
            pending_state_reconciled = False
        if after.final_upstream_commit_count != 1:
            issues.append(
                f"R0.13: expected one final logical upstream commit: {record_id}"
            )
            pending_state_reconciled = False
        if after.final_upstream_event_id != before.event_id:
            issues.append(f"R0.13: final upstream event mismatch: {record_id}")
            pending_state_reconciled = False
        if not after.local_marked_synchronized:
            issues.append(f"R0.13: record not locally synchronized: {record_id}")
            pending_state_reconciled = False
        if after.false_sync_ack_observed_during_failure:
            issues.append(f"R0.13: false sync acknowledgement observed: {record_id}")
            pending_state_reconciled = False

    expected_commitment = build_rollback_reconciliation_commitment(
        reconciliation.records
    )
    if reconciliation.reconciliation_commitment_sha256 != expected_commitment:
        issues.append("R0.13: rollback reconciliation commitment mismatch")
        pending_state_reconciled = False

    proof_keys: dict[tuple[RollbackProofSubject, str], EdgeR0RollbackProofReceipt] = {}
    for proof_receipt in proofs:
        key = (proof_receipt.subject_kind, proof_receipt.subject_id)
        if key in proof_keys:
            issues.append(
                "R0.13: duplicate proof receipt for "
                f"{proof_receipt.subject_kind.value}:{proof_receipt.subject_id}"
            )
            continue
        proof_keys[key] = proof_receipt

    verifier_host = manifest.verifier.verifier_host_id
    independent_verification_complete = True

    for proof_digest in baseline.representative_proof_sha256:
        pre_receipt = proof_keys.get((RollbackProofSubject.PRE_FAILURE, proof_digest))
        if pre_receipt is None:
            issues.append(
                f"R0.13: missing pre-failure proof verification: {proof_digest}"
            )
            independent_verification_complete = False
            continue
        if pre_receipt.proof_artifact_sha256 != proof_digest:
            issues.append(
                f"R0.13: pre-failure proof digest mismatch: {proof_digest}"
            )
            independent_verification_complete = False
        if (
            not pre_receipt.inclusion_valid
            or not pre_receipt.independent_execution_context
            or verifier_host is None
            or pre_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.13: pre-failure proof failed independent verification: {proof_digest}"
            )
            independent_verification_complete = False

    for record_id in sorted(pending_ids):
        final_record = recovered_by_id.get(record_id)
        if final_record is None or final_record.final_upstream_commit_count != 1:
            independent_verification_complete = False
            continue
        record_receipt = proof_keys.get(
            (RollbackProofSubject.PENDING_RECORD, record_id)
        )
        if record_receipt is None:
            issues.append(f"R0.13: missing pending-record proof receipt: {record_id}")
            independent_verification_complete = False
            continue
        if record_receipt.proof_artifact_sha256 != final_record.final_proof_sha256:
            issues.append(f"R0.13: pending-record proof digest mismatch: {record_id}")
            independent_verification_complete = False
        if (
            not record_receipt.inclusion_valid
            or not record_receipt.independent_execution_context
            or verifier_host is None
            or record_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.13: pending record failed independent verification: {record_id}"
            )
            independent_verification_complete = False

    canary_valid = True
    if canary.rollback_id != rollback.rollback_id:
        issues.append("R0.13: canary references another rollback")
        canary_valid = False
    if canary.captured_at < rollback.completed_at:
        issues.append("R0.13: canary predates completed rollback")
        canary_valid = False
    if canary.recovery_build_sha != recovery_plan.recovery_build_sha:
        issues.append("R0.13: canary is not bound to recovered build")
        canary_valid = False
    if (
        canary.recovery_configuration_digest
        != recovery_plan.recovery_configuration_digest
    ):
        issues.append("R0.13: canary is not bound to recovered configuration")
        canary_valid = False
    if (
        not canary.inclusion_valid
        or not canary.independent_execution_context
        or verifier_host is None
        or canary.verifier_host_id != verifier_host
    ):
        issues.append("R0.13: post-recovery canary did not independently verify")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase11_evaluation_id": phase11.evaluation_id,
        "baseline_id": baseline.baseline_id,
        "target_id": target.target_id,
        "failure_id": failure.failure_id,
        "rollback_id": rollback.rollback_id,
        "reconciliation_id": reconciliation.reconciliation_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        failure_observed
        and no_false_target_success
        and recovery_build_valid
        and identity_continuity_preserved
        and trust_posture_preserved
        and historical_evidence_preserved
        and pending_state_reconciled
        and checkpoints_non_regressing
        and no_ambiguous_half_upgrade
        and prior_phase_boundaries_preserved
        and independent_verification_complete
        and canary_valid
        and not issues
    )
    return EdgeR0Phase12Evaluation(
        evaluation_id=f"edge-r0-phase12-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase11_evaluation_id=phase11.evaluation_id,
        baseline_id=baseline.baseline_id,
        target_id=target.target_id,
        failure_id=failure.failure_id,
        rollback_id=rollback.rollback_id,
        reconciliation_id=reconciliation.reconciliation_id,
        evaluated_at=evaluated_at,
        failure_observed=failure_observed,
        no_false_target_success=no_false_target_success,
        recovery_build_valid=recovery_build_valid,
        identity_continuity_preserved=identity_continuity_preserved,
        trust_posture_preserved=trust_posture_preserved,
        historical_evidence_preserved=historical_evidence_preserved,
        pending_state_reconciled=pending_state_reconciled,
        checkpoints_non_regressing=checkpoints_non_regressing,
        no_ambiguous_half_upgrade=no_ambiguous_half_upgrade,
        prior_phase_boundaries_preserved=prior_phase_boundaries_preserved,
        independent_verification_complete=independent_verification_complete,
        post_recovery_canary_valid=canary_valid,
        r0_13_passed=passed,
        issues=tuple(issues),
    )


def load_phase11_evaluation(raw: bytes) -> EdgeR0Phase11Evaluation:
    return EdgeR0Phase11Evaluation.model_validate_json(raw)


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
        description="ETS Wave 1 Edge Compact R0 R0.13 failed-upgrade evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser("evaluate-r0-13")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase11-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--baseline", type=Path, required=True)
    evaluate_parser.add_argument("--failed-target", type=Path, required=True)
    evaluate_parser.add_argument("--recovery-plan", type=Path, required=True)
    evaluate_parser.add_argument("--failure", type=Path, required=True)
    evaluate_parser.add_argument("--rollback", type=Path, required=True)
    evaluate_parser.add_argument("--reconciliation", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-13":
        result = evaluate_r0_13(
            load_manifest(args.manifest.read_bytes()),
            load_phase11_evaluation(args.phase11_evaluation.read_bytes()),
            EdgeR0RollbackBaseline.model_validate_json(args.baseline.read_bytes()),
            EdgeR0FailedUpgradeTarget.model_validate_json(
                args.failed_target.read_bytes()
            ),
            EdgeR0RecoveryPlan.model_validate_json(args.recovery_plan.read_bytes()),
            EdgeR0UpgradeFailureObservation.model_validate_json(
                args.failure.read_bytes()
            ),
            EdgeR0RollbackExecution.model_validate_json(args.rollback.read_bytes()),
            EdgeR0RollbackReconciliation.model_validate_json(
                args.reconciliation.read_bytes()
            ),
            tuple(
                EdgeR0RollbackProofReceipt.model_validate_json(path.read_bytes())
                for path in args.proof_receipt
            ),
            EdgeR0RollbackCanary.model_validate_json(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_13_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
