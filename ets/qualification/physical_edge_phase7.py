"""Wave 1 Edge Compact R0 dedicated-volume storage-pressure evidence.

R0.8 evaluates storage watermark, bounded exhaustion, backpressure and recovery
evidence for an isolated qualification volume. This module never fills or deletes
storage and cannot publish a hardware qualification claim.
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
    BenchControlKind,
    EdgeCompactR0BenchManifest,
    load_manifest,
    readiness_issues,
)
from ets.qualification.physical_edge_phase3 import EdgeSyncStatusEvidence
from ets.qualification.physical_edge_phase6 import EdgeR0Phase6Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE7_CLAIM_BOUNDARY: Literal[
    "r0_8_phase_evidence_not_a_physical_qualification_result"
] = "r0_8_phase_evidence_not_a_physical_qualification_result"
_PHASE7_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase7Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class StoragePressureBand(StrEnum):
    HIGH = "high"
    CRITICAL = "critical"


class PressureIngressDisposition(StrEnum):
    AUTHORITATIVELY_COMMITTED = "authoritatively_committed"
    REJECTED_BACKPRESSURE = "rejected_backpressure"
    NON_AUTHORITATIVE_UNACKNOWLEDGED = "non_authoritative_unacknowledged"


class StorageProofSubject(StrEnum):
    PRE_PRESSURE = "pre_pressure"
    PRESSURE_ATTEMPT = "pressure_attempt"


class EdgeR0StorageBaseline(StrictPhase7Model):
    schema_version: Literal["ets.edge-compact-r0-storage-baseline.v1"] = (
        "ets.edge-compact-r0-storage-baseline.v1"
    )
    baseline_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase6_evaluation_id: str = Field(min_length=1, max_length=256)
    phase6_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    storage_control_id: str = Field(min_length=1, max_length=256)
    filesystem_id: str = Field(min_length=1, max_length=256)
    device_id: str = Field(min_length=1, max_length=256)
    mount_point: str = Field(min_length=1, max_length=1024)
    qualification_volume: Literal[True] = True
    root_filesystem: Literal[False] = False
    total_bytes: int = Field(gt=0)
    used_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)
    high_watermark_used_bytes: int = Field(gt=0)
    critical_watermark_used_bytes: int = Field(gt=0)
    reserved_recovery_bytes: int = Field(gt=0)
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    log_head_sha256: str = Field(pattern=_SHA256_RE)
    queue_state: EdgeSyncStatusEvidence
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_8_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE7_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "storage-baseline timestamp")

    @model_validator(mode="after")
    def validate_capacity(self) -> EdgeR0StorageBaseline:
        if self.used_bytes + self.free_bytes > self.total_bytes:
            raise ValueError("used plus free bytes cannot exceed total capacity")
        if not (
            self.used_bytes
            < self.high_watermark_used_bytes
            < self.critical_watermark_used_bytes
        ):
            raise ValueError("baseline must begin below ordered high/critical watermarks")
        safe_used_ceiling = self.total_bytes - self.reserved_recovery_bytes
        if self.critical_watermark_used_bytes > safe_used_ceiling:
            raise ValueError("critical watermark must preserve reserved recovery headroom")
        if self.free_bytes < self.reserved_recovery_bytes:
            raise ValueError("baseline does not preserve reserved recovery headroom")
        if len(self.representative_proof_sha256) != len(
            set(self.representative_proof_sha256)
        ):
            raise ValueError("representative proof digests must be unique")
        return self


class EdgeR0StorageTransitionObservation(StrictPhase7Model):
    schema_version: Literal["ets.edge-compact-r0-storage-transition.v1"] = (
        "ets.edge-compact-r0-storage-transition.v1"
    )
    transition_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    baseline_sha256: str = Field(pattern=_SHA256_RE)
    band: StoragePressureBand
    started_at: datetime
    observed_at: datetime
    total_bytes: int = Field(gt=0)
    used_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)
    edge_storage_state: str = Field(min_length=1, max_length=128)
    backpressure_active: bool
    authoritative_ingress_enabled: bool
    reserved_headroom_preserved: bool
    operator_approved: Literal[True] = True
    root_filesystem_targeted: Literal[False] = False
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    independent_measurement_sha256: str = Field(pattern=_SHA256_RE)
    edge_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_8_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE7_CLAIM_BOUNDARY

    @field_validator("started_at", "observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "storage-transition timestamp")

    @model_validator(mode="after")
    def validate_transition(self) -> EdgeR0StorageTransitionObservation:
        if self.observed_at < self.started_at:
            raise ValueError("storage transition observation cannot precede its start")
        if self.used_bytes + self.free_bytes > self.total_bytes:
            raise ValueError("used plus free bytes cannot exceed transition capacity")
        return self


class EdgeR0PressureIngressAttempt(StrictPhase7Model):
    schema_version: Literal["ets.edge-compact-r0-pressure-ingress-attempt.v1"] = (
        "ets.edge-compact-r0-pressure-ingress-attempt.v1"
    )
    attempt_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    band: StoragePressureBand
    attempted_at: datetime
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    response_artifact_sha256: str = Field(pattern=_SHA256_RE)
    disposition: PressureIngressDisposition
    event_id: str | None = Field(default=None, max_length=256)
    event_hash: str | None = Field(default=None, pattern=_SHA256_RE)
    content_hash: str | None = Field(default=None, pattern=_SHA256_RE)
    proof_artifact_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    backpressure_signal: str | None = Field(default=None, max_length=256)
    retry_after_seconds: int | None = Field(default=None, ge=0)
    claim_boundary: Literal[
        "r0_8_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE7_CLAIM_BOUNDARY

    @field_validator("attempted_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "pressure-ingress timestamp")

    @model_validator(mode="after")
    def validate_disposition(self) -> EdgeR0PressureIngressAttempt:
        commit_fields = (
            self.event_id,
            self.event_hash,
            self.content_hash,
            self.proof_artifact_sha256,
        )
        if self.disposition is PressureIngressDisposition.AUTHORITATIVELY_COMMITTED:
            if any(value is None for value in commit_fields):
                raise ValueError("committed pressure attempt requires commit/proof fields")
            if self.request_payload_sha256 != self.content_hash:
                raise ValueError("committed request SHA-256 must match Edge content_hash")
            if self.backpressure_signal is not None:
                raise ValueError("committed attempt cannot also be a backpressure rejection")
        elif self.disposition is PressureIngressDisposition.REJECTED_BACKPRESSURE:
            if any(value is not None for value in commit_fields):
                raise ValueError("backpressure rejection cannot carry authoritative commit fields")
            if self.backpressure_signal is None:
                raise ValueError("backpressure rejection requires an explicit signal")
        else:
            if any(value is not None for value in commit_fields):
                raise ValueError(
                    "non-authoritative pressure attempt cannot carry commit/proof fields"
                )
        return self


class EdgeR0StoragePressureWindow(StrictPhase7Model):
    schema_version: Literal["ets.edge-compact-r0-storage-pressure-window.v1"] = (
        "ets.edge-compact-r0-storage-pressure-window.v1"
    )
    window_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    high_transition_id: str = Field(min_length=1, max_length=256)
    critical_transition_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    attempts: tuple[EdgeR0PressureIngressAttempt, ...] = Field(min_length=2)
    controller_timeline_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_8_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE7_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "storage-pressure window timestamp")

    @model_validator(mode="after")
    def validate_window(self) -> EdgeR0StoragePressureWindow:
        if self.completed_at <= self.started_at:
            raise ValueError("storage-pressure window must have positive duration")
        attempt_ids = [attempt.attempt_id for attempt in self.attempts]
        sequences = [attempt.sequence_number for attempt in self.attempts]
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValueError("pressure attempt IDs must be unique")
        if sequences != list(range(1, len(self.attempts) + 1)):
            raise ValueError("pressure attempt sequence numbers must be contiguous")
        if any(
            not (self.started_at <= attempt.attempted_at <= self.completed_at)
            for attempt in self.attempts
        ):
            raise ValueError("pressure attempt timestamp lies outside the pressure window")
        bands = {attempt.band for attempt in self.attempts}
        if bands != {StoragePressureBand.HIGH, StoragePressureBand.CRITICAL}:
            raise ValueError("pressure window must exercise both high and critical bands")
        return self


class EdgeR0PressureRecoveryRecord(StrictPhase7Model):
    schema_version: Literal["ets.edge-compact-r0-pressure-recovery-record.v1"] = (
        "ets.edge-compact-r0-pressure-recovery-record.v1"
    )
    attempt_id: str = Field(min_length=1, max_length=256)
    authoritative_commit_count: int = Field(ge=0, le=32)
    recovered_event_id: str | None = Field(default=None, max_length=256)
    recovered_proof_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    recovery_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_8_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE7_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_recovery_record(self) -> EdgeR0PressureRecoveryRecord:
        if self.authoritative_commit_count > 0:
            if self.recovered_event_id is None or self.recovered_proof_sha256 is None:
                raise ValueError("recovered commit requires event and proof fields")
        elif self.recovered_event_id is not None or self.recovered_proof_sha256 is not None:
            raise ValueError("zero recovered commits cannot carry event/proof fields")
        return self


class EdgeR0StorageRestoration(StrictPhase7Model):
    schema_version: Literal["ets.edge-compact-r0-storage-restoration.v1"] = (
        "ets.edge-compact-r0-storage-restoration.v1"
    )
    restoration_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    critical_transition_id: str = Field(min_length=1, max_length=256)
    restored_at: datetime
    total_bytes: int = Field(gt=0)
    used_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)
    normal_range_restored: bool
    cleanup_operator_approved: Literal[True] = True
    cleanup_receipt_sha256: str = Field(pattern=_SHA256_RE)
    independent_measurement_sha256: str = Field(pattern=_SHA256_RE)
    pre_pressure_log_head_sha256: str = Field(pattern=_SHA256_RE)
    pre_pressure_log_head_observed: bool
    post_recovery_checkpoint_index: int = Field(ge=0)
    post_recovery_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    final_queue_state: EdgeSyncStatusEvidence
    recovery_records: tuple[EdgeR0PressureRecoveryRecord, ...] = Field(min_length=1)
    claim_boundary: Literal[
        "r0_8_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE7_CLAIM_BOUNDARY

    @field_validator("restored_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "storage-restoration timestamp")

    @model_validator(mode="after")
    def validate_restoration(self) -> EdgeR0StorageRestoration:
        if self.used_bytes + self.free_bytes > self.total_bytes:
            raise ValueError("used plus free bytes cannot exceed restored capacity")
        attempt_ids = [record.attempt_id for record in self.recovery_records]
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValueError("pressure recovery attempt IDs must be unique")
        return self


class EdgeR0StorageProofReceipt(StrictPhase7Model):
    schema_version: Literal["ets.edge-compact-r0-storage-proof-receipt.v1"] = (
        "ets.edge-compact-r0-storage-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    subject_kind: StorageProofSubject
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
        "r0_8_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE7_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "storage-proof verification timestamp")


class EdgeR0StorageRecoveryCanary(StrictPhase7Model):
    schema_version: Literal["ets.edge-compact-r0-storage-recovery-canary.v1"] = (
        "ets.edge-compact-r0-storage-recovery-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    restoration_id: str = Field(min_length=1, max_length=256)
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
        "r0_8_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE7_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.8 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0StorageRecoveryCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("canary request SHA-256 must match Edge content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("canary verification cannot precede capture")
        return self


class EdgeR0Phase7Evaluation(StrictPhase7Model):
    schema_version: Literal["ets.edge-compact-r0-phase7-evaluation.v1"] = (
        "ets.edge-compact-r0-phase7-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase6_evaluation_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    restoration_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    attempted_count: int = Field(ge=0)
    pressure_committed_count: int = Field(ge=0)
    rejected_backpressure_count: int = Field(ge=0)
    watermarks_observed: bool
    recovery_headroom_preserved: bool
    backpressure_before_unsafe_ack: bool
    attempt_reconciliation_complete: bool
    acknowledged_commits_preserved: bool
    preexisting_evidence_preserved: bool
    history_not_rewritten: bool
    normal_operation_restored: bool
    post_recovery_canary_valid: bool
    r0_8_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE7_DISPOSITION
    claim_boundary: Literal[
        "r0_8_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE7_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.8 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase7Evaluation:
        expected = (
            self.watermarks_observed
            and self.recovery_headroom_preserved
            and self.backpressure_before_unsafe_ack
            and self.attempt_reconciliation_complete
            and self.acknowledged_commits_preserved
            and self.preexisting_evidence_preserved
            and self.history_not_rewritten
            and self.normal_operation_restored
            and self.post_recovery_canary_valid
            and not self.issues
        )
        if self.r0_8_passed != expected:
            raise ValueError("r0_8_passed must match the component results and issues")
        return self


def load_phase6_evaluation(raw: bytes) -> EdgeR0Phase6Evaluation:
    return EdgeR0Phase6Evaluation.model_validate_json(raw)


def load_storage_baseline(raw: bytes) -> EdgeR0StorageBaseline:
    return EdgeR0StorageBaseline.model_validate_json(raw)


def load_storage_transition(raw: bytes) -> EdgeR0StorageTransitionObservation:
    return EdgeR0StorageTransitionObservation.model_validate_json(raw)


def load_pressure_window(raw: bytes) -> EdgeR0StoragePressureWindow:
    return EdgeR0StoragePressureWindow.model_validate_json(raw)


def load_storage_restoration(raw: bytes) -> EdgeR0StorageRestoration:
    return EdgeR0StorageRestoration.model_validate_json(raw)


def load_storage_proof(raw: bytes) -> EdgeR0StorageProofReceipt:
    return EdgeR0StorageProofReceipt.model_validate_json(raw)


def load_recovery_canary(raw: bytes) -> EdgeR0StorageRecoveryCanary:
    return EdgeR0StorageRecoveryCanary.model_validate_json(raw)


def evaluate_r0_8(
    manifest: EdgeCompactR0BenchManifest,
    phase6: EdgeR0Phase6Evaluation,
    baseline: EdgeR0StorageBaseline,
    high: EdgeR0StorageTransitionObservation,
    critical: EdgeR0StorageTransitionObservation,
    window: EdgeR0StoragePressureWindow,
    restoration: EdgeR0StorageRestoration,
    proofs: tuple[EdgeR0StorageProofReceipt, ...],
    canary: EdgeR0StorageRecoveryCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase7Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.8: bench manifest not ready: {blocker}")
    if not phase6.r0_7_passed:
        issues.append("R0.8: R0.7 did not pass")
    if phase6.manifest_id != manifest.manifest_id or phase6.asset_id != asset_id:
        issues.append("R0.8: R0.7 evaluation is bound to another DUT")

    if baseline.manifest_id != manifest.manifest_id or baseline.asset_id != asset_id:
        issues.append("R0.8: storage baseline is bound to another DUT")
    if baseline.phase6_evaluation_id != phase6.evaluation_id:
        issues.append("R0.8: storage baseline references another R0.7 evaluation")
    if baseline.phase6_evaluation_sha256 != canonical_sha256(
        phase6.model_dump(mode="json")
    ):
        issues.append("R0.8: R0.7 digest binding mismatch")

    storage_control = next(
        (control for control in manifest.controls if control.kind is BenchControlKind.STORAGE),
        None,
    )
    if storage_control is None or baseline.storage_control_id != storage_control.control_id:
        issues.append("R0.8: baseline does not bind to the W1-1 storage control")

    for transition, expected_band in (
        (high, StoragePressureBand.HIGH),
        (critical, StoragePressureBand.CRITICAL),
    ):
        if transition.baseline_id != baseline.baseline_id:
            issues.append(f"R0.8: {expected_band.value} transition references another baseline")
        if transition.baseline_sha256 != canonical_sha256(
            baseline.model_dump(mode="json")
        ):
            issues.append(f"R0.8: {expected_band.value} baseline digest mismatch")
        if transition.band is not expected_band:
            issues.append(f"R0.8: expected {expected_band.value} transition band")
        if transition.total_bytes != baseline.total_bytes:
            issues.append(f"R0.8: {expected_band.value} capacity changed unexpectedly")

    high_crossed = (
        high.used_bytes >= baseline.high_watermark_used_bytes
        and high.used_bytes < baseline.critical_watermark_used_bytes
    )
    critical_crossed = critical.used_bytes >= baseline.critical_watermark_used_bytes
    watermarks_observed = high_crossed and critical_crossed
    if not high_crossed:
        issues.append("R0.8: high-watermark transition was not independently established")
    if not critical_crossed:
        issues.append("R0.8: critical-watermark transition was not independently established")

    safe_used_ceiling = baseline.total_bytes - baseline.reserved_recovery_bytes
    recovery_headroom_preserved = (
        high.used_bytes <= safe_used_ceiling
        and critical.used_bytes <= safe_used_ceiling
        and high.reserved_headroom_preserved
        and critical.reserved_headroom_preserved
        and high.free_bytes >= baseline.reserved_recovery_bytes
        and critical.free_bytes >= baseline.reserved_recovery_bytes
    )
    if not recovery_headroom_preserved:
        issues.append("R0.8: reserved recovery headroom was violated")

    backpressure_before_unsafe_ack = True
    if not high.backpressure_active:
        issues.append("R0.8: high-watermark transition did not activate backpressure")
        backpressure_before_unsafe_ack = False
    if not critical.backpressure_active:
        issues.append("R0.8: critical-watermark transition did not retain backpressure")
        backpressure_before_unsafe_ack = False
    if critical.authoritative_ingress_enabled:
        issues.append("R0.8: authoritative ingress remained enabled at critical watermark")
        backpressure_before_unsafe_ack = False

    if window.baseline_id != baseline.baseline_id:
        issues.append("R0.8: pressure window references another storage baseline")
    if window.high_transition_id != high.transition_id:
        issues.append("R0.8: pressure window references another high transition")
    if window.critical_transition_id != critical.transition_id:
        issues.append("R0.8: pressure window references another critical transition")
    if window.started_at < high.observed_at:
        issues.append("R0.8: pressure ingress began before high watermark was established")
    if window.completed_at < critical.observed_at:
        issues.append("R0.8: pressure window ended before critical transition observation")

    attempts_by_id = {attempt.attempt_id: attempt for attempt in window.attempts}
    recovery_by_id = {
        record.attempt_id: record for record in restoration.recovery_records
    }
    attempt_ids = set(attempts_by_id)
    recovery_ids = set(recovery_by_id)
    missing_recovery = sorted(attempt_ids - recovery_ids)
    unknown_recovery = sorted(recovery_ids - attempt_ids)
    if missing_recovery:
        issues.append(f"R0.8: missing recovery disposition for attempts: {missing_recovery}")
    if unknown_recovery:
        issues.append(f"R0.8: recovery inventory contains unknown attempts: {unknown_recovery}")

    attempt_reconciliation_complete = not missing_recovery and not unknown_recovery
    acknowledged_commits_preserved = attempt_reconciliation_complete
    committed_count = 0
    rejected_count = 0

    for attempt_id in sorted(attempt_ids & recovery_ids):
        attempt = attempts_by_id[attempt_id]
        recovered = recovery_by_id[attempt_id]

        if (
            attempt.band is StoragePressureBand.CRITICAL
            and attempt.disposition is PressureIngressDisposition.AUTHORITATIVELY_COMMITTED
        ):
            issues.append(
                f"R0.8: critical-band attempt was authoritatively committed: {attempt_id}"
            )
            backpressure_before_unsafe_ack = False

        if attempt.disposition is PressureIngressDisposition.AUTHORITATIVELY_COMMITTED:
            committed_count += 1
            if recovered.authoritative_commit_count != 1:
                issues.append(
                    f"R0.8: acknowledged commit was not preserved exactly once: {attempt_id}"
                )
                acknowledged_commits_preserved = False
            if recovered.recovered_event_id != attempt.event_id:
                issues.append(f"R0.8: recovered event binding mismatch for {attempt_id}")
                acknowledged_commits_preserved = False
            if recovered.recovered_proof_sha256 != attempt.proof_artifact_sha256:
                issues.append(f"R0.8: recovered proof binding mismatch for {attempt_id}")
                acknowledged_commits_preserved = False
        elif attempt.disposition is PressureIngressDisposition.REJECTED_BACKPRESSURE:
            rejected_count += 1
            if recovered.authoritative_commit_count != 0:
                issues.append(
                    f"R0.8: explicitly rejected attempt later became committed: {attempt_id}"
                )
                attempt_reconciliation_complete = False
        elif recovered.authoritative_commit_count > 1:
            issues.append(
                f"R0.8: unacknowledged attempt recovered multiple commits: {attempt_id}"
            )
            attempt_reconciliation_complete = False

    if not any(
        attempt.band is StoragePressureBand.CRITICAL
        and attempt.disposition is PressureIngressDisposition.REJECTED_BACKPRESSURE
        for attempt in window.attempts
    ):
        issues.append("R0.8: no explicit critical-band backpressure rejection was retained")
        backpressure_before_unsafe_ack = False

    if restoration.baseline_id != baseline.baseline_id:
        issues.append("R0.8: restoration references another storage baseline")
    if restoration.critical_transition_id != critical.transition_id:
        issues.append("R0.8: restoration references another critical transition")
    if restoration.restored_at < window.completed_at:
        issues.append("R0.8: restoration predates completion of pressure window")

    queue = restoration.final_queue_state
    queue_clean = (
        queue.queue_depth == 0
        and queue.queue_bytes == 0
        and queue.pending == 0
        and queue.in_flight == 0
        and queue.retryable_failure == 0
        and queue.terminal_failure == 0
    )
    normal_operation_restored = (
        restoration.normal_range_restored
        and restoration.used_bytes < baseline.high_watermark_used_bytes
        and restoration.free_bytes >= baseline.reserved_recovery_bytes
        and queue_clean
    )
    if not normal_operation_restored:
        issues.append("R0.8: storage/queue state did not return to normal operating range")

    history_not_rewritten = (
        restoration.pre_pressure_log_head_observed
        and restoration.pre_pressure_log_head_sha256 == baseline.log_head_sha256
        and restoration.post_recovery_checkpoint_index >= baseline.local_checkpoint_index
    )
    if not restoration.pre_pressure_log_head_observed:
        issues.append("R0.8: pre-pressure log head was not observed after restoration")
    if restoration.pre_pressure_log_head_sha256 != baseline.log_head_sha256:
        issues.append("R0.8: pre-pressure log-head digest changed after restoration")
    if restoration.post_recovery_checkpoint_index < baseline.local_checkpoint_index:
        issues.append("R0.8: local checkpoint regressed after storage recovery")

    proof_keys: dict[tuple[StorageProofSubject, str], EdgeR0StorageProofReceipt] = {}
    for proof_receipt in proofs:
        key = (proof_receipt.subject_kind, proof_receipt.subject_id)
        if key in proof_keys:
            issues.append(
                "R0.8: duplicate storage proof receipt for "
                f"{proof_receipt.subject_kind.value}:{proof_receipt.subject_id}"
            )
            continue
        proof_keys[key] = proof_receipt

    verifier_host = manifest.verifier.verifier_host_id
    preexisting_evidence_preserved = True
    for proof_digest in baseline.representative_proof_sha256:
        receipt = proof_keys.get((StorageProofSubject.PRE_PRESSURE, proof_digest))
        if receipt is None:
            issues.append(f"R0.8: missing pre-pressure proof verification for {proof_digest}")
            preexisting_evidence_preserved = False
            continue
        if receipt.proof_artifact_sha256 != proof_digest:
            issues.append(f"R0.8: pre-pressure proof digest mismatch for {proof_digest}")
            preexisting_evidence_preserved = False
        if not receipt.inclusion_valid or not receipt.independent_execution_context:
            issues.append(f"R0.8: pre-pressure proof did not independently verify: {proof_digest}")
            preexisting_evidence_preserved = False
        if verifier_host is None or receipt.verifier_host_id != verifier_host:
            issues.append(f"R0.8: pre-pressure verifier host mismatch for {proof_digest}")
            preexisting_evidence_preserved = False

    for attempt_id, recovered in recovery_by_id.items():
        if recovered.authoritative_commit_count != 1:
            continue
        receipt = proof_keys.get((StorageProofSubject.PRESSURE_ATTEMPT, attempt_id))
        if receipt is None:
            issues.append(f"R0.8: recovered pressure commit lacks proof: {attempt_id}")
            acknowledged_commits_preserved = False
            continue
        if receipt.proof_artifact_sha256 != recovered.recovered_proof_sha256:
            issues.append(f"R0.8: pressure proof digest mismatch for {attempt_id}")
            acknowledged_commits_preserved = False
        if not receipt.inclusion_valid or not receipt.independent_execution_context:
            issues.append(f"R0.8: pressure commit did not independently verify: {attempt_id}")
            acknowledged_commits_preserved = False
        if verifier_host is None or receipt.verifier_host_id != verifier_host:
            issues.append(f"R0.8: pressure verifier host mismatch for {attempt_id}")
            acknowledged_commits_preserved = False

    canary_valid = True
    if canary.restoration_id != restoration.restoration_id:
        issues.append("R0.8: recovery canary references another restoration")
        canary_valid = False
    if canary.captured_at < restoration.restored_at:
        issues.append("R0.8: recovery canary predates storage restoration")
        canary_valid = False
    if not canary.inclusion_valid or not canary.independent_execution_context:
        issues.append("R0.8: post-recovery canary did not verify independently")
        canary_valid = False
    if verifier_host is None or canary.verifier_host_id != verifier_host:
        issues.append("R0.8: canary verifier host does not match bench binding")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase6_evaluation_id": phase6.evaluation_id,
        "baseline_id": baseline.baseline_id,
        "window_id": window.window_id,
        "restoration_id": restoration.restoration_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        watermarks_observed
        and recovery_headroom_preserved
        and backpressure_before_unsafe_ack
        and attempt_reconciliation_complete
        and acknowledged_commits_preserved
        and preexisting_evidence_preserved
        and history_not_rewritten
        and normal_operation_restored
        and canary_valid
        and not issues
    )
    return EdgeR0Phase7Evaluation(
        evaluation_id=f"edge-r0-phase7-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase6_evaluation_id=phase6.evaluation_id,
        baseline_id=baseline.baseline_id,
        window_id=window.window_id,
        restoration_id=restoration.restoration_id,
        evaluated_at=evaluated_at,
        attempted_count=len(window.attempts),
        pressure_committed_count=committed_count,
        rejected_backpressure_count=rejected_count,
        watermarks_observed=watermarks_observed,
        recovery_headroom_preserved=recovery_headroom_preserved,
        backpressure_before_unsafe_ack=backpressure_before_unsafe_ack,
        attempt_reconciliation_complete=attempt_reconciliation_complete,
        acknowledged_commits_preserved=acknowledged_commits_preserved,
        preexisting_evidence_preserved=preexisting_evidence_preserved,
        history_not_rewritten=history_not_rewritten,
        normal_operation_restored=normal_operation_restored,
        post_recovery_canary_valid=canary_valid,
        r0_8_passed=passed,
        issues=tuple(issues),
    )


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
        description="ETS Wave 1 Edge Compact R0 R0.8 storage-pressure evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser("evaluate-r0-8")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase6-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--baseline", type=Path, required=True)
    evaluate_parser.add_argument("--high-transition", type=Path, required=True)
    evaluate_parser.add_argument("--critical-transition", type=Path, required=True)
    evaluate_parser.add_argument("--pressure-window", type=Path, required=True)
    evaluate_parser.add_argument("--restoration", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-8":
        result = evaluate_r0_8(
            load_manifest(args.manifest.read_bytes()),
            load_phase6_evaluation(args.phase6_evaluation.read_bytes()),
            load_storage_baseline(args.baseline.read_bytes()),
            load_storage_transition(args.high_transition.read_bytes()),
            load_storage_transition(args.critical_transition.read_bytes()),
            load_pressure_window(args.pressure_window.read_bytes()),
            load_storage_restoration(args.restoration.read_bytes()),
            tuple(load_storage_proof(path.read_bytes()) for path in args.proof_receipt),
            load_recovery_canary(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_8_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
