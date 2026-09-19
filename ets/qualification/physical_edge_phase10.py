"""Wave 1 Edge Compact R0 clock-displacement and time-quality evidence.

R0.11 evaluates forward wall-clock displacement, rollback, unsynchronized time and
restoration while preserving monotonic/log ordering and explicit time quality. The
evaluator never changes system time.
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
from ets.qualification.physical_edge_phase9 import EdgeR0Phase9Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE10_CLAIM_BOUNDARY: Literal[
    "r0_11_phase_evidence_not_a_physical_qualification_result"
] = "r0_11_phase_evidence_not_a_physical_qualification_result"
_PHASE10_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase10Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class TimeQuality(StrEnum):
    TRUSTED_SYNCHRONIZED = "trusted_synchronized"
    EXTERNALLY_BOUNDED_UNSYNCHRONIZED = "externally_bounded_unsynchronized"
    DEVICE_RELATIVE_UNTRUSTED = "device_relative_untrusted"
    UNKNOWN = "unknown"


class ClockSyncState(StrEnum):
    SYNCHRONIZED = "synchronized"
    UNSYNCHRONIZED = "unsynchronized"
    UNAVAILABLE = "unavailable"


class ClockFaultKind(StrEnum):
    FORWARD_JUMP = "forward_jump"
    BACKWARD_ROLLBACK = "backward_rollback"
    UNSYNCHRONIZED = "unsynchronized"
    RESTORE = "restore"


class ClockProofSubject(StrEnum):
    PRE_FAULT = "pre_fault"
    FAULT_EVENT = "fault_event"


class EdgeR0ClockBaseline(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-clock-baseline.v1"] = (
        "ets.edge-compact-r0-clock-baseline.v1"
    )
    baseline_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase9_evaluation_id: str = Field(min_length=1, max_length=256)
    phase9_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    boot_id: str = Field(min_length=1, max_length=128)
    wall_clock_utc: datetime
    monotonic_ns: int = Field(ge=0)
    external_utc: datetime
    sync_state: ClockSyncState
    time_quality: TimeQuality
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    log_head_sha256: str = Field(pattern=_SHA256_RE)
    queue_state: EdgeSyncStatusEvidence
    queue_item_limit: int = Field(gt=0)
    queue_byte_limit: int = Field(gt=0)
    queue_item_allowance: int = Field(default=0, ge=0)
    queue_byte_allowance: int = Field(default=0, ge=0)
    storage_used_bytes: int = Field(ge=0)
    storage_high_watermark_used_bytes: int = Field(gt=0)
    network_connected: Literal[True] = True
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @field_validator("captured_at", "wall_clock_utc", "external_utc")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "clock-baseline timestamp")

    @model_validator(mode="after")
    def validate_baseline(self) -> EdgeR0ClockBaseline:
        if self.sync_state is not ClockSyncState.SYNCHRONIZED:
            raise ValueError("R0.11 baseline must start synchronized")
        if self.time_quality is not TimeQuality.TRUSTED_SYNCHRONIZED:
            raise ValueError("R0.11 baseline must start with trusted synchronized time")
        if self.queue_state.max_items != self.queue_item_limit:
            raise ValueError("baseline queue max_items mismatch")
        if self.queue_state.max_bytes != self.queue_byte_limit:
            raise ValueError("baseline queue max_bytes mismatch")
        if self.queue_state.queue_depth > self.queue_item_limit:
            raise ValueError("baseline queue depth exceeds R0.9 boundary")
        if self.queue_state.queue_bytes > self.queue_byte_limit:
            raise ValueError("baseline queue bytes exceed R0.9 boundary")
        if self.storage_used_bytes >= self.storage_high_watermark_used_bytes:
            raise ValueError("baseline storage exceeds R0.8 high watermark")
        if len(self.representative_proof_sha256) != len(
            set(self.representative_proof_sha256)
        ):
            raise ValueError("representative proof digests must be unique")
        return self


class EdgeR0ClockFaultStep(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-clock-fault-step.v1"] = (
        "ets.edge-compact-r0-clock-fault-step.v1"
    )
    step_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    kind: ClockFaultKind
    requested_offset_seconds: float
    max_duration_seconds: float = Field(gt=0, le=3600)
    offset_tolerance_seconds: float = Field(ge=0, le=60)
    expected_sync_state: ClockSyncState
    expected_time_quality: TimeQuality
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_step(self) -> EdgeR0ClockFaultStep:
        if self.kind is ClockFaultKind.FORWARD_JUMP:
            if self.requested_offset_seconds <= 0:
                raise ValueError("forward jump must request a positive offset")
        elif self.kind is ClockFaultKind.BACKWARD_ROLLBACK:
            if self.requested_offset_seconds >= 0:
                raise ValueError("rollback must request a negative offset")
        elif self.kind is ClockFaultKind.RESTORE:
            if abs(self.requested_offset_seconds) > self.offset_tolerance_seconds:
                raise ValueError("restore step must target approximately zero offset")
            if self.expected_sync_state is not ClockSyncState.SYNCHRONIZED:
                raise ValueError("restore must expect synchronized clock state")
            if self.expected_time_quality is not TimeQuality.TRUSTED_SYNCHRONIZED:
                raise ValueError("restore must expect trusted synchronized time")
        return self


class EdgeR0ClockFaultProfile(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-clock-fault-profile.v1"] = (
        "ets.edge-compact-r0-clock-fault-profile.v1"
    )
    profile_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    generated_at: datetime
    max_total_duration_seconds: float = Field(gt=0, le=86_400)
    steps: tuple[EdgeR0ClockFaultStep, ...] = Field(min_length=3)
    controller_definition_sha256: str = Field(pattern=_SHA256_RE)
    operator_stop_condition: str = Field(min_length=1, max_length=1024)
    evaluator_sets_system_time: Literal[False] = False
    claim_boundary: Literal[
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @field_validator("generated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "clock-profile timestamp")

    @model_validator(mode="after")
    def validate_steps(self) -> EdgeR0ClockFaultProfile:
        sequences = [step.sequence_number for step in self.steps]
        ids = [step.step_id for step in self.steps]
        kinds = {step.kind for step in self.steps}
        if sequences != list(range(1, len(self.steps) + 1)):
            raise ValueError("clock-fault step sequence must be contiguous")
        if len(ids) != len(set(ids)):
            raise ValueError("clock-fault step IDs must be unique")
        required = {
            ClockFaultKind.FORWARD_JUMP,
            ClockFaultKind.BACKWARD_ROLLBACK,
            ClockFaultKind.RESTORE,
        }
        if not required.issubset(kinds):
            raise ValueError("profile must include forward, rollback and restore steps")
        if self.steps[-1].kind is not ClockFaultKind.RESTORE:
            raise ValueError("final clock-fault step must restore synchronization")
        return self


class EdgeR0ClockTransition(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-clock-transition.v1"] = (
        "ets.edge-compact-r0-clock-transition.v1"
    )
    transition_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    step_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    commanded_at: datetime
    observed_at: datetime
    dut_wall_clock_utc: datetime
    monotonic_ns: int = Field(ge=0)
    external_utc: datetime
    observed_sync_state: ClockSyncState
    observed_time_quality: TimeQuality
    queue_depth: int = Field(ge=0)
    queue_bytes: int = Field(ge=0)
    storage_used_bytes: int = Field(ge=0)
    network_connected: bool
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    external_observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    dut_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @field_validator(
        "commanded_at",
        "observed_at",
        "dut_wall_clock_utc",
        "external_utc",
    )
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "clock-transition timestamp")

    @model_validator(mode="after")
    def validate_transition(self) -> EdgeR0ClockTransition:
        if self.observed_at < self.commanded_at:
            raise ValueError("clock transition observation cannot precede command")
        return self


class EdgeR0TimedEvidenceEvent(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-timed-event.v1"] = (
        "ets.edge-compact-r0-timed-event.v1"
    )
    event_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    fault_step_id: str = Field(min_length=1, max_length=256)
    captured_wall_clock_utc: datetime
    monotonic_ns: int = Field(ge=0)
    external_utc: datetime
    sync_state: ClockSyncState
    time_quality: TimeQuality
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    local_checkpoint_index: int = Field(ge=0)
    log_head_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @field_validator("captured_wall_clock_utc", "external_utc")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "timed-event timestamp")

    @model_validator(mode="after")
    def validate_content(self) -> EdgeR0TimedEvidenceEvent:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("timed-event payload digest must match content_hash")
        return self


class EdgeR0ClockFaultWindow(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-clock-fault-window.v1"] = (
        "ets.edge-compact-r0-clock-fault-window.v1"
    )
    window_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    transitions: tuple[EdgeR0ClockTransition, ...] = Field(min_length=3)
    events: tuple[EdgeR0TimedEvidenceEvent, ...] = Field(min_length=3)
    event_commitment_sha256: str = Field(pattern=_SHA256_RE)
    controller_timeline_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "clock-window timestamp")

    @model_validator(mode="after")
    def validate_window(self) -> EdgeR0ClockFaultWindow:
        if self.completed_at <= self.started_at:
            raise ValueError("clock-fault window must have positive duration")
        transition_seq = [item.sequence_number for item in self.transitions]
        event_seq = [item.sequence_number for item in self.events]
        if transition_seq != list(range(1, len(self.transitions) + 1)):
            raise ValueError("clock transition sequence must be contiguous")
        if event_seq != list(range(1, len(self.events) + 1)):
            raise ValueError("timed-event sequence must be contiguous")
        return self


class EdgeR0ClockRestoration(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-clock-restoration.v1"] = (
        "ets.edge-compact-r0-clock-restoration.v1"
    )
    restoration_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    restored_at: datetime
    wall_clock_utc: datetime
    external_utc: datetime
    monotonic_ns: int = Field(ge=0)
    sync_state: ClockSyncState
    time_quality: TimeQuality
    restored_offset_tolerance_seconds: float = Field(ge=0, le=60)
    preserved_event_commitment_sha256: str = Field(pattern=_SHA256_RE)
    pre_fault_log_head_sha256: str = Field(pattern=_SHA256_RE)
    pre_fault_log_head_observed: bool
    final_checkpoint_index: int = Field(ge=0)
    final_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    final_queue_state: EdgeSyncStatusEvidence
    storage_used_bytes: int = Field(ge=0)
    network_connected: bool
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @field_validator("restored_at", "wall_clock_utc", "external_utc")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "clock-restoration timestamp")


class EdgeR0ClockProofReceipt(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-clock-proof-receipt.v1"] = (
        "ets.edge-compact-r0-clock-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    subject_kind: ClockProofSubject
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
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "clock-proof timestamp")


class EdgeR0ClockRecoveryCanary(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-clock-recovery-canary.v1"] = (
        "ets.edge-compact-r0-clock-recovery-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    restoration_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    time_quality: TimeQuality
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.11 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0ClockRecoveryCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("clock canary request SHA-256 must match content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("clock canary verification cannot precede capture")
        return self


class EdgeR0Phase10Evaluation(StrictPhase10Model):
    schema_version: Literal["ets.edge-compact-r0-phase10-evaluation.v1"] = (
        "ets.edge-compact-r0-phase10-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase9_evaluation_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    restoration_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    transition_profile_observed: bool
    monotonic_order_preserved: bool
    log_checkpoint_order_preserved: bool
    time_quality_preserved: bool
    wall_clock_offsets_observed: bool
    prior_evidence_not_rewritten: bool
    prior_phase_boundaries_preserved: bool
    independent_verification_complete: bool
    restoration_valid: bool
    post_recovery_canary_valid: bool
    r0_11_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE10_DISPOSITION
    claim_boundary: Literal[
        "r0_11_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE10_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.11 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase10Evaluation:
        expected = (
            self.transition_profile_observed
            and self.monotonic_order_preserved
            and self.log_checkpoint_order_preserved
            and self.time_quality_preserved
            and self.wall_clock_offsets_observed
            and self.prior_evidence_not_rewritten
            and self.prior_phase_boundaries_preserved
            and self.independent_verification_complete
            and self.restoration_valid
            and self.post_recovery_canary_valid
            and not self.issues
        )
        if self.r0_11_passed != expected:
            raise ValueError("r0_11_passed must match component results and issues")
        return self


def build_timed_event_commitment(
    events: tuple[EdgeR0TimedEvidenceEvent, ...],
) -> str:
    return canonical_sha256(
        [event.model_dump(mode="json") for event in sorted(events, key=lambda x: x.sequence_number)]
    )


def evaluate_r0_11(
    manifest: EdgeCompactR0BenchManifest,
    phase9: EdgeR0Phase9Evaluation,
    baseline: EdgeR0ClockBaseline,
    profile: EdgeR0ClockFaultProfile,
    window: EdgeR0ClockFaultWindow,
    restoration: EdgeR0ClockRestoration,
    proofs: tuple[EdgeR0ClockProofReceipt, ...],
    canary: EdgeR0ClockRecoveryCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase10Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.11: bench manifest not ready: {blocker}")
    if not phase9.r0_10_passed:
        issues.append("R0.11: R0.10 did not pass")
    if phase9.manifest_id != manifest.manifest_id or phase9.asset_id != asset_id:
        issues.append("R0.11: R0.10 evaluation is bound to another DUT")
    if baseline.manifest_id != manifest.manifest_id or baseline.asset_id != asset_id:
        issues.append("R0.11: baseline is bound to another DUT")
    if baseline.phase9_evaluation_id != phase9.evaluation_id:
        issues.append("R0.11: baseline references another R0.10 evaluation")
    if baseline.phase9_evaluation_sha256 != canonical_sha256(
        phase9.model_dump(mode="json")
    ):
        issues.append("R0.11: R0.10 digest binding mismatch")
    if profile.baseline_id != baseline.baseline_id:
        issues.append("R0.11: fault profile references another baseline")
    if window.baseline_id != baseline.baseline_id or window.profile_id != profile.profile_id:
        issues.append("R0.11: clock-fault window binding mismatch")
    if restoration.baseline_id != baseline.baseline_id:
        issues.append("R0.11: restoration references another baseline")
    if restoration.window_id != window.window_id:
        issues.append("R0.11: restoration references another clock-fault window")

    transition_profile_observed = len(window.transitions) == len(profile.steps)
    if not transition_profile_observed:
        issues.append("R0.11: transition count does not match fault profile")

    steps_by_id = {step.step_id: step for step in profile.steps}
    prior_phase_boundaries_preserved = True
    wall_clock_offsets_observed = True
    time_quality_preserved = True
    last_monotonic = baseline.monotonic_ns

    max_items = baseline.queue_item_limit + baseline.queue_item_allowance
    max_bytes = baseline.queue_byte_limit + baseline.queue_byte_allowance

    for index, transition in enumerate(window.transitions):
        if transition.profile_id != profile.profile_id:
            issues.append(
                f"R0.11: transition references another profile: {transition.transition_id}"
            )
            transition_profile_observed = False
        if index >= len(profile.steps):
            continue
        step = profile.steps[index]
        if transition.step_id != step.step_id:
            issues.append(
                f"R0.11: transition/step sequence mismatch: {transition.transition_id}"
            )
            transition_profile_observed = False
        observed_offset = (
            transition.dut_wall_clock_utc - transition.external_utc
        ).total_seconds()
        if abs(observed_offset - step.requested_offset_seconds) > (
            step.offset_tolerance_seconds
        ):
            issues.append(
                f"R0.11: requested wall-clock offset not observed: {transition.step_id}"
            )
            wall_clock_offsets_observed = False
        if transition.observed_sync_state is not step.expected_sync_state:
            issues.append(f"R0.11: sync-state mismatch: {transition.step_id}")
            time_quality_preserved = False
        if transition.observed_time_quality is not step.expected_time_quality:
            issues.append(f"R0.11: time-quality mismatch: {transition.step_id}")
            time_quality_preserved = False
        if transition.monotonic_ns <= last_monotonic:
            issues.append(f"R0.11: monotonic clock regressed: {transition.step_id}")
            transition_profile_observed = False
        last_monotonic = transition.monotonic_ns
        if transition.queue_depth > max_items or transition.queue_bytes > max_bytes:
            issues.append(f"R0.11: R0.9 queue boundary crossed: {transition.step_id}")
            prior_phase_boundaries_preserved = False
        if transition.storage_used_bytes >= baseline.storage_high_watermark_used_bytes:
            issues.append(f"R0.11: R0.8 storage boundary crossed: {transition.step_id}")
            prior_phase_boundaries_preserved = False
        if not transition.network_connected:
            issues.append(f"R0.11: R0.10 network boundary crossed: {transition.step_id}")
            prior_phase_boundaries_preserved = False

    if (window.completed_at - window.started_at).total_seconds() > (
        profile.max_total_duration_seconds
    ):
        issues.append("R0.11: clock-fault window exceeded declared duration")
        transition_profile_observed = False

    event_commitment = build_timed_event_commitment(window.events)
    prior_evidence_not_rewritten = window.event_commitment_sha256 == event_commitment
    if not prior_evidence_not_rewritten:
        issues.append("R0.11: retained fault-window event commitment mismatch")

    monotonic_order_preserved = True
    log_checkpoint_order_preserved = True
    previous_event_monotonic = baseline.monotonic_ns
    previous_checkpoint = baseline.local_checkpoint_index
    event_ids: set[str] = set()

    for event in window.events:
        if event.event_id in event_ids:
            issues.append(f"R0.11: duplicate event identity: {event.event_id}")
            log_checkpoint_order_preserved = False
        event_ids.add(event.event_id)
        if event.monotonic_ns <= previous_event_monotonic:
            issues.append(f"R0.11: event monotonic ordering regressed: {event.event_id}")
            monotonic_order_preserved = False
        previous_event_monotonic = event.monotonic_ns
        if event.local_checkpoint_index < previous_checkpoint:
            issues.append(f"R0.11: event checkpoint regressed: {event.event_id}")
            log_checkpoint_order_preserved = False
        previous_checkpoint = event.local_checkpoint_index

        step = steps_by_id.get(event.fault_step_id)
        if step is None:
            issues.append(f"R0.11: event references unknown fault step: {event.event_id}")
            time_quality_preserved = False
            continue
        if event.sync_state is not step.expected_sync_state:
            issues.append(f"R0.11: event sync-state mismatch: {event.event_id}")
            time_quality_preserved = False
        if event.time_quality is not step.expected_time_quality:
            issues.append(f"R0.11: event time-quality mismatch: {event.event_id}")
            time_quality_preserved = False

    if restoration.preserved_event_commitment_sha256 != event_commitment:
        issues.append("R0.11: restoration rewrote fault-window event commitment")
        prior_evidence_not_rewritten = False
    if not restoration.pre_fault_log_head_observed:
        issues.append("R0.11: pre-fault log head was not observed after restoration")
        prior_evidence_not_rewritten = False
    if restoration.pre_fault_log_head_sha256 != baseline.log_head_sha256:
        issues.append("R0.11: pre-fault log-head digest changed")
        prior_evidence_not_rewritten = False
    if restoration.final_checkpoint_index < previous_checkpoint:
        issues.append("R0.11: final checkpoint regressed")
        log_checkpoint_order_preserved = False
    if restoration.monotonic_ns <= previous_event_monotonic:
        issues.append("R0.11: restoration monotonic reading regressed")
        monotonic_order_preserved = False

    restored_offset = (
        restoration.wall_clock_utc - restoration.external_utc
    ).total_seconds()
    restoration_valid = (
        restoration.sync_state is ClockSyncState.SYNCHRONIZED
        and restoration.time_quality is TimeQuality.TRUSTED_SYNCHRONIZED
        and abs(restored_offset) <= restoration.restored_offset_tolerance_seconds
        and restoration.network_connected
    )
    if not restoration_valid:
        issues.append("R0.11: clock restoration did not return to trusted synchronized state")

    final_queue = restoration.final_queue_state
    if (
        final_queue.queue_depth > max_items
        or final_queue.queue_bytes > max_bytes
        or restoration.storage_used_bytes >= baseline.storage_high_watermark_used_bytes
        or not restoration.network_connected
    ):
        issues.append("R0.11: restoration crossed a prior qualification boundary")
        prior_phase_boundaries_preserved = False

    proof_keys: dict[tuple[ClockProofSubject, str], EdgeR0ClockProofReceipt] = {}
    for proof_receipt in proofs:
        key = (proof_receipt.subject_kind, proof_receipt.subject_id)
        if key in proof_keys:
            issues.append(
                "R0.11: duplicate proof receipt for "
                f"{proof_receipt.subject_kind.value}:{proof_receipt.subject_id}"
            )
            continue
        proof_keys[key] = proof_receipt

    verifier_host = manifest.verifier.verifier_host_id
    independent_verification_complete = True

    for proof_digest in baseline.representative_proof_sha256:
        pre_receipt = proof_keys.get((ClockProofSubject.PRE_FAULT, proof_digest))
        if pre_receipt is None:
            issues.append(f"R0.11: missing pre-fault proof verification: {proof_digest}")
            independent_verification_complete = False
            continue
        if pre_receipt.proof_artifact_sha256 != proof_digest:
            issues.append(f"R0.11: pre-fault proof digest mismatch: {proof_digest}")
            independent_verification_complete = False
        if (
            not pre_receipt.inclusion_valid
            or not pre_receipt.independent_execution_context
            or verifier_host is None
            or pre_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.11: pre-fault proof failed independent verification: {proof_digest}"
            )
            independent_verification_complete = False

    for event in window.events:
        event_receipt = proof_keys.get((ClockProofSubject.FAULT_EVENT, event.event_id))
        if event_receipt is None:
            issues.append(f"R0.11: missing event proof receipt: {event.event_id}")
            independent_verification_complete = False
            continue
        if event_receipt.proof_artifact_sha256 != event.proof_artifact_sha256:
            issues.append(f"R0.11: event proof digest mismatch: {event.event_id}")
            independent_verification_complete = False
        if (
            not event_receipt.inclusion_valid
            or not event_receipt.independent_execution_context
            or verifier_host is None
            or event_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.11: event proof failed independent verification: {event.event_id}"
            )
            independent_verification_complete = False

    canary_valid = True
    if canary.restoration_id != restoration.restoration_id:
        issues.append("R0.11: canary references another restoration")
        canary_valid = False
    if canary.captured_at < restoration.restored_at:
        issues.append("R0.11: canary predates restoration")
        canary_valid = False
    if canary.time_quality is not TimeQuality.TRUSTED_SYNCHRONIZED:
        issues.append("R0.11: canary did not use restored trusted time quality")
        canary_valid = False
    if (
        not canary.inclusion_valid
        or not canary.independent_execution_context
        or verifier_host is None
        or canary.verifier_host_id != verifier_host
    ):
        issues.append("R0.11: post-recovery canary did not independently verify")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase9_evaluation_id": phase9.evaluation_id,
        "baseline_id": baseline.baseline_id,
        "profile_id": profile.profile_id,
        "window_id": window.window_id,
        "restoration_id": restoration.restoration_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        transition_profile_observed
        and monotonic_order_preserved
        and log_checkpoint_order_preserved
        and time_quality_preserved
        and wall_clock_offsets_observed
        and prior_evidence_not_rewritten
        and prior_phase_boundaries_preserved
        and independent_verification_complete
        and restoration_valid
        and canary_valid
        and not issues
    )
    return EdgeR0Phase10Evaluation(
        evaluation_id=f"edge-r0-phase10-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase9_evaluation_id=phase9.evaluation_id,
        baseline_id=baseline.baseline_id,
        profile_id=profile.profile_id,
        window_id=window.window_id,
        restoration_id=restoration.restoration_id,
        evaluated_at=evaluated_at,
        transition_profile_observed=transition_profile_observed,
        monotonic_order_preserved=monotonic_order_preserved,
        log_checkpoint_order_preserved=log_checkpoint_order_preserved,
        time_quality_preserved=time_quality_preserved,
        wall_clock_offsets_observed=wall_clock_offsets_observed,
        prior_evidence_not_rewritten=prior_evidence_not_rewritten,
        prior_phase_boundaries_preserved=prior_phase_boundaries_preserved,
        independent_verification_complete=independent_verification_complete,
        restoration_valid=restoration_valid,
        post_recovery_canary_valid=canary_valid,
        r0_11_passed=passed,
        issues=tuple(issues),
    )


def load_phase9_evaluation(raw: bytes) -> EdgeR0Phase9Evaluation:
    return EdgeR0Phase9Evaluation.model_validate_json(raw)


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
        description="ETS Wave 1 Edge Compact R0 R0.11 clock-displacement evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser("evaluate-r0-11")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase9-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--baseline", type=Path, required=True)
    evaluate_parser.add_argument("--fault-profile", type=Path, required=True)
    evaluate_parser.add_argument("--window", type=Path, required=True)
    evaluate_parser.add_argument("--restoration", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-11":
        result = evaluate_r0_11(
            load_manifest(args.manifest.read_bytes()),
            load_phase9_evaluation(args.phase9_evaluation.read_bytes()),
            EdgeR0ClockBaseline.model_validate_json(args.baseline.read_bytes()),
            EdgeR0ClockFaultProfile.model_validate_json(args.fault_profile.read_bytes()),
            EdgeR0ClockFaultWindow.model_validate_json(args.window.read_bytes()),
            EdgeR0ClockRestoration.model_validate_json(args.restoration.read_bytes()),
            tuple(
                EdgeR0ClockProofReceipt.model_validate_json(path.read_bytes())
                for path in args.proof_receipt
            ),
            EdgeR0ClockRecoveryCanary.model_validate_json(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_11_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
