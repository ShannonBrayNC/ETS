"""Wave 1 Edge Compact R0 bounded queue-saturation evidence.

R0.9 evaluates logical queue item/byte limits, explicit backpressure, accepted-record
preservation and recovery while storage remains healthy. The evaluator never generates
load or mutates queue limits and cannot publish a hardware qualification claim.
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
from ets.qualification.physical_edge_phase7 import EdgeR0Phase7Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE8_CLAIM_BOUNDARY: Literal[
    "r0_9_phase_evidence_not_a_physical_qualification_result"
] = "r0_9_phase_evidence_not_a_physical_qualification_result"
_PHASE8_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase8Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class QueueAttemptDisposition(StrEnum):
    AUTHORITATIVELY_ACCEPTED = "authoritatively_accepted"
    REJECTED_BACKPRESSURE = "rejected_backpressure"
    NON_AUTHORITATIVE_UNACKNOWLEDGED = "non_authoritative_unacknowledged"


class QueueProofSubject(StrEnum):
    PRE_SATURATION = "pre_saturation"
    SATURATION_ATTEMPT = "saturation_attempt"


class EdgeR0QueueBaseline(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-queue-baseline.v1"] = (
        "ets.edge-compact-r0-queue-baseline.v1"
    )
    baseline_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase7_evaluation_id: str = Field(min_length=1, max_length=256)
    phase7_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    max_items: int = Field(gt=0)
    max_bytes: int = Field(gt=0)
    atomic_item_allowance: int = Field(default=0, ge=0)
    atomic_byte_allowance: int = Field(default=0, ge=0)
    queue_state: EdgeSyncStatusEvidence
    storage_used_bytes: int = Field(ge=0)
    storage_high_watermark_used_bytes: int = Field(gt=0)
    storage_healthy: Literal[True] = True
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    log_head_sha256: str = Field(pattern=_SHA256_RE)
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "queue-baseline timestamp")

    @model_validator(mode="after")
    def validate_baseline(self) -> EdgeR0QueueBaseline:
        if self.queue_state.max_items != self.max_items:
            raise ValueError("queue-state max_items must match qualification limit")
        if self.queue_state.max_bytes != self.max_bytes:
            raise ValueError("queue-state max_bytes must match qualification limit")
        if self.queue_state.queue_depth > self.max_items:
            raise ValueError("baseline queue depth already exceeds qualification limit")
        if self.queue_state.queue_bytes > self.max_bytes:
            raise ValueError("baseline queue bytes already exceed qualification limit")
        if self.storage_used_bytes >= self.storage_high_watermark_used_bytes:
            raise ValueError("R0.9 must begin below the storage high watermark")
        if len(self.representative_proof_sha256) != len(
            set(self.representative_proof_sha256)
        ):
            raise ValueError("representative proof digests must be unique")
        return self


class EdgeR0QueueWorkloadDefinition(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-queue-workload.v1"] = (
        "ets.edge-compact-r0-queue-workload.v1"
    )
    workload_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    generated_at: datetime
    request_count: int = Field(gt=0)
    total_payload_bytes: int = Field(gt=0)
    max_duration_seconds: int = Field(gt=0)
    deterministic_seed_sha256: str = Field(pattern=_SHA256_RE)
    generator_definition_sha256: str = Field(pattern=_SHA256_RE)
    operator_stop_condition: str = Field(min_length=1, max_length=1024)
    controller_start_receipt_sha256: str = Field(pattern=_SHA256_RE)
    controller_stop_receipt_sha256: str = Field(pattern=_SHA256_RE)
    unbounded_generation_forbidden: Literal[True] = True
    claim_boundary: Literal[
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @field_validator("generated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "queue-workload timestamp")


class EdgeR0QueueSample(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-queue-sample.v1"] = (
        "ets.edge-compact-r0-queue-sample.v1"
    )
    sample_id: str = Field(min_length=1, max_length=256)
    workload_id: str = Field(min_length=1, max_length=256)
    sample_index: int = Field(ge=0)
    observed_at: datetime
    queue_depth: int = Field(ge=0)
    queue_bytes: int = Field(ge=0)
    pending: int = Field(ge=0)
    in_flight: int = Field(ge=0)
    retryable_failure: int = Field(ge=0)
    terminal_failure: int = Field(ge=0)
    storage_used_bytes: int = Field(ge=0)
    rss_bytes: int = Field(ge=0)
    backpressure_active: bool
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "queue-sample timestamp")


class EdgeR0QueueAttempt(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-queue-attempt.v1"] = (
        "ets.edge-compact-r0-queue-attempt.v1"
    )
    attempt_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    attempted_at: datetime
    payload_bytes: int = Field(gt=0)
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    response_artifact_sha256: str = Field(pattern=_SHA256_RE)
    disposition: QueueAttemptDisposition
    event_id: str | None = Field(default=None, max_length=256)
    content_hash: str | None = Field(default=None, pattern=_SHA256_RE)
    proof_artifact_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    backpressure_signal: str | None = Field(default=None, max_length=256)
    retry_after_seconds: int | None = Field(default=None, ge=0)
    claim_boundary: Literal[
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @field_validator("attempted_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "queue-attempt timestamp")

    @model_validator(mode="after")
    def validate_disposition(self) -> EdgeR0QueueAttempt:
        commit_fields = (self.event_id, self.content_hash, self.proof_artifact_sha256)
        if self.disposition is QueueAttemptDisposition.AUTHORITATIVELY_ACCEPTED:
            if any(value is None for value in commit_fields):
                raise ValueError("accepted queue attempt requires event/content/proof fields")
            if self.content_hash != self.request_payload_sha256:
                raise ValueError("accepted queue request SHA-256 must match content_hash")
            if self.backpressure_signal is not None:
                raise ValueError("accepted attempt cannot also be a backpressure rejection")
        elif self.disposition is QueueAttemptDisposition.REJECTED_BACKPRESSURE:
            if any(value is not None for value in commit_fields):
                raise ValueError("rejected queue attempt cannot carry commit fields")
            if self.backpressure_signal is None:
                raise ValueError("backpressure rejection requires an explicit signal")
        elif any(value is not None for value in commit_fields):
            raise ValueError("unacknowledged queue attempt cannot carry commit fields")
        return self


class EdgeR0QueueSaturationWindow(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-queue-saturation-window.v1"] = (
        "ets.edge-compact-r0-queue-saturation-window.v1"
    )
    window_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    workload_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    samples: tuple[EdgeR0QueueSample, ...] = Field(min_length=2)
    attempts: tuple[EdgeR0QueueAttempt, ...] = Field(min_length=2)
    first_limit_sample_id: str = Field(min_length=1, max_length=256)
    first_backpressure_attempt_id: str = Field(min_length=1, max_length=256)
    controller_timeline_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "queue-window timestamp")

    @model_validator(mode="after")
    def validate_window(self) -> EdgeR0QueueSaturationWindow:
        if self.completed_at <= self.started_at:
            raise ValueError("queue saturation window must have positive duration")
        sample_ids = [sample.sample_id for sample in self.samples]
        attempt_ids = [attempt.attempt_id for attempt in self.attempts]
        sample_indexes = [sample.sample_index for sample in self.samples]
        sequences = [attempt.sequence_number for attempt in self.attempts]
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError("queue sample IDs must be unique")
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValueError("queue attempt IDs must be unique")
        if sample_indexes != list(range(len(self.samples))):
            raise ValueError("queue sample indexes must be contiguous and ordered")
        if sequences != list(range(1, len(self.attempts) + 1)):
            raise ValueError("queue attempt sequence numbers must be contiguous")
        if self.first_limit_sample_id not in set(sample_ids):
            raise ValueError("first_limit_sample_id must reference a retained sample")
        if self.first_backpressure_attempt_id not in set(attempt_ids):
            raise ValueError(
                "first_backpressure_attempt_id must reference a retained attempt"
            )
        return self


class EdgeR0QueueRecoveryRecord(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-queue-recovery-record.v1"] = (
        "ets.edge-compact-r0-queue-recovery-record.v1"
    )
    attempt_id: str = Field(min_length=1, max_length=256)
    authoritative_commit_count: int = Field(ge=0, le=32)
    recovered_event_id: str | None = Field(default=None, max_length=256)
    recovered_proof_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    recovery_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_record(self) -> EdgeR0QueueRecoveryRecord:
        if self.authoritative_commit_count > 0:
            if self.recovered_event_id is None or self.recovered_proof_sha256 is None:
                raise ValueError("recovered queue commit requires event and proof fields")
        elif self.recovered_event_id is not None or self.recovered_proof_sha256 is not None:
            raise ValueError("zero recovered queue commits cannot carry event/proof fields")
        return self


class EdgeR0QueueRecovery(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-queue-recovery.v1"] = (
        "ets.edge-compact-r0-queue-recovery.v1"
    )
    recovery_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    recovered_at: datetime
    final_queue_state: EdgeSyncStatusEvidence
    storage_used_bytes: int = Field(ge=0)
    rss_bytes: int = Field(ge=0)
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    pre_saturation_log_head_sha256: str = Field(pattern=_SHA256_RE)
    pre_saturation_log_head_observed: bool
    records: tuple[EdgeR0QueueRecoveryRecord, ...] = Field(min_length=1)
    recovery_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @field_validator("recovered_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "queue-recovery timestamp")

    @model_validator(mode="after")
    def validate_recovery(self) -> EdgeR0QueueRecovery:
        ids = [record.attempt_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("queue recovery attempt IDs must be unique")
        return self


class EdgeR0QueueProofReceipt(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-queue-proof-receipt.v1"] = (
        "ets.edge-compact-r0-queue-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    subject_kind: QueueProofSubject
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
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "queue-proof timestamp")


class EdgeR0QueueRecoveryCanary(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-queue-recovery-canary.v1"] = (
        "ets.edge-compact-r0-queue-recovery-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    recovery_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
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
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.9 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0QueueRecoveryCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("canary request SHA-256 must match content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("canary verification cannot precede capture")
        return self


class EdgeR0Phase8Evaluation(StrictPhase8Model):
    schema_version: Literal["ets.edge-compact-r0-phase8-evaluation.v1"] = (
        "ets.edge-compact-r0-phase8-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase7_evaluation_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    workload_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    recovery_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    attempted_count: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    queue_bounds_enforced: bool
    explicit_backpressure_observed: bool
    storage_boundary_not_crossed: bool
    resource_growth_bounded: bool
    attempt_reconciliation_complete: bool
    accepted_records_preserved: bool
    preexisting_evidence_preserved: bool
    history_not_rewritten: bool
    final_queue_clean: bool
    post_recovery_canary_valid: bool
    r0_9_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE8_DISPOSITION
    claim_boundary: Literal[
        "r0_9_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE8_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.9 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase8Evaluation:
        expected = (
            self.queue_bounds_enforced
            and self.explicit_backpressure_observed
            and self.storage_boundary_not_crossed
            and self.resource_growth_bounded
            and self.attempt_reconciliation_complete
            and self.accepted_records_preserved
            and self.preexisting_evidence_preserved
            and self.history_not_rewritten
            and self.final_queue_clean
            and self.post_recovery_canary_valid
            and not self.issues
        )
        if self.r0_9_passed != expected:
            raise ValueError("r0_9_passed must match component results and issues")
        return self


def evaluate_r0_9(
    manifest: EdgeCompactR0BenchManifest,
    phase7: EdgeR0Phase7Evaluation,
    baseline: EdgeR0QueueBaseline,
    workload: EdgeR0QueueWorkloadDefinition,
    window: EdgeR0QueueSaturationWindow,
    recovery: EdgeR0QueueRecovery,
    proofs: tuple[EdgeR0QueueProofReceipt, ...],
    canary: EdgeR0QueueRecoveryCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase8Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.9: bench manifest not ready: {blocker}")
    if not phase7.r0_8_passed:
        issues.append("R0.9: R0.8 did not pass")
    if phase7.manifest_id != manifest.manifest_id or phase7.asset_id != asset_id:
        issues.append("R0.9: R0.8 evaluation is bound to another DUT")

    if baseline.manifest_id != manifest.manifest_id or baseline.asset_id != asset_id:
        issues.append("R0.9: queue baseline is bound to another DUT")
    if baseline.phase7_evaluation_id != phase7.evaluation_id:
        issues.append("R0.9: queue baseline references another R0.8 evaluation")
    if baseline.phase7_evaluation_sha256 != canonical_sha256(
        phase7.model_dump(mode="json")
    ):
        issues.append("R0.9: R0.8 digest binding mismatch")
    if workload.baseline_id != baseline.baseline_id:
        issues.append("R0.9: workload references another queue baseline")
    if window.baseline_id != baseline.baseline_id:
        issues.append("R0.9: window references another queue baseline")
    if window.workload_id != workload.workload_id:
        issues.append("R0.9: window references another workload")
    if recovery.baseline_id != baseline.baseline_id:
        issues.append("R0.9: recovery references another queue baseline")
    if recovery.window_id != window.window_id:
        issues.append("R0.9: recovery references another saturation window")
    if recovery.recovered_at < window.completed_at:
        issues.append("R0.9: recovery predates saturation-window completion")

    max_items_allowed = baseline.max_items + baseline.atomic_item_allowance
    max_bytes_allowed = baseline.max_bytes + baseline.atomic_byte_allowance
    queue_bounds_enforced = True
    storage_boundary_not_crossed = True

    for sample in window.samples:
        if sample.workload_id != workload.workload_id:
            issues.append(f"R0.9: sample references another workload: {sample.sample_id}")
            queue_bounds_enforced = False
        if sample.queue_depth > max_items_allowed:
            issues.append(f"R0.9: queue item bound exceeded at {sample.sample_id}")
            queue_bounds_enforced = False
        if sample.queue_bytes > max_bytes_allowed:
            issues.append(f"R0.9: queue byte bound exceeded at {sample.sample_id}")
            queue_bounds_enforced = False
        if sample.storage_used_bytes >= baseline.storage_high_watermark_used_bytes:
            issues.append(f"R0.9: storage high watermark crossed at {sample.sample_id}")
            storage_boundary_not_crossed = False

    sample_by_id = {sample.sample_id: sample for sample in window.samples}
    limit_sample = sample_by_id[window.first_limit_sample_id]
    reached_limit = (
        limit_sample.queue_depth >= baseline.max_items
        or limit_sample.queue_bytes >= baseline.max_bytes
    )
    if not reached_limit:
        issues.append("R0.9: retained first-limit sample did not reach a configured limit")
        queue_bounds_enforced = False

    attempt_by_id = {attempt.attempt_id: attempt for attempt in window.attempts}
    first_bp = attempt_by_id[window.first_backpressure_attempt_id]
    explicit_backpressure_observed = (
        first_bp.disposition is QueueAttemptDisposition.REJECTED_BACKPRESSURE
        and first_bp.backpressure_signal is not None
    )
    if not explicit_backpressure_observed:
        issues.append("R0.9: first backpressure attempt is not an explicit rejection")

    if not any(sample.backpressure_active for sample in window.samples):
        issues.append("R0.9: queue samples never observed active backpressure")
        explicit_backpressure_observed = False

    total_attempt_bytes = sum(attempt.payload_bytes for attempt in window.attempts)
    if len(window.attempts) != workload.request_count:
        issues.append("R0.9: workload request count does not match retained attempts")
    if total_attempt_bytes != workload.total_payload_bytes:
        issues.append("R0.9: workload byte total does not match retained attempts")

    recovery_by_id = {record.attempt_id: record for record in recovery.records}
    attempt_ids = set(attempt_by_id)
    recovery_ids = set(recovery_by_id)
    missing = sorted(attempt_ids - recovery_ids)
    unknown = sorted(recovery_ids - attempt_ids)
    if missing:
        issues.append(f"R0.9: missing recovery records: {missing}")
    if unknown:
        issues.append(f"R0.9: unknown recovery records: {unknown}")
    attempt_reconciliation_complete = not missing and not unknown
    accepted_records_preserved = attempt_reconciliation_complete
    accepted_count = 0
    rejected_count = 0

    for attempt_id in sorted(attempt_ids & recovery_ids):
        attempt = attempt_by_id[attempt_id]
        recovered = recovery_by_id[attempt_id]
        if attempt.disposition is QueueAttemptDisposition.AUTHORITATIVELY_ACCEPTED:
            accepted_count += 1
            if recovered.authoritative_commit_count != 1:
                issues.append(
                    f"R0.9: accepted record not preserved exactly once: {attempt_id}"
                )
                accepted_records_preserved = False
            if recovered.recovered_event_id != attempt.event_id:
                issues.append(f"R0.9: recovered event mismatch for {attempt_id}")
                accepted_records_preserved = False
            if recovered.recovered_proof_sha256 != attempt.proof_artifact_sha256:
                issues.append(f"R0.9: recovered proof mismatch for {attempt_id}")
                accepted_records_preserved = False
        elif attempt.disposition is QueueAttemptDisposition.REJECTED_BACKPRESSURE:
            rejected_count += 1
            if recovered.authoritative_commit_count != 0:
                issues.append(
                    f"R0.9: rejected attempt later became committed: {attempt_id}"
                )
                attempt_reconciliation_complete = False
        elif recovered.authoritative_commit_count > 1:
            issues.append(
                f"R0.9: unacknowledged attempt recovered duplicate commits: {attempt_id}"
            )
            attempt_reconciliation_complete = False

    final = recovery.final_queue_state
    final_queue_clean = (
        final.queue_depth == 0
        and final.queue_bytes == 0
        and final.pending == 0
        and final.in_flight == 0
        and final.retryable_failure == 0
        and final.terminal_failure == 0
    )
    if not final_queue_clean:
        issues.append("R0.9: final queue state is not clean")

    history_not_rewritten = (
        recovery.pre_saturation_log_head_observed
        and recovery.pre_saturation_log_head_sha256 == baseline.log_head_sha256
        and recovery.local_checkpoint_index >= baseline.local_checkpoint_index
    )
    if not recovery.pre_saturation_log_head_observed:
        issues.append("R0.9: pre-saturation log head not observed after recovery")
    if recovery.pre_saturation_log_head_sha256 != baseline.log_head_sha256:
        issues.append("R0.9: pre-saturation log-head digest changed")
    if recovery.local_checkpoint_index < baseline.local_checkpoint_index:
        issues.append("R0.9: local checkpoint regressed")

    max_observed_rss = max(sample.rss_bytes for sample in window.samples)
    baseline_rss = window.samples[0].rss_bytes
    resource_growth_bounded = max_observed_rss <= max(
        baseline_rss * 4,
        baseline_rss + 512 * 1024 * 1024,
    )
    if not resource_growth_bounded:
        issues.append("R0.9: memory growth exceeded the bounded qualification envelope")

    if recovery.storage_used_bytes >= baseline.storage_high_watermark_used_bytes:
        issues.append("R0.9: recovery storage state crossed the R0.8 high watermark")
        storage_boundary_not_crossed = False

    proof_keys: dict[tuple[QueueProofSubject, str], EdgeR0QueueProofReceipt] = {}
    for receipt in proofs:
        key = (receipt.subject_kind, receipt.subject_id)
        if key in proof_keys:
            issues.append(
                "R0.9: duplicate proof receipt for "
                f"{receipt.subject_kind.value}:{receipt.subject_id}"
            )
            continue
        proof_keys[key] = receipt

    verifier_host = manifest.verifier.verifier_host_id
    preexisting_evidence_preserved = True
    for proof_digest in baseline.representative_proof_sha256:
        pre_receipt = proof_keys.get(
            (QueueProofSubject.PRE_SATURATION, proof_digest)
        )
        if pre_receipt is None:
            issues.append(
                f"R0.9: missing pre-saturation proof verification: {proof_digest}"
            )
            preexisting_evidence_preserved = False
            continue
        if pre_receipt.proof_artifact_sha256 != proof_digest:
            issues.append(
                f"R0.9: pre-saturation proof digest mismatch: {proof_digest}"
            )
            preexisting_evidence_preserved = False
        if (
            not pre_receipt.inclusion_valid
            or not pre_receipt.independent_execution_context
        ):
            issues.append(
                f"R0.9: pre-saturation proof failed verification: {proof_digest}"
            )
            preexisting_evidence_preserved = False
        if verifier_host is None or pre_receipt.verifier_host_id != verifier_host:
            issues.append(f"R0.9: verifier host mismatch: {proof_digest}")
            preexisting_evidence_preserved = False

    for attempt_id, recovered in recovery_by_id.items():
        if recovered.authoritative_commit_count != 1:
            continue
        accepted_receipt = proof_keys.get(
            (QueueProofSubject.SATURATION_ATTEMPT, attempt_id)
        )
        if accepted_receipt is None:
            issues.append(
                f"R0.9: recovered accepted record lacks proof: {attempt_id}"
            )
            accepted_records_preserved = False
            continue
        if (
            accepted_receipt.proof_artifact_sha256
            != recovered.recovered_proof_sha256
        ):
            issues.append(
                f"R0.9: accepted-record proof digest mismatch: {attempt_id}"
            )
            accepted_records_preserved = False
        if (
            not accepted_receipt.inclusion_valid
            or not accepted_receipt.independent_execution_context
        ):
            issues.append(
                f"R0.9: accepted record failed independent proof: {attempt_id}"
            )
            accepted_records_preserved = False
        if (
            verifier_host is None
            or accepted_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.9: accepted-record verifier host mismatch: {attempt_id}"
            )
            accepted_records_preserved = False

    canary_valid = True
    if canary.recovery_id != recovery.recovery_id:
        issues.append("R0.9: recovery canary references another recovery")
        canary_valid = False
    if canary.captured_at < recovery.recovered_at:
        issues.append("R0.9: recovery canary predates queue recovery")
        canary_valid = False
    if not canary.inclusion_valid or not canary.independent_execution_context:
        issues.append("R0.9: recovery canary did not independently verify")
        canary_valid = False
    if verifier_host is None or canary.verifier_host_id != verifier_host:
        issues.append("R0.9: canary verifier host does not match bench binding")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase7_evaluation_id": phase7.evaluation_id,
        "baseline_id": baseline.baseline_id,
        "workload_id": workload.workload_id,
        "window_id": window.window_id,
        "recovery_id": recovery.recovery_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        queue_bounds_enforced
        and explicit_backpressure_observed
        and storage_boundary_not_crossed
        and resource_growth_bounded
        and attempt_reconciliation_complete
        and accepted_records_preserved
        and preexisting_evidence_preserved
        and history_not_rewritten
        and final_queue_clean
        and canary_valid
        and not issues
    )
    return EdgeR0Phase8Evaluation(
        evaluation_id=f"edge-r0-phase8-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase7_evaluation_id=phase7.evaluation_id,
        baseline_id=baseline.baseline_id,
        workload_id=workload.workload_id,
        window_id=window.window_id,
        recovery_id=recovery.recovery_id,
        evaluated_at=evaluated_at,
        attempted_count=len(window.attempts),
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        queue_bounds_enforced=queue_bounds_enforced,
        explicit_backpressure_observed=explicit_backpressure_observed,
        storage_boundary_not_crossed=storage_boundary_not_crossed,
        resource_growth_bounded=resource_growth_bounded,
        attempt_reconciliation_complete=attempt_reconciliation_complete,
        accepted_records_preserved=accepted_records_preserved,
        preexisting_evidence_preserved=preexisting_evidence_preserved,
        history_not_rewritten=history_not_rewritten,
        final_queue_clean=final_queue_clean,
        post_recovery_canary_valid=canary_valid,
        r0_9_passed=passed,
        issues=tuple(issues),
    )


def load_phase7_evaluation(raw: bytes) -> EdgeR0Phase7Evaluation:
    return EdgeR0Phase7Evaluation.model_validate_json(raw)


def _load(raw: bytes, model: type[StrictPhase8Model]) -> StrictPhase8Model:
    return model.model_validate_json(raw)


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
        description="ETS Wave 1 Edge Compact R0 R0.9 bounded queue evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser("evaluate-r0-9")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase7-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--baseline", type=Path, required=True)
    evaluate_parser.add_argument("--workload", type=Path, required=True)
    evaluate_parser.add_argument("--window", type=Path, required=True)
    evaluate_parser.add_argument("--recovery", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-9":
        result = evaluate_r0_9(
            load_manifest(args.manifest.read_bytes()),
            load_phase7_evaluation(args.phase7_evaluation.read_bytes()),
            EdgeR0QueueBaseline.model_validate_json(args.baseline.read_bytes()),
            EdgeR0QueueWorkloadDefinition.model_validate_json(args.workload.read_bytes()),
            EdgeR0QueueSaturationWindow.model_validate_json(args.window.read_bytes()),
            EdgeR0QueueRecovery.model_validate_json(args.recovery.read_bytes()),
            tuple(
                EdgeR0QueueProofReceipt.model_validate_json(path.read_bytes())
                for path in args.proof_receipt
            ),
            EdgeR0QueueRecoveryCanary.model_validate_json(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_9_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
