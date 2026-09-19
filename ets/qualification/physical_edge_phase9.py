"""Wave 1 Edge Compact R0 bounded network-instability evidence.

R0.10 evaluates repeated disconnect/reconnect, latency and packet-loss behavior while
the DUT remains powered and prior storage/queue qualification boundaries stay healthy.
The evaluator records retained evidence only; it never injects network faults.
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
from ets.qualification.physical_edge_phase8 import EdgeR0Phase8Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE9_CLAIM_BOUNDARY: Literal[
    "r0_10_phase_evidence_not_a_physical_qualification_result"
] = "r0_10_phase_evidence_not_a_physical_qualification_result"
_PHASE9_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase9Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class NetworkState(StrEnum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"


class NetworkProofSubject(StrEnum):
    PRE_INSTABILITY = "pre_instability"
    INSTABILITY_RECORD = "instability_record"


class EdgeR0NetworkBaseline(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-network-baseline.v1"] = (
        "ets.edge-compact-r0-network-baseline.v1"
    )
    baseline_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase8_evaluation_id: str = Field(min_length=1, max_length=256)
    phase8_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    interface_name: str = Field(min_length=1, max_length=128)
    interface_mac: str = Field(min_length=1, max_length=64)
    upstream_target: str = Field(min_length=1, max_length=512)
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    queue_state: EdgeSyncStatusEvidence
    queue_item_limit: int = Field(gt=0)
    queue_byte_limit: int = Field(gt=0)
    queue_item_allowance: int = Field(default=0, ge=0)
    queue_byte_allowance: int = Field(default=0, ge=0)
    storage_used_bytes: int = Field(ge=0)
    storage_high_watermark_used_bytes: int = Field(gt=0)
    baseline_rss_bytes: int = Field(gt=0)
    reachability_rtt_ms: float = Field(ge=0)
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "network-baseline timestamp")

    @model_validator(mode="after")
    def validate_baseline(self) -> EdgeR0NetworkBaseline:
        if self.queue_state.max_items != self.queue_item_limit:
            raise ValueError("queue-state max_items must match R0.10 qualification limit")
        if self.queue_state.max_bytes != self.queue_byte_limit:
            raise ValueError("queue-state max_bytes must match R0.10 qualification limit")
        if self.queue_state.queue_depth > self.queue_item_limit:
            raise ValueError("baseline queue depth exceeds R0.9 qualification limit")
        if self.queue_state.queue_bytes > self.queue_byte_limit:
            raise ValueError("baseline queue bytes exceed R0.9 qualification limit")
        if self.storage_used_bytes >= self.storage_high_watermark_used_bytes:
            raise ValueError("R0.10 baseline must remain below R0.8 high watermark")
        if len(self.representative_proof_sha256) != len(
            set(self.representative_proof_sha256)
        ):
            raise ValueError("representative proof digests must be unique")
        return self


class EdgeR0NetworkFaultProfile(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-network-fault-profile.v1"] = (
        "ets.edge-compact-r0-network-fault-profile.v1"
    )
    profile_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    generated_at: datetime
    disconnect_cycle_count: int = Field(ge=1, le=100)
    max_disconnect_seconds: float = Field(gt=0, le=3600)
    max_added_latency_ms: float = Field(ge=0, le=60_000)
    max_jitter_ms: float = Field(ge=0, le=60_000)
    max_packet_loss_percent: float = Field(ge=0, le=100)
    max_total_duration_seconds: float = Field(gt=0, le=86_400)
    max_retry_attempts_per_minute: int = Field(gt=0, le=100_000)
    max_rss_growth_bytes: int = Field(gt=0)
    controller_definition_sha256: str = Field(pattern=_SHA256_RE)
    operator_stop_condition: str = Field(min_length=1, max_length=1024)
    evaluator_injects_faults: Literal[False] = False
    claim_boundary: Literal[
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @field_validator("generated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "network-profile timestamp")


class EdgeR0NetworkTransition(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-network-transition.v1"] = (
        "ets.edge-compact-r0-network-transition.v1"
    )
    transition_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    cycle_number: int = Field(ge=1)
    commanded_state: NetworkState
    commanded_at: datetime
    externally_observed_state: NetworkState
    externally_observed_at: datetime
    edge_reported_state: NetworkState
    edge_reported_at: datetime
    added_latency_ms: float = Field(ge=0)
    jitter_ms: float = Field(ge=0)
    packet_loss_percent: float = Field(ge=0, le=100)
    queue_depth: int = Field(ge=0)
    queue_bytes: int = Field(ge=0)
    storage_used_bytes: int = Field(ge=0)
    rss_bytes: int = Field(ge=0)
    retry_attempts_last_minute: int = Field(ge=0)
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    external_observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    edge_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @field_validator("commanded_at", "externally_observed_at", "edge_reported_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "network-transition timestamp")

    @model_validator(mode="after")
    def validate_order(self) -> EdgeR0NetworkTransition:
        if self.externally_observed_at < self.commanded_at:
            raise ValueError("external observation cannot precede controller command")
        return self


class EdgeR0InstabilityRecord(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-instability-record.v1"] = (
        "ets.edge-compact-r0-instability-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    local_proof_sha256: str = Field(pattern=_SHA256_RE)
    local_authoritative_commit: Literal[True] = True
    sync_attempted: bool
    network_state_at_sync_attempt: NetworkState
    upstream_accepted_during_window: bool
    upstream_acceptance_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    local_ack_applied_during_window: bool
    claim_boundary: Literal[
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "instability-record timestamp")

    @model_validator(mode="after")
    def validate_record(self) -> EdgeR0InstabilityRecord:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("request payload SHA-256 must match local content_hash")
        if self.upstream_accepted_during_window:
            if not self.sync_attempted:
                raise ValueError("upstream acceptance requires a sync attempt")
            if self.upstream_acceptance_sha256 is None:
                raise ValueError("upstream acceptance requires a retained receipt")
        elif self.upstream_acceptance_sha256 is not None:
            raise ValueError("unaccepted record cannot carry an upstream receipt")
        if (
            self.local_ack_applied_during_window
            and not self.upstream_accepted_during_window
        ):
            raise ValueError("local sync acknowledgement cannot precede upstream acceptance")
        return self


class EdgeR0NetworkInstabilityWindow(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-network-instability-window.v1"] = (
        "ets.edge-compact-r0-network-instability-window.v1"
    )
    window_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    transitions: tuple[EdgeR0NetworkTransition, ...] = Field(min_length=2)
    records: tuple[EdgeR0InstabilityRecord, ...] = Field(min_length=1)
    controller_timeline_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "network-window timestamp")

    @model_validator(mode="after")
    def validate_window(self) -> EdgeR0NetworkInstabilityWindow:
        if self.completed_at <= self.started_at:
            raise ValueError("network-instability window must have positive duration")
        transition_ids = [item.transition_id for item in self.transitions]
        transition_sequences = [item.sequence_number for item in self.transitions]
        record_ids = [item.record_id for item in self.records]
        record_sequences = [item.sequence_number for item in self.records]
        if len(transition_ids) != len(set(transition_ids)):
            raise ValueError("network transition IDs must be unique")
        if transition_sequences != list(range(1, len(self.transitions) + 1)):
            raise ValueError("network transition sequence numbers must be contiguous")
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("instability record IDs must be unique")
        if record_sequences != list(range(1, len(self.records) + 1)):
            raise ValueError("instability record sequence numbers must be contiguous")
        return self


class EdgeR0NetworkRecoveredRecord(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-network-recovered-record.v1"] = (
        "ets.edge-compact-r0-network-recovered-record.v1"
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
    recovery_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_commit_shape(self) -> EdgeR0NetworkRecoveredRecord:
        fields = (
            self.final_upstream_event_id,
            self.final_upstream_acceptance_sha256,
            self.final_proof_sha256,
        )
        if self.final_upstream_commit_count > 0:
            if any(value is None for value in fields):
                raise ValueError("recovered network commit requires event/acceptance/proof")
        elif any(value is not None for value in fields):
            raise ValueError("zero recovered commits cannot carry final commit fields")
        return self


class EdgeR0NetworkReconciliation(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-network-reconciliation.v1"] = (
        "ets.edge-compact-r0-network-reconciliation.v1"
    )
    reconciliation_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    recovered_at: datetime
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    final_queue_state: EdgeSyncStatusEvidence
    storage_used_bytes: int = Field(ge=0)
    rss_bytes: int = Field(ge=0)
    max_retry_attempts_per_minute_observed: int = Field(ge=0)
    records: tuple[EdgeR0NetworkRecoveredRecord, ...] = Field(min_length=1)
    reconciliation_commitment_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @field_validator("recovered_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "network-reconciliation timestamp")

    @model_validator(mode="after")
    def validate_reconciliation(self) -> EdgeR0NetworkReconciliation:
        ids = [record.record_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("network recovery record IDs must be unique")
        return self


class EdgeR0NetworkProofReceipt(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-network-proof-receipt.v1"] = (
        "ets.edge-compact-r0-network-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    subject_kind: NetworkProofSubject
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
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "network-proof timestamp")


class EdgeR0NetworkRecoveryCanary(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-network-recovery-canary.v1"] = (
        "ets.edge-compact-r0-network-recovery-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    reconciliation_id: str = Field(min_length=1, max_length=256)
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
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.10 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0NetworkRecoveryCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("canary request SHA-256 must match content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("canary verification cannot precede capture")
        return self


class EdgeR0Phase9Evaluation(StrictPhase9Model):
    schema_version: Literal["ets.edge-compact-r0-phase9-evaluation.v1"] = (
        "ets.edge-compact-r0-phase9-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase8_evaluation_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    profile_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    reconciliation_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    intended_record_count: int = Field(ge=0)
    fault_profile_observed: bool
    observer_agreement_preserved: bool
    no_invented_remote_acknowledgement: bool
    local_authoritative_records_preserved: bool
    idempotent_reconciliation: bool
    checkpoints_non_regressing: bool
    queue_storage_boundaries_preserved: bool
    retry_resource_envelope_preserved: bool
    independent_verification_complete: bool
    final_backlog_clear: bool
    post_recovery_canary_valid: bool
    r0_10_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE9_DISPOSITION
    claim_boundary: Literal[
        "r0_10_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE9_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.10 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase9Evaluation:
        expected = (
            self.fault_profile_observed
            and self.observer_agreement_preserved
            and self.no_invented_remote_acknowledgement
            and self.local_authoritative_records_preserved
            and self.idempotent_reconciliation
            and self.checkpoints_non_regressing
            and self.queue_storage_boundaries_preserved
            and self.retry_resource_envelope_preserved
            and self.independent_verification_complete
            and self.final_backlog_clear
            and self.post_recovery_canary_valid
            and not self.issues
        )
        if self.r0_10_passed != expected:
            raise ValueError("r0_10_passed must match component results and issues")
        return self


def build_network_reconciliation_commitment(
    records: tuple[EdgeR0NetworkRecoveredRecord, ...],
) -> str:
    value = [
        {
            "record_id": item.record_id,
            "event_id": item.event_id,
            "idempotency_key": item.idempotency_key,
            "authoritative_local_present": item.authoritative_local_present,
            "final_upstream_commit_count": item.final_upstream_commit_count,
            "final_upstream_event_id": item.final_upstream_event_id,
            "final_upstream_acceptance_sha256": item.final_upstream_acceptance_sha256,
            "final_proof_sha256": item.final_proof_sha256,
            "local_marked_synchronized": item.local_marked_synchronized,
        }
        for item in sorted(records, key=lambda record: record.record_id)
    ]
    return canonical_sha256(value)


def evaluate_r0_10(
    manifest: EdgeCompactR0BenchManifest,
    phase8: EdgeR0Phase8Evaluation,
    baseline: EdgeR0NetworkBaseline,
    profile: EdgeR0NetworkFaultProfile,
    window: EdgeR0NetworkInstabilityWindow,
    reconciliation: EdgeR0NetworkReconciliation,
    proofs: tuple[EdgeR0NetworkProofReceipt, ...],
    canary: EdgeR0NetworkRecoveryCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase9Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.10: bench manifest not ready: {blocker}")
    if not phase8.r0_9_passed:
        issues.append("R0.10: R0.9 did not pass")
    if phase8.manifest_id != manifest.manifest_id or phase8.asset_id != asset_id:
        issues.append("R0.10: R0.9 evaluation is bound to another DUT")
    if baseline.manifest_id != manifest.manifest_id or baseline.asset_id != asset_id:
        issues.append("R0.10: baseline is bound to another DUT")
    if baseline.phase8_evaluation_id != phase8.evaluation_id:
        issues.append("R0.10: baseline references another R0.9 evaluation")
    if baseline.phase8_evaluation_sha256 != canonical_sha256(
        phase8.model_dump(mode="json")
    ):
        issues.append("R0.10: R0.9 digest binding mismatch")
    if profile.baseline_id != baseline.baseline_id:
        issues.append("R0.10: fault profile references another baseline")
    if window.baseline_id != baseline.baseline_id or window.profile_id != profile.profile_id:
        issues.append("R0.10: instability window binding mismatch")
    if reconciliation.baseline_id != baseline.baseline_id:
        issues.append("R0.10: reconciliation references another baseline")
    if reconciliation.window_id != window.window_id:
        issues.append("R0.10: reconciliation references another instability window")
    if reconciliation.recovered_at < window.completed_at:
        issues.append("R0.10: reconciliation predates instability-window completion")

    expected_transition_count = profile.disconnect_cycle_count * 2
    fault_profile_observed = len(window.transitions) == expected_transition_count
    if not fault_profile_observed:
        issues.append(
            "R0.10: retained transition count does not match disconnect/reconnect profile"
        )

    expected_sequence: list[tuple[int, NetworkState]] = []
    for cycle in range(1, profile.disconnect_cycle_count + 1):
        expected_sequence.extend(
            [(cycle, NetworkState.DISCONNECTED), (cycle, NetworkState.CONNECTED)]
        )

    observer_agreement_preserved = True
    queue_storage_boundaries_preserved = True
    retry_resource_envelope_preserved = True
    max_items = baseline.queue_item_limit + baseline.queue_item_allowance
    max_bytes = baseline.queue_byte_limit + baseline.queue_byte_allowance
    max_rss = baseline.baseline_rss_bytes + profile.max_rss_growth_bytes

    for index, transition in enumerate(window.transitions):
        if transition.profile_id != profile.profile_id:
            issues.append(
                f"R0.10: transition references another fault profile: {transition.transition_id}"
            )
            fault_profile_observed = False
        if index < len(expected_sequence):
            expected_cycle, expected_state = expected_sequence[index]
            if (
                transition.cycle_number != expected_cycle
                or transition.commanded_state is not expected_state
            ):
                issues.append(
                    f"R0.10: transition order/state mismatch: {transition.transition_id}"
                )
                fault_profile_observed = False
        if transition.externally_observed_state is not transition.commanded_state:
            issues.append(
                f"R0.10: controller/external observer contradiction: {transition.transition_id}"
            )
            observer_agreement_preserved = False
        if transition.edge_reported_state is not transition.externally_observed_state:
            issues.append(
                f"R0.10: external observer/Edge contradiction: {transition.transition_id}"
            )
            observer_agreement_preserved = False
        if transition.added_latency_ms > profile.max_added_latency_ms:
            issues.append(f"R0.10: latency envelope exceeded: {transition.transition_id}")
            fault_profile_observed = False
        if transition.jitter_ms > profile.max_jitter_ms:
            issues.append(f"R0.10: jitter envelope exceeded: {transition.transition_id}")
            fault_profile_observed = False
        if transition.packet_loss_percent > profile.max_packet_loss_percent:
            issues.append(
                f"R0.10: packet-loss envelope exceeded: {transition.transition_id}"
            )
            fault_profile_observed = False
        if transition.queue_depth > max_items or transition.queue_bytes > max_bytes:
            issues.append(
                f"R0.10: R0.9 queue boundary crossed: {transition.transition_id}"
            )
            queue_storage_boundaries_preserved = False
        if transition.storage_used_bytes >= baseline.storage_high_watermark_used_bytes:
            issues.append(
                f"R0.10: R0.8 storage boundary crossed: {transition.transition_id}"
            )
            queue_storage_boundaries_preserved = False
        if transition.retry_attempts_last_minute > profile.max_retry_attempts_per_minute:
            issues.append(
                f"R0.10: retry-rate envelope exceeded: {transition.transition_id}"
            )
            retry_resource_envelope_preserved = False
        if transition.rss_bytes > max_rss:
            issues.append(f"R0.10: RSS envelope exceeded: {transition.transition_id}")
            retry_resource_envelope_preserved = False

    if window.completed_at.timestamp() - window.started_at.timestamp() > (
        profile.max_total_duration_seconds
    ):
        issues.append("R0.10: total instability duration exceeded declared profile")
        fault_profile_observed = False

    by_cycle: dict[int, list[EdgeR0NetworkTransition]] = {}
    for transition in window.transitions:
        by_cycle.setdefault(transition.cycle_number, []).append(transition)
    for cycle, transitions in by_cycle.items():
        disconnect = next(
            (
                item
                for item in transitions
                if item.externally_observed_state is NetworkState.DISCONNECTED
            ),
            None,
        )
        reconnect = next(
            (
                item
                for item in transitions
                if item.externally_observed_state is NetworkState.CONNECTED
            ),
            None,
        )
        if disconnect is None or reconnect is None:
            continue
        disconnect_seconds = (
            reconnect.externally_observed_at - disconnect.externally_observed_at
        ).total_seconds()
        if disconnect_seconds > profile.max_disconnect_seconds:
            issues.append(f"R0.10: disconnect duration exceeded in cycle {cycle}")
            fault_profile_observed = False

    no_invented_remote_acknowledgement = True
    intended_by_id = {record.record_id: record for record in window.records}
    for record in window.records:
        if (
            record.network_state_at_sync_attempt is NetworkState.DISCONNECTED
            and record.upstream_accepted_during_window
        ):
            issues.append(
                f"R0.10: upstream acknowledgement claimed while disconnected: {record.record_id}"
            )
            no_invented_remote_acknowledgement = False

    recovered_by_id = {record.record_id: record for record in reconciliation.records}
    intended_ids = set(intended_by_id)
    recovered_ids = set(recovered_by_id)
    missing = sorted(intended_ids - recovered_ids)
    unknown = sorted(recovered_ids - intended_ids)
    local_authoritative_records_preserved = not missing and not unknown
    idempotent_reconciliation = not missing and not unknown
    if missing:
        issues.append(f"R0.10: reconciliation missing records: {missing}")
    if unknown:
        issues.append(f"R0.10: reconciliation contains unknown records: {unknown}")

    for record_id in sorted(intended_ids & recovered_ids):
        intended = intended_by_id[record_id]
        recovered = recovered_by_id[record_id]
        if not recovered.authoritative_local_present:
            issues.append(f"R0.10: local authoritative record disappeared: {record_id}")
            local_authoritative_records_preserved = False
        if recovered.event_id != intended.event_id:
            issues.append(f"R0.10: recovered event binding changed: {record_id}")
            idempotent_reconciliation = False
        if recovered.idempotency_key != intended.idempotency_key:
            issues.append(f"R0.10: idempotency key changed: {record_id}")
            idempotent_reconciliation = False
        if recovered.final_upstream_commit_count != 1:
            issues.append(
                f"R0.10: expected one final logical upstream commit for {record_id}"
            )
            idempotent_reconciliation = False
        if recovered.final_upstream_event_id != intended.event_id:
            issues.append(f"R0.10: final upstream event mismatch: {record_id}")
            idempotent_reconciliation = False
        if not recovered.local_marked_synchronized:
            issues.append(f"R0.10: record not locally synchronized: {record_id}")
            idempotent_reconciliation = False

    expected_commitment = build_network_reconciliation_commitment(
        reconciliation.records
    )
    if reconciliation.reconciliation_commitment_sha256 != expected_commitment:
        issues.append("R0.10: reconciliation commitment mismatch")
        idempotent_reconciliation = False

    checkpoints_non_regressing = (
        reconciliation.local_checkpoint_index >= baseline.local_checkpoint_index
        and reconciliation.upstream_checkpoint_index >= baseline.upstream_checkpoint_index
    )
    if reconciliation.local_checkpoint_index < baseline.local_checkpoint_index:
        issues.append("R0.10: local checkpoint regressed")
    if reconciliation.upstream_checkpoint_index < baseline.upstream_checkpoint_index:
        issues.append("R0.10: upstream checkpoint regressed")

    final_queue = reconciliation.final_queue_state
    final_backlog_clear = (
        final_queue.queue_depth == 0
        and final_queue.queue_bytes == 0
        and final_queue.pending == 0
        and final_queue.in_flight == 0
        and final_queue.retryable_failure == 0
        and final_queue.terminal_failure == 0
    )
    if not final_backlog_clear:
        issues.append("R0.10: final synchronization backlog is not clean")
    if (
        reconciliation.storage_used_bytes
        >= baseline.storage_high_watermark_used_bytes
        or final_queue.queue_depth > max_items
        or final_queue.queue_bytes > max_bytes
    ):
        issues.append("R0.10: final state crossed prior storage/queue boundary")
        queue_storage_boundaries_preserved = False
    if (
        reconciliation.max_retry_attempts_per_minute_observed
        > profile.max_retry_attempts_per_minute
        or reconciliation.rss_bytes > max_rss
    ):
        issues.append("R0.10: final retry/resource envelope exceeded")
        retry_resource_envelope_preserved = False

    proof_keys: dict[tuple[NetworkProofSubject, str], EdgeR0NetworkProofReceipt] = {}
    for proof_receipt in proofs:
        key = (proof_receipt.subject_kind, proof_receipt.subject_id)
        if key in proof_keys:
            issues.append(
                "R0.10: duplicate proof receipt for "
                f"{proof_receipt.subject_kind.value}:{proof_receipt.subject_id}"
            )
            continue
        proof_keys[key] = proof_receipt

    verifier_host = manifest.verifier.verifier_host_id
    independent_verification_complete = True
    for proof_digest in baseline.representative_proof_sha256:
        pre_receipt = proof_keys.get(
            (NetworkProofSubject.PRE_INSTABILITY, proof_digest)
        )
        if pre_receipt is None:
            issues.append(
                f"R0.10: missing pre-instability proof verification: {proof_digest}"
            )
            independent_verification_complete = False
            continue
        if pre_receipt.proof_artifact_sha256 != proof_digest:
            issues.append(
                f"R0.10: pre-instability proof digest mismatch: {proof_digest}"
            )
            independent_verification_complete = False
        if (
            not pre_receipt.inclusion_valid
            or not pre_receipt.independent_execution_context
            or verifier_host is None
            or pre_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.10: pre-instability proof failed independent verification: {proof_digest}"
            )
            independent_verification_complete = False

    for record_id in sorted(intended_ids):
        recovered = recovered_by_id.get(record_id)
        if recovered is None or recovered.final_upstream_commit_count != 1:
            independent_verification_complete = False
            continue
        record_receipt = proof_keys.get(
            (NetworkProofSubject.INSTABILITY_RECORD, record_id)
        )
        if record_receipt is None:
            issues.append(f"R0.10: missing final proof receipt: {record_id}")
            independent_verification_complete = False
            continue
        if record_receipt.proof_artifact_sha256 != recovered.final_proof_sha256:
            issues.append(f"R0.10: final proof digest mismatch: {record_id}")
            independent_verification_complete = False
        if (
            not record_receipt.inclusion_valid
            or not record_receipt.independent_execution_context
            or verifier_host is None
            or record_receipt.verifier_host_id != verifier_host
        ):
            issues.append(f"R0.10: final proof failed independent verification: {record_id}")
            independent_verification_complete = False

    canary_valid = True
    if canary.reconciliation_id != reconciliation.reconciliation_id:
        issues.append("R0.10: canary references another reconciliation")
        canary_valid = False
    if canary.captured_at < reconciliation.recovered_at:
        issues.append("R0.10: canary predates reconciliation")
        canary_valid = False
    if (
        not canary.inclusion_valid
        or not canary.independent_execution_context
        or verifier_host is None
        or canary.verifier_host_id != verifier_host
    ):
        issues.append("R0.10: post-recovery canary did not independently verify")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase8_evaluation_id": phase8.evaluation_id,
        "baseline_id": baseline.baseline_id,
        "profile_id": profile.profile_id,
        "window_id": window.window_id,
        "reconciliation_id": reconciliation.reconciliation_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        fault_profile_observed
        and observer_agreement_preserved
        and no_invented_remote_acknowledgement
        and local_authoritative_records_preserved
        and idempotent_reconciliation
        and checkpoints_non_regressing
        and queue_storage_boundaries_preserved
        and retry_resource_envelope_preserved
        and independent_verification_complete
        and final_backlog_clear
        and canary_valid
        and not issues
    )
    return EdgeR0Phase9Evaluation(
        evaluation_id=f"edge-r0-phase9-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase8_evaluation_id=phase8.evaluation_id,
        baseline_id=baseline.baseline_id,
        profile_id=profile.profile_id,
        window_id=window.window_id,
        reconciliation_id=reconciliation.reconciliation_id,
        evaluated_at=evaluated_at,
        intended_record_count=len(window.records),
        fault_profile_observed=fault_profile_observed,
        observer_agreement_preserved=observer_agreement_preserved,
        no_invented_remote_acknowledgement=no_invented_remote_acknowledgement,
        local_authoritative_records_preserved=local_authoritative_records_preserved,
        idempotent_reconciliation=idempotent_reconciliation,
        checkpoints_non_regressing=checkpoints_non_regressing,
        queue_storage_boundaries_preserved=queue_storage_boundaries_preserved,
        retry_resource_envelope_preserved=retry_resource_envelope_preserved,
        independent_verification_complete=independent_verification_complete,
        final_backlog_clear=final_backlog_clear,
        post_recovery_canary_valid=canary_valid,
        r0_10_passed=passed,
        issues=tuple(issues),
    )


def load_phase8_evaluation(raw: bytes) -> EdgeR0Phase8Evaluation:
    return EdgeR0Phase8Evaluation.model_validate_json(raw)


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
        description="ETS Wave 1 Edge Compact R0 R0.10 network-instability evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser("evaluate-r0-10")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase8-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--baseline", type=Path, required=True)
    evaluate_parser.add_argument("--fault-profile", type=Path, required=True)
    evaluate_parser.add_argument("--window", type=Path, required=True)
    evaluate_parser.add_argument("--reconciliation", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-10":
        result = evaluate_r0_10(
            load_manifest(args.manifest.read_bytes()),
            load_phase8_evaluation(args.phase8_evaluation.read_bytes()),
            EdgeR0NetworkBaseline.model_validate_json(args.baseline.read_bytes()),
            EdgeR0NetworkFaultProfile.model_validate_json(args.fault_profile.read_bytes()),
            EdgeR0NetworkInstabilityWindow.model_validate_json(args.window.read_bytes()),
            EdgeR0NetworkReconciliation.model_validate_json(
                args.reconciliation.read_bytes()
            ),
            tuple(
                EdgeR0NetworkProofReceipt.model_validate_json(path.read_bytes())
                for path in args.proof_receipt
            ),
            EdgeR0NetworkRecoveryCanary.model_validate_json(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_10_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
