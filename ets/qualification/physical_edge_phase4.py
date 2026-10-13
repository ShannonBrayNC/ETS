"""Wave 1 Edge Compact R0 idle hard-power interruption evidence.

R0.5 proves recovery from an operator-authorized external hard-power interruption while
Edge is demonstrably idle. This module records and evaluates evidence only; it never
actuates the power control and cannot publish a hardware qualification claim.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.edge.device_identity import EdgeDeviceIdentity, load_device_identity
from ets.edge.webhook_adapter import WebhookCaptureReceipt
from ets.qualification.physical_edge import (
    BenchControlKind,
    EdgeCompactR0BenchManifest,
    load_manifest,
    readiness_issues,
)
from ets.qualification.physical_edge_phase1 import sha256_file
from ets.qualification.physical_edge_phase3 import (
    EdgeR0Phase3Evaluation,
    EdgeSyncStatusEvidence,
)

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE4_CLAIM_BOUNDARY: Literal[
    "r0_5_phase_evidence_not_a_physical_qualification_result"
] = "r0_5_phase_evidence_not_a_physical_qualification_result"
_PHASE4_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase4Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class EdgeR0IdlePreCutSnapshot(StrictPhase4Model):
    schema_version: Literal["ets.edge-compact-r0-idle-pre-cut.v1"] = (
        "ets.edge-compact-r0-idle-pre-cut.v1"
    )
    snapshot_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase3_evaluation_id: str = Field(min_length=1, max_length=256)
    phase3_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    boot_id: str = Field(min_length=36, max_length=36)
    identity_manifest_sha256: str = Field(pattern=_SHA256_RE)
    device_id: str = Field(min_length=1, max_length=256)
    signing_algorithm: Literal["ed25519"] = "ed25519"
    signing_public_key_id: str = Field(min_length=1, max_length=256)
    signing_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_key_fingerprint_sha256: str = Field(pattern=_SHA256_RE)
    key_custody: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    queue_state: EdgeSyncStatusEvidence
    capture_idle: Literal[True] = True
    sync_idle: Literal[True] = True
    local_endpoint_reachable: Literal[True] = True
    log_head_sha256: str = Field(pattern=_SHA256_RE)
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_5_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE4_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "pre-cut timestamp")

    @field_validator("boot_id")
    @classmethod
    def validate_boot_id(cls, value: str) -> str:
        return _canonical_boot_id(value)

    @field_validator("representative_proof_sha256")
    @classmethod
    def validate_proof_digests(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_validate_sha256(value) for value in values)
        if len(normalized) != len(set(normalized)):
            raise ValueError("representative proof digests must be unique")
        return normalized


class EdgeR0IdlePowerInterruptionObservation(StrictPhase4Model):
    schema_version: Literal["ets.edge-compact-r0-idle-power-interruption.v1"] = (
        "ets.edge-compact-r0-idle-power-interruption.v1"
    )
    observation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    pre_cut_snapshot_id: str = Field(min_length=1, max_length=256)
    pre_cut_snapshot_sha256: str = Field(pattern=_SHA256_RE)
    power_control_id: str = Field(min_length=1, max_length=256)
    observer_id: str = Field(min_length=1, max_length=256)
    controller_id: str = Field(min_length=1, max_length=256)
    cut_commanded_at: datetime
    power_loss_observed_at: datetime
    restore_commanded_at: datetime
    power_restored_observed_at: datetime
    operator_approved: Literal[True] = True
    pre_cut_idle_confirmed: Literal[True] = True
    dut_unreachable_during_interruption: Literal[True] = True
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    observer_loss_receipt_sha256: str = Field(pattern=_SHA256_RE)
    observer_restore_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_5_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE4_CLAIM_BOUNDARY

    @field_validator(
        "cut_commanded_at",
        "power_loss_observed_at",
        "restore_commanded_at",
        "power_restored_observed_at",
    )
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "power-interruption timestamp")

    @model_validator(mode="after")
    def require_order(self) -> EdgeR0IdlePowerInterruptionObservation:
        timeline = (
            self.cut_commanded_at,
            self.power_loss_observed_at,
            self.restore_commanded_at,
            self.power_restored_observed_at,
        )
        if tuple(sorted(timeline)) != timeline:
            raise ValueError("power interruption timestamps must be monotonic")
        return self


class EdgeR0IdleRecoverySnapshot(StrictPhase4Model):
    schema_version: Literal["ets.edge-compact-r0-idle-recovery.v1"] = (
        "ets.edge-compact-r0-idle-recovery.v1"
    )
    snapshot_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    pre_cut_snapshot_id: str = Field(min_length=1, max_length=256)
    power_observation_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    boot_id: str = Field(min_length=36, max_length=36)
    identity_manifest_sha256: str = Field(pattern=_SHA256_RE)
    device_id: str = Field(min_length=1, max_length=256)
    signing_algorithm: Literal["ed25519"] = "ed25519"
    signing_public_key_id: str = Field(min_length=1, max_length=256)
    signing_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_key_fingerprint_sha256: str = Field(pattern=_SHA256_RE)
    key_custody: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    queue_state: EdgeSyncStatusEvidence
    local_endpoint_reachable: Literal[True] = True
    pre_cut_log_head_sha256: str = Field(pattern=_SHA256_RE)
    pre_cut_log_head_observed: bool
    filesystem_recovery_clean: bool
    recovery_journal_sha256: str = Field(pattern=_SHA256_RE)
    filesystem_check_sha256: str = Field(pattern=_SHA256_RE)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_5_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE4_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "recovery timestamp")

    @field_validator("boot_id")
    @classmethod
    def validate_boot_id(cls, value: str) -> str:
        return _canonical_boot_id(value)


class EdgeR0PreservedProofReceipt(StrictPhase4Model):
    schema_version: Literal["ets.edge-compact-r0-preserved-proof-receipt.v1"] = (
        "ets.edge-compact-r0-preserved-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    pre_cut_snapshot_id: str = Field(min_length=1, max_length=256)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_5_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE4_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "preserved-proof verification timestamp")


class EdgeR0RecoveryCanary(StrictPhase4Model):
    schema_version: Literal["ets.edge-compact-r0-recovery-canary.v1"] = (
        "ets.edge-compact-r0-recovery-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    recovery_snapshot_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    receipt_artifact_sha256: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    event_hash: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    sync_state: str = Field(min_length=1, max_length=64)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_5_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE4_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "canary timestamp")

    @model_validator(mode="after")
    def bind_payload(self) -> EdgeR0RecoveryCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("canary request SHA-256 must match Edge content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("canary verification cannot precede capture")
        return self


class EdgeR0Phase4Evaluation(StrictPhase4Model):
    schema_version: Literal["ets.edge-compact-r0-phase4-evaluation.v1"] = (
        "ets.edge-compact-r0-phase4-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase3_evaluation_id: str = Field(min_length=1, max_length=256)
    pre_cut_snapshot_id: str = Field(min_length=1, max_length=256)
    power_observation_id: str = Field(min_length=1, max_length=256)
    recovery_snapshot_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    preserved_proof_count: int = Field(ge=0)
    identity_preserved: bool
    queue_semantics_preserved: bool
    committed_evidence_preserved: bool
    post_recovery_canary_valid: bool
    r0_5_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE4_DISPOSITION
    claim_boundary: Literal[
        "r0_5_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE4_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.5 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase4Evaluation:
        expected = (
            self.identity_preserved
            and self.queue_semantics_preserved
            and self.committed_evidence_preserved
            and self.post_recovery_canary_valid
            and not self.issues
        )
        if self.r0_5_passed != expected:
            raise ValueError("r0_5_passed must match the component results and issues")
        return self


def load_phase3_evaluation(raw: bytes) -> EdgeR0Phase3Evaluation:
    return EdgeR0Phase3Evaluation.model_validate_json(raw)


def load_pre_cut_snapshot(raw: bytes) -> EdgeR0IdlePreCutSnapshot:
    return EdgeR0IdlePreCutSnapshot.model_validate_json(raw)


def load_power_observation(raw: bytes) -> EdgeR0IdlePowerInterruptionObservation:
    return EdgeR0IdlePowerInterruptionObservation.model_validate_json(raw)


def load_recovery_snapshot(raw: bytes) -> EdgeR0IdleRecoverySnapshot:
    return EdgeR0IdleRecoverySnapshot.model_validate_json(raw)


def load_preserved_proof(raw: bytes) -> EdgeR0PreservedProofReceipt:
    return EdgeR0PreservedProofReceipt.model_validate_json(raw)


def load_recovery_canary(raw: bytes) -> EdgeR0RecoveryCanary:
    return EdgeR0RecoveryCanary.model_validate_json(raw)


def build_pre_cut_snapshot(
    manifest: EdgeCompactR0BenchManifest,
    phase3: EdgeR0Phase3Evaluation,
    identity: EdgeDeviceIdentity,
    *,
    boot_id: str,
    captured_at: datetime,
    queue_state: EdgeSyncStatusEvidence,
    log_head_sha256: str,
    representative_proof_sha256: tuple[str, ...],
    observer_receipt_sha256: str,
) -> EdgeR0IdlePreCutSnapshot:
    blockers = readiness_issues(manifest)
    if blockers:
        raise ValueError("bench manifest is not ready for R0.5 execution")
    if not phase3.r0_4_passed:
        raise ValueError("R0.4 must pass before R0.5 begins")
    asset_id = _require_present(manifest.dut.asset_id, "DUT asset_id")
    if phase3.manifest_id != manifest.manifest_id or phase3.asset_id != asset_id:
        raise ValueError("R0.4 evaluation is bound to another DUT")
    _require_idle_queue(queue_state)
    _require_software_identity(identity)
    power_control = next(
        (control for control in manifest.controls if control.kind is BenchControlKind.POWER),
        None,
    )
    if power_control is None or not power_control.operator_approval_required:
        raise ValueError("R0.5 requires the operator-gated W1-1 power control")

    boot_id = _canonical_boot_id(boot_id)
    seed = {
        "manifest_id": manifest.manifest_id,
        "asset_id": asset_id,
        "phase3_evaluation_id": phase3.evaluation_id,
        "boot_id": boot_id,
        "captured_at": captured_at.isoformat(),
    }
    return EdgeR0IdlePreCutSnapshot(
        snapshot_id=f"edge-r0-precut-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase3_evaluation_id=phase3.evaluation_id,
        phase3_evaluation_sha256=canonical_sha256(phase3.model_dump(mode="json")),
        captured_at=captured_at,
        boot_id=boot_id,
        identity_manifest_sha256=canonical_sha256(identity),
        device_id=identity["device_id"],
        signing_public_key_id=identity["signing_public_key_id"],
        signing_public_key_hex=identity["signing_public_key_hex"],
        public_key_fingerprint_sha256=identity["public_key_fingerprint_sha256"],
        queue_state=queue_state,
        log_head_sha256=_validate_sha256(log_head_sha256),
        representative_proof_sha256=representative_proof_sha256,
        observer_receipt_sha256=_validate_sha256(observer_receipt_sha256),
    )


def build_power_observation(
    manifest: EdgeCompactR0BenchManifest,
    pre_cut: EdgeR0IdlePreCutSnapshot,
    *,
    controller_id: str,
    cut_commanded_at: datetime,
    power_loss_observed_at: datetime,
    restore_commanded_at: datetime,
    power_restored_observed_at: datetime,
    controller_receipt_sha256: str,
    observer_loss_receipt_sha256: str,
    observer_restore_receipt_sha256: str,
) -> EdgeR0IdlePowerInterruptionObservation:
    asset_id = _require_present(manifest.dut.asset_id, "DUT asset_id")
    if pre_cut.manifest_id != manifest.manifest_id or pre_cut.asset_id != asset_id:
        raise ValueError("pre-cut snapshot is bound to another DUT")
    power_control = next(
        (control for control in manifest.controls if control.kind is BenchControlKind.POWER),
        None,
    )
    if power_control is None or not power_control.operator_approval_required:
        raise ValueError("R0.5 requires an operator-gated W1-1 power control")
    observer_id = _require_present(manifest.observer.observer_id, "observer_id")
    seed = {
        "pre_cut_snapshot_id": pre_cut.snapshot_id,
        "power_control_id": power_control.control_id,
        "cut_commanded_at": cut_commanded_at.isoformat(),
        "controller_id": controller_id,
    }
    return EdgeR0IdlePowerInterruptionObservation(
        observation_id=f"edge-r0-power-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        pre_cut_snapshot_id=pre_cut.snapshot_id,
        pre_cut_snapshot_sha256=canonical_sha256(pre_cut.model_dump(mode="json")),
        power_control_id=power_control.control_id,
        observer_id=observer_id,
        controller_id=controller_id,
        cut_commanded_at=cut_commanded_at,
        power_loss_observed_at=power_loss_observed_at,
        restore_commanded_at=restore_commanded_at,
        power_restored_observed_at=power_restored_observed_at,
        controller_receipt_sha256=_validate_sha256(controller_receipt_sha256),
        observer_loss_receipt_sha256=_validate_sha256(observer_loss_receipt_sha256),
        observer_restore_receipt_sha256=_validate_sha256(observer_restore_receipt_sha256),
    )


def build_recovery_snapshot(
    manifest: EdgeCompactR0BenchManifest,
    pre_cut: EdgeR0IdlePreCutSnapshot,
    power: EdgeR0IdlePowerInterruptionObservation,
    identity: EdgeDeviceIdentity,
    *,
    boot_id: str,
    captured_at: datetime,
    queue_state: EdgeSyncStatusEvidence,
    pre_cut_log_head_sha256: str,
    pre_cut_log_head_observed: bool,
    filesystem_recovery_clean: bool,
    recovery_journal_sha256: str,
    filesystem_check_sha256: str,
    observer_receipt_sha256: str,
) -> EdgeR0IdleRecoverySnapshot:
    asset_id = _require_present(manifest.dut.asset_id, "DUT asset_id")
    if pre_cut.manifest_id != manifest.manifest_id or pre_cut.asset_id != asset_id:
        raise ValueError("pre-cut snapshot is bound to another DUT")
    if power.pre_cut_snapshot_id != pre_cut.snapshot_id:
        raise ValueError("power observation is bound to another pre-cut snapshot")
    _require_software_identity(identity)
    boot_id = _canonical_boot_id(boot_id)
    seed = {
        "pre_cut_snapshot_id": pre_cut.snapshot_id,
        "power_observation_id": power.observation_id,
        "boot_id": boot_id,
        "captured_at": captured_at.isoformat(),
    }
    return EdgeR0IdleRecoverySnapshot(
        snapshot_id=f"edge-r0-recovery-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        pre_cut_snapshot_id=pre_cut.snapshot_id,
        power_observation_id=power.observation_id,
        captured_at=captured_at,
        boot_id=boot_id,
        identity_manifest_sha256=canonical_sha256(identity),
        device_id=identity["device_id"],
        signing_public_key_id=identity["signing_public_key_id"],
        signing_public_key_hex=identity["signing_public_key_hex"],
        public_key_fingerprint_sha256=identity["public_key_fingerprint_sha256"],
        queue_state=queue_state,
        pre_cut_log_head_sha256=_validate_sha256(pre_cut_log_head_sha256),
        pre_cut_log_head_observed=pre_cut_log_head_observed,
        filesystem_recovery_clean=filesystem_recovery_clean,
        recovery_journal_sha256=_validate_sha256(recovery_journal_sha256),
        filesystem_check_sha256=_validate_sha256(filesystem_check_sha256),
        observer_receipt_sha256=_validate_sha256(observer_receipt_sha256),
    )


def build_preserved_proof_receipt(
    pre_cut: EdgeR0IdlePreCutSnapshot,
    *,
    proof_artifact_sha256: str,
    verification_result: dict[str, object],
    verifier_id: str,
    verifier_host_id: str,
    verifier_build_sha256: str,
    verification_result_sha256: str,
    verified_at: datetime,
    independent_execution_context: bool,
) -> EdgeR0PreservedProofReceipt:
    proof_digest = _validate_sha256(proof_artifact_sha256)
    if proof_digest not in pre_cut.representative_proof_sha256:
        raise ValueError("proof digest was not part of the pre-cut representative set")
    seed = {
        "pre_cut_snapshot_id": pre_cut.snapshot_id,
        "proof_artifact_sha256": proof_digest,
        "verified_at": verified_at.isoformat(),
        "verifier_host_id": verifier_host_id,
    }
    return EdgeR0PreservedProofReceipt(
        receipt_id=f"edge-r0-preserved-{canonical_sha256(seed)[:24]}",
        pre_cut_snapshot_id=pre_cut.snapshot_id,
        proof_artifact_sha256=proof_digest,
        verified_at=verified_at,
        verifier_id=verifier_id,
        verifier_host_id=verifier_host_id,
        verifier_build_sha256=_validate_sha256(verifier_build_sha256),
        verification_result_sha256=_validate_sha256(verification_result_sha256),
        inclusion_valid=verification_result.get("valid") is True,
        independent_execution_context=independent_execution_context,
    )


def build_recovery_canary(
    recovery: EdgeR0IdleRecoverySnapshot,
    receipt: WebhookCaptureReceipt,
    verification_result: dict[str, object],
    *,
    captured_at: datetime,
    request_payload_sha256: str,
    receipt_artifact_sha256: str,
    proof_artifact_sha256: str,
    verified_at: datetime,
    verifier_id: str,
    verifier_host_id: str,
    verifier_build_sha256: str,
    verification_result_sha256: str,
    independent_execution_context: bool,
) -> EdgeR0RecoveryCanary:
    seed = {
        "recovery_snapshot_id": recovery.snapshot_id,
        "event_id": receipt.event_id,
        "captured_at": captured_at.isoformat(),
    }
    return EdgeR0RecoveryCanary(
        canary_id=f"edge-r0-canary-{canonical_sha256(seed)[:24]}",
        recovery_snapshot_id=recovery.snapshot_id,
        captured_at=captured_at,
        request_payload_sha256=_validate_sha256(request_payload_sha256),
        receipt_artifact_sha256=_validate_sha256(receipt_artifact_sha256),
        event_id=receipt.event_id,
        event_hash=_validate_sha256(receipt.event_hash),
        content_hash=_validate_sha256(receipt.content_hash),
        sync_state=receipt.sync_state,
        proof_artifact_sha256=_validate_sha256(proof_artifact_sha256),
        verified_at=verified_at,
        verifier_id=verifier_id,
        verifier_host_id=verifier_host_id,
        verifier_build_sha256=_validate_sha256(verifier_build_sha256),
        verification_result_sha256=_validate_sha256(verification_result_sha256),
        inclusion_valid=verification_result.get("valid") is True,
        independent_execution_context=independent_execution_context,
    )


def evaluate_r0_5(
    manifest: EdgeCompactR0BenchManifest,
    phase3: EdgeR0Phase3Evaluation,
    pre_cut: EdgeR0IdlePreCutSnapshot,
    power: EdgeR0IdlePowerInterruptionObservation,
    recovery: EdgeR0IdleRecoverySnapshot,
    preserved_proofs: tuple[EdgeR0PreservedProofReceipt, ...],
    canary: EdgeR0RecoveryCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase4Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.5: bench manifest not ready: {blocker}")
    if not phase3.r0_4_passed:
        issues.append("R0.5: R0.4 did not pass")
    if phase3.manifest_id != manifest.manifest_id or phase3.asset_id != asset_id:
        issues.append("R0.5: R0.4 evaluation is bound to another DUT")
    if pre_cut.phase3_evaluation_id != phase3.evaluation_id:
        issues.append("R0.5: pre-cut snapshot references another R0.4 evaluation")
    if pre_cut.phase3_evaluation_sha256 != canonical_sha256(phase3.model_dump(mode="json")):
        issues.append("R0.5: R0.4 digest binding mismatch")
    if pre_cut.manifest_id != manifest.manifest_id or pre_cut.asset_id != asset_id:
        issues.append("R0.5: pre-cut snapshot is bound to another DUT")

    power_control = next(
        (control for control in manifest.controls if control.kind is BenchControlKind.POWER),
        None,
    )
    if power_control is None or power.power_control_id != power_control.control_id:
        issues.append("R0.5: power observation does not bind to the W1-1 power control")
    if power.observer_id != manifest.observer.observer_id:
        issues.append("R0.5: power observer does not match bench observer")
    if power.pre_cut_snapshot_id != pre_cut.snapshot_id:
        issues.append("R0.5: power observation references another pre-cut snapshot")
    if power.pre_cut_snapshot_sha256 != canonical_sha256(pre_cut.model_dump(mode="json")):
        issues.append("R0.5: pre-cut snapshot digest mismatch")
    if power.cut_commanded_at < pre_cut.captured_at:
        issues.append("R0.5: power cut was commanded before the retained idle snapshot")

    pre_queue_idle = _queue_is_idle(pre_cut.queue_state)
    if not pre_queue_idle:
        issues.append("R0.5: pre-cut queue was not idle")
    if not pre_cut.capture_idle or not pre_cut.sync_idle:
        issues.append("R0.5: pre-cut capture/sync activity was not idle")

    if recovery.manifest_id != manifest.manifest_id or recovery.asset_id != asset_id:
        issues.append("R0.5: recovery snapshot is bound to another DUT")
    if recovery.pre_cut_snapshot_id != pre_cut.snapshot_id:
        issues.append("R0.5: recovery snapshot references another pre-cut snapshot")
    if recovery.power_observation_id != power.observation_id:
        issues.append("R0.5: recovery snapshot references another power observation")
    if recovery.captured_at < power.power_restored_observed_at:
        issues.append("R0.5: recovery snapshot predates observed power restoration")
    if recovery.boot_id == pre_cut.boot_id:
        issues.append("R0.5: Linux boot ID did not change after hard-power recovery")
    if not recovery.filesystem_recovery_clean:
        issues.append("R0.5: filesystem recovery check was not clean")
    if not recovery.pre_cut_log_head_observed:
        issues.append("R0.5: pre-cut log head was not observed after recovery")
    if recovery.pre_cut_log_head_sha256 != pre_cut.log_head_sha256:
        issues.append("R0.5: recovered pre-cut log-head digest mismatch")

    identity_fields = (
        "device_id",
        "signing_algorithm",
        "signing_public_key_id",
        "signing_public_key_hex",
        "public_key_fingerprint_sha256",
        "key_custody",
        "hardware_attested",
    )
    identity_preserved = all(
        getattr(pre_cut, field) == getattr(recovery, field) for field in identity_fields
    )
    if not identity_preserved:
        issues.append("R0.5: software-backed device identity changed across power loss")

    post_queue_idle = _queue_is_idle(recovery.queue_state)
    queue_semantics_preserved = (
        pre_queue_idle
        and post_queue_idle
        and recovery.queue_state.synchronized == pre_cut.queue_state.synchronized
    )
    if not post_queue_idle:
        issues.append("R0.5: recovered queue contains unresolved work")
    if recovery.queue_state.synchronized != pre_cut.queue_state.synchronized:
        issues.append("R0.5: synchronized-record count changed during idle power interruption")

    proof_by_digest: dict[str, EdgeR0PreservedProofReceipt] = {}
    verifier_host = manifest.verifier.verifier_host_id
    valid_preserved_count = 0
    for proof_receipt in preserved_proofs:
        if proof_receipt.proof_artifact_sha256 in proof_by_digest:
            issues.append(
                "R0.5: duplicate preserved-proof verification for "
                f"{proof_receipt.proof_artifact_sha256}"
            )
            continue
        proof_by_digest[proof_receipt.proof_artifact_sha256] = proof_receipt
    for proof_digest in pre_cut.representative_proof_sha256:
        retained_receipt = proof_by_digest.get(proof_digest)
        if retained_receipt is None:
            issues.append(f"R0.5: missing preserved-proof verification for {proof_digest}")
            continue
        if retained_receipt.pre_cut_snapshot_id != pre_cut.snapshot_id:
            issues.append(f"R0.5: preserved-proof snapshot binding mismatch for {proof_digest}")
        if not retained_receipt.inclusion_valid:
            issues.append(f"R0.5: preserved proof did not verify after recovery: {proof_digest}")
        if not retained_receipt.independent_execution_context:
            issues.append(f"R0.5: preserved proof was not independently verified: {proof_digest}")
        if verifier_host is None or retained_receipt.verifier_host_id != verifier_host:
            issues.append(f"R0.5: preserved-proof verifier host mismatch for {proof_digest}")
        if (
            retained_receipt.inclusion_valid
            and retained_receipt.independent_execution_context
            and retained_receipt.verifier_host_id == verifier_host
        ):
            valid_preserved_count += 1

    unknown_proofs = sorted(set(proof_by_digest) - set(pre_cut.representative_proof_sha256))
    if unknown_proofs:
        issues.append(f"R0.5: proof receipts reference unknown pre-cut proofs: {unknown_proofs}")
    committed_evidence_preserved = (
        recovery.pre_cut_log_head_observed
        and recovery.pre_cut_log_head_sha256 == pre_cut.log_head_sha256
        and valid_preserved_count == len(pre_cut.representative_proof_sha256)
    )

    canary_valid = True
    if canary.recovery_snapshot_id != recovery.snapshot_id:
        issues.append("R0.5: recovery canary references another recovery snapshot")
        canary_valid = False
    if canary.captured_at < recovery.captured_at:
        issues.append("R0.5: recovery canary predates recovery snapshot")
        canary_valid = False
    if not canary.inclusion_valid or not canary.independent_execution_context:
        issues.append("R0.5: post-recovery canary proof did not verify independently")
        canary_valid = False
    if verifier_host is None or canary.verifier_host_id != verifier_host:
        issues.append("R0.5: recovery canary verifier host does not match bench binding")
        canary_valid = False
    if canary.sync_state in {"terminal_failure", "rejected", "conflict"}:
        issues.append("R0.5: recovery canary entered a terminal synchronization state")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase3_evaluation_id": phase3.evaluation_id,
        "pre_cut_snapshot_id": pre_cut.snapshot_id,
        "power_observation_id": power.observation_id,
        "recovery_snapshot_id": recovery.snapshot_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        identity_preserved
        and queue_semantics_preserved
        and committed_evidence_preserved
        and canary_valid
        and not issues
    )
    return EdgeR0Phase4Evaluation(
        evaluation_id=f"edge-r0-phase4-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase3_evaluation_id=phase3.evaluation_id,
        pre_cut_snapshot_id=pre_cut.snapshot_id,
        power_observation_id=power.observation_id,
        recovery_snapshot_id=recovery.snapshot_id,
        evaluated_at=evaluated_at,
        preserved_proof_count=valid_preserved_count,
        identity_preserved=identity_preserved,
        queue_semantics_preserved=queue_semantics_preserved,
        committed_evidence_preserved=committed_evidence_preserved,
        post_recovery_canary_valid=canary_valid,
        r0_5_passed=passed,
        issues=tuple(issues),
    )


def _queue_is_idle(queue: EdgeSyncStatusEvidence) -> bool:
    return (
        queue.queue_depth == 0
        and queue.queue_bytes == 0
        and queue.pending == 0
        and queue.in_flight == 0
        and queue.retryable_failure == 0
        and queue.terminal_failure == 0
    )


def _require_idle_queue(queue: EdgeSyncStatusEvidence) -> None:
    if not _queue_is_idle(queue):
        raise ValueError("R0.5 hard-power interruption requires an idle synchronization queue")


def _require_software_identity(identity: EdgeDeviceIdentity) -> None:
    if identity["signing_algorithm"] != "ed25519":
        raise ValueError("R0.5 requires the canonical Edge Ed25519 identity")
    if identity["key_custody"] != "software_volume" or identity["hardware_attested"] is not False:
        raise ValueError("R0.5 remains inside the software_volume/non-attested trust boundary")


def _canonical_boot_id(value: str) -> str:
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ValueError("boot_id must be a canonical UUID") from exc
    canonical = str(parsed)
    if value.lower() != canonical:
        raise ValueError("boot_id must use canonical UUID formatting")
    return canonical


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


def _read_boot_id(path: Path) -> str:
    return _canonical_boot_id(path.read_text(encoding="utf-8").strip())


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
    parser = argparse.ArgumentParser(description="ETS Wave 1 Edge Compact R0 R0.5 evidence tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pre = subparsers.add_parser("record-pre-cut")
    pre.add_argument("--manifest", type=Path, required=True)
    pre.add_argument("--phase3-evaluation", type=Path, required=True)
    pre.add_argument("--identity", type=Path, required=True)
    pre.add_argument(
        "--boot-id-file",
        type=Path,
        default=Path("/proc/sys/kernel/random/boot_id"),
    )
    pre.add_argument("--captured-at", required=True)
    pre.add_argument("--queue-state", type=Path, required=True)
    pre.add_argument("--log-head", type=Path, required=True)
    pre.add_argument("--proof", type=Path, action="append", required=True)
    pre.add_argument("--observer-receipt", type=Path, required=True)
    pre.add_argument("--output", type=Path, required=True)

    power_parser = subparsers.add_parser("record-power-event")
    power_parser.add_argument("--manifest", type=Path, required=True)
    power_parser.add_argument("--pre-cut", type=Path, required=True)
    power_parser.add_argument("--controller-id", required=True)
    power_parser.add_argument("--cut-commanded-at", required=True)
    power_parser.add_argument("--power-loss-observed-at", required=True)
    power_parser.add_argument("--restore-commanded-at", required=True)
    power_parser.add_argument("--power-restored-observed-at", required=True)
    power_parser.add_argument("--controller-receipt", type=Path, required=True)
    power_parser.add_argument("--observer-loss-receipt", type=Path, required=True)
    power_parser.add_argument("--observer-restore-receipt", type=Path, required=True)
    power_parser.add_argument("--output", type=Path, required=True)

    recovery_parser = subparsers.add_parser("record-recovery")
    recovery_parser.add_argument("--manifest", type=Path, required=True)
    recovery_parser.add_argument("--pre-cut", type=Path, required=True)
    recovery_parser.add_argument("--power-event", type=Path, required=True)
    recovery_parser.add_argument("--identity", type=Path, required=True)
    recovery_parser.add_argument(
        "--boot-id-file",
        type=Path,
        default=Path("/proc/sys/kernel/random/boot_id"),
    )
    recovery_parser.add_argument("--captured-at", required=True)
    recovery_parser.add_argument("--queue-state", type=Path, required=True)
    recovery_parser.add_argument("--pre-cut-log-head", type=Path, required=True)
    recovery_parser.add_argument("--pre-cut-log-head-observed", action="store_true")
    recovery_parser.add_argument("--filesystem-recovery-clean", action="store_true")
    recovery_parser.add_argument("--recovery-journal", type=Path, required=True)
    recovery_parser.add_argument("--filesystem-check", type=Path, required=True)
    recovery_parser.add_argument("--observer-receipt", type=Path, required=True)
    recovery_parser.add_argument("--output", type=Path, required=True)

    proof_parser = subparsers.add_parser("record-preserved-proof")
    proof_parser.add_argument("--pre-cut", type=Path, required=True)
    proof_parser.add_argument("--proof", type=Path, required=True)
    proof_parser.add_argument("--verification-result", type=Path, required=True)
    proof_parser.add_argument("--verifier-id", required=True)
    proof_parser.add_argument("--verifier-host-id", required=True)
    proof_parser.add_argument("--verifier-build-digest", required=True)
    proof_parser.add_argument("--verified-at", required=True)
    proof_parser.add_argument("--independent", action="store_true")
    proof_parser.add_argument("--output", type=Path, required=True)

    canary_parser = subparsers.add_parser("record-canary")
    canary_parser.add_argument("--recovery", type=Path, required=True)
    canary_parser.add_argument("--receipt", type=Path, required=True)
    canary_parser.add_argument("--request-payload", type=Path, required=True)
    canary_parser.add_argument("--proof", type=Path, required=True)
    canary_parser.add_argument("--verification-result", type=Path, required=True)
    canary_parser.add_argument("--captured-at", required=True)
    canary_parser.add_argument("--verified-at", required=True)
    canary_parser.add_argument("--verifier-id", required=True)
    canary_parser.add_argument("--verifier-host-id", required=True)
    canary_parser.add_argument("--verifier-build-digest", required=True)
    canary_parser.add_argument("--independent", action="store_true")
    canary_parser.add_argument("--output", type=Path, required=True)

    evaluate_parser = subparsers.add_parser("evaluate-r0-5")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase3-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--pre-cut", type=Path, required=True)
    evaluate_parser.add_argument("--power-event", type=Path, required=True)
    evaluate_parser.add_argument("--recovery", type=Path, required=True)
    evaluate_parser.add_argument("--preserved-proof", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "record-pre-cut":
        pre_cut_result = build_pre_cut_snapshot(
            load_manifest(args.manifest.read_bytes()),
            load_phase3_evaluation(args.phase3_evaluation.read_bytes()),
            load_device_identity(args.identity),
            boot_id=_read_boot_id(args.boot_id_file),
            captured_at=_parse_datetime(args.captured_at),
            queue_state=_load_sync_status(args.queue_state),
            log_head_sha256=sha256_file(args.log_head),
            representative_proof_sha256=tuple(sha256_file(path) for path in args.proof),
            observer_receipt_sha256=sha256_file(args.observer_receipt),
        )
        _write_json(args.output, pre_cut_result)
        return 0

    if args.command == "record-power-event":
        power_result = build_power_observation(
            load_manifest(args.manifest.read_bytes()),
            load_pre_cut_snapshot(args.pre_cut.read_bytes()),
            controller_id=args.controller_id,
            cut_commanded_at=_parse_datetime(args.cut_commanded_at),
            power_loss_observed_at=_parse_datetime(args.power_loss_observed_at),
            restore_commanded_at=_parse_datetime(args.restore_commanded_at),
            power_restored_observed_at=_parse_datetime(args.power_restored_observed_at),
            controller_receipt_sha256=sha256_file(args.controller_receipt),
            observer_loss_receipt_sha256=sha256_file(args.observer_loss_receipt),
            observer_restore_receipt_sha256=sha256_file(args.observer_restore_receipt),
        )
        _write_json(args.output, power_result)
        return 0

    if args.command == "record-recovery":
        recovery_result = build_recovery_snapshot(
            load_manifest(args.manifest.read_bytes()),
            load_pre_cut_snapshot(args.pre_cut.read_bytes()),
            load_power_observation(args.power_event.read_bytes()),
            load_device_identity(args.identity),
            boot_id=_read_boot_id(args.boot_id_file),
            captured_at=_parse_datetime(args.captured_at),
            queue_state=_load_sync_status(args.queue_state),
            pre_cut_log_head_sha256=sha256_file(args.pre_cut_log_head),
            pre_cut_log_head_observed=args.pre_cut_log_head_observed,
            filesystem_recovery_clean=args.filesystem_recovery_clean,
            recovery_journal_sha256=sha256_file(args.recovery_journal),
            filesystem_check_sha256=sha256_file(args.filesystem_check),
            observer_receipt_sha256=sha256_file(args.observer_receipt),
        )
        _write_json(args.output, recovery_result)
        return 0

    if args.command == "record-preserved-proof":
        preserved_result = build_preserved_proof_receipt(
            load_pre_cut_snapshot(args.pre_cut.read_bytes()),
            proof_artifact_sha256=sha256_file(args.proof),
            verification_result=_load_json_object(args.verification_result),
            verifier_id=args.verifier_id,
            verifier_host_id=args.verifier_host_id,
            verifier_build_sha256=args.verifier_build_digest,
            verification_result_sha256=sha256_file(args.verification_result),
            verified_at=_parse_datetime(args.verified_at),
            independent_execution_context=args.independent,
        )
        _write_json(args.output, preserved_result)
        return 0

    if args.command == "record-canary":
        canary_result = build_recovery_canary(
            load_recovery_snapshot(args.recovery.read_bytes()),
            WebhookCaptureReceipt.model_validate_json(args.receipt.read_bytes()),
            _load_json_object(args.verification_result),
            captured_at=_parse_datetime(args.captured_at),
            request_payload_sha256=sha256_file(args.request_payload),
            receipt_artifact_sha256=sha256_file(args.receipt),
            proof_artifact_sha256=sha256_file(args.proof),
            verified_at=_parse_datetime(args.verified_at),
            verifier_id=args.verifier_id,
            verifier_host_id=args.verifier_host_id,
            verifier_build_sha256=args.verifier_build_digest,
            verification_result_sha256=sha256_file(args.verification_result),
            independent_execution_context=args.independent,
        )
        _write_json(args.output, canary_result)
        return 0

    if args.command == "evaluate-r0-5":
        evaluation_result = evaluate_r0_5(
            load_manifest(args.manifest.read_bytes()),
            load_phase3_evaluation(args.phase3_evaluation.read_bytes()),
            load_pre_cut_snapshot(args.pre_cut.read_bytes()),
            load_power_observation(args.power_event.read_bytes()),
            load_recovery_snapshot(args.recovery.read_bytes()),
            tuple(
                load_preserved_proof(path.read_bytes())
                for path in args.preserved_proof
            ),
            load_recovery_canary(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, evaluation_result)
        return 0 if evaluation_result.r0_5_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")
