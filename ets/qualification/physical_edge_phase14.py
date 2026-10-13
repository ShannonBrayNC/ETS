"""Wave 1 Edge Compact R0 bounded endurance/soak evidence.

R0.15 evaluates sustained bounded operation over a frozen qualification workload while
preserving record reconciliation, proof validity, checkpoint/history continuity,
resource envelopes and the post-R0.14 identity/trust state. The evaluator never
generates soak load or changes resource limits.
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
from ets.qualification.physical_edge_phase13 import EdgeR0Phase13Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE14_CLAIM_BOUNDARY: Literal[
    "r0_15_phase_evidence_not_a_physical_qualification_result"
] = "r0_15_phase_evidence_not_a_physical_qualification_result"
_PHASE14_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase14Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class SoakDisposition(StrEnum):
    AUTHORITATIVE_ACCEPTED = "authoritative_accepted"
    REJECTED_BACKPRESSURE = "rejected_backpressure"
    NON_AUTHORITATIVE_UNACKNOWLEDGED = "non_authoritative_unacknowledged"


class SoakProofSubject(StrEnum):
    PRE_SOAK = "pre_soak"
    SOAK_RECORD = "soak_record"


class EdgeR0SoakBaseline(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-soak-baseline.v1"] = (
        "ets.edge-compact-r0-soak-baseline.v1"
    )
    baseline_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase13_evaluation_id: str = Field(min_length=1, max_length=256)
    phase13_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    build_sha: str = Field(min_length=7, max_length=128)
    artifact_digest: str = Field(pattern=_SHA256_RE)
    configuration_digest: str = Field(pattern=_SHA256_RE)
    runtime_id: str = Field(min_length=1, max_length=256)
    device_identity_id: str = Field(min_length=1, max_length=256)
    signing_key_id: str = Field(min_length=1, max_length=256)
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
    storage_free_bytes: int = Field(gt=0)
    storage_high_watermark_used_bytes: int = Field(gt=0)
    process_rss_bytes: int = Field(gt=0)
    cpu_percent: float = Field(ge=0, le=100)
    host_load_1m: float = Field(ge=0)
    temperature_c: float | None = None
    network_connected: Literal[True] = True
    reachability_rtt_ms: float = Field(ge=0)
    time_quality: Literal[TimeQuality.TRUSTED_SYNCHRONIZED] = (
        TimeQuality.TRUSTED_SYNCHRONIZED
    )
    service_healthy: Literal[True] = True
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "soak-baseline timestamp")

    @model_validator(mode="after")
    def validate_baseline(self) -> EdgeR0SoakBaseline:
        if self.storage_used_bytes >= self.storage_high_watermark_used_bytes:
            raise ValueError("R0.15 baseline exceeds the R0.8 storage boundary")
        if self.queue_state.queue_depth != 0 or self.queue_state.queue_bytes != 0:
            raise ValueError("R0.15 baseline queue must begin clean")
        if (
            self.queue_state.pending != 0
            or self.queue_state.in_flight != 0
            or self.queue_state.retryable_failure != 0
            or self.queue_state.terminal_failure != 0
        ):
            raise ValueError("R0.15 baseline queue dispositions must begin clean")
        if len(self.representative_proof_sha256) != len(
            set(self.representative_proof_sha256)
        ):
            raise ValueError("representative proof digests must be unique")
        return self


class EdgeR0SoakProfile(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-soak-profile.v1"] = (
        "ets.edge-compact-r0-soak-profile.v1"
    )
    profile_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    frozen_at: datetime
    planned_duration_seconds: float = Field(gt=0, le=604_800)
    sample_interval_seconds: float = Field(gt=0, le=86_400)
    max_sample_gap_seconds: float = Field(gt=0, le=86_400)
    max_event_count: int = Field(gt=0, le=10_000_000)
    max_payload_bytes: int = Field(gt=0)
    max_event_rate_per_second: float = Field(gt=0)
    max_storage_growth_bytes: int = Field(gt=0)
    max_queue_items: int = Field(gt=0)
    max_queue_bytes: int = Field(gt=0)
    queue_item_allowance: int = Field(default=0, ge=0)
    queue_byte_allowance: int = Field(default=0, ge=0)
    max_rss_growth_bytes: int = Field(gt=0)
    max_retry_attempts_per_minute: int = Field(gt=0)
    max_service_restarts: int = Field(default=0, ge=0)
    max_temperature_c: float | None = None
    workload_definition_sha256: str = Field(pattern=_SHA256_RE)
    controller_definition_sha256: str = Field(pattern=_SHA256_RE)
    operator_stop_condition: str = Field(min_length=1, max_length=1024)
    evaluator_generates_load: Literal[False] = False
    claim_boundary: Literal[
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @field_validator("frozen_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "soak-profile timestamp")

    @model_validator(mode="after")
    def validate_profile(self) -> EdgeR0SoakProfile:
        if self.max_sample_gap_seconds < self.sample_interval_seconds:
            raise ValueError("maximum sample gap cannot be below sample interval")
        if self.max_temperature_c is not None and self.max_temperature_c <= 0:
            raise ValueError("temperature envelope must be positive when declared")
        return self


class EdgeR0SoakAttempt(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-soak-attempt.v1"] = (
        "ets.edge-compact-r0-soak-attempt.v1"
    )
    attempt_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    attempted_at: datetime
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    payload_bytes: int = Field(gt=0)
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    disposition: SoakDisposition
    local_authoritative_commit: bool
    local_proof_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    explicit_backpressure_signal: bool
    claim_boundary: Literal[
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @field_validator("attempted_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "soak-attempt timestamp")

    @model_validator(mode="after")
    def validate_disposition(self) -> EdgeR0SoakAttempt:
        if self.disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED:
            if not self.local_authoritative_commit or self.local_proof_sha256 is None:
                raise ValueError("accepted attempt requires local commit and proof")
            if self.explicit_backpressure_signal:
                raise ValueError("accepted attempt cannot carry backpressure signal")
        elif self.disposition is SoakDisposition.REJECTED_BACKPRESSURE:
            if self.local_authoritative_commit or self.local_proof_sha256 is not None:
                raise ValueError("rejected attempt cannot carry authoritative commit")
            if not self.explicit_backpressure_signal:
                raise ValueError("backpressure rejection requires explicit signal")
        else:
            if self.local_authoritative_commit or self.local_proof_sha256 is not None:
                raise ValueError("unacknowledged attempt cannot carry authoritative commit")
            if self.explicit_backpressure_signal:
                raise ValueError("unacknowledged attempt cannot claim backpressure signal")
        return self


class EdgeR0SoakSample(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-soak-sample.v1"] = (
        "ets.edge-compact-r0-soak-sample.v1"
    )
    sample_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    observed_at: datetime
    elapsed_monotonic_seconds: float = Field(ge=0)
    attempted_since_prior: int = Field(ge=0)
    accepted_since_prior: int = Field(ge=0)
    rejected_since_prior: int = Field(ge=0)
    unacknowledged_since_prior: int = Field(ge=0)
    cumulative_attempted: int = Field(ge=0)
    cumulative_accepted: int = Field(ge=0)
    cumulative_rejected: int = Field(ge=0)
    cumulative_unacknowledged: int = Field(ge=0)
    cumulative_authoritative_commits: int = Field(ge=0)
    cumulative_synchronized: int = Field(ge=0)
    queue_state: EdgeSyncStatusEvidence
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    storage_used_bytes: int = Field(ge=0)
    storage_free_bytes: int = Field(ge=0)
    process_rss_bytes: int = Field(gt=0)
    cpu_percent: float = Field(ge=0, le=100)
    host_load_1m: float = Field(ge=0)
    temperature_c: float | None = None
    retry_attempts_last_minute: int = Field(ge=0)
    network_connected: bool
    time_quality: TimeQuality
    service_healthy: bool
    service_restart_count: int = Field(ge=0)
    build_sha: str = Field(min_length=7, max_length=128)
    configuration_digest: str = Field(pattern=_SHA256_RE)
    device_identity_id: str = Field(min_length=1, max_length=256)
    signing_key_id: str = Field(min_length=1, max_length=256)
    identity_profile: str = Field(min_length=1, max_length=128)
    hardware_attested: bool
    secure_boot_verified: bool
    hardware_key_protection: bool
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "soak-sample timestamp")

    @model_validator(mode="after")
    def validate_counts(self) -> EdgeR0SoakSample:
        if self.attempted_since_prior != (
            self.accepted_since_prior
            + self.rejected_since_prior
            + self.unacknowledged_since_prior
        ):
            raise ValueError("sample interval dispositions must reconcile to attempts")
        if self.cumulative_attempted != (
            self.cumulative_accepted
            + self.cumulative_rejected
            + self.cumulative_unacknowledged
        ):
            raise ValueError("sample cumulative dispositions must reconcile to attempts")
        if self.cumulative_authoritative_commits != self.cumulative_accepted:
            raise ValueError("authoritative commit count must equal accepted count")
        return self


class EdgeR0SoakWindow(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-soak-window.v1"] = (
        "ets.edge-compact-r0-soak-window.v1"
    )
    window_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    attempts: tuple[EdgeR0SoakAttempt, ...] = Field(min_length=1)
    samples: tuple[EdgeR0SoakSample, ...] = Field(min_length=2)
    workload_commitment_sha256: str = Field(pattern=_SHA256_RE)
    observer_timeline_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "soak-window timestamp")

    @model_validator(mode="after")
    def validate_window(self) -> EdgeR0SoakWindow:
        if self.completed_at <= self.started_at:
            raise ValueError("soak window must have positive duration")
        attempt_seq = [attempt.sequence_number for attempt in self.attempts]
        sample_seq = [sample.sequence_number for sample in self.samples]
        if attempt_seq != list(range(1, len(self.attempts) + 1)):
            raise ValueError("soak attempt sequence must be contiguous")
        if sample_seq != list(range(1, len(self.samples) + 1)):
            raise ValueError("soak sample sequence must be contiguous")
        attempt_ids = [attempt.attempt_id for attempt in self.attempts]
        event_ids = [attempt.event_id for attempt in self.attempts]
        idempotency = [attempt.idempotency_key for attempt in self.attempts]
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValueError("soak attempt IDs must be unique")
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("soak event IDs must be unique")
        if len(idempotency) != len(set(idempotency)):
            raise ValueError("soak idempotency keys must be unique")
        return self


class EdgeR0SoakFinalRecord(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-soak-final-record.v1"] = (
        "ets.edge-compact-r0-soak-final-record.v1"
    )
    attempt_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    final_disposition: SoakDisposition
    authoritative_local_present: bool
    final_upstream_commit_count: int = Field(ge=0, le=32)
    final_upstream_event_id: str | None = Field(default=None, max_length=256)
    final_upstream_acceptance_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    final_proof_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    local_marked_synchronized: bool
    replayed_or_duplicated: bool
    final_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_final_shape(self) -> EdgeR0SoakFinalRecord:
        commit_fields = (
            self.final_upstream_event_id,
            self.final_upstream_acceptance_sha256,
            self.final_proof_sha256,
        )
        if self.final_disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED:
            if not self.authoritative_local_present:
                raise ValueError("accepted final record must remain authoritative locally")
            if self.final_upstream_commit_count != 1:
                raise ValueError("accepted final record requires one upstream commit")
            if any(value is None for value in commit_fields):
                raise ValueError("accepted final record requires event/acceptance/proof")
            if not self.local_marked_synchronized:
                raise ValueError("accepted final record must finish synchronized")
        else:
            if self.authoritative_local_present:
                raise ValueError("non-accepted attempt cannot become authoritative")
            if self.final_upstream_commit_count != 0:
                raise ValueError("non-accepted attempt cannot gain upstream commit")
            if any(value is not None for value in commit_fields):
                raise ValueError("non-accepted attempt cannot carry final commit fields")
            if self.local_marked_synchronized:
                raise ValueError("non-accepted attempt cannot be marked synchronized")
        return self


class EdgeR0SoakReconciliation(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-soak-reconciliation.v1"] = (
        "ets.edge-compact-r0-soak-reconciliation.v1"
    )
    reconciliation_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    reconciled_at: datetime
    actual_duration_seconds: float = Field(gt=0)
    records: tuple[EdgeR0SoakFinalRecord, ...] = Field(min_length=1)
    final_local_checkpoint_index: int = Field(ge=0)
    final_local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    final_upstream_checkpoint_index: int = Field(ge=0)
    final_upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    preserved_log_head_observed: bool
    preserved_pre_soak_log_head_sha256: str = Field(pattern=_SHA256_RE)
    preserved_historical_record_commitment_sha256: str = Field(pattern=_SHA256_RE)
    final_queue_state: EdgeSyncStatusEvidence
    final_storage_used_bytes: int = Field(ge=0)
    final_storage_free_bytes: int = Field(ge=0)
    final_process_rss_bytes: int = Field(gt=0)
    final_network_connected: bool
    final_time_quality: TimeQuality
    final_service_healthy: bool
    final_build_sha: str = Field(min_length=7, max_length=128)
    final_configuration_digest: str = Field(pattern=_SHA256_RE)
    final_device_identity_id: str = Field(min_length=1, max_length=256)
    final_signing_key_id: str = Field(min_length=1, max_length=256)
    final_identity_profile: str = Field(min_length=1, max_length=128)
    final_hardware_attested: bool
    final_secure_boot_verified: bool
    final_hardware_key_protection: bool
    reconciliation_commitment_sha256: str = Field(pattern=_SHA256_RE)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @field_validator("reconciled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "soak-reconciliation timestamp")

    @model_validator(mode="after")
    def validate_records(self) -> EdgeR0SoakReconciliation:
        ids = [record.attempt_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("soak final record attempt IDs must be unique")
        return self


class EdgeR0SoakProofReceipt(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-soak-proof-receipt.v1"] = (
        "ets.edge-compact-r0-soak-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    subject_kind: SoakProofSubject
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
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "soak-proof timestamp")


class EdgeR0SoakCanary(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-soak-canary.v1"] = (
        "ets.edge-compact-r0-soak-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    reconciliation_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    build_sha: str = Field(min_length=7, max_length=128)
    configuration_digest: str = Field(pattern=_SHA256_RE)
    device_identity_id: str = Field(min_length=1, max_length=256)
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
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.15 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0SoakCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("soak canary payload SHA-256 must match content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("soak canary verification cannot precede capture")
        return self


class EdgeR0Phase14Evaluation(StrictPhase14Model):
    schema_version: Literal["ets.edge-compact-r0-phase14-evaluation.v1"] = (
        "ets.edge-compact-r0-phase14-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase13_evaluation_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    reconciliation_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    duration_completed: bool
    sampling_continuity_valid: bool
    workload_reconciled: bool
    accepted_records_preserved: bool
    no_logical_duplication_or_promotion: bool
    checkpoints_monotonic: bool
    history_preserved: bool
    resource_envelope_preserved: bool
    identity_trust_state_preserved: bool
    independent_verification_complete: bool
    final_backlog_clear: bool
    post_soak_canary_valid: bool
    r0_15_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE14_DISPOSITION
    claim_boundary: Literal[
        "r0_15_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE14_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.15 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase14Evaluation:
        expected = (
            self.duration_completed
            and self.sampling_continuity_valid
            and self.workload_reconciled
            and self.accepted_records_preserved
            and self.no_logical_duplication_or_promotion
            and self.checkpoints_monotonic
            and self.history_preserved
            and self.resource_envelope_preserved
            and self.identity_trust_state_preserved
            and self.independent_verification_complete
            and self.final_backlog_clear
            and self.post_soak_canary_valid
            and not self.issues
        )
        if self.r0_15_passed != expected:
            raise ValueError("r0_15_passed must match component results and issues")
        return self


def build_soak_workload_commitment(
    attempts: tuple[EdgeR0SoakAttempt, ...],
) -> str:
    return canonical_sha256(
        [
            attempt.model_dump(mode="json")
            for attempt in sorted(attempts, key=lambda item: item.sequence_number)
        ]
    )


def build_soak_reconciliation_commitment(
    records: tuple[EdgeR0SoakFinalRecord, ...],
) -> str:
    return canonical_sha256(
        [
            record.model_dump(mode="json")
            for record in sorted(records, key=lambda item: item.attempt_id)
        ]
    )


def _queue_is_clean(queue: EdgeSyncStatusEvidence) -> bool:
    return (
        queue.queue_depth == 0
        and queue.queue_bytes == 0
        and queue.pending == 0
        and queue.in_flight == 0
        and queue.retryable_failure == 0
        and queue.terminal_failure == 0
    )


def evaluate_r0_15(
    manifest: EdgeCompactR0BenchManifest,
    phase13: EdgeR0Phase13Evaluation,
    baseline: EdgeR0SoakBaseline,
    profile: EdgeR0SoakProfile,
    window: EdgeR0SoakWindow,
    reconciliation: EdgeR0SoakReconciliation,
    proofs: tuple[EdgeR0SoakProofReceipt, ...],
    canary: EdgeR0SoakCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase14Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.15: bench manifest not ready: {blocker}")
    if not phase13.r0_14_passed:
        issues.append("R0.15: R0.14 did not pass")
    if phase13.manifest_id != manifest.manifest_id or phase13.asset_id != asset_id:
        issues.append("R0.15: R0.14 evaluation is bound to another DUT")

    if baseline.manifest_id != manifest.manifest_id or baseline.asset_id != asset_id:
        issues.append("R0.15: baseline is bound to another DUT")
    if baseline.phase13_evaluation_id != phase13.evaluation_id:
        issues.append("R0.15: baseline references another R0.14 evaluation")
    if baseline.phase13_evaluation_sha256 != canonical_sha256(
        phase13.model_dump(mode="json")
    ):
        issues.append("R0.15: R0.14 digest binding mismatch")
    if baseline.build_sha != manifest.build.source_revision:
        issues.append("R0.15: baseline build does not match W1-1 manifest")
    if baseline.artifact_digest != manifest.build.artifact_digest:
        issues.append("R0.15: baseline artifact digest mismatch")
    if baseline.configuration_digest != manifest.build.configuration_digest:
        issues.append("R0.15: baseline configuration digest mismatch")

    if profile.baseline_id != baseline.baseline_id:
        issues.append("R0.15: soak profile references another baseline")
    if window.baseline_id != baseline.baseline_id:
        issues.append("R0.15: soak window references another baseline")
    if window.profile_id != profile.profile_id:
        issues.append("R0.15: soak window references another profile")
    if reconciliation.window_id != window.window_id:
        issues.append("R0.15: reconciliation references another soak window")
    if reconciliation.reconciled_at < window.completed_at:
        issues.append("R0.15: reconciliation predates soak completion")

    duration_completed = reconciliation.actual_duration_seconds >= (
        profile.planned_duration_seconds
    )
    actual_window_duration = (window.completed_at - window.started_at).total_seconds()
    if actual_window_duration < profile.planned_duration_seconds:
        issues.append("R0.15: soak window ended before planned duration")
        duration_completed = False
    if reconciliation.actual_duration_seconds < profile.planned_duration_seconds:
        issues.append("R0.15: reconciled duration is below planned duration")
        duration_completed = False

    attempts = window.attempts
    if window.workload_commitment_sha256 != build_soak_workload_commitment(attempts):
        issues.append("R0.15: workload commitment mismatch")

    workload_reconciled = True
    if len(attempts) > profile.max_event_count:
        issues.append("R0.15: event-count envelope exceeded")
        workload_reconciled = False
    total_payload = sum(attempt.payload_bytes for attempt in attempts)
    if total_payload > profile.max_payload_bytes:
        issues.append("R0.15: workload payload-byte envelope exceeded")
        workload_reconciled = False
    if actual_window_duration > 0:
        observed_rate = len(attempts) / actual_window_duration
        if observed_rate > profile.max_event_rate_per_second:
            issues.append("R0.15: event-rate envelope exceeded")
            workload_reconciled = False

    disposition_counts = {
        SoakDisposition.AUTHORITATIVE_ACCEPTED: 0,
        SoakDisposition.REJECTED_BACKPRESSURE: 0,
        SoakDisposition.NON_AUTHORITATIVE_UNACKNOWLEDGED: 0,
    }
    attempts_by_id = {attempt.attempt_id: attempt for attempt in attempts}
    for attempt in attempts:
        disposition_counts[attempt.disposition] += 1

    sampling_continuity_valid = True
    resource_envelope_preserved = True
    identity_trust_state_preserved = True
    checkpoints_monotonic = True

    prior_elapsed: float | None = None
    prior_observed_at: datetime | None = None
    prior_cumulative = (0, 0, 0, 0)
    prior_local_checkpoint = baseline.local_checkpoint_index
    prior_upstream_checkpoint = baseline.upstream_checkpoint_index

    expected_attempted = 0
    expected_accepted = 0
    expected_rejected = 0
    expected_unacknowledged = 0

    max_queue_items = profile.max_queue_items + profile.queue_item_allowance
    max_queue_bytes = profile.max_queue_bytes + profile.queue_byte_allowance
    max_rss = baseline.process_rss_bytes + profile.max_rss_growth_bytes
    max_storage = baseline.storage_used_bytes + profile.max_storage_growth_bytes

    for sample in window.samples:
        if prior_elapsed is not None:
            elapsed_gap = sample.elapsed_monotonic_seconds - prior_elapsed
            if elapsed_gap <= 0 or elapsed_gap > profile.max_sample_gap_seconds:
                issues.append(f"R0.15: invalid sample gap at {sample.sample_id}")
                sampling_continuity_valid = False
        if prior_observed_at is not None:
            wall_gap = (sample.observed_at - prior_observed_at).total_seconds()
            if wall_gap <= 0 or wall_gap > profile.max_sample_gap_seconds:
                issues.append(f"R0.15: wall-clock sample gap at {sample.sample_id}")
                sampling_continuity_valid = False

        expected_attempted += sample.attempted_since_prior
        expected_accepted += sample.accepted_since_prior
        expected_rejected += sample.rejected_since_prior
        expected_unacknowledged += sample.unacknowledged_since_prior
        expected_cumulative = (
            expected_attempted,
            expected_accepted,
            expected_rejected,
            expected_unacknowledged,
        )
        actual_cumulative = (
            sample.cumulative_attempted,
            sample.cumulative_accepted,
            sample.cumulative_rejected,
            sample.cumulative_unacknowledged,
        )
        if actual_cumulative != expected_cumulative:
            issues.append(f"R0.15: sample cumulative-count mismatch: {sample.sample_id}")
            sampling_continuity_valid = False
        if any(
            current < prior
            for current, prior in zip(actual_cumulative, prior_cumulative, strict=True)
        ):
            issues.append(f"R0.15: cumulative count regressed: {sample.sample_id}")
            sampling_continuity_valid = False

        if sample.local_checkpoint_index < prior_local_checkpoint:
            issues.append(f"R0.15: local checkpoint regressed: {sample.sample_id}")
            checkpoints_monotonic = False
        if sample.upstream_checkpoint_index < prior_upstream_checkpoint:
            issues.append(f"R0.15: upstream checkpoint regressed: {sample.sample_id}")
            checkpoints_monotonic = False

        queue = sample.queue_state
        if queue.queue_depth > max_queue_items or queue.queue_bytes > max_queue_bytes:
            issues.append(f"R0.15: queue envelope exceeded: {sample.sample_id}")
            resource_envelope_preserved = False
        if sample.storage_used_bytes >= baseline.storage_high_watermark_used_bytes:
            issues.append(f"R0.15: R0.8 storage boundary crossed: {sample.sample_id}")
            resource_envelope_preserved = False
        if sample.storage_used_bytes > max_storage:
            issues.append(f"R0.15: storage-growth envelope exceeded: {sample.sample_id}")
            resource_envelope_preserved = False
        if sample.process_rss_bytes > max_rss:
            issues.append(f"R0.15: RSS envelope exceeded: {sample.sample_id}")
            resource_envelope_preserved = False
        if sample.retry_attempts_last_minute > profile.max_retry_attempts_per_minute:
            issues.append(f"R0.15: retry-rate envelope exceeded: {sample.sample_id}")
            resource_envelope_preserved = False
        if sample.service_restart_count > profile.max_service_restarts:
            issues.append(f"R0.15: service-restart envelope exceeded: {sample.sample_id}")
            resource_envelope_preserved = False
        if (
            profile.max_temperature_c is not None
            and sample.temperature_c is not None
            and sample.temperature_c > profile.max_temperature_c
        ):
            issues.append(f"R0.15: thermal envelope exceeded: {sample.sample_id}")
            resource_envelope_preserved = False
        if not sample.network_connected:
            issues.append(f"R0.15: R0.10 network boundary crossed: {sample.sample_id}")
            resource_envelope_preserved = False
        if sample.time_quality is not TimeQuality.TRUSTED_SYNCHRONIZED:
            issues.append(f"R0.15: R0.11 time boundary crossed: {sample.sample_id}")
            resource_envelope_preserved = False
        if not sample.service_healthy:
            issues.append(f"R0.15: service unhealthy during soak: {sample.sample_id}")
            resource_envelope_preserved = False

        identity_matches = (
            sample.build_sha == baseline.build_sha
            and sample.configuration_digest == baseline.configuration_digest
            and sample.device_identity_id == baseline.device_identity_id
            and sample.signing_key_id == baseline.signing_key_id
            and sample.identity_profile == baseline.identity_profile
            and sample.hardware_attested is False
            and sample.secure_boot_verified is False
            and sample.hardware_key_protection is False
        )
        if not identity_matches:
            issues.append(f"R0.15: identity/trust/software drift: {sample.sample_id}")
            identity_trust_state_preserved = False

        prior_elapsed = sample.elapsed_monotonic_seconds
        prior_observed_at = sample.observed_at
        prior_cumulative = actual_cumulative
        prior_local_checkpoint = sample.local_checkpoint_index
        prior_upstream_checkpoint = sample.upstream_checkpoint_index

    final_sample = window.samples[-1]
    final_counts = (
        len(attempts),
        disposition_counts[SoakDisposition.AUTHORITATIVE_ACCEPTED],
        disposition_counts[SoakDisposition.REJECTED_BACKPRESSURE],
        disposition_counts[SoakDisposition.NON_AUTHORITATIVE_UNACKNOWLEDGED],
    )
    sample_counts = (
        final_sample.cumulative_attempted,
        final_sample.cumulative_accepted,
        final_sample.cumulative_rejected,
        final_sample.cumulative_unacknowledged,
    )
    if final_counts != sample_counts:
        issues.append("R0.15: final sample counts do not match retained workload")
        workload_reconciled = False
    if final_sample.elapsed_monotonic_seconds < profile.planned_duration_seconds:
        issues.append("R0.15: final periodic sample does not cover planned duration")
        sampling_continuity_valid = False

    final_by_id = {record.attempt_id: record for record in reconciliation.records}
    attempt_ids = set(attempts_by_id)
    final_ids = set(final_by_id)
    missing = sorted(attempt_ids - final_ids)
    unknown = sorted(final_ids - attempt_ids)
    if missing:
        issues.append(f"R0.15: final reconciliation missing attempts: {missing}")
        workload_reconciled = False
    if unknown:
        issues.append(f"R0.15: final reconciliation has unknown attempts: {unknown}")
        workload_reconciled = False

    accepted_records_preserved = True
    no_logical_duplication_or_promotion = True
    for attempt_id in sorted(attempt_ids & final_ids):
        attempt = attempts_by_id[attempt_id]
        final_record = final_by_id[attempt_id]
        if final_record.event_id != attempt.event_id:
            issues.append(f"R0.15: event binding changed: {attempt_id}")
            workload_reconciled = False
        if final_record.idempotency_key != attempt.idempotency_key:
            issues.append(f"R0.15: idempotency binding changed: {attempt_id}")
            workload_reconciled = False
        if final_record.final_disposition is not attempt.disposition:
            issues.append(f"R0.15: attempt disposition changed: {attempt_id}")
            no_logical_duplication_or_promotion = False
        if final_record.replayed_or_duplicated:
            issues.append(f"R0.15: logical replay/duplication observed: {attempt_id}")
            no_logical_duplication_or_promotion = False

        if attempt.disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED:
            if not final_record.authoritative_local_present:
                issues.append(f"R0.15: accepted record lost locally: {attempt_id}")
                accepted_records_preserved = False
            if final_record.final_upstream_commit_count != 1:
                issues.append(f"R0.15: accepted record commit count invalid: {attempt_id}")
                accepted_records_preserved = False
            if final_record.final_upstream_event_id != attempt.event_id:
                issues.append(f"R0.15: accepted upstream event mismatch: {attempt_id}")
                accepted_records_preserved = False
        else:
            if final_record.authoritative_local_present:
                issues.append(f"R0.15: rejected/unacknowledged attempt promoted: {attempt_id}")
                no_logical_duplication_or_promotion = False
            if final_record.final_upstream_commit_count != 0:
                issues.append(f"R0.15: non-accepted attempt gained upstream commit: {attempt_id}")
                no_logical_duplication_or_promotion = False

    if reconciliation.reconciliation_commitment_sha256 != (
        build_soak_reconciliation_commitment(reconciliation.records)
    ):
        issues.append("R0.15: final reconciliation commitment mismatch")
        workload_reconciled = False

    if reconciliation.final_local_checkpoint_index < prior_local_checkpoint:
        issues.append("R0.15: final local checkpoint regressed")
        checkpoints_monotonic = False
    if reconciliation.final_upstream_checkpoint_index < prior_upstream_checkpoint:
        issues.append("R0.15: final upstream checkpoint regressed")
        checkpoints_monotonic = False

    history_preserved = (
        reconciliation.preserved_log_head_observed
        and reconciliation.preserved_pre_soak_log_head_sha256 == baseline.log_head_sha256
        and reconciliation.preserved_historical_record_commitment_sha256
        == baseline.historical_record_commitment_sha256
    )
    if not reconciliation.preserved_log_head_observed:
        issues.append("R0.15: pre-soak log head was not observed after soak")
    if reconciliation.preserved_pre_soak_log_head_sha256 != baseline.log_head_sha256:
        issues.append("R0.15: pre-soak log-head digest changed")
    if (
        reconciliation.preserved_historical_record_commitment_sha256
        != baseline.historical_record_commitment_sha256
    ):
        issues.append("R0.15: historical record commitment changed")

    final_backlog_clear = _queue_is_clean(reconciliation.final_queue_state)
    if not final_backlog_clear:
        issues.append("R0.15: final synchronization backlog is not clean")

    if reconciliation.final_storage_used_bytes >= baseline.storage_high_watermark_used_bytes:
        issues.append("R0.15: final R0.8 storage boundary crossed")
        resource_envelope_preserved = False
    if reconciliation.final_storage_used_bytes > max_storage:
        issues.append("R0.15: final storage-growth envelope exceeded")
        resource_envelope_preserved = False
    if reconciliation.final_process_rss_bytes > max_rss:
        issues.append("R0.15: final RSS envelope exceeded")
        resource_envelope_preserved = False
    if not reconciliation.final_network_connected:
        issues.append("R0.15: final network state is not healthy")
        resource_envelope_preserved = False
    if reconciliation.final_time_quality is not TimeQuality.TRUSTED_SYNCHRONIZED:
        issues.append("R0.15: final time quality is not trusted/synchronized")
        resource_envelope_preserved = False
    if not reconciliation.final_service_healthy:
        issues.append("R0.15: final service state is unhealthy")
        resource_envelope_preserved = False

    final_identity_matches = (
        reconciliation.final_build_sha == baseline.build_sha
        and reconciliation.final_configuration_digest == baseline.configuration_digest
        and reconciliation.final_device_identity_id == baseline.device_identity_id
        and reconciliation.final_signing_key_id == baseline.signing_key_id
        and reconciliation.final_identity_profile == baseline.identity_profile
        and reconciliation.final_hardware_attested is False
        and reconciliation.final_secure_boot_verified is False
        and reconciliation.final_hardware_key_protection is False
    )
    if not final_identity_matches:
        issues.append("R0.15: final identity/trust/software state drifted")
        identity_trust_state_preserved = False

    proof_keys: dict[tuple[SoakProofSubject, str], EdgeR0SoakProofReceipt] = {}
    for proof_receipt in proofs:
        key = (proof_receipt.subject_kind, proof_receipt.subject_id)
        if key in proof_keys:
            issues.append(
                "R0.15: duplicate proof receipt for "
                f"{proof_receipt.subject_kind.value}:{proof_receipt.subject_id}"
            )
            continue
        proof_keys[key] = proof_receipt

    verifier_host = manifest.verifier.verifier_host_id
    independent_verification_complete = True

    for proof_digest in baseline.representative_proof_sha256:
        pre_receipt = proof_keys.get((SoakProofSubject.PRE_SOAK, proof_digest))
        if pre_receipt is None:
            issues.append(f"R0.15: missing pre-soak proof receipt: {proof_digest}")
            independent_verification_complete = False
            continue
        if pre_receipt.proof_artifact_sha256 != proof_digest:
            issues.append(f"R0.15: pre-soak proof digest mismatch: {proof_digest}")
            independent_verification_complete = False
        if (
            not pre_receipt.inclusion_valid
            or not pre_receipt.independent_execution_context
            or verifier_host is None
            or pre_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.15: pre-soak proof failed independent verification: {proof_digest}"
            )
            independent_verification_complete = False

    for attempt in attempts:
        if attempt.disposition is not SoakDisposition.AUTHORITATIVE_ACCEPTED:
            continue
        proof_record = final_by_id.get(attempt.attempt_id)
        if proof_record is None:
            independent_verification_complete = False
            continue
        record_receipt = proof_keys.get(
            (SoakProofSubject.SOAK_RECORD, attempt.attempt_id)
        )
        if record_receipt is None:
            issues.append(
                f"R0.15: missing accepted-record proof receipt: {attempt.attempt_id}"
            )
            independent_verification_complete = False
            continue
        if record_receipt.proof_artifact_sha256 != proof_record.final_proof_sha256:
            issues.append(
                f"R0.15: accepted-record proof digest mismatch: {attempt.attempt_id}"
            )
            independent_verification_complete = False
        if (
            not record_receipt.inclusion_valid
            or not record_receipt.independent_execution_context
            or verifier_host is None
            or record_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.15: accepted record failed independent verification: "
                f"{attempt.attempt_id}"
            )
            independent_verification_complete = False

    canary_valid = True
    if canary.reconciliation_id != reconciliation.reconciliation_id:
        issues.append("R0.15: canary references another reconciliation")
        canary_valid = False
    if canary.captured_at < reconciliation.reconciled_at:
        issues.append("R0.15: canary predates final reconciliation")
        canary_valid = False
    if canary.build_sha != baseline.build_sha:
        issues.append("R0.15: canary build binding mismatch")
        canary_valid = False
    if canary.configuration_digest != baseline.configuration_digest:
        issues.append("R0.15: canary configuration binding mismatch")
        canary_valid = False
    if canary.device_identity_id != baseline.device_identity_id:
        issues.append("R0.15: canary identity binding mismatch")
        canary_valid = False
    if not canary.synchronized:
        issues.append("R0.15: post-soak canary did not synchronize")
        canary_valid = False
    if (
        not canary.inclusion_valid
        or not canary.independent_execution_context
        or verifier_host is None
        or canary.verifier_host_id != verifier_host
    ):
        issues.append("R0.15: post-soak canary did not independently verify")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase13_evaluation_id": phase13.evaluation_id,
        "baseline_id": baseline.baseline_id,
        "profile_id": profile.profile_id,
        "window_id": window.window_id,
        "reconciliation_id": reconciliation.reconciliation_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        duration_completed
        and sampling_continuity_valid
        and workload_reconciled
        and accepted_records_preserved
        and no_logical_duplication_or_promotion
        and checkpoints_monotonic
        and history_preserved
        and resource_envelope_preserved
        and identity_trust_state_preserved
        and independent_verification_complete
        and final_backlog_clear
        and canary_valid
        and not issues
    )
    return EdgeR0Phase14Evaluation(
        evaluation_id=f"edge-r0-phase14-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase13_evaluation_id=phase13.evaluation_id,
        baseline_id=baseline.baseline_id,
        profile_id=profile.profile_id,
        window_id=window.window_id,
        reconciliation_id=reconciliation.reconciliation_id,
        evaluated_at=evaluated_at,
        duration_completed=duration_completed,
        sampling_continuity_valid=sampling_continuity_valid,
        workload_reconciled=workload_reconciled,
        accepted_records_preserved=accepted_records_preserved,
        no_logical_duplication_or_promotion=no_logical_duplication_or_promotion,
        checkpoints_monotonic=checkpoints_monotonic,
        history_preserved=history_preserved,
        resource_envelope_preserved=resource_envelope_preserved,
        identity_trust_state_preserved=identity_trust_state_preserved,
        independent_verification_complete=independent_verification_complete,
        final_backlog_clear=final_backlog_clear,
        post_soak_canary_valid=canary_valid,
        r0_15_passed=passed,
        issues=tuple(issues),
    )


def load_phase13_evaluation(raw: bytes) -> EdgeR0Phase13Evaluation:
    return EdgeR0Phase13Evaluation.model_validate_json(raw)


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
        description="ETS Wave 1 Edge Compact R0 R0.15 endurance/soak evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser("evaluate-r0-15")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase13-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--baseline", type=Path, required=True)
    evaluate_parser.add_argument("--profile", type=Path, required=True)
    evaluate_parser.add_argument("--window", type=Path, required=True)
    evaluate_parser.add_argument("--reconciliation", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-15":
        result = evaluate_r0_15(
            load_manifest(args.manifest.read_bytes()),
            load_phase13_evaluation(args.phase13_evaluation.read_bytes()),
            EdgeR0SoakBaseline.model_validate_json(args.baseline.read_bytes()),
            EdgeR0SoakProfile.model_validate_json(args.profile.read_bytes()),
            EdgeR0SoakWindow.model_validate_json(args.window.read_bytes()),
            EdgeR0SoakReconciliation.model_validate_json(
                args.reconciliation.read_bytes()
            ),
            tuple(
                EdgeR0SoakProofReceipt.model_validate_json(path.read_bytes())
                for path in args.proof_receipt
            ),
            EdgeR0SoakCanary.model_validate_json(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_15_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
