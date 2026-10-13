"""Wave 1 Edge Compact R0 active-capture hard-power interruption evidence.

R0.6 evaluates a physical power interruption that occurs while controlled ingestion is
active. The module records/evaluates retained evidence only. It never actuates power
control and cannot publish a hardware qualification claim.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
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
from ets.qualification.physical_edge_phase4 import EdgeR0Phase4Evaluation

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE5_CLAIM_BOUNDARY: Literal[
    "r0_6_phase_evidence_not_a_physical_qualification_result"
] = "r0_6_phase_evidence_not_a_physical_qualification_result"
_PHASE5_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase5Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class R0CaptureState(StrEnum):
    AUTHORITATIVELY_COMMITTED = "authoritatively_committed"
    IN_FLIGHT_UNACKNOWLEDGED = "in_flight_unacknowledged"
    CLIENT_ATTEMPT_ONLY = "client_attempt_only"


class R0RecoveryDisposition(StrEnum):
    COMMITTED_BEFORE_CUT_PRESERVED = "committed_before_cut_preserved"
    UNACKNOWLEDGED_COMMIT_RECOVERED = "not_authoritatively_acknowledged_but_commit_recovered"
    UNACKNOWLEDGED_RETRYABLE = "not_authoritatively_acknowledged_retryable"
    UNACKNOWLEDGED_ABSENT = "not_authoritatively_acknowledged_absent"
    REJECTED_WITH_EXPLICIT_RECEIPT = "rejected_with_explicit_receipt"


class EdgeR0CaptureAttemptEvidence(StrictPhase5Model):
    schema_version: Literal["ets.edge-compact-r0-capture-attempt.v1"] = (
        "ets.edge-compact-r0-capture-attempt.v1"
    )
    attempt_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    attempted_at: datetime
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    client_attempt_receipt_sha256: str = Field(pattern=_SHA256_RE)
    pre_cut_state: R0CaptureState
    event_id: str | None = Field(default=None, max_length=256)
    event_hash: str | None = Field(default=None, pattern=_SHA256_RE)
    content_hash: str | None = Field(default=None, pattern=_SHA256_RE)
    commit_receipt_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    proof_artifact_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_6_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE5_CLAIM_BOUNDARY

    @field_validator("attempted_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "capture-attempt timestamp")

    @model_validator(mode="after")
    def enforce_pre_cut_state(self) -> EdgeR0CaptureAttemptEvidence:
        commit_fields = (
            self.event_id,
            self.event_hash,
            self.content_hash,
            self.commit_receipt_sha256,
            self.proof_artifact_sha256,
        )
        if self.pre_cut_state is R0CaptureState.AUTHORITATIVELY_COMMITTED:
            if any(value is None for value in commit_fields):
                raise ValueError(
                    "authoritatively committed attempts require event, commit and proof fields"
                )
            if self.request_payload_sha256 != self.content_hash:
                raise ValueError("committed request SHA-256 must match Edge content_hash")
        elif any(value is not None for value in commit_fields):
            raise ValueError(
                "unacknowledged pre-cut attempts must not carry authoritative commit fields"
            )
        return self


class EdgeR0ActiveCaptureWindow(StrictPhase5Model):
    schema_version: Literal["ets.edge-compact-r0-active-capture-window.v1"] = (
        "ets.edge-compact-r0-active-capture-window.v1"
    )
    window_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase4_evaluation_id: str = Field(min_length=1, max_length=256)
    phase4_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    started_at: datetime
    cut_boundary_at: datetime
    boot_id: str = Field(min_length=36, max_length=36)
    device_id: str = Field(min_length=1, max_length=256)
    signing_public_key_id: str = Field(min_length=1, max_length=256)
    signing_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_key_fingerprint_sha256: str = Field(pattern=_SHA256_RE)
    key_custody: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    active_ingestion_confirmed: Literal[True] = True
    synchronization_active: Literal[False] = False
    starting_log_head_sha256: str = Field(pattern=_SHA256_RE)
    starting_queue_state: EdgeSyncStatusEvidence
    controller_timeline_sha256: str = Field(pattern=_SHA256_RE)
    attempts: tuple[EdgeR0CaptureAttemptEvidence, ...] = Field(min_length=2)
    claim_boundary: Literal[
        "r0_6_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE5_CLAIM_BOUNDARY

    @field_validator("started_at", "cut_boundary_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "active-capture timestamp")

    @field_validator("boot_id")
    @classmethod
    def validate_boot_id(cls, value: str) -> str:
        return _canonical_boot_id(value)

    @model_validator(mode="after")
    def validate_window(self) -> EdgeR0ActiveCaptureWindow:
        if self.cut_boundary_at <= self.started_at:
            raise ValueError("cut boundary must follow active-capture start")
        attempt_ids = [item.attempt_id for item in self.attempts]
        sequences = [item.sequence_number for item in self.attempts]
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValueError("capture attempt IDs must be unique")
        if sequences != list(range(1, len(self.attempts) + 1)):
            raise ValueError("capture attempt sequence numbers must be contiguous and ordered")
        if any(item.window_id != self.window_id for item in self.attempts):
            raise ValueError("capture attempt belongs to another active-capture window")
        if any(
            not (self.started_at <= item.attempted_at <= self.cut_boundary_at)
            for item in self.attempts
        ):
            raise ValueError("capture attempt timestamp lies outside the pre-cut window")
        states = {item.pre_cut_state for item in self.attempts}
        if R0CaptureState.AUTHORITATIVELY_COMMITTED not in states:
            raise ValueError("R0.6 requires at least one authoritative pre-cut commit")
        if R0CaptureState.IN_FLIGHT_UNACKNOWLEDGED not in states:
            raise ValueError("R0.6 requires an in-flight unacknowledged cut-boundary attempt")
        return self


class EdgeR0ActivePowerObservation(StrictPhase5Model):
    schema_version: Literal["ets.edge-compact-r0-active-power-interruption.v1"] = (
        "ets.edge-compact-r0-active-power-interruption.v1"
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
    active_capture_confirmed: Literal[True] = True
    sync_idle_confirmed: Literal[True] = True
    dut_unreachable_during_interruption: Literal[True] = True
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    observer_loss_receipt_sha256: str = Field(pattern=_SHA256_RE)
    observer_restore_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_6_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE5_CLAIM_BOUNDARY

    @field_validator(
        "cut_commanded_at",
        "power_loss_observed_at",
        "restore_commanded_at",
        "power_restored_observed_at",
    )
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "active-power timestamp")

    @model_validator(mode="after")
    def require_order(self) -> EdgeR0ActivePowerObservation:
        timeline = (
            self.cut_commanded_at,
            self.power_loss_observed_at,
            self.restore_commanded_at,
            self.power_restored_observed_at,
        )
        if tuple(sorted(timeline)) != timeline:
            raise ValueError("power interruption timestamps must be monotonic")
        return self


class EdgeR0ActiveRecoverySnapshot(StrictPhase5Model):
    schema_version: Literal["ets.edge-compact-r0-active-recovery.v1"] = (
        "ets.edge-compact-r0-active-recovery.v1"
    )
    snapshot_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    power_observation_id: str = Field(min_length=1, max_length=256)
    recovered_at: datetime
    boot_id: str = Field(min_length=36, max_length=36)
    device_id: str = Field(min_length=1, max_length=256)
    signing_public_key_id: str = Field(min_length=1, max_length=256)
    signing_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_key_fingerprint_sha256: str = Field(pattern=_SHA256_RE)
    key_custody: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    recovered_log_head_sha256: str = Field(pattern=_SHA256_RE)
    queue_state: EdgeSyncStatusEvidence
    filesystem_recovery_clean: bool
    recovery_journal_sha256: str = Field(pattern=_SHA256_RE)
    filesystem_check_sha256: str = Field(pattern=_SHA256_RE)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_6_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE5_CLAIM_BOUNDARY

    @field_validator("recovered_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "active-recovery timestamp")

    @field_validator("boot_id")
    @classmethod
    def validate_boot_id(cls, value: str) -> str:
        return _canonical_boot_id(value)


class EdgeR0AttemptRecoveryDisposition(StrictPhase5Model):
    schema_version: Literal["ets.edge-compact-r0-attempt-recovery.v1"] = (
        "ets.edge-compact-r0-attempt-recovery.v1"
    )
    attempt_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    disposition: R0RecoveryDisposition
    authoritative_commit_count: int = Field(ge=0, le=32)
    recovered_event_id: str | None = Field(default=None, max_length=256)
    recovered_proof_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    retryable: bool = False
    explicit_rejection_receipt_sha256: str | None = Field(
        default=None,
        pattern=_SHA256_RE,
    )
    recovery_observation_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_6_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE5_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def enforce_disposition_shape(self) -> EdgeR0AttemptRecoveryDisposition:
        commit_dispositions = {
            R0RecoveryDisposition.COMMITTED_BEFORE_CUT_PRESERVED,
            R0RecoveryDisposition.UNACKNOWLEDGED_COMMIT_RECOVERED,
        }
        if self.disposition in commit_dispositions:
            if self.authoritative_commit_count < 1:
                raise ValueError("commit recovery disposition requires a recovered commit")
            if self.recovered_event_id is None or self.recovered_proof_sha256 is None:
                raise ValueError("commit recovery disposition requires event and proof binding")
        else:
            if self.authoritative_commit_count != 0:
                raise ValueError("non-commit recovery disposition must have zero commits")
            if self.recovered_event_id is not None or self.recovered_proof_sha256 is not None:
                raise ValueError("non-commit recovery disposition cannot carry commit fields")

        if self.disposition is R0RecoveryDisposition.UNACKNOWLEDGED_RETRYABLE:
            if not self.retryable:
                raise ValueError("retryable disposition must explicitly set retryable=true")
        elif self.retryable:
            raise ValueError("retryable=true is valid only for the retryable disposition")

        if self.disposition is R0RecoveryDisposition.REJECTED_WITH_EXPLICIT_RECEIPT:
            if self.explicit_rejection_receipt_sha256 is None:
                raise ValueError("rejected disposition requires an explicit rejection receipt")
        elif self.explicit_rejection_receipt_sha256 is not None:
            raise ValueError("rejection receipt is valid only for the rejected disposition")
        return self


class EdgeR0RecoveredCommitProofReceipt(StrictPhase5Model):
    schema_version: Literal["ets.edge-compact-r0-recovered-commit-proof.v1"] = (
        "ets.edge-compact-r0-recovered-commit-proof.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    attempt_id: str = Field(min_length=1, max_length=256)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_6_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE5_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "recovered-proof verification timestamp")


class EdgeR0ActiveRecoveryCanary(StrictPhase5Model):
    schema_version: Literal["ets.edge-compact-r0-active-recovery-canary.v1"] = (
        "ets.edge-compact-r0-active-recovery-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    recovery_snapshot_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    event_hash: str = Field(pattern=_SHA256_RE)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    claim_boundary: Literal[
        "r0_6_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE5_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.6 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0ActiveRecoveryCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("canary request SHA-256 must match Edge content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("canary verification cannot precede capture")
        return self


class EdgeR0Phase5Evaluation(StrictPhase5Model):
    schema_version: Literal["ets.edge-compact-r0-phase5-evaluation.v1"] = (
        "ets.edge-compact-r0-phase5-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase4_evaluation_id: str = Field(min_length=1, max_length=256)
    window_id: str = Field(min_length=1, max_length=256)
    power_observation_id: str = Field(min_length=1, max_length=256)
    recovery_snapshot_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    attempted_count: int = Field(ge=0)
    pre_cut_committed_count: int = Field(ge=0)
    recovered_commit_count: int = Field(ge=0)
    independently_verified_commit_count: int = Field(ge=0)
    acknowledged_commits_preserved: bool
    attempt_classification_complete: bool
    no_duplicate_authoritative_commits: bool
    identity_preserved: bool
    post_recovery_canary_valid: bool
    r0_6_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE5_DISPOSITION
    claim_boundary: Literal[
        "r0_6_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE5_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.6 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase5Evaluation:
        expected = (
            self.acknowledged_commits_preserved
            and self.attempt_classification_complete
            and self.no_duplicate_authoritative_commits
            and self.identity_preserved
            and self.post_recovery_canary_valid
            and not self.issues
        )
        if self.r0_6_passed != expected:
            raise ValueError("r0_6_passed must match the component results and issues")
        return self


def load_phase4_evaluation(raw: bytes) -> EdgeR0Phase4Evaluation:
    return EdgeR0Phase4Evaluation.model_validate_json(raw)


def load_active_capture_window(raw: bytes) -> EdgeR0ActiveCaptureWindow:
    return EdgeR0ActiveCaptureWindow.model_validate_json(raw)


def load_power_observation(raw: bytes) -> EdgeR0ActivePowerObservation:
    return EdgeR0ActivePowerObservation.model_validate_json(raw)


def load_recovery_snapshot(raw: bytes) -> EdgeR0ActiveRecoverySnapshot:
    return EdgeR0ActiveRecoverySnapshot.model_validate_json(raw)


def load_attempt_recovery(raw: bytes) -> EdgeR0AttemptRecoveryDisposition:
    return EdgeR0AttemptRecoveryDisposition.model_validate_json(raw)


def load_recovered_proof(raw: bytes) -> EdgeR0RecoveredCommitProofReceipt:
    return EdgeR0RecoveredCommitProofReceipt.model_validate_json(raw)


def load_recovery_canary(raw: bytes) -> EdgeR0ActiveRecoveryCanary:
    return EdgeR0ActiveRecoveryCanary.model_validate_json(raw)


def evaluate_r0_6(
    manifest: EdgeCompactR0BenchManifest,
    phase4: EdgeR0Phase4Evaluation,
    window: EdgeR0ActiveCaptureWindow,
    power: EdgeR0ActivePowerObservation,
    recovery: EdgeR0ActiveRecoverySnapshot,
    dispositions: tuple[EdgeR0AttemptRecoveryDisposition, ...],
    proofs: tuple[EdgeR0RecoveredCommitProofReceipt, ...],
    canary: EdgeR0ActiveRecoveryCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase5Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.6: bench manifest not ready: {blocker}")
    if not phase4.r0_5_passed:
        issues.append("R0.6: R0.5 did not pass")
    if phase4.manifest_id != manifest.manifest_id or phase4.asset_id != asset_id:
        issues.append("R0.6: R0.5 evaluation is bound to another DUT")

    if window.manifest_id != manifest.manifest_id or window.asset_id != asset_id:
        issues.append("R0.6: active-capture window is bound to another DUT")
    if window.phase4_evaluation_id != phase4.evaluation_id:
        issues.append("R0.6: active-capture window references another R0.5 evaluation")
    if window.phase4_evaluation_sha256 != canonical_sha256(phase4.model_dump(mode="json")):
        issues.append("R0.6: R0.5 digest binding mismatch")

    power_control = next(
        (control for control in manifest.controls if control.kind is BenchControlKind.POWER),
        None,
    )
    if power_control is None or power.power_control_id != power_control.control_id:
        issues.append("R0.6: power observation does not bind to the W1-1 power control")
    if power.observer_id != manifest.observer.observer_id:
        issues.append("R0.6: power observer does not match bench observer")
    if power.manifest_id != manifest.manifest_id or power.asset_id != asset_id:
        issues.append("R0.6: power observation is bound to another DUT")
    if power.window_id != window.window_id:
        issues.append("R0.6: power observation references another capture window")
    if power.window_sha256 != canonical_sha256(window.model_dump(mode="json")):
        issues.append("R0.6: active-capture window digest mismatch")
    if power.cut_commanded_at != window.cut_boundary_at:
        issues.append("R0.6: independent cut time does not match retained window boundary")

    if recovery.manifest_id != manifest.manifest_id or recovery.asset_id != asset_id:
        issues.append("R0.6: recovery snapshot is bound to another DUT")
    if recovery.window_id != window.window_id:
        issues.append("R0.6: recovery snapshot references another capture window")
    if recovery.power_observation_id != power.observation_id:
        issues.append("R0.6: recovery snapshot references another power observation")
    if recovery.recovered_at < power.power_restored_observed_at:
        issues.append("R0.6: recovery snapshot predates observed power restoration")
    if recovery.boot_id == window.boot_id:
        issues.append("R0.6: Linux boot ID did not change after hard-power recovery")
    if not recovery.filesystem_recovery_clean:
        issues.append("R0.6: filesystem recovery check was not clean")

    identity_fields = (
        "device_id",
        "signing_public_key_id",
        "signing_public_key_hex",
        "public_key_fingerprint_sha256",
        "key_custody",
        "hardware_attested",
    )
    identity_preserved = all(
        getattr(window, field) == getattr(recovery, field) for field in identity_fields
    )
    if not identity_preserved:
        issues.append("R0.6: software-backed device identity changed across power loss")

    attempts_by_id = {item.attempt_id: item for item in window.attempts}
    dispositions_by_id: dict[str, EdgeR0AttemptRecoveryDisposition] = {}
    for item in dispositions:
        if item.attempt_id in dispositions_by_id:
            issues.append(f"R0.6: duplicate recovery disposition for {item.attempt_id}")
            continue
        dispositions_by_id[item.attempt_id] = item

    unknown_dispositions = sorted(set(dispositions_by_id) - set(attempts_by_id))
    if unknown_dispositions:
        issues.append(
            f"R0.6: recovery dispositions reference unknown attempts: {unknown_dispositions}"
        )
    missing_dispositions = sorted(set(attempts_by_id) - set(dispositions_by_id))
    if missing_dispositions:
        issues.append(
            f"R0.6: missing recovery dispositions for attempts: {missing_dispositions}"
        )

    proof_by_attempt: dict[str, EdgeR0RecoveredCommitProofReceipt] = {}
    for proof_receipt in proofs:
        if proof_receipt.attempt_id in proof_by_attempt:
            issues.append(
                f"R0.6: duplicate recovered proof for {proof_receipt.attempt_id}"
            )
            continue
        proof_by_attempt[proof_receipt.attempt_id] = proof_receipt

    verifier_host = manifest.verifier.verifier_host_id
    pre_cut_committed = 0
    recovered_commit_count = 0
    independently_verified_commit_count = 0
    no_duplicate_authoritative_commits = True
    acknowledged_commits_preserved = True

    for attempt in window.attempts:
        disposition = dispositions_by_id.get(attempt.attempt_id)
        if disposition is None:
            acknowledged_commits_preserved = False
            continue
        if disposition.sequence_number != attempt.sequence_number:
            issues.append(f"R0.6: sequence mismatch for {attempt.attempt_id}")
        if disposition.authoritative_commit_count > 1:
            issues.append(f"R0.6: duplicate authoritative commit for {attempt.attempt_id}")
            no_duplicate_authoritative_commits = False

        pre_cut_committed_attempt = (
            attempt.pre_cut_state is R0CaptureState.AUTHORITATIVELY_COMMITTED
        )
        if pre_cut_committed_attempt:
            pre_cut_committed += 1
            if (
                disposition.disposition
                is not R0RecoveryDisposition.COMMITTED_BEFORE_CUT_PRESERVED
            ):
                issues.append(
                    f"R0.6: acknowledged pre-cut commit not preserved for {attempt.attempt_id}"
                )
                acknowledged_commits_preserved = False
            if disposition.recovered_event_id != attempt.event_id:
                issues.append(f"R0.6: recovered event ID mismatch for {attempt.attempt_id}")
                acknowledged_commits_preserved = False
            if disposition.recovered_proof_sha256 != attempt.proof_artifact_sha256:
                issues.append(f"R0.6: recovered proof digest mismatch for {attempt.attempt_id}")
                acknowledged_commits_preserved = False
        elif (
            disposition.disposition
            is R0RecoveryDisposition.COMMITTED_BEFORE_CUT_PRESERVED
        ):
            issues.append(
                "R0.6: unacknowledged attempt was retroactively classified as "
                f"acknowledged-before-cut: {attempt.attempt_id}"
            )

        if disposition.authoritative_commit_count == 1:
            recovered_commit_count += 1
            recovered_proof = proof_by_attempt.get(attempt.attempt_id)
            if recovered_proof is None:
                issues.append(
                    f"R0.6: recovered commit lacks independent proof for {attempt.attempt_id}"
                )
                if pre_cut_committed_attempt:
                    acknowledged_commits_preserved = False
                continue
            if recovered_proof.proof_artifact_sha256 != disposition.recovered_proof_sha256:
                issues.append(f"R0.6: proof receipt digest mismatch for {attempt.attempt_id}")
            if (
                not recovered_proof.inclusion_valid
                or not recovered_proof.independent_execution_context
            ):
                issues.append(
                    f"R0.6: recovered commit did not verify independently for "
                    f"{attempt.attempt_id}"
                )
            if verifier_host is None or recovered_proof.verifier_host_id != verifier_host:
                issues.append(f"R0.6: verifier host mismatch for {attempt.attempt_id}")
            if (
                recovered_proof.proof_artifact_sha256 == disposition.recovered_proof_sha256
                and recovered_proof.inclusion_valid
                and recovered_proof.independent_execution_context
                and recovered_proof.verifier_host_id == verifier_host
            ):
                independently_verified_commit_count += 1

    unknown_proofs = sorted(set(proof_by_attempt) - set(attempts_by_id))
    if unknown_proofs:
        issues.append(f"R0.6: proof receipts reference unknown attempts: {unknown_proofs}")

    attempt_classification_complete = (
        not missing_dispositions
        and not unknown_dispositions
        and len(dispositions_by_id) == len(attempts_by_id)
    )

    canary_valid = True
    if canary.recovery_snapshot_id != recovery.snapshot_id:
        issues.append("R0.6: recovery canary references another recovery snapshot")
        canary_valid = False
    if canary.captured_at < recovery.recovered_at:
        issues.append("R0.6: recovery canary predates recovery snapshot")
        canary_valid = False
    if not canary.inclusion_valid or not canary.independent_execution_context:
        issues.append("R0.6: post-recovery canary did not verify independently")
        canary_valid = False
    if verifier_host is None or canary.verifier_host_id != verifier_host:
        issues.append("R0.6: recovery canary verifier host does not match bench binding")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase4_evaluation_id": phase4.evaluation_id,
        "window_id": window.window_id,
        "power_observation_id": power.observation_id,
        "recovery_snapshot_id": recovery.snapshot_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        acknowledged_commits_preserved
        and attempt_classification_complete
        and no_duplicate_authoritative_commits
        and identity_preserved
        and canary_valid
        and not issues
    )
    return EdgeR0Phase5Evaluation(
        evaluation_id=f"edge-r0-phase5-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase4_evaluation_id=phase4.evaluation_id,
        window_id=window.window_id,
        power_observation_id=power.observation_id,
        recovery_snapshot_id=recovery.snapshot_id,
        evaluated_at=evaluated_at,
        attempted_count=len(window.attempts),
        pre_cut_committed_count=pre_cut_committed,
        recovered_commit_count=recovered_commit_count,
        independently_verified_commit_count=independently_verified_commit_count,
        acknowledged_commits_preserved=acknowledged_commits_preserved,
        attempt_classification_complete=attempt_classification_complete,
        no_duplicate_authoritative_commits=no_duplicate_authoritative_commits,
        identity_preserved=identity_preserved,
        post_recovery_canary_valid=canary_valid,
        r0_6_passed=passed,
        issues=tuple(issues),
    )


def _require_timezone(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone offset")
    return value.astimezone(UTC)


def _validate_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized[7:]
    if re.fullmatch(_SHA256_RE, normalized) is None:
        raise ValueError("expected a 64-character SHA-256 hex digest")
    return normalized


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
        description="ETS Wave 1 Edge Compact R0 R0.6 active-capture power-loss evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser("evaluate-r0-6")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase4-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--window", type=Path, required=True)
    evaluate_parser.add_argument("--power-observation", type=Path, required=True)
    evaluate_parser.add_argument("--recovery", type=Path, required=True)
    evaluate_parser.add_argument("--attempt-recovery", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-6":
        result = evaluate_r0_6(
            load_manifest(args.manifest.read_bytes()),
            load_phase4_evaluation(args.phase4_evaluation.read_bytes()),
            load_active_capture_window(args.window.read_bytes()),
            load_power_observation(args.power_observation.read_bytes()),
            load_recovery_snapshot(args.recovery.read_bytes()),
            tuple(
                load_attempt_recovery(path.read_bytes())
                for path in args.attempt_recovery
            ),
            tuple(load_recovered_proof(path.read_bytes()) for path in args.proof_receipt),
            load_recovery_canary(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_6_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
