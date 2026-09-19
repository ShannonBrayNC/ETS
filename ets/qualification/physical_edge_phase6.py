"""Wave 1 Edge Compact R0 synchronization hard-power interruption evidence.

R0.7 evaluates a physical power interruption during synchronization of records that
were already authoritatively committed locally. The module records/evaluates retained
evidence only. It never actuates power control and cannot publish a qualification claim.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.qualification.physical_edge import (
    BenchControlKind,
    EdgeCompactR0BenchManifest,
    load_manifest,
    readiness_issues,
)
from ets.qualification.physical_edge_phase3 import EdgeSyncStatusEvidence
from ets.qualification.physical_edge_phase5 import EdgeR0Phase5Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE6_CLAIM_BOUNDARY: Literal[
    "r0_7_phase_evidence_not_a_physical_qualification_result"
] = "r0_7_phase_evidence_not_a_physical_qualification_result"
_PHASE6_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase6Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class EdgeR0PendingSyncRecord(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-pending-sync-record.v1"] = (
        "ets.edge-compact-r0-pending-sync-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    local_record_sha256: str = Field(pattern=_SHA256_RE)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    idempotency_key: str = Field(min_length=1, max_length=256)
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY


class EdgeR0PreSyncSet(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-pre-sync-set.v1"] = (
        "ets.edge-compact-r0-pre-sync-set.v1"
    )
    set_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase5_evaluation_id: str = Field(min_length=1, max_length=256)
    phase5_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    boot_id: str = Field(min_length=36, max_length=36)
    device_id: str = Field(min_length=1, max_length=256)
    signing_public_key_id: str = Field(min_length=1, max_length=256)
    signing_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_key_fingerprint_sha256: str = Field(pattern=_SHA256_RE)
    key_custody: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    queue_state: EdgeSyncStatusEvidence
    records: tuple[EdgeR0PendingSyncRecord, ...] = Field(min_length=1)
    source_commitment_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "pre-sync timestamp")

    @field_validator("boot_id")
    @classmethod
    def validate_boot_id(cls, value: str) -> str:
        return _canonical_boot_id(value)

    @model_validator(mode="after")
    def validate_pending_set(self) -> EdgeR0PreSyncSet:
        record_ids = [record.record_id for record in self.records]
        event_ids = [record.event_id for record in self.records]
        idempotency_keys = [record.idempotency_key for record in self.records]
        sequences = [record.sequence_number for record in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("pending record IDs must be unique")
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("pending event IDs must be unique")
        if len(idempotency_keys) != len(set(idempotency_keys)):
            raise ValueError("pending idempotency keys must be unique")
        if sequences != list(range(1, len(self.records) + 1)):
            raise ValueError("pending sequence numbers must be contiguous and ordered")
        if self.queue_state.queue_depth != len(self.records):
            raise ValueError("pre-sync queue depth must equal the bounded pending set size")
        if self.queue_state.pending != len(self.records):
            raise ValueError("pre-sync pending count must equal the bounded pending set size")
        if self.queue_state.in_flight != 0:
            raise ValueError("pre-sync set must be captured before synchronization starts")
        if self.queue_state.retryable_failure != 0:
            raise ValueError("pre-sync set cannot begin with retryable failures")
        if self.queue_state.terminal_failure != 0:
            raise ValueError("pre-sync set cannot begin with terminal failures")
        return self


class EdgeR0SyncAttemptState(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-sync-attempt-state.v1"] = (
        "ets.edge-compact-r0-sync-attempt-state.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    transport_attempt_count: int = Field(ge=0)
    upstream_accepted_before_cut: bool
    upstream_acceptance_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    local_ack_applied_before_cut: bool
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_attempt_state(self) -> EdgeR0SyncAttemptState:
        if self.upstream_accepted_before_cut:
            if self.transport_attempt_count < 1:
                raise ValueError("upstream acceptance requires at least one transport attempt")
            if self.upstream_acceptance_sha256 is None:
                raise ValueError("upstream acceptance requires a retained acceptance receipt")
        elif self.upstream_acceptance_sha256 is not None:
            raise ValueError("unaccepted record cannot carry an upstream acceptance receipt")

        if self.local_ack_applied_before_cut and not self.upstream_accepted_before_cut:
            raise ValueError("local acknowledgement cannot precede upstream acceptance")
        return self


class EdgeR0ActiveSyncWindow(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-active-sync-window.v1"] = (
        "ets.edge-compact-r0-active-sync-window.v1"
    )
    window_id: str = Field(min_length=1, max_length=256)
    pre_sync_set_id: str = Field(min_length=1, max_length=256)
    pre_sync_set_sha256: str = Field(pattern=_SHA256_RE)
    sync_run_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    cut_boundary_at: datetime
    synchronization_active_confirmed: Literal[True] = True
    ingestion_active: Literal[False] = False
    controller_timeline_sha256: str = Field(pattern=_SHA256_RE)
    attempts: tuple[EdgeR0SyncAttemptState, ...] = Field(min_length=1)
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY

    @field_validator("started_at", "cut_boundary_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "active-sync timestamp")

    @model_validator(mode="after")
    def validate_window(self) -> EdgeR0ActiveSyncWindow:
        if self.cut_boundary_at <= self.started_at:
            raise ValueError("cut boundary must follow synchronization start")
        record_ids = [attempt.record_id for attempt in self.attempts]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("active-sync record IDs must be unique")
        return self


class EdgeR0SyncPowerObservation(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-sync-power-interruption.v1"] = (
        "ets.edge-compact-r0-sync-power-interruption.v1"
    )
    observation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    window_sha256: str = Field(pattern=_SHA256_RE)
    power_control_id: str = Field(min_length=1, max_length=256)
    observer_id: str = Field(min_length=1, max_length=256)
    controller_id: str = Field(min_length=1, max_length=256)
    cut_commanded_at: datetime
    power_loss_observed_at: datetime
    restore_commanded_at: datetime
    power_restored_observed_at: datetime
    operator_approved: Literal[True] = True
    active_sync_confirmed: Literal[True] = True
    dut_unreachable_during_interruption: Literal[True] = True
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    observer_loss_receipt_sha256: str = Field(pattern=_SHA256_RE)
    observer_restore_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY

    @field_validator(
        "cut_commanded_at",
        "power_loss_observed_at",
        "restore_commanded_at",
        "power_restored_observed_at",
    )
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "sync-power timestamp")

    @model_validator(mode="after")
    def require_order(self) -> EdgeR0SyncPowerObservation:
        timeline = (
            self.cut_commanded_at,
            self.power_loss_observed_at,
            self.restore_commanded_at,
            self.power_restored_observed_at,
        )
        if tuple(sorted(timeline)) != timeline:
            raise ValueError("power interruption timestamps must be monotonic")
        return self


class EdgeR0RecoveredSyncRecord(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-recovered-sync-record.v1"] = (
        "ets.edge-compact-r0-recovered-sync-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    authoritative_local_present: bool
    transport_attempt_count: int = Field(ge=0)
    final_upstream_commit_count: int = Field(ge=0, le=32)
    final_upstream_event_id: str | None = Field(default=None, max_length=256)
    final_upstream_acceptance_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    final_proof_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    local_marked_synchronized: bool
    recovery_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_final_commit_shape(self) -> EdgeR0RecoveredSyncRecord:
        commit_fields = (
            self.final_upstream_event_id,
            self.final_upstream_acceptance_sha256,
            self.final_proof_sha256,
        )
        if self.final_upstream_commit_count > 0:
            if any(value is None for value in commit_fields):
                raise ValueError("upstream commit requires event, acceptance and proof fields")
        elif any(value is not None for value in commit_fields):
            raise ValueError("zero upstream commits cannot carry final commit fields")
        return self


class EdgeR0SyncRecoveryReconciliation(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-sync-recovery.v1"] = (
        "ets.edge-compact-r0-sync-recovery.v1"
    )
    reconciliation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    pre_sync_set_id: str = Field(min_length=1, max_length=256)
    power_observation_id: str = Field(min_length=1, max_length=256)
    recovered_at: datetime
    boot_id: str = Field(min_length=36, max_length=36)
    device_id: str = Field(min_length=1, max_length=256)
    signing_public_key_id: str = Field(min_length=1, max_length=256)
    signing_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_key_fingerprint_sha256: str = Field(pattern=_SHA256_RE)
    key_custody: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    final_queue_state: EdgeSyncStatusEvidence
    resumed_sync_run_ids: tuple[str, ...] = Field(min_length=1)
    records: tuple[EdgeR0RecoveredSyncRecord, ...] = Field(min_length=1)
    reconciliation_commitment_sha256: str = Field(pattern=_SHA256_RE)
    filesystem_recovery_clean: bool
    recovery_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY

    @field_validator("recovered_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "sync-recovery timestamp")

    @field_validator("boot_id")
    @classmethod
    def validate_boot_id(cls, value: str) -> str:
        return _canonical_boot_id(value)

    @model_validator(mode="after")
    def validate_recovery(self) -> EdgeR0SyncRecoveryReconciliation:
        if len(self.resumed_sync_run_ids) != len(set(self.resumed_sync_run_ids)):
            raise ValueError("resumed synchronization run IDs must be unique")
        record_ids = [record.record_id for record in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("recovered synchronization record IDs must be unique")
        return self


class EdgeR0SyncProofReceipt(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-sync-proof-receipt.v1"] = (
        "ets.edge-compact-r0-sync-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    record_id: str = Field(min_length=1, max_length=256)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "sync-proof verification timestamp")


class EdgeR0SyncRecoveryCanary(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-sync-recovery-canary.v1"] = (
        "ets.edge-compact-r0-sync-recovery-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    reconciliation_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    final_upstream_commit_count: int = Field(ge=0, le=32)
    upstream_acceptance_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    local_marked_synchronized: bool
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.7 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0SyncRecoveryCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("canary request SHA-256 must match Edge content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("canary verification cannot precede capture")
        if self.final_upstream_commit_count > 0 and self.upstream_acceptance_sha256 is None:
            raise ValueError("committed canary requires an upstream acceptance receipt")
        if self.final_upstream_commit_count == 0 and self.upstream_acceptance_sha256 is not None:
            raise ValueError("uncommitted canary cannot carry an upstream acceptance receipt")
        return self


class EdgeR0Phase6Evaluation(StrictPhase6Model):
    schema_version: Literal["ets.edge-compact-r0-phase6-evaluation.v1"] = (
        "ets.edge-compact-r0-phase6-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase5_evaluation_id: str = Field(min_length=1, max_length=256)
    pre_sync_set_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    power_observation_id: str = Field(min_length=1, max_length=256)
    reconciliation_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    intended_record_count: int = Field(ge=0)
    final_upstream_record_count: int = Field(ge=0)
    independently_verified_record_count: int = Field(ge=0)
    local_set_preserved: bool
    exactly_once_logical_reconciliation: bool
    local_acknowledgements_supported: bool
    checkpoints_non_regressing: bool
    reconciliation_commitment_valid: bool
    final_backlog_clear: bool
    identity_preserved: bool
    post_recovery_canary_valid: bool
    r0_7_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE6_DISPOSITION
    claim_boundary: Literal[
        "r0_7_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE6_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.7 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase6Evaluation:
        expected = (
            self.local_set_preserved
            and self.exactly_once_logical_reconciliation
            and self.local_acknowledgements_supported
            and self.checkpoints_non_regressing
            and self.reconciliation_commitment_valid
            and self.final_backlog_clear
            and self.identity_preserved
            and self.post_recovery_canary_valid
            and not self.issues
        )
        if self.r0_7_passed != expected:
            raise ValueError("r0_7_passed must match the component results and issues")
        return self


def build_reconciliation_commitment(
    records: tuple[EdgeR0RecoveredSyncRecord, ...],
) -> str:
    ordered = sorted(records, key=lambda record: record.record_id)
    value = [
        {
            "record_id": record.record_id,
            "event_id": record.event_id,
            "idempotency_key": record.idempotency_key,
            "authoritative_local_present": record.authoritative_local_present,
            "final_upstream_commit_count": record.final_upstream_commit_count,
            "final_upstream_event_id": record.final_upstream_event_id,
            "final_upstream_acceptance_sha256": (
                record.final_upstream_acceptance_sha256
            ),
            "final_proof_sha256": record.final_proof_sha256,
            "local_marked_synchronized": record.local_marked_synchronized,
        }
        for record in ordered
    ]
    return canonical_sha256(value)


def load_phase5_evaluation(raw: bytes) -> EdgeR0Phase5Evaluation:
    return EdgeR0Phase5Evaluation.model_validate_json(raw)


def load_pre_sync_set(raw: bytes) -> EdgeR0PreSyncSet:
    return EdgeR0PreSyncSet.model_validate_json(raw)


def load_sync_window(raw: bytes) -> EdgeR0ActiveSyncWindow:
    return EdgeR0ActiveSyncWindow.model_validate_json(raw)


def load_power_observation(raw: bytes) -> EdgeR0SyncPowerObservation:
    return EdgeR0SyncPowerObservation.model_validate_json(raw)


def load_reconciliation(raw: bytes) -> EdgeR0SyncRecoveryReconciliation:
    return EdgeR0SyncRecoveryReconciliation.model_validate_json(raw)


def load_sync_proof(raw: bytes) -> EdgeR0SyncProofReceipt:
    return EdgeR0SyncProofReceipt.model_validate_json(raw)


def load_recovery_canary(raw: bytes) -> EdgeR0SyncRecoveryCanary:
    return EdgeR0SyncRecoveryCanary.model_validate_json(raw)


def evaluate_r0_7(
    manifest: EdgeCompactR0BenchManifest,
    phase5: EdgeR0Phase5Evaluation,
    pre_sync: EdgeR0PreSyncSet,
    window: EdgeR0ActiveSyncWindow,
    power: EdgeR0SyncPowerObservation,
    recovery: EdgeR0SyncRecoveryReconciliation,
    proofs: tuple[EdgeR0SyncProofReceipt, ...],
    canary: EdgeR0SyncRecoveryCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase6Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.7: bench manifest not ready: {blocker}")
    if not phase5.r0_6_passed:
        issues.append("R0.7: R0.6 did not pass")
    if phase5.manifest_id != manifest.manifest_id or phase5.asset_id != asset_id:
        issues.append("R0.7: R0.6 evaluation is bound to another DUT")

    if pre_sync.manifest_id != manifest.manifest_id or pre_sync.asset_id != asset_id:
        issues.append("R0.7: pre-sync set is bound to another DUT")
    if pre_sync.phase5_evaluation_id != phase5.evaluation_id:
        issues.append("R0.7: pre-sync set references another R0.6 evaluation")
    if pre_sync.phase5_evaluation_sha256 != canonical_sha256(
        phase5.model_dump(mode="json")
    ):
        issues.append("R0.7: R0.6 digest binding mismatch")

    if window.pre_sync_set_id != pre_sync.set_id:
        issues.append("R0.7: active-sync window references another pre-sync set")
    if window.pre_sync_set_sha256 != canonical_sha256(pre_sync.model_dump(mode="json")):
        issues.append("R0.7: pre-sync set digest mismatch")
    if window.started_at < pre_sync.captured_at:
        issues.append("R0.7: active synchronization predates the retained pre-sync set")

    intended_by_id = {record.record_id: record for record in pre_sync.records}
    attempt_by_id = {attempt.record_id: attempt for attempt in window.attempts}
    intended_ids = set(intended_by_id)
    attempt_ids = set(attempt_by_id)
    if attempt_ids != intended_ids:
        missing = sorted(intended_ids - attempt_ids)
        unknown = sorted(attempt_ids - intended_ids)
        if missing:
            issues.append(f"R0.7: active-sync window is missing records: {missing}")
        if unknown:
            issues.append(f"R0.7: active-sync window contains unknown records: {unknown}")
    for record_id in sorted(intended_ids & attempt_ids):
        intended = intended_by_id[record_id]
        attempt = attempt_by_id[record_id]
        if attempt.idempotency_key != intended.idempotency_key:
            issues.append(f"R0.7: idempotency-key mismatch for {record_id}")

    power_control = next(
        (control for control in manifest.controls if control.kind is BenchControlKind.POWER),
        None,
    )
    if power_control is None or power.power_control_id != power_control.control_id:
        issues.append("R0.7: power observation does not bind to the W1-1 power control")
    if power.observer_id != manifest.observer.observer_id:
        issues.append("R0.7: power observer does not match bench observer")
    if power.manifest_id != manifest.manifest_id or power.asset_id != asset_id:
        issues.append("R0.7: power observation is bound to another DUT")
    if power.window_id != window.window_id:
        issues.append("R0.7: power observation references another sync window")
    if power.window_sha256 != canonical_sha256(window.model_dump(mode="json")):
        issues.append("R0.7: active-sync window digest mismatch")
    if power.cut_commanded_at != window.cut_boundary_at:
        issues.append("R0.7: independent cut time does not match retained sync boundary")

    if recovery.manifest_id != manifest.manifest_id or recovery.asset_id != asset_id:
        issues.append("R0.7: recovery reconciliation is bound to another DUT")
    if recovery.pre_sync_set_id != pre_sync.set_id:
        issues.append("R0.7: recovery references another pre-sync set")
    if recovery.power_observation_id != power.observation_id:
        issues.append("R0.7: recovery references another power observation")
    if recovery.recovered_at < power.power_restored_observed_at:
        issues.append("R0.7: recovery predates observed power restoration")
    if recovery.boot_id == pre_sync.boot_id:
        issues.append("R0.7: Linux boot ID did not change after hard-power recovery")
    if not recovery.filesystem_recovery_clean:
        issues.append("R0.7: filesystem recovery check was not clean")

    identity_fields = (
        "device_id",
        "signing_public_key_id",
        "signing_public_key_hex",
        "public_key_fingerprint_sha256",
        "key_custody",
        "hardware_attested",
    )
    identity_preserved = all(
        getattr(pre_sync, field) == getattr(recovery, field)
        for field in identity_fields
    )
    if not identity_preserved:
        issues.append("R0.7: software-backed device identity changed across power loss")

    recovered_by_id = {record.record_id: record for record in recovery.records}
    recovered_ids = set(recovered_by_id)
    missing_recovered = sorted(intended_ids - recovered_ids)
    unknown_recovered = sorted(recovered_ids - intended_ids)
    if missing_recovered:
        issues.append(f"R0.7: recovered set is missing records: {missing_recovered}")
    if unknown_recovered:
        issues.append(f"R0.7: recovered set contains unknown records: {unknown_recovered}")

    local_set_preserved = not missing_recovered and not unknown_recovered
    exactly_once = local_set_preserved
    local_acks_supported = local_set_preserved
    final_upstream_count = 0

    for record_id in sorted(intended_ids & recovered_ids):
        intended = intended_by_id[record_id]
        recovered = recovered_by_id[record_id]
        if not recovered.authoritative_local_present:
            issues.append(f"R0.7: authoritative local record disappeared: {record_id}")
            local_set_preserved = False
        if recovered.event_id != intended.event_id:
            issues.append(f"R0.7: recovered event binding changed for {record_id}")
            local_set_preserved = False
        if recovered.idempotency_key != intended.idempotency_key:
            issues.append(f"R0.7: recovered idempotency key changed for {record_id}")
            local_set_preserved = False

        if recovered.final_upstream_commit_count != 1:
            issues.append(
                "R0.7: expected exactly one logical upstream commit for "
                f"{record_id}, observed {recovered.final_upstream_commit_count}"
            )
            exactly_once = False
        else:
            final_upstream_count += 1

        if recovered.final_upstream_event_id != intended.event_id:
            issues.append(f"R0.7: final upstream event binding mismatch for {record_id}")
            exactly_once = False

        if recovered.local_marked_synchronized:
            if (
                recovered.final_upstream_commit_count != 1
                or recovered.final_upstream_acceptance_sha256 is None
            ):
                issues.append(
                    "R0.7: local synchronized state lacks upstream acceptance evidence "
                    f"for {record_id}"
                )
                local_acks_supported = False
        else:
            issues.append(f"R0.7: record did not reach synchronized state: {record_id}")
            local_acks_supported = False

    checkpoints_non_regressing = (
        recovery.local_checkpoint_index >= pre_sync.local_checkpoint_index
        and recovery.upstream_checkpoint_index >= pre_sync.upstream_checkpoint_index
    )
    if recovery.local_checkpoint_index < pre_sync.local_checkpoint_index:
        issues.append("R0.7: local checkpoint regressed after recovery")
    if recovery.upstream_checkpoint_index < pre_sync.upstream_checkpoint_index:
        issues.append("R0.7: upstream checkpoint regressed after recovery")

    expected_reconciliation = build_reconciliation_commitment(recovery.records)
    reconciliation_commitment_valid = (
        recovery.reconciliation_commitment_sha256 == expected_reconciliation
    )
    if not reconciliation_commitment_valid:
        issues.append("R0.7: final reconciliation commitment does not match recovered set")

    queue = recovery.final_queue_state
    final_backlog_clear = (
        queue.queue_depth == 0
        and queue.queue_bytes == 0
        and queue.pending == 0
        and queue.in_flight == 0
        and queue.retryable_failure == 0
        and queue.terminal_failure == 0
        and queue.upstream_status == "online"
        and queue.synchronized
        >= pre_sync.queue_state.synchronized + len(pre_sync.records)
    )
    if not final_backlog_clear:
        issues.append("R0.7: final synchronization backlog/checkpoint state is not clean")

    proofs_by_record: dict[str, EdgeR0SyncProofReceipt] = {}
    for proof_receipt in proofs:
        if proof_receipt.record_id in proofs_by_record:
            issues.append(
                f"R0.7: duplicate independent proof receipt for {proof_receipt.record_id}"
            )
            continue
        proofs_by_record[proof_receipt.record_id] = proof_receipt

    unknown_proofs = sorted(set(proofs_by_record) - intended_ids)
    if unknown_proofs:
        issues.append(f"R0.7: proof receipts reference unknown records: {unknown_proofs}")

    verifier_host = manifest.verifier.verifier_host_id
    independently_verified = 0
    for record_id in sorted(intended_ids):
        recovered_record = recovered_by_id.get(record_id)
        verification_receipt = proofs_by_record.get(record_id)
        if (
            recovered_record is None
            or recovered_record.final_upstream_commit_count != 1
        ):
            continue
        if verification_receipt is None:
            issues.append(f"R0.7: missing independent proof receipt for {record_id}")
            continue
        if (
            verification_receipt.proof_artifact_sha256
            != recovered_record.final_proof_sha256
        ):
            issues.append(f"R0.7: final proof digest mismatch for {record_id}")
        if not verification_receipt.inclusion_valid:
            issues.append(f"R0.7: proof inclusion verification failed for {record_id}")
        if not verification_receipt.independent_execution_context:
            issues.append(f"R0.7: proof was not independently verified for {record_id}")
        if (
            verifier_host is None
            or verification_receipt.verifier_host_id != verifier_host
        ):
            issues.append(f"R0.7: verifier host mismatch for {record_id}")
        if (
            verification_receipt.proof_artifact_sha256
            == recovered_record.final_proof_sha256
            and verification_receipt.inclusion_valid
            and verification_receipt.independent_execution_context
            and verification_receipt.verifier_host_id == verifier_host
        ):
            independently_verified += 1

    canary_valid = True
    if canary.reconciliation_id != recovery.reconciliation_id:
        issues.append("R0.7: post-recovery canary references another reconciliation")
        canary_valid = False
    if canary.captured_at < recovery.recovered_at:
        issues.append("R0.7: post-recovery canary predates reconciliation")
        canary_valid = False
    if canary.final_upstream_commit_count != 1:
        issues.append("R0.7: post-recovery canary did not commit exactly once upstream")
        canary_valid = False
    if not canary.local_marked_synchronized:
        issues.append("R0.7: post-recovery canary was not locally marked synchronized")
        canary_valid = False
    if canary.upstream_acceptance_sha256 is None:
        issues.append("R0.7: post-recovery canary lacks upstream acceptance evidence")
        canary_valid = False
    if not canary.inclusion_valid or not canary.independent_execution_context:
        issues.append("R0.7: post-recovery canary did not verify independently")
        canary_valid = False
    if verifier_host is None or canary.verifier_host_id != verifier_host:
        issues.append("R0.7: canary verifier host does not match bench binding")
        canary_valid = False

    if independently_verified != len(pre_sync.records):
        issues.append("R0.7: not every intended record independently verified")

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase5_evaluation_id": phase5.evaluation_id,
        "pre_sync_set_id": pre_sync.set_id,
        "window_id": window.window_id,
        "power_observation_id": power.observation_id,
        "reconciliation_id": recovery.reconciliation_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        local_set_preserved
        and exactly_once
        and local_acks_supported
        and checkpoints_non_regressing
        and reconciliation_commitment_valid
        and final_backlog_clear
        and identity_preserved
        and canary_valid
        and independently_verified == len(pre_sync.records)
        and not issues
    )
    return EdgeR0Phase6Evaluation(
        evaluation_id=f"edge-r0-phase6-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase5_evaluation_id=phase5.evaluation_id,
        pre_sync_set_id=pre_sync.set_id,
        window_id=window.window_id,
        power_observation_id=power.observation_id,
        reconciliation_id=recovery.reconciliation_id,
        evaluated_at=evaluated_at,
        intended_record_count=len(pre_sync.records),
        final_upstream_record_count=final_upstream_count,
        independently_verified_record_count=independently_verified,
        local_set_preserved=local_set_preserved,
        exactly_once_logical_reconciliation=exactly_once,
        local_acknowledgements_supported=local_acks_supported,
        checkpoints_non_regressing=checkpoints_non_regressing,
        reconciliation_commitment_valid=reconciliation_commitment_valid,
        final_backlog_clear=final_backlog_clear,
        identity_preserved=identity_preserved,
        post_recovery_canary_valid=canary_valid,
        r0_7_passed=passed,
        issues=tuple(issues),
    )


def _require_timezone(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone offset")
    return value.astimezone(UTC)


def _canonical_boot_id(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise ValueError("boot_id must be a canonical UUID") from exc


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
        description="ETS Wave 1 Edge Compact R0 R0.7 synchronization power-loss evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser("evaluate-r0-7")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase5-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--pre-sync-set", type=Path, required=True)
    evaluate_parser.add_argument("--sync-window", type=Path, required=True)
    evaluate_parser.add_argument("--power-observation", type=Path, required=True)
    evaluate_parser.add_argument("--reconciliation", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-7":
        result = evaluate_r0_7(
            load_manifest(args.manifest.read_bytes()),
            load_phase5_evaluation(args.phase5_evaluation.read_bytes()),
            load_pre_sync_set(args.pre_sync_set.read_bytes()),
            load_sync_window(args.sync_window.read_bytes()),
            load_power_observation(args.power_observation.read_bytes()),
            load_reconciliation(args.reconciliation.read_bytes()),
            tuple(load_sync_proof(path.read_bytes()) for path in args.proof_receipt),
            load_recovery_canary(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_7_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
