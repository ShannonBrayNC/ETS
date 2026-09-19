from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from ets.core.canonical_json import canonical_sha256
from ets.qualification.physical_edge import (
    BenchControl,
    BenchControlKind,
    EdgeBuildBinding,
    EdgeCompactR0BenchManifest,
    EdgeR0Dut,
    EdgeR0TrustPosture,
    EdgeRuntimeBinding,
    IndependentObserver,
    IndependentVerifier,
    ManifestState,
    NetworkInterface,
    StorageDevice,
)
from ets.qualification.physical_edge_phase3 import EdgeSyncStatusEvidence
from ets.qualification.physical_edge_phase10 import TimeQuality
from ets.qualification.physical_edge_phase11 import EdgeR0Phase11Evaluation
from ets.qualification.physical_edge_phase12 import (
    EdgeR0FailedUpgradeTarget,
    EdgeR0RecoveryPlan,
    EdgeR0RollbackBaseline,
    EdgeR0RollbackCanary,
    EdgeR0RollbackExecution,
    EdgeR0RollbackPendingRecord,
    EdgeR0RollbackProofReceipt,
    EdgeR0RollbackReconciliation,
    EdgeR0RollbackRecoveredRecord,
    EdgeR0UpgradeFailureObservation,
    MigrationFailureState,
    RecoveryMode,
    RollbackProofSubject,
    UpgradeFailureStage,
    build_rollback_reconciliation_commitment,
    evaluate_r0_13,
)

_NOW = datetime(2026, 9, 19, 17, 0, tzinfo=UTC)
_SOURCE_BUILD = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_FAILED_BUILD = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _controls() -> tuple[BenchControl, ...]:
    return tuple(
        BenchControl(
            kind=kind,
            control_id=f"r0-{kind.value}-control",
            method=f"isolated {kind.value} qualification control",
            independent_observation_method=f"external {kind.value} observer receipt",
            destructive_or_disruptive=True,
            operator_approval_required=True,
            bootstrap_cli_executes_action=False,
        )
        for kind in BenchControlKind
    )


def _manifest() -> EdgeCompactR0BenchManifest:
    return EdgeCompactR0BenchManifest(
        schema_version="ets.edge-compact-r0-bench-manifest.v1",
        manifest_id="edge-r0-lab-001",
        qualification_class="EDGE_COMPACT_R0",
        manifest_state=ManifestState.READY_FOR_QUALIFICATION,
        collected_at=_NOW,
        dut=EdgeR0Dut(
            manufacturer="Example Manufacturer",
            model="Example Mini PC",
            hardware_revision="rev-a",
            asset_id="EDGE-R0-001",
            cpu_architecture="x86_64",
            cpu_model="Example x86-64 CPU",
            memory_bytes=16 * 1024**3,
            storage=(
                StorageDevice(
                    name="nvme0n1",
                    vendor="Example Storage Vendor",
                    model="Example NVMe",
                    serial="TEST-SERIAL",
                    firmware="1.0",
                    size_bytes=512 * 1024**3,
                    transport="nvme",
                ),
            ),
            network=(
                NetworkInterface(
                    name="enp1s0",
                    mac_address="02:00:00:00:00:01",
                    driver="example_nic",
                    firmware="2.0",
                ),
            ),
            firmware={"bios_vendor": "Example", "bios_version": "1.2.3"},
            claim_critical_fields_confirmed_by_operator=True,
        ),
        runtime=EdgeRuntimeBinding(
            os_id="ubuntu",
            os_version_id="24.04",
            os_pretty_name="Ubuntu 24.04 LTS",
            kernel_release="6.8.0-test",
            python_version="3.12.10",
            hostname="edge-r0-001",
        ),
        build=EdgeBuildBinding(
            source_revision=_SOURCE_BUILD,
            artifact_digest=_sha("rollback-source-artifact"),
            configuration_digest=_sha("rollback-source-config"),
        ),
        trust=EdgeR0TrustPosture(),
        observer=IndependentObserver(
            observer_id="observer-lab-a",
            observer_host_id="bench-controller-001",
            observation_method="controller journal plus independent receipts",
            independent_from_dut=True,
        ),
        verifier=IndependentVerifier(
            verifier_host_id="bench-controller-001",
            verifier_identity="hqp2-clean-verifier",
            command="python -m ets.hqp_verify",
            independent_from_dut=True,
        ),
        controls=_controls(),
        notes=("Synthetic W1-13 unit-test manifest.",),
    )


