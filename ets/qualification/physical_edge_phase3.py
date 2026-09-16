"""Wave 1 Edge Compact R0 controlled network-loss evidence.

R0.4 is the first deliberate physical fault gate. The evidence tooling records an
externally controlled upstream outage, continued local capture/proof generation,
reconnection, and exact-once synchronization. It never manipulates networking or
other hardware itself and cannot publish a hardware qualification claim.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.edge.webhook_adapter import WebhookCaptureReceipt
from ets.qualification.physical_edge import (
    BenchControlKind,
    EdgeCompactR0BenchManifest,
    load_manifest,
    readiness_issues,
)
from ets.qualification.physical_edge_phase1 import sha256_file
from ets.qualification.physical_edge_phase2 import EdgeR0Phase2Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE3_CLAIM_BOUNDARY: Literal[
    "r0_4_phase_evidence_not_a_physical_qualification_result"
] = "r0_4_phase_evidence_not_a_physical_qualification_result"
_PHASE3_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"
_MIN_OFFLINE_EVENTS = 10
_MIN_OFFLINE_SECONDS = 30
OfflineSyncState = Literal["pending", "retryable_failure"]


class StrictPhase3Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class EdgeSyncStatusEvidence(StrictPhase3Model):
    queue_depth: int = Field(ge=0)
    queue_bytes: int = Field(ge=0)
    pending: int = Field(ge=0)
    in_flight: int = Field(ge=0)
    retryable_failure: int = Field(ge=0)
    terminal_failure: int = Field(ge=0)
    synchronized: int = Field(ge=0)
    max_items: int = Field(gt=0)
    max_bytes: int = Field(gt=0)
    oldest_pending_age_seconds: float | None = Field(default=None, ge=0)
    last_successful_sync: str | None = None
    last_failure: str | None = None
    upstream_status: str = Field(min_length=1, max_length=64)


class EdgeR0NetworkLossObservation(StrictPhase3Model):
    schema_version: Literal["ets.edge-compact-r0-network-loss-observation.v1"] = (
        "ets.edge-compact-r0-network-loss-observation.v1"
    )
    observation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    network_control_id: str = Field(min_length=1, max_length=256)
    observer_id: str = Field(min_length=1, max_length=256)
    controller_id: str = Field(min_length=1, max_length=256)
    loss_started_at: datetime
    loss_confirmed_at: datetime
    upstream_reachable_before: Literal[True] = True
    upstream_reachable_during: Literal[False] = False
    dut_local_endpoint_reachable_during: Literal[True] = True
    operator_approved: Literal[True] = True
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    independent_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_4_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE3_CLAIM_BOUNDARY

    @field_validator("loss_started_at", "loss_confirmed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "network-loss timestamp")

    @model_validator(mode="after")
    def require_order(self) -> EdgeR0NetworkLossObservation:
        if self.loss_confirmed_at < self.loss_started_at:
            raise ValueError("loss_confirmed_at must not precede loss_started_at")
        return self


class EdgeR0OfflineCaptureWindow(StrictPhase3Model):
    schema_version: Literal["ets.edge-compact-r0-offline-capture-window.v1"] = (
        "ets.edge-compact-r0-offline-capture-window.v1"
    )
    window_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase2_evaluation_id: str = Field(min_length=1, max_length=256)
    phase2_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    network_observation_id: str = Field(min_length=1, max_length=256)
    network_observation_sha256: str = Field(pattern=_SHA256_RE)
    started_at: datetime
    completed_at: datetime
    attempted_event_count: int = Field(ge=1)
    pre_loss_queue: EdgeSyncStatusEvidence
    outage_queue: EdgeSyncStatusEvidence
    resource_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_4_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE3_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "offline-window timestamp")

    @model_validator(mode="after")
    def require_meaningful_window(self) -> EdgeR0OfflineCaptureWindow:
        if self.completed_at < self.started_at:
            raise ValueError("offline completed_at must not precede started_at")
        if (self.completed_at - self.started_at).total_seconds() < _MIN_OFFLINE_SECONDS:
            raise ValueError(f"R0.4 requires at least {_MIN_OFFLINE_SECONDS} offline seconds")
        if self.attempted_event_count < _MIN_OFFLINE_EVENTS:
            raise ValueError(f"R0.4 requires at least {_MIN_OFFLINE_EVENTS} offline captures")
        return self


class EdgeR0OfflineCaptureRecord(StrictPhase3Model):
    schema_version: Literal["ets.edge-compact-r0-offline-capture-record.v1"] = (
        "ets.edge-compact-r0-offline-capture-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    captured_at: datetime
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    receipt_artifact_sha256: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    evidence_id: str = Field(min_length=1, max_length=512)
    log_index: int = Field(ge=0)
    event_hash: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    sync_state_at_capture: OfflineSyncState
    local_commit_observed: Literal[True] = True
    local_proof_observed: Literal[True] = True
    upstream_reachable_at_capture: Literal[False] = False
    claim_boundary: Literal[
        "r0_4_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE3_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "offline-capture timestamp")

    @model_validator(mode="after")
    def bind_exact_payload(self) -> EdgeR0OfflineCaptureRecord:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("request payload SHA-256 must match Edge content_hash")
        return self


class EdgeR0OfflineProofReceipt(StrictPhase3Model):
    schema_version: Literal["ets.edge-compact-r0-offline-proof-receipt.v1"] = (
        "ets.edge-compact-r0-offline-proof-receipt.v1"
    )
    verification_id: str = Field(min_length=1, max_length=256)
    record_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_4_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE3_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "proof-verification timestamp")


class EdgeR0UpstreamAcceptanceReceipt(StrictPhase3Model):
    schema_version: Literal["ets.edge-compact-r0-upstream-acceptance-receipt.v1"] = (
        "ets.edge-compact-r0-upstream-acceptance-receipt.v1"
    )
    acceptance_id: str = Field(min_length=1, max_length=256)
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=512)
    accepted_at: datetime
    acknowledgement_hash: str = Field(pattern=_SHA256_RE)
    upstream_artifact_sha256: str = Field(pattern=_SHA256_RE)
    upstream_observer_id: str = Field(min_length=1, max_length=256)
    duplicate_observation_count: Literal[0] = 0
    final_state: Literal["synchronized"] = "synchronized"
    claim_boundary: Literal[
        "r0_4_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE3_CLAIM_BOUNDARY

    @field_validator("accepted_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "upstream-acceptance timestamp")


class EdgeR0ReconnectSyncSummary(StrictPhase3Model):
    schema_version: Literal["ets.edge-compact-r0-reconnect-sync-summary.v1"] = (
        "ets.edge-compact-r0-reconnect-sync-summary.v1"
    )
    summary_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    reconnect_observed_at: datetime
    sync_completed_at: datetime
    upstream_reachable_after: Literal[True] = True
    independent_reconnect_observation_sha256: str = Field(pattern=_SHA256_RE)
    initial_queue: EdgeSyncStatusEvidence
    final_queue: EdgeSyncStatusEvidence
    sync_run_artifact_sha256: tuple[str, ...] = Field(min_length=1)
    remaining_outage_records: Literal[0] = 0
    claim_boundary: Literal[
        "r0_4_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE3_CLAIM_BOUNDARY

    @field_validator("reconnect_observed_at", "sync_completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "reconnect timestamp")

    @field_validator("sync_run_artifact_sha256")
    @classmethod
    def validate_run_digests(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_validate_sha256(value) for value in values)

    @model_validator(mode="after")
    def require_order(self) -> EdgeR0ReconnectSyncSummary:
        if self.sync_completed_at < self.reconnect_observed_at:
            raise ValueError("sync_completed_at must not precede reconnect_observed_at")
        return self


class EdgeR0Phase3Evaluation(StrictPhase3Model):
    schema_version: Literal["ets.edge-compact-r0-phase3-evaluation.v1"] = (
        "ets.edge-compact-r0-phase3-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase2_evaluation_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    attempted_event_count: int = Field(ge=0)
    locally_committed_count: int = Field(ge=0)
    independently_verified_count: int = Field(ge=0)
    synchronized_exactly_once_count: int = Field(ge=0)
    r0_4_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE3_DISPOSITION
    claim_boundary: Literal[
        "r0_4_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE3_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.4 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase3Evaluation:
        if self.r0_4_passed and self.issues:
            raise ValueError("passing R0.4 evaluation cannot retain blocking issues")
        return self


def load_phase2_evaluation(raw: bytes) -> EdgeR0Phase2Evaluation:
    return EdgeR0Phase2Evaluation.model_validate_json(raw)


def load_network_observation(raw: bytes) -> EdgeR0NetworkLossObservation:
    return EdgeR0NetworkLossObservation.model_validate_json(raw)


def load_offline_window(raw: bytes) -> EdgeR0OfflineCaptureWindow:
    return EdgeR0OfflineCaptureWindow.model_validate_json(raw)


def load_offline_capture(raw: bytes) -> EdgeR0OfflineCaptureRecord:
    return EdgeR0OfflineCaptureRecord.model_validate_json(raw)


def load_offline_proof(raw: bytes) -> EdgeR0OfflineProofReceipt:
    return EdgeR0OfflineProofReceipt.model_validate_json(raw)


def load_upstream_acceptance(raw: bytes) -> EdgeR0UpstreamAcceptanceReceipt:
    return EdgeR0UpstreamAcceptanceReceipt.model_validate_json(raw)


def load_reconnect_summary(raw: bytes) -> EdgeR0ReconnectSyncSummary:
    return EdgeR0ReconnectSyncSummary.model_validate_json(raw)


def build_network_loss_observation(
    manifest: EdgeCompactR0BenchManifest,
    *,
    observer_id: str,
    controller_id: str,
    loss_started_at: datetime,
    loss_confirmed_at: datetime,
    controller_receipt_sha256: str,
    independent_observation_sha256: str,
) -> EdgeR0NetworkLossObservation:
    blockers = readiness_issues(manifest)
    if blockers:
        raise ValueError("bench manifest is not ready for R0.4 execution")
    network_control = next(
        (control for control in manifest.controls if control.kind is BenchControlKind.NETWORK),
        None,
    )
    if network_control is None:
        raise ValueError("R0.4 requires the W1-1 network control")
    if not network_control.operator_approval_required:
        raise ValueError("R0.4 network control must require operator approval")
    asset_id = _require_present(manifest.dut.asset_id, "DUT asset_id")
    expected_observer = _require_present(manifest.observer.observer_id, "observer_id")
    if observer_id != expected_observer:
        raise ValueError("network-loss observer must match the W1-1 observer binding")
    seed = {
        "manifest_id": manifest.manifest_id,
        "asset_id": asset_id,
        "network_control_id": network_control.control_id,
        "observer_id": observer_id,
        "controller_id": controller_id,
        "loss_started_at": loss_started_at.isoformat(),
    }
    return EdgeR0NetworkLossObservation(
        observation_id=f"edge-r0-netloss-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        network_control_id=network_control.control_id,
        observer_id=observer_id,
        controller_id=controller_id,
        loss_started_at=loss_started_at,
        loss_confirmed_at=loss_confirmed_at,
        controller_receipt_sha256=_validate_sha256(controller_receipt_sha256),
        independent_observation_sha256=_validate_sha256(independent_observation_sha256),
    )


def build_offline_window(
    manifest: EdgeCompactR0BenchManifest,
    phase2: EdgeR0Phase2Evaluation,
    observation: EdgeR0NetworkLossObservation,
    *,
    window_id: str,
    started_at: datetime,
    completed_at: datetime,
    attempted_event_count: int,
    pre_loss_queue: EdgeSyncStatusEvidence,
    outage_queue: EdgeSyncStatusEvidence,
    resource_observation_sha256: str,
) -> EdgeR0OfflineCaptureWindow:
    if not phase2.r0_3_passed:
        raise ValueError("R0.3 must pass before R0.4 begins")
    asset_id = _require_present(manifest.dut.asset_id, "DUT asset_id")
    if phase2.manifest_id != manifest.manifest_id or phase2.asset_id != asset_id:
        raise ValueError("R0.3 evaluation is bound to another DUT")
    if observation.manifest_id != manifest.manifest_id or observation.asset_id != asset_id:
        raise ValueError("network-loss observation is bound to another DUT")
    return EdgeR0OfflineCaptureWindow(
        window_id=window_id,
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase2_evaluation_id=phase2.evaluation_id,
        phase2_evaluation_sha256=canonical_sha256(phase2.model_dump(mode="json")),
        network_observation_id=observation.observation_id,
        network_observation_sha256=canonical_sha256(observation.model_dump(mode="json")),
        started_at=started_at,
        completed_at=completed_at,
        attempted_event_count=attempted_event_count,
        pre_loss_queue=pre_loss_queue,
        outage_queue=outage_queue,
        resource_observation_sha256=_validate_sha256(resource_observation_sha256),
    )


def _offline_sync_state(value: str) -> OfflineSyncState:
    if value == "pending":
        return "pending"
    if value == "retryable_failure":
        return "retryable_failure"
    raise ValueError("offline capture must be pending or retryable_failure")


def build_offline_capture_record(
    window: EdgeR0OfflineCaptureWindow,
    receipt: WebhookCaptureReceipt,
    *,
    sequence_number: int,
    captured_at: datetime,
    request_payload_sha256: str,
    receipt_artifact_sha256: str,
    proof_artifact_sha256: str,
) -> EdgeR0OfflineCaptureRecord:
    sync_state = _offline_sync_state(receipt.sync_state)
    seed = {
        "window_id": window.window_id,
        "sequence_number": sequence_number,
        "event_id": receipt.event_id,
        "event_hash": receipt.event_hash,
    }
    return EdgeR0OfflineCaptureRecord(
        record_id=f"edge-r0-offline-{canonical_sha256(seed)[:24]}",
        window_id=window.window_id,
        sequence_number=sequence_number,
        captured_at=captured_at,
        request_payload_sha256=_validate_sha256(request_payload_sha256),
        receipt_artifact_sha256=_validate_sha256(receipt_artifact_sha256),
        event_id=receipt.event_id,
        evidence_id=receipt.evidence_id,
        log_index=receipt.log_index,
        event_hash=_validate_sha256(receipt.event_hash),
        content_hash=_validate_sha256(receipt.content_hash),
        proof_artifact_sha256=_validate_sha256(proof_artifact_sha256),
        sync_state_at_capture=sync_state,
    )


def build_offline_proof_receipt(
    record: EdgeR0OfflineCaptureRecord,
    verification_result: dict[str, object],
    *,
    verifier_id: str,
    verifier_host_id: str,
    verifier_build_sha256: str,
    verification_result_sha256: str,
    verified_at: datetime,
    independent_execution_context: bool,
) -> EdgeR0OfflineProofReceipt:
    seed = {
        "record_id": record.record_id,
        "event_id": record.event_id,
        "verified_at": verified_at.isoformat(),
        "verifier_host_id": verifier_host_id,
    }
    return EdgeR0OfflineProofReceipt(
        verification_id=f"edge-r0-offline-verify-{canonical_sha256(seed)[:24]}",
        record_id=record.record_id,
        window_id=record.window_id,
        event_id=record.event_id,
        verified_at=verified_at,
        verifier_id=verifier_id,
        verifier_host_id=verifier_host_id,
        verifier_build_sha256=_validate_sha256(verifier_build_sha256),
        proof_artifact_sha256=record.proof_artifact_sha256,
        verification_result_sha256=_validate_sha256(verification_result_sha256),
        inclusion_valid=verification_result.get("valid") is True,
        independent_execution_context=independent_execution_context,
    )


def build_upstream_acceptance(
    record: EdgeR0OfflineCaptureRecord,
    *,
    idempotency_key: str,
    accepted_at: datetime,
    acknowledgement_hash: str,
    upstream_artifact_sha256: str,
    upstream_observer_id: str,
) -> EdgeR0UpstreamAcceptanceReceipt:
    seed = {
        "record_id": record.record_id,
        "event_id": record.event_id,
        "idempotency_key": idempotency_key,
        "accepted_at": accepted_at.isoformat(),
    }
    return EdgeR0UpstreamAcceptanceReceipt(
        acceptance_id=f"edge-r0-upstream-{canonical_sha256(seed)[:24]}",
        record_id=record.record_id,
        event_id=record.event_id,
        idempotency_key=idempotency_key,
        accepted_at=accepted_at,
        acknowledgement_hash=_validate_sha256(acknowledgement_hash),
        upstream_artifact_sha256=_validate_sha256(upstream_artifact_sha256),
        upstream_observer_id=upstream_observer_id,
    )


def build_reconnect_summary(
    window: EdgeR0OfflineCaptureWindow,
    *,
    reconnect_observed_at: datetime,
    sync_completed_at: datetime,
    independent_reconnect_observation_sha256: str,
    initial_queue: EdgeSyncStatusEvidence,
    final_queue: EdgeSyncStatusEvidence,
    sync_run_artifact_sha256: tuple[str, ...],
) -> EdgeR0ReconnectSyncSummary:
    seed = {
        "window_id": window.window_id,
        "reconnect_observed_at": reconnect_observed_at.isoformat(),
        "sync_completed_at": sync_completed_at.isoformat(),
        "sync_runs": list(sync_run_artifact_sha256),
    }
    return EdgeR0ReconnectSyncSummary(
        summary_id=f"edge-r0-reconnect-{canonical_sha256(seed)[:24]}",
        window_id=window.window_id,
        reconnect_observed_at=reconnect_observed_at,
        sync_completed_at=sync_completed_at,
        independent_reconnect_observation_sha256=_validate_sha256(
            independent_reconnect_observation_sha256
        ),
        initial_queue=initial_queue,
        final_queue=final_queue,
        sync_run_artifact_sha256=sync_run_artifact_sha256,
    )


def evaluate_r0_4(
    manifest: EdgeCompactR0BenchManifest,
    phase2: EdgeR0Phase2Evaluation,
    observation: EdgeR0NetworkLossObservation,
    window: EdgeR0OfflineCaptureWindow,
    captures: tuple[EdgeR0OfflineCaptureRecord, ...],
    proofs: tuple[EdgeR0OfflineProofReceipt, ...],
    reconnect: EdgeR0ReconnectSyncSummary,
    acceptances: tuple[EdgeR0UpstreamAcceptanceReceipt, ...],
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase3Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.4: bench manifest not ready: {blocker}")
    if not phase2.r0_3_passed:
        issues.append("R0.4: R0.3 did not pass")
    if phase2.manifest_id != manifest.manifest_id or phase2.asset_id != asset_id:
        issues.append("R0.4: R0.3 evaluation is bound to another DUT")

    if window.phase2_evaluation_id != phase2.evaluation_id:
        issues.append("R0.4: offline window references another R0.3 evaluation")
    if window.phase2_evaluation_sha256 != canonical_sha256(phase2.model_dump(mode="json")):
        issues.append("R0.4: R0.3 digest binding mismatch")
    if window.manifest_id != manifest.manifest_id or window.asset_id != asset_id:
        issues.append("R0.4: offline window is bound to another DUT")

    if window.network_observation_id != observation.observation_id:
        issues.append("R0.4: offline window references another network-loss observation")
    if window.network_observation_sha256 != canonical_sha256(
        observation.model_dump(mode="json")
    ):
        issues.append("R0.4: network-loss observation digest mismatch")
    if window.started_at < observation.loss_confirmed_at:
        issues.append("R0.4: capture began before upstream loss was independently confirmed")

    network_control = next(
        (control for control in manifest.controls if control.kind is BenchControlKind.NETWORK),
        None,
    )
    if network_control is None or observation.network_control_id != network_control.control_id:
        issues.append("R0.4: observation does not bind to the W1-1 network control")
    if observation.observer_id != manifest.observer.observer_id:
        issues.append("R0.4: network-loss observer does not match bench observer")

    if window.outage_queue.upstream_status not in {"offline", "degraded", "unknown"}:
        issues.append("R0.4: outage queue did not record unavailable/degraded upstream")
    if window.outage_queue.terminal_failure != 0:
        issues.append("R0.4: terminal queue failure occurred during outage")

    record_ids = [item.record_id for item in captures]
    event_ids = [item.event_id for item in captures]
    log_indices = [item.log_index for item in captures]
    sequences = [item.sequence_number for item in captures]
    if len(captures) != window.attempted_event_count:
        issues.append("R0.4: local capture count differs from attempted event count")
    if len(record_ids) != len(set(record_ids)):
        issues.append("R0.4: offline capture IDs are not unique")
    if len(event_ids) != len(set(event_ids)):
        issues.append("R0.4: offline event IDs are not unique")
    if len(log_indices) != len(set(log_indices)):
        issues.append("R0.4: offline log indices are not unique")
    if sorted(sequences) != list(range(1, window.attempted_event_count + 1)):
        issues.append("R0.4: offline sequence coverage is incomplete or duplicated")
    for record in captures:
        if record.window_id != window.window_id:
            issues.append(f"R0.4: capture {record.record_id} belongs to another window")
        if not (window.started_at <= record.captured_at <= window.completed_at):
            issues.append(f"R0.4: capture {record.record_id} lies outside outage window")

    proofs_by_record: dict[str, EdgeR0OfflineProofReceipt] = {}
    for proof_item in proofs:
        if proof_item.record_id in proofs_by_record:
            issues.append(f"R0.4: duplicate proof verification for {proof_item.record_id}")
            continue
        proofs_by_record[proof_item.record_id] = proof_item

    verified_count = 0
    verifier_host = manifest.verifier.verifier_host_id
    for record in captures:
        verification_receipt = proofs_by_record.get(record.record_id)
        if verification_receipt is None:
            issues.append(f"R0.4: missing proof verification for {record.record_id}")
            continue
        if (
            verification_receipt.window_id != window.window_id
            or verification_receipt.event_id != record.event_id
        ):
            issues.append(f"R0.4: proof binding mismatch for {record.record_id}")
        if verification_receipt.proof_artifact_sha256 != record.proof_artifact_sha256:
            issues.append(f"R0.4: proof digest mismatch for {record.record_id}")
        if (
            not verification_receipt.inclusion_valid
            or not verification_receipt.independent_execution_context
        ):
            issues.append(f"R0.4: independent proof verification failed for {record.record_id}")
        if verifier_host is None or verification_receipt.verifier_host_id != verifier_host:
            issues.append(f"R0.4: verifier host mismatch for {record.record_id}")
        if (
            verification_receipt.inclusion_valid
            and verification_receipt.independent_execution_context
            and verification_receipt.verifier_host_id == verifier_host
        ):
            verified_count += 1

    if reconnect.window_id != window.window_id:
        issues.append("R0.4: reconnect summary references another outage window")
    if reconnect.reconnect_observed_at < window.completed_at:
        issues.append("R0.4: reconnect predates completion of offline capture window")
    final_queue = reconnect.final_queue
    if final_queue.queue_depth != 0:
        issues.append("R0.4: synchronization backlog remains after reconnect")
    if final_queue.pending != 0 or final_queue.in_flight != 0:
        issues.append("R0.4: pending/in-flight queue state remains after reconnect")
    if final_queue.retryable_failure != 0 or final_queue.terminal_failure != 0:
        issues.append("R0.4: failed queue state remains after reconnect")
    if final_queue.upstream_status != "online":
        issues.append("R0.4: upstream did not return to online state")

    acceptances_by_record: dict[str, EdgeR0UpstreamAcceptanceReceipt] = {}
    idempotency_keys: list[str] = []
    acceptance_event_ids: list[str] = []
    for acceptance_item in acceptances:
        if acceptance_item.record_id in acceptances_by_record:
            issues.append(
                f"R0.4: duplicate upstream acceptance for {acceptance_item.record_id}"
            )
            continue
        acceptances_by_record[acceptance_item.record_id] = acceptance_item
        idempotency_keys.append(acceptance_item.idempotency_key)
        acceptance_event_ids.append(acceptance_item.event_id)
    if len(idempotency_keys) != len(set(idempotency_keys)):
        issues.append("R0.4: duplicate idempotency keys observed")
    if set(acceptance_event_ids) != set(event_ids):
        issues.append("R0.4: upstream event set does not exactly match outage event set")

    exactly_once_count = 0
    for record in captures:
        upstream_acceptance = acceptances_by_record.get(record.record_id)
        if upstream_acceptance is None:
            issues.append(f"R0.4: missing upstream acceptance for {record.record_id}")
            continue
        if upstream_acceptance.event_id != record.event_id:
            issues.append(f"R0.4: acceptance event mismatch for {record.record_id}")
            continue
        if upstream_acceptance.accepted_at < reconnect.reconnect_observed_at:
            issues.append(f"R0.4: acceptance predates reconnect for {record.record_id}")
            continue
        exactly_once_count += 1

    unknown_proofs = sorted(set(proofs_by_record) - set(record_ids))
    if unknown_proofs:
        issues.append(f"R0.4: proofs reference unknown captures: {unknown_proofs}")
    unknown_acceptances = sorted(set(acceptances_by_record) - set(record_ids))
    if unknown_acceptances:
        issues.append(f"R0.4: acceptances reference unknown captures: {unknown_acceptances}")

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase2_evaluation_id": phase2.evaluation_id,
        "window_id": window.window_id,
        "evaluated_at": evaluated_at.isoformat(),
        "record_ids": sorted(record_ids),
        "acceptance_ids": sorted(item.acceptance_id for item in acceptances),
        "issues": issues,
    }
    return EdgeR0Phase3Evaluation(
        evaluation_id=f"edge-r0-phase3-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase2_evaluation_id=phase2.evaluation_id,
        window_id=window.window_id,
        evaluated_at=evaluated_at,
        attempted_event_count=window.attempted_event_count,
        locally_committed_count=len(captures),
        independently_verified_count=verified_count,
        synchronized_exactly_once_count=exactly_once_count,
        r0_4_passed=not issues,
        issues=tuple(issues),
    )


def _require_timezone(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone offset")
    return value


def _validate_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized[7:]
    if re.fullmatch(_SHA256_RE, normalized) is None:
        raise ValueError("expected a 64-character SHA-256 hex digest")
    return normalized


def _require_present(value: str | None, label: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"missing required {label}")
    return value.strip()


def _parse_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return _require_timezone(datetime.fromisoformat(normalized), "timestamp")


def _load_json_object(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _load_sync_status(path: Path) -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence.model_validate_json(path.read_bytes())


def _write_json(path: Path, value: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ETS Wave 1 Edge Compact R0 R0.4 evidence tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fault_parser = subparsers.add_parser("record-network-loss")
    fault_parser.add_argument("--manifest", type=Path, required=True)
    fault_parser.add_argument("--observer-id", required=True)
    fault_parser.add_argument("--controller-id", required=True)
    fault_parser.add_argument("--loss-started-at", required=True)
    fault_parser.add_argument("--loss-confirmed-at", required=True)
    fault_parser.add_argument("--controller-receipt", type=Path, required=True)
    fault_parser.add_argument("--independent-observation", type=Path, required=True)
    fault_parser.add_argument("--output", type=Path, required=True)

    window_parser = subparsers.add_parser("record-offline-window")
    window_parser.add_argument("--manifest", type=Path, required=True)
    window_parser.add_argument("--phase2-evaluation", type=Path, required=True)
    window_parser.add_argument("--network-observation", type=Path, required=True)
    window_parser.add_argument("--window-id", required=True)
    window_parser.add_argument("--started-at", required=True)
    window_parser.add_argument("--completed-at", required=True)
    window_parser.add_argument("--attempted-events", type=int, required=True)
    window_parser.add_argument("--pre-loss-queue", type=Path, required=True)
    window_parser.add_argument("--outage-queue", type=Path, required=True)
    window_parser.add_argument("--resource-observation", type=Path, required=True)
    window_parser.add_argument("--output", type=Path, required=True)

    capture_parser = subparsers.add_parser("record-offline-capture")
    capture_parser.add_argument("--window", type=Path, required=True)
    capture_parser.add_argument("--receipt", type=Path, required=True)
    capture_parser.add_argument("--sequence", type=int, required=True)
    capture_parser.add_argument("--captured-at", required=True)
    capture_parser.add_argument("--request-payload", type=Path, required=True)
    capture_parser.add_argument("--proof", type=Path, required=True)
    capture_parser.add_argument("--output", type=Path, required=True)

    proof_parser = subparsers.add_parser("record-offline-proof")
    proof_parser.add_argument("--capture-record", type=Path, required=True)
    proof_parser.add_argument("--verification-result", type=Path, required=True)
    proof_parser.add_argument("--verifier-id", required=True)
    proof_parser.add_argument("--verifier-host-id", required=True)
    proof_parser.add_argument("--verifier-build-digest", required=True)
    proof_parser.add_argument("--verified-at", required=True)
    proof_parser.add_argument("--independent", action="store_true")
    proof_parser.add_argument("--output", type=Path, required=True)

    acceptance_parser = subparsers.add_parser("record-upstream-acceptance")
    acceptance_parser.add_argument("--capture-record", type=Path, required=True)
    acceptance_parser.add_argument("--idempotency-key", required=True)
    acceptance_parser.add_argument("--accepted-at", required=True)
    acceptance_parser.add_argument("--acknowledgement-hash", required=True)
    acceptance_parser.add_argument("--upstream-artifact", type=Path, required=True)
    acceptance_parser.add_argument("--upstream-observer-id", required=True)
    acceptance_parser.add_argument("--output", type=Path, required=True)

    reconnect_parser = subparsers.add_parser("record-reconnect")
    reconnect_parser.add_argument("--window", type=Path, required=True)
    reconnect_parser.add_argument("--reconnect-observed-at", required=True)
    reconnect_parser.add_argument("--sync-completed-at", required=True)
    reconnect_parser.add_argument("--reconnect-observation", type=Path, required=True)
    reconnect_parser.add_argument("--initial-queue", type=Path, required=True)
    reconnect_parser.add_argument("--final-queue", type=Path, required=True)
    reconnect_parser.add_argument("--sync-run-artifact", type=Path, action="append", required=True)
    reconnect_parser.add_argument("--output", type=Path, required=True)

    evaluate_parser = subparsers.add_parser("evaluate-r0-4")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase2-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--network-observation", type=Path, required=True)
    evaluate_parser.add_argument("--window", type=Path, required=True)
    evaluate_parser.add_argument("--capture-record", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--reconnect-summary", type=Path, required=True)
    evaluate_parser.add_argument("--upstream-acceptance", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "record-network-loss":
        manifest = load_manifest(args.manifest.read_bytes())
        network_loss_result = build_network_loss_observation(
            manifest,
            observer_id=args.observer_id,
            controller_id=args.controller_id,
            loss_started_at=_parse_datetime(args.loss_started_at),
            loss_confirmed_at=_parse_datetime(args.loss_confirmed_at),
            controller_receipt_sha256=sha256_file(args.controller_receipt),
            independent_observation_sha256=sha256_file(args.independent_observation),
        )
        _write_json(args.output, network_loss_result)
        return 0

    if args.command == "record-offline-window":
        offline_window_result = build_offline_window(
            load_manifest(args.manifest.read_bytes()),
            load_phase2_evaluation(args.phase2_evaluation.read_bytes()),
            load_network_observation(args.network_observation.read_bytes()),
            window_id=args.window_id,
            started_at=_parse_datetime(args.started_at),
            completed_at=_parse_datetime(args.completed_at),
            attempted_event_count=args.attempted_events,
            pre_loss_queue=_load_sync_status(args.pre_loss_queue),
            outage_queue=_load_sync_status(args.outage_queue),
            resource_observation_sha256=sha256_file(args.resource_observation),
        )
        _write_json(args.output, offline_window_result)
        return 0

    if args.command == "record-offline-capture":
        offline_capture_result = build_offline_capture_record(
            load_offline_window(args.window.read_bytes()),
            WebhookCaptureReceipt.model_validate_json(args.receipt.read_bytes()),
            sequence_number=args.sequence,
            captured_at=_parse_datetime(args.captured_at),
            request_payload_sha256=sha256_file(args.request_payload),
            receipt_artifact_sha256=sha256_file(args.receipt),
            proof_artifact_sha256=sha256_file(args.proof),
        )
        _write_json(args.output, offline_capture_result)
        return 0

    if args.command == "record-offline-proof":
        record = load_offline_capture(args.capture_record.read_bytes())
        offline_proof_result = build_offline_proof_receipt(
            record,
            _load_json_object(args.verification_result),
            verifier_id=args.verifier_id,
            verifier_host_id=args.verifier_host_id,
            verifier_build_sha256=args.verifier_build_digest,
            verification_result_sha256=sha256_file(args.verification_result),
            verified_at=_parse_datetime(args.verified_at),
            independent_execution_context=args.independent,
        )
        _write_json(args.output, offline_proof_result)
        return 0

    if args.command == "record-upstream-acceptance":
        upstream_acceptance_result = build_upstream_acceptance(
            load_offline_capture(args.capture_record.read_bytes()),
            idempotency_key=args.idempotency_key,
            accepted_at=_parse_datetime(args.accepted_at),
            acknowledgement_hash=args.acknowledgement_hash,
            upstream_artifact_sha256=sha256_file(args.upstream_artifact),
            upstream_observer_id=args.upstream_observer_id,
        )
        _write_json(args.output, upstream_acceptance_result)
        return 0

    if args.command == "record-reconnect":
        reconnect_result = build_reconnect_summary(
            load_offline_window(args.window.read_bytes()),
            reconnect_observed_at=_parse_datetime(args.reconnect_observed_at),
            sync_completed_at=_parse_datetime(args.sync_completed_at),
            independent_reconnect_observation_sha256=sha256_file(
                args.reconnect_observation
            ),
            initial_queue=_load_sync_status(args.initial_queue),
            final_queue=_load_sync_status(args.final_queue),
            sync_run_artifact_sha256=tuple(
                sha256_file(path) for path in args.sync_run_artifact
            ),
        )
        _write_json(args.output, reconnect_result)
        return 0

    if args.command == "evaluate-r0-4":
        evaluation_result = evaluate_r0_4(
            load_manifest(args.manifest.read_bytes()),
            load_phase2_evaluation(args.phase2_evaluation.read_bytes()),
            load_network_observation(args.network_observation.read_bytes()),
            load_offline_window(args.window.read_bytes()),
            tuple(load_offline_capture(path.read_bytes()) for path in args.capture_record),
            tuple(load_offline_proof(path.read_bytes()) for path in args.proof_receipt),
            load_reconnect_summary(args.reconnect_summary.read_bytes()),
            tuple(
                load_upstream_acceptance(path.read_bytes())
                for path in args.upstream_acceptance
            ),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, evaluation_result)
        return 0 if evaluation_result.r0_4_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")
