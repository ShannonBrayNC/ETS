"""Wave 1 Edge Compact R0 valid software-upgrade evidence.

R0.12 evaluates one approved source-to-target upgrade while preserving identity,
historical evidence, pending synchronization state and prior qualification boundaries.
The evaluator never installs software.
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
from ets.qualification.physical_edge_phase10 import (
    EdgeR0Phase10Evaluation,
    TimeQuality,
)

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE11_CLAIM_BOUNDARY: Literal[
    "r0_12_phase_evidence_not_a_physical_qualification_result"
] = "r0_12_phase_evidence_not_a_physical_qualification_result"
_PHASE11_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class StrictPhase11Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class UpgradeProofSubject(StrEnum):
    PRE_UPGRADE = "pre_upgrade"
    PENDING_RECORD = "pending_record"


class EdgeR0PendingUpgradeRecord(StrictPhase11Model):
    schema_version: Literal["ets.edge-compact-r0-upgrade-pending-record.v1"] = (
        "ets.edge-compact-r0-upgrade-pending-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    local_proof_sha256: str = Field(pattern=_SHA256_RE)
    local_authoritative: Literal[True] = True
    synchronized_before_upgrade: bool
    upstream_acceptance_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_12_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE11_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_sync_state(self) -> EdgeR0PendingUpgradeRecord:
        if self.synchronized_before_upgrade:
            if self.upstream_acceptance_sha256 is None:
                raise ValueError("synchronized record requires upstream acceptance")
        elif self.upstream_acceptance_sha256 is not None:
            raise ValueError("pending record cannot carry upstream acceptance")
        return self


class EdgeR0UpgradeBaseline(StrictPhase11Model):
    schema_version: Literal["ets.edge-compact-r0-upgrade-baseline.v1"] = (
        "ets.edge-compact-r0-upgrade-baseline.v1"
    )
    baseline_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase10_evaluation_id: str = Field(min_length=1, max_length=256)
    phase10_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    captured_at: datetime
    source_build_sha: str = Field(min_length=7, max_length=128)
    source_artifact_digest: str = Field(pattern=_SHA256_RE)
    source_configuration_digest: str = Field(pattern=_SHA256_RE)
    source_version: str = Field(min_length=1, max_length=128)
    device_identity_id: str = Field(min_length=1, max_length=256)
    signing_key_id: str = Field(min_length=1, max_length=256)
    hardware_attested: Literal[False] = False
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    log_head_sha256: str = Field(pattern=_SHA256_RE)
    historical_record_commitment_sha256: str = Field(pattern=_SHA256_RE)
    data_schema_version: str = Field(min_length=1, max_length=128)
    queue_state: EdgeSyncStatusEvidence
    storage_used_bytes: int = Field(ge=0)
    storage_high_watermark_used_bytes: int = Field(gt=0)
    network_connected: Literal[True] = True
    time_quality: Literal[TimeQuality.TRUSTED_SYNCHRONIZED] = (
        TimeQuality.TRUSTED_SYNCHRONIZED
    )
    pending_variant_required: Literal[True] = True
    pending_records: tuple[EdgeR0PendingUpgradeRecord, ...] = Field(min_length=1)
    representative_proof_sha256: tuple[str, ...] = Field(min_length=1)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_12_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE11_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "upgrade-baseline timestamp")

    @model_validator(mode="after")
    def validate_baseline(self) -> EdgeR0UpgradeBaseline:
        if self.storage_used_bytes >= self.storage_high_watermark_used_bytes:
            raise ValueError("R0.12 baseline exceeds the R0.8 storage boundary")
        ids = [record.record_id for record in self.pending_records]
        event_ids = [record.event_id for record in self.pending_records]
        idempotency = [record.idempotency_key for record in self.pending_records]
        if len(ids) != len(set(ids)):
            raise ValueError("pending record IDs must be unique")
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("pending event IDs must be unique")
        if len(idempotency) != len(set(idempotency)):
            raise ValueError("pending idempotency keys must be unique")
        pending_count = sum(
            not record.synchronized_before_upgrade for record in self.pending_records
        )
        if self.queue_state.pending < pending_count:
            raise ValueError("queue pending count cannot understate pending records")
        if len(self.representative_proof_sha256) != len(
            set(self.representative_proof_sha256)
        ):
            raise ValueError("representative proof digests must be unique")
        return self


class EdgeR0UpgradePackage(StrictPhase11Model):
    schema_version: Literal["ets.edge-compact-r0-upgrade-package.v1"] = (
        "ets.edge-compact-r0-upgrade-package.v1"
    )
    package_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    prepared_at: datetime
    source_build_sha: str = Field(min_length=7, max_length=128)
    target_build_sha: str = Field(min_length=7, max_length=128)
    target_artifact_digest: str = Field(pattern=_SHA256_RE)
    target_configuration_digest: str = Field(pattern=_SHA256_RE)
    package_digest: str = Field(pattern=_SHA256_RE)
    target_version: str = Field(min_length=1, max_length=128)
    target_data_schema_version: str = Field(min_length=1, max_length=128)
    migration_plan_sha256: str = Field(pattern=_SHA256_RE)
    installer_definition_sha256: str = Field(pattern=_SHA256_RE)
    signature_verified: Literal[True] = True
    operator_approved: Literal[True] = True
    independent_verification_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_12_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE11_CLAIM_BOUNDARY

    @field_validator("prepared_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "upgrade-package timestamp")

    @model_validator(mode="after")
    def validate_target(self) -> EdgeR0UpgradePackage:
        if self.source_build_sha == self.target_build_sha:
            raise ValueError("valid-upgrade target build must differ from source")
        return self


class EdgeR0UpgradeExecution(StrictPhase11Model):
    schema_version: Literal["ets.edge-compact-r0-upgrade-execution.v1"] = (
        "ets.edge-compact-r0-upgrade-execution.v1"
    )
    execution_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    package_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    pre_boot_id: str = Field(min_length=1, max_length=128)
    post_boot_id: str = Field(min_length=1, max_length=128)
    reboot_required: bool
    installer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    service_restart_receipt_sha256: str = Field(pattern=_SHA256_RE)
    migration_success: bool
    migration_result_sha256: str = Field(pattern=_SHA256_RE)
    service_healthy: bool
    installed_build_sha: str = Field(min_length=7, max_length=128)
    installed_artifact_digest: str = Field(pattern=_SHA256_RE)
    installed_configuration_digest: str = Field(pattern=_SHA256_RE)
    installed_version: str = Field(min_length=1, max_length=128)
    installed_data_schema_version: str = Field(min_length=1, max_length=128)
    device_identity_id: str = Field(min_length=1, max_length=256)
    signing_key_id: str = Field(min_length=1, max_length=256)
    hardware_attested: Literal[False] = False
    preserved_historical_record_commitment_sha256: str = Field(pattern=_SHA256_RE)
    pre_upgrade_log_head_observed: bool
    pre_upgrade_log_head_sha256: str = Field(pattern=_SHA256_RE)
    local_checkpoint_index: int = Field(ge=0)
    local_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    upstream_checkpoint_index: int = Field(ge=0)
    upstream_checkpoint_sha256: str = Field(pattern=_SHA256_RE)
    final_queue_state: EdgeSyncStatusEvidence
    storage_used_bytes: int = Field(ge=0)
    network_connected: bool
    time_quality: TimeQuality
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_12_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE11_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "upgrade-execution timestamp")

    @model_validator(mode="after")
    def validate_execution(self) -> EdgeR0UpgradeExecution:
        if self.completed_at <= self.started_at:
            raise ValueError("upgrade execution must have positive duration")
        if self.reboot_required and self.pre_boot_id == self.post_boot_id:
            raise ValueError("required reboot must produce a new boot ID")
        return self


class EdgeR0UpgradeRecoveredRecord(StrictPhase11Model):
    schema_version: Literal["ets.edge-compact-r0-upgrade-recovered-record.v1"] = (
        "ets.edge-compact-r0-upgrade-recovered-record.v1"
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
        "r0_12_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE11_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def validate_commit_shape(self) -> EdgeR0UpgradeRecoveredRecord:
        fields = (
            self.final_upstream_event_id,
            self.final_upstream_acceptance_sha256,
            self.final_proof_sha256,
        )
        if self.final_upstream_commit_count > 0:
            if any(value is None for value in fields):
                raise ValueError("recovered upgrade commit requires event/acceptance/proof")
        elif any(value is not None for value in fields):
            raise ValueError("zero recovered commits cannot carry final commit fields")
        if self.local_marked_synchronized and self.final_upstream_commit_count != 1:
            raise ValueError("local synchronized state requires one upstream commit")
        return self


class EdgeR0UpgradeReconciliation(StrictPhase11Model):
    schema_version: Literal["ets.edge-compact-r0-upgrade-reconciliation.v1"] = (
        "ets.edge-compact-r0-upgrade-reconciliation.v1"
    )
    reconciliation_id: str = Field(min_length=1, max_length=256)
    execution_id: str = Field(min_length=1, max_length=256)
    reconciled_at: datetime
    records: tuple[EdgeR0UpgradeRecoveredRecord, ...] = Field(min_length=1)
    reconciliation_commitment_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "r0_12_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE11_CLAIM_BOUNDARY

    @field_validator("reconciled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "upgrade-reconciliation timestamp")

    @model_validator(mode="after")
    def validate_records(self) -> EdgeR0UpgradeReconciliation:
        ids = [record.record_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("upgrade recovery record IDs must be unique")
        return self


class EdgeR0UpgradeProofReceipt(StrictPhase11Model):
    schema_version: Literal["ets.edge-compact-r0-upgrade-proof-receipt.v1"] = (
        "ets.edge-compact-r0-upgrade-proof-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    subject_kind: UpgradeProofSubject
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
        "r0_12_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE11_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "upgrade-proof timestamp")


class EdgeR0UpgradeCanary(StrictPhase11Model):
    schema_version: Literal["ets.edge-compact-r0-upgrade-canary.v1"] = (
        "ets.edge-compact-r0-upgrade-canary.v1"
    )
    canary_id: str = Field(min_length=1, max_length=256)
    execution_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    target_build_sha: str = Field(min_length=7, max_length=128)
    target_configuration_digest: str = Field(pattern=_SHA256_RE)
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
        "r0_12_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE11_CLAIM_BOUNDARY

    @field_validator("captured_at", "verified_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.12 canary timestamp")

    @model_validator(mode="after")
    def validate_canary(self) -> EdgeR0UpgradeCanary:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("upgrade canary request SHA-256 must match content_hash")
        if self.verified_at < self.captured_at:
            raise ValueError("upgrade canary verification cannot precede capture")
        return self


class EdgeR0Phase11Evaluation(StrictPhase11Model):
    schema_version: Literal["ets.edge-compact-r0-phase11-evaluation.v1"] = (
        "ets.edge-compact-r0-phase11-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase10_evaluation_id: str = Field(min_length=1, max_length=256)
    baseline_id: str = Field(min_length=1, max_length=256)
    package_id: str = Field(min_length=1, max_length=256)
    execution_id: str = Field(min_length=1, max_length=256)
    reconciliation_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    package_provenance_valid: bool
    target_build_installed: bool
    identity_continuity_preserved: bool
    trust_posture_preserved: bool
    historical_evidence_preserved: bool
    pending_state_reconciled: bool
    checkpoints_non_regressing: bool
    prior_phase_boundaries_preserved: bool
    independent_verification_complete: bool
    post_upgrade_canary_valid: bool
    r0_12_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE11_DISPOSITION
    claim_boundary: Literal[
        "r0_12_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE11_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value, "R0.12 evaluation timestamp")

    @model_validator(mode="after")
    def enforce_result(self) -> EdgeR0Phase11Evaluation:
        expected = (
            self.package_provenance_valid
            and self.target_build_installed
            and self.identity_continuity_preserved
            and self.trust_posture_preserved
            and self.historical_evidence_preserved
            and self.pending_state_reconciled
            and self.checkpoints_non_regressing
            and self.prior_phase_boundaries_preserved
            and self.independent_verification_complete
            and self.post_upgrade_canary_valid
            and not self.issues
        )
        if self.r0_12_passed != expected:
            raise ValueError("r0_12_passed must match component results and issues")
        return self


def build_upgrade_reconciliation_commitment(
    records: tuple[EdgeR0UpgradeRecoveredRecord, ...],
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
        }
        for record in sorted(records, key=lambda item: item.record_id)
    ]
    return canonical_sha256(value)


def evaluate_r0_12(
    manifest: EdgeCompactR0BenchManifest,
    phase10: EdgeR0Phase10Evaluation,
    baseline: EdgeR0UpgradeBaseline,
    package: EdgeR0UpgradePackage,
    execution: EdgeR0UpgradeExecution,
    reconciliation: EdgeR0UpgradeReconciliation,
    proofs: tuple[EdgeR0UpgradeProofReceipt, ...],
    canary: EdgeR0UpgradeCanary,
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase11Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.12: bench manifest not ready: {blocker}")
    if not phase10.r0_11_passed:
        issues.append("R0.12: R0.11 did not pass")
    if phase10.manifest_id != manifest.manifest_id or phase10.asset_id != asset_id:
        issues.append("R0.12: R0.11 evaluation is bound to another DUT")

    if baseline.manifest_id != manifest.manifest_id or baseline.asset_id != asset_id:
        issues.append("R0.12: baseline is bound to another DUT")
    if baseline.phase10_evaluation_id != phase10.evaluation_id:
        issues.append("R0.12: baseline references another R0.11 evaluation")
    if baseline.phase10_evaluation_sha256 != canonical_sha256(
        phase10.model_dump(mode="json")
    ):
        issues.append("R0.12: R0.11 digest binding mismatch")

    package_provenance_valid = True
    if baseline.source_build_sha != manifest.build.source_revision:
        issues.append("R0.12: baseline source build does not match W1-1 manifest")
        package_provenance_valid = False
    if baseline.source_artifact_digest != manifest.build.artifact_digest:
        issues.append("R0.12: baseline source artifact digest mismatch")
        package_provenance_valid = False
    if baseline.source_configuration_digest != manifest.build.configuration_digest:
        issues.append("R0.12: baseline source configuration digest mismatch")
        package_provenance_valid = False
    if package.baseline_id != baseline.baseline_id:
        issues.append("R0.12: upgrade package references another baseline")
        package_provenance_valid = False
    if package.source_build_sha != baseline.source_build_sha:
        issues.append("R0.12: package source build does not match baseline")
        package_provenance_valid = False

    target_build_installed = True
    if execution.baseline_id != baseline.baseline_id:
        issues.append("R0.12: execution references another baseline")
        target_build_installed = False
    if execution.package_id != package.package_id:
        issues.append("R0.12: execution references another upgrade package")
        target_build_installed = False
    if execution.started_at < package.prepared_at:
        issues.append("R0.12: upgrade execution predates package preparation")
        target_build_installed = False
    target_fields = (
        (execution.installed_build_sha, package.target_build_sha, "build"),
        (
            execution.installed_artifact_digest,
            package.target_artifact_digest,
            "artifact digest",
        ),
        (
            execution.installed_configuration_digest,
            package.target_configuration_digest,
            "configuration digest",
        ),
        (execution.installed_version, package.target_version, "version"),
        (
            execution.installed_data_schema_version,
            package.target_data_schema_version,
            "data schema version",
        ),
    )
    for installed, expected, label in target_fields:
        if installed != expected:
            issues.append(f"R0.12: installed target {label} mismatch")
            target_build_installed = False
    if not execution.migration_success:
        issues.append("R0.12: declared migration did not succeed")
        target_build_installed = False
    if not execution.service_healthy:
        issues.append("R0.12: target service is not healthy")
        target_build_installed = False

    identity_continuity_preserved = (
        execution.device_identity_id == baseline.device_identity_id
        and execution.signing_key_id == baseline.signing_key_id
    )
    if execution.device_identity_id != baseline.device_identity_id:
        issues.append("R0.12: device identity changed unexpectedly")
    if execution.signing_key_id != baseline.signing_key_id:
        issues.append("R0.12: signing key changed unexpectedly")

    trust_posture_preserved = (
        baseline.hardware_attested is False and execution.hardware_attested is False
    )
    if not trust_posture_preserved:
        issues.append("R0.12: R0 trust posture changed unexpectedly")

    historical_evidence_preserved = True
    if (
        execution.preserved_historical_record_commitment_sha256
        != baseline.historical_record_commitment_sha256
    ):
        issues.append("R0.12: historical record commitment changed during upgrade")
        historical_evidence_preserved = False
    if not execution.pre_upgrade_log_head_observed:
        issues.append("R0.12: pre-upgrade log head was not observed after upgrade")
        historical_evidence_preserved = False
    if execution.pre_upgrade_log_head_sha256 != baseline.log_head_sha256:
        issues.append("R0.12: pre-upgrade log-head digest changed")
        historical_evidence_preserved = False

    checkpoints_non_regressing = (
        execution.local_checkpoint_index >= baseline.local_checkpoint_index
        and execution.upstream_checkpoint_index >= baseline.upstream_checkpoint_index
    )
    if execution.local_checkpoint_index < baseline.local_checkpoint_index:
        issues.append("R0.12: local checkpoint regressed")
    if execution.upstream_checkpoint_index < baseline.upstream_checkpoint_index:
        issues.append("R0.12: upstream checkpoint regressed")

    prior_phase_boundaries_preserved = (
        execution.storage_used_bytes < baseline.storage_high_watermark_used_bytes
        and execution.network_connected
        and execution.time_quality is TimeQuality.TRUSTED_SYNCHRONIZED
    )
    if execution.storage_used_bytes >= baseline.storage_high_watermark_used_bytes:
        issues.append("R0.12: R0.8 storage boundary crossed")
    if not execution.network_connected:
        issues.append("R0.12: R0.10 network boundary crossed")
    if execution.time_quality is not TimeQuality.TRUSTED_SYNCHRONIZED:
        issues.append("R0.12: R0.11 trusted-time boundary not restored")

    final_queue = execution.final_queue_state
    if (
        final_queue.queue_depth != 0
        or final_queue.queue_bytes != 0
        or final_queue.pending != 0
        or final_queue.in_flight != 0
        or final_queue.retryable_failure != 0
        or final_queue.terminal_failure != 0
    ):
        issues.append("R0.12: post-upgrade queue did not reconcile cleanly")
        prior_phase_boundaries_preserved = False

    if reconciliation.execution_id != execution.execution_id:
        issues.append("R0.12: reconciliation references another execution")

    pending_by_id = {record.record_id: record for record in baseline.pending_records}
    recovered_by_id = {record.record_id: record for record in reconciliation.records}
    pending_ids = set(pending_by_id)
    recovered_ids = set(recovered_by_id)
    missing = sorted(pending_ids - recovered_ids)
    unknown = sorted(recovered_ids - pending_ids)
    pending_state_reconciled = not missing and not unknown
    if missing:
        issues.append(f"R0.12: pending records missing after upgrade: {missing}")
    if unknown:
        issues.append(f"R0.12: unknown recovered records after upgrade: {unknown}")

    for record_id in sorted(pending_ids & recovered_ids):
        before = pending_by_id[record_id]
        after = recovered_by_id[record_id]
        if not after.authoritative_local_present:
            issues.append(f"R0.12: authoritative pending record disappeared: {record_id}")
            pending_state_reconciled = False
        if after.event_id != before.event_id:
            issues.append(f"R0.12: pending event ID changed: {record_id}")
            pending_state_reconciled = False
        if after.idempotency_key != before.idempotency_key:
            issues.append(f"R0.12: pending idempotency key changed: {record_id}")
            pending_state_reconciled = False
        if after.final_upstream_commit_count != 1:
            issues.append(
                f"R0.12: expected one final logical upstream commit: {record_id}"
            )
            pending_state_reconciled = False
        if after.final_upstream_event_id != before.event_id:
            issues.append(f"R0.12: final upstream event mismatch: {record_id}")
            pending_state_reconciled = False
        if not after.local_marked_synchronized:
            issues.append(f"R0.12: pending record not locally synchronized: {record_id}")
            pending_state_reconciled = False

    expected_reconciliation = build_upgrade_reconciliation_commitment(
        reconciliation.records
    )
    if reconciliation.reconciliation_commitment_sha256 != expected_reconciliation:
        issues.append("R0.12: upgrade reconciliation commitment mismatch")
        pending_state_reconciled = False

    proof_keys: dict[tuple[UpgradeProofSubject, str], EdgeR0UpgradeProofReceipt] = {}
    for proof_receipt in proofs:
        key = (proof_receipt.subject_kind, proof_receipt.subject_id)
        if key in proof_keys:
            issues.append(
                "R0.12: duplicate proof receipt for "
                f"{proof_receipt.subject_kind.value}:{proof_receipt.subject_id}"
            )
            continue
        proof_keys[key] = proof_receipt

    verifier_host = manifest.verifier.verifier_host_id
    independent_verification_complete = True

    for proof_digest in baseline.representative_proof_sha256:
        pre_receipt = proof_keys.get((UpgradeProofSubject.PRE_UPGRADE, proof_digest))
        if pre_receipt is None:
            issues.append(
                f"R0.12: missing pre-upgrade proof verification: {proof_digest}"
            )
            independent_verification_complete = False
            continue
        if pre_receipt.proof_artifact_sha256 != proof_digest:
            issues.append(
                f"R0.12: pre-upgrade proof digest mismatch: {proof_digest}"
            )
            independent_verification_complete = False
        if (
            not pre_receipt.inclusion_valid
            or not pre_receipt.independent_execution_context
            or verifier_host is None
            or pre_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.12: pre-upgrade proof failed independent verification: {proof_digest}"
            )
            independent_verification_complete = False

    for record_id in sorted(pending_ids):
        recovered = recovered_by_id.get(record_id)
        if recovered is None or recovered.final_upstream_commit_count != 1:
            independent_verification_complete = False
            continue
        record_receipt = proof_keys.get((UpgradeProofSubject.PENDING_RECORD, record_id))
        if record_receipt is None:
            issues.append(f"R0.12: missing pending-record proof receipt: {record_id}")
            independent_verification_complete = False
            continue
        if record_receipt.proof_artifact_sha256 != recovered.final_proof_sha256:
            issues.append(f"R0.12: pending-record proof digest mismatch: {record_id}")
            independent_verification_complete = False
        if (
            not record_receipt.inclusion_valid
            or not record_receipt.independent_execution_context
            or verifier_host is None
            or record_receipt.verifier_host_id != verifier_host
        ):
            issues.append(
                f"R0.12: pending-record proof failed independent verification: {record_id}"
            )
            independent_verification_complete = False

    canary_valid = True
    if canary.execution_id != execution.execution_id:
        issues.append("R0.12: canary references another upgrade execution")
        canary_valid = False
    if canary.captured_at < execution.completed_at:
        issues.append("R0.12: canary predates completed upgrade")
        canary_valid = False
    if canary.target_build_sha != package.target_build_sha:
        issues.append("R0.12: canary is not bound to target build")
        canary_valid = False
    if canary.target_configuration_digest != package.target_configuration_digest:
        issues.append("R0.12: canary is not bound to target configuration")
        canary_valid = False
    if (
        not canary.inclusion_valid
        or not canary.independent_execution_context
        or verifier_host is None
        or canary.verifier_host_id != verifier_host
    ):
        issues.append("R0.12: post-upgrade canary did not independently verify")
        canary_valid = False

    seed = {
        "manifest_id": manifest.manifest_id,
        "phase10_evaluation_id": phase10.evaluation_id,
        "baseline_id": baseline.baseline_id,
        "package_id": package.package_id,
        "execution_id": execution.execution_id,
        "reconciliation_id": reconciliation.reconciliation_id,
        "canary_id": canary.canary_id,
        "evaluated_at": evaluated_at.isoformat(),
        "issues": issues,
    }
    passed = (
        package_provenance_valid
        and target_build_installed
        and identity_continuity_preserved
        and trust_posture_preserved
        and historical_evidence_preserved
        and pending_state_reconciled
        and checkpoints_non_regressing
        and prior_phase_boundaries_preserved
        and independent_verification_complete
        and canary_valid
        and not issues
    )
    return EdgeR0Phase11Evaluation(
        evaluation_id=f"edge-r0-phase11-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase10_evaluation_id=phase10.evaluation_id,
        baseline_id=baseline.baseline_id,
        package_id=package.package_id,
        execution_id=execution.execution_id,
        reconciliation_id=reconciliation.reconciliation_id,
        evaluated_at=evaluated_at,
        package_provenance_valid=package_provenance_valid,
        target_build_installed=target_build_installed,
        identity_continuity_preserved=identity_continuity_preserved,
        trust_posture_preserved=trust_posture_preserved,
        historical_evidence_preserved=historical_evidence_preserved,
        pending_state_reconciled=pending_state_reconciled,
        checkpoints_non_regressing=checkpoints_non_regressing,
        prior_phase_boundaries_preserved=prior_phase_boundaries_preserved,
        independent_verification_complete=independent_verification_complete,
        post_upgrade_canary_valid=canary_valid,
        r0_12_passed=passed,
        issues=tuple(issues),
    )


def load_phase10_evaluation(raw: bytes) -> EdgeR0Phase10Evaluation:
    return EdgeR0Phase10Evaluation.model_validate_json(raw)


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
        description="ETS Wave 1 Edge Compact R0 R0.12 valid-upgrade evaluator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = subparsers.add_parser("evaluate-r0-12")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase10-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--baseline", type=Path, required=True)
    evaluate_parser.add_argument("--package", type=Path, required=True)
    evaluate_parser.add_argument("--execution", type=Path, required=True)
    evaluate_parser.add_argument("--reconciliation", type=Path, required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--canary", type=Path, required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "evaluate-r0-12":
        result = evaluate_r0_12(
            load_manifest(args.manifest.read_bytes()),
            load_phase10_evaluation(args.phase10_evaluation.read_bytes()),
            EdgeR0UpgradeBaseline.model_validate_json(args.baseline.read_bytes()),
            EdgeR0UpgradePackage.model_validate_json(args.package.read_bytes()),
            EdgeR0UpgradeExecution.model_validate_json(args.execution.read_bytes()),
            EdgeR0UpgradeReconciliation.model_validate_json(
                args.reconciliation.read_bytes()
            ),
            tuple(
                EdgeR0UpgradeProofReceipt.model_validate_json(path.read_bytes())
                for path in args.proof_receipt
            ),
            EdgeR0UpgradeCanary.model_validate_json(args.canary.read_bytes()),
            evaluated_at=(
                _parse_datetime(args.evaluated_at)
                if args.evaluated_at is not None
                else datetime.now(UTC)
            ),
        )
        _write_json(args.output, result)
        return 0 if result.r0_12_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