def _queue(
    *,
    depth: int,
    bytes_used: int,
    pending: int,
    synchronized: int = 70,
) -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=depth,
        queue_bytes=bytes_used,
        pending=pending,
        in_flight=0,
        retryable_failure=0,
        terminal_failure=0,
        synchronized=synchronized,
        max_items=10,
        max_bytes=10_000,
        oldest_pending_age_seconds=None if pending == 0 else 1.0,
        last_successful_sync=_NOW.isoformat(),
        last_failure=None,
        upstream_status="online",
    )


def _phase11(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase11Evaluation:
    return EdgeR0Phase11Evaluation(
        evaluation_id="edge-r0-phase11-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase10_evaluation_id="edge-r0-phase10-passed",
        baseline_id="upgrade-baseline-001",
        package_id="upgrade-package-001",
        execution_id="upgrade-execution-001",
        reconciliation_id="upgrade-reconciliation-001",
        evaluated_at=_NOW,
        package_provenance_valid=True,
        target_build_installed=True,
        identity_continuity_preserved=True,
        trust_posture_preserved=True,
        historical_evidence_preserved=True,
        pending_state_reconciled=True,
        checkpoints_non_regressing=True,
        prior_phase_boundaries_preserved=True,
        independent_verification_complete=True,
        post_upgrade_canary_valid=True,
        r0_12_passed=True,
        issues=(),
    )


def _artifacts():
    manifest = _manifest()
    phase11 = _phase11(manifest)
    pending = (
        EdgeR0RollbackPendingRecord(
            record_id="rollback-pending-1",
            event_id="rollback-event-1",
            idempotency_key="rollback-idem-1",
            local_proof_sha256=_sha("rollback-local-proof-1"),
            synchronized_before_failure=False,
        ),
        EdgeR0RollbackPendingRecord(
            record_id="rollback-pending-2",
            event_id="rollback-event-2",
            idempotency_key="rollback-idem-2",
            local_proof_sha256=_sha("rollback-local-proof-2"),
            synchronized_before_failure=False,
        ),
    )
    baseline = EdgeR0RollbackBaseline(
        baseline_id="rollback-baseline-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase11_evaluation_id=phase11.evaluation_id,
        phase11_evaluation_sha256=canonical_sha256(phase11.model_dump(mode="json")),
        captured_at=_NOW + timedelta(seconds=1),
        source_build_sha=_SOURCE_BUILD,
        source_artifact_digest=_sha("rollback-source-artifact"),
        source_configuration_digest=_sha("rollback-source-config"),
        source_version="0.13.0-r0",
        source_data_schema_version="13",
        device_identity_id="edge-r0-device-identity",
        signing_key_id="edge-r0-software-key",
        local_checkpoint_index=700,
        local_checkpoint_sha256=_sha("rollback-local-pre"),
        upstream_checkpoint_index=350,
        upstream_checkpoint_sha256=_sha("rollback-upstream-pre"),
        log_head_sha256=_sha("rollback-log-head-pre"),
        historical_record_commitment_sha256=_sha("rollback-history"),
        queue_state=_queue(depth=2, bytes_used=200, pending=2),
        storage_used_bytes=40_000,
        storage_high_watermark_used_bytes=70_000,
        pending_records=pending,
        representative_proof_sha256=(_sha("rollback-pre-proof"),),
        observer_receipt_sha256=_sha("rollback-baseline-observer"),
    )
    target = EdgeR0FailedUpgradeTarget(
        target_id="failed-target-001",
        baseline_id=baseline.baseline_id,
        prepared_at=_NOW + timedelta(seconds=2),
        attempted_build_sha=_FAILED_BUILD,
        attempted_artifact_digest=_sha("failed-target-artifact"),
        attempted_configuration_digest=_sha("failed-target-config"),
        attempted_version="0.14.0-failed",
        attempted_data_schema_version="14",
        package_digest=_sha("failed-target-package"),
        migration_plan_sha256=_sha("failed-target-migration"),
        expected_failure_stage=UpgradeFailureStage.MIGRATION,
        independent_package_verification_sha256=_sha("failed-target-verification"),
    )
    recovery_plan = EdgeR0RecoveryPlan(
        recovery_plan_id="recovery-plan-001",
        baseline_id=baseline.baseline_id,
        target_id=target.target_id,
        prepared_at=_NOW + timedelta(seconds=2, milliseconds=100),
        recovery_mode=RecoveryMode.ROLLBACK_SOURCE,
        recovery_build_sha=baseline.source_build_sha,
        recovery_artifact_digest=baseline.source_artifact_digest,
        recovery_configuration_digest=baseline.source_configuration_digest,
        recovery_version=baseline.source_version,
        recovery_data_schema_version=baseline.source_data_schema_version,
        recovery_package_digest=_sha("source-recovery-package"),
        recovery_plan_sha256=_sha("source-recovery-plan"),
        verification_receipt_sha256=_sha("source-recovery-verification"),
    )
    failure = EdgeR0UpgradeFailureObservation(
        failure_id="upgrade-failure-001",
        baseline_id=baseline.baseline_id,
        target_id=target.target_id,
        started_at=_NOW + timedelta(seconds=3),
        failed_at=_NOW + timedelta(seconds=8),
        observed_failure_stage=UpgradeFailureStage.MIGRATION,
        process_exit_code=42,
        migration_state=MigrationFailureState.PARTIAL,
        target_success_claimed=False,
        service_healthy_at_failure=False,
        observed_build_sha=_FAILED_BUILD,
        observed_data_schema_version="14-partial",
        installer_receipt_sha256=_sha("failed-installer-receipt"),
        controller_failure_receipt_sha256=_sha("failure-controller"),
        independent_failure_observation_sha256=_sha("failure-observer"),
    )
    rollback = EdgeR0RollbackExecution(
        rollback_id="rollback-execution-001",
        baseline_id=baseline.baseline_id,
        failure_id=failure.failure_id,
        recovery_plan_id=recovery_plan.recovery_plan_id,
        started_at=failure.failed_at + timedelta(seconds=1),
        completed_at=failure.failed_at + timedelta(seconds=10),
        rollback_receipt_sha256=_sha("rollback-receipt"),
        migration_recovery_success=True,
        migration_recovery_receipt_sha256=_sha("migration-recovery"),
        final_service_healthy=True,
        final_build_independently_identified=True,
        mixed_version_inventory_detected=False,
        final_build_sha=recovery_plan.recovery_build_sha,
        final_artifact_digest=recovery_plan.recovery_artifact_digest,
        final_configuration_digest=recovery_plan.recovery_configuration_digest,
        final_version=recovery_plan.recovery_version,
        final_data_schema_version=recovery_plan.recovery_data_schema_version,
        device_identity_id=baseline.device_identity_id,
        signing_key_id=baseline.signing_key_id,
        preserved_historical_record_commitment_sha256=(
            baseline.historical_record_commitment_sha256
        ),
        pre_failure_log_head_observed=True,
        pre_failure_log_head_sha256=baseline.log_head_sha256,
        local_checkpoint_index=702,
        local_checkpoint_sha256=_sha("rollback-local-post"),
        upstream_checkpoint_index=352,
        upstream_checkpoint_sha256=_sha("rollback-upstream-post"),
        final_queue_state=_queue(depth=0, bytes_used=0, pending=0, synchronized=72),
        storage_used_bytes=40_500,
        network_connected=True,
        time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
        final_boot_id="boot-after-rollback",
        observer_receipt_sha256=_sha("rollback-observer"),
    )
    recovered = tuple(
        EdgeR0RollbackRecoveredRecord(
            record_id=record.record_id,
            event_id=record.event_id,
            idempotency_key=record.idempotency_key,
            authoritative_local_present=True,
            final_upstream_commit_count=1,
            final_upstream_event_id=record.event_id,
            final_upstream_acceptance_sha256=_sha(
                f"rollback-final-accept-{record.record_id}"
            ),
            final_proof_sha256=_sha(f"rollback-final-proof-{record.record_id}"),
            local_marked_synchronized=True,
            false_sync_ack_observed_during_failure=False,
            recovery_observation_sha256=_sha(f"rollback-recover-{record.record_id}"),
        )
        for record in pending
    )
    reconciliation = EdgeR0RollbackReconciliation(
        reconciliation_id="rollback-reconciliation-001",
        rollback_id=rollback.rollback_id,
        reconciled_at=rollback.completed_at + timedelta(seconds=1),
        records=recovered,
        reconciliation_commitment_sha256=build_rollback_reconciliation_commitment(
            recovered
        ),
    )
    proofs = [
        EdgeR0RollbackProofReceipt(
            receipt_id="rollback-pre-proof-receipt",
            subject_kind=RollbackProofSubject.PRE_FAILURE,
            subject_id=_sha("rollback-pre-proof"),
            proof_artifact_sha256=_sha("rollback-pre-proof"),
            verified_at=reconciliation.reconciled_at + timedelta(seconds=1),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("rollback-pre-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        )
    ]
    for index, record in enumerate(recovered, start=1):
        proofs.append(
            EdgeR0RollbackProofReceipt(
                receipt_id=f"rollback-pending-proof-{index}",
                subject_kind=RollbackProofSubject.PENDING_RECORD,
                subject_id=record.record_id,
                proof_artifact_sha256=record.final_proof_sha256 or _sha("missing"),
                verified_at=reconciliation.reconciled_at
                + timedelta(seconds=index + 1),
                verifier_id="ets-verify-offline",
                verifier_host_id="bench-controller-001",
                verifier_build_sha256=_sha("verifier-build"),
                verification_result_sha256=_sha(f"rollback-pending-result-{index}"),
                inclusion_valid=True,
                independent_execution_context=True,
            )
        )
    canary_payload = _sha("rollback-canary-payload")
    canary = EdgeR0RollbackCanary(
        canary_id="rollback-canary-001",
        rollback_id=rollback.rollback_id,
        captured_at=rollback.completed_at + timedelta(minutes=1),
        recovery_build_sha=recovery_plan.recovery_build_sha,
        recovery_configuration_digest=recovery_plan.recovery_configuration_digest,
        request_payload_sha256=canary_payload,
        content_hash=canary_payload,
        event_id="rollback-canary-event",
        proof_artifact_sha256=_sha("rollback-canary-proof"),
        verified_at=rollback.completed_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("rollback-canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return (
        manifest,
        phase11,
        baseline,
        target,
        recovery_plan,
        failure,
        rollback,
        reconciliation,
        tuple(proofs),
        canary,
    )


def test_r0_13_passes_failed_upgrade_and_source_rollback() -> None:
    artifacts = _artifacts()

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is True
    assert result.issues == ()


def test_r0_13_fails_false_target_success_claim() -> None:
    artifacts = list(_artifacts())
    artifacts[5] = artifacts[5].model_copy(update={"target_success_claimed": True})

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is False
    assert result.no_false_target_success is False
    assert any("falsely claimed successful" in issue for issue in result.issues)


def test_r0_13_fails_wrong_recovery_build() -> None:
    artifacts = list(_artifacts())
    artifacts[6] = artifacts[6].model_copy(update={"final_build_sha": "c" * 40})

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is False
    assert result.recovery_build_valid is False
    assert any("final recovery build mismatch" in issue for issue in result.issues)


def test_r0_13_fails_identity_drift() -> None:
    artifacts = list(_artifacts())
    artifacts[6] = artifacts[6].model_copy(
        update={"signing_key_id": "unexpected-rollback-key"}
    )

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is False
    assert result.identity_continuity_preserved is False
    assert any("signing key changed unexpectedly" in issue for issue in result.issues)


def test_r0_13_fails_historical_evidence_rewrite() -> None:
    artifacts = list(_artifacts())
    artifacts[6] = artifacts[6].model_copy(
        update={
            "preserved_historical_record_commitment_sha256": _sha("rewritten-history")
        }
    )

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is False
    assert result.historical_evidence_preserved is False
    assert any("historical record commitment changed" in issue for issue in result.issues)


def test_r0_13_fails_checkpoint_regression() -> None:
    artifacts = list(_artifacts())
    artifacts[6] = artifacts[6].model_copy(update={"local_checkpoint_index": 699})

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is False
    assert result.checkpoints_non_regressing is False
    assert any("local checkpoint regressed" in issue for issue in result.issues)


def test_r0_13_fails_mixed_version_inventory() -> None:
    artifacts = list(_artifacts())
    artifacts[6] = artifacts[6].model_copy(
        update={"mixed_version_inventory_detected": True}
    )

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is False
    assert result.no_ambiguous_half_upgrade is False
    assert any("mixed-version inventory remains" in issue for issue in result.issues)


def test_r0_13_fails_pending_record_duplication() -> None:
    artifacts = list(_artifacts())
    rec = artifacts[7]
    duplicate = rec.records[0].model_copy(update={"final_upstream_commit_count": 2})
    records = (duplicate, rec.records[1])
    artifacts[7] = rec.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": (
                build_rollback_reconciliation_commitment(records)
            ),
        }
    )

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is False
    assert result.pending_state_reconciled is False
    assert any("expected one final logical upstream commit" in issue for issue in result.issues)


def test_r0_13_fails_unresolved_final_queue() -> None:
    artifacts = list(_artifacts())
    dirty = _queue(depth=1, bytes_used=100, pending=1, synchronized=71)
    artifacts[6] = artifacts[6].model_copy(update={"final_queue_state": dirty})

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is False
    assert result.prior_phase_boundaries_preserved is False
    assert any("final queue did not reconcile cleanly" in issue for issue in result.issues)


def test_r0_13_fails_canary_on_wrong_recovered_build() -> None:
    artifacts = list(_artifacts())
    artifacts[9] = artifacts[9].model_copy(update={"recovery_build_sha": "d" * 40})

    result = evaluate_r0_13(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_13_passed is False
    assert result.post_recovery_canary_valid is False
    assert any("canary is not bound to recovered build" in issue for issue in result.issues)
