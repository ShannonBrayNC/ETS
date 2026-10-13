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
from ets.qualification.physical_edge_phase10 import (
    EdgeR0Phase10Evaluation,
    TimeQuality,
)
from ets.qualification.physical_edge_phase11 import (
    EdgeR0PendingUpgradeRecord,
    EdgeR0UpgradeBaseline,
    EdgeR0UpgradeCanary,
    EdgeR0UpgradeExecution,
    EdgeR0UpgradePackage,
    EdgeR0UpgradeProofReceipt,
    EdgeR0UpgradeReconciliation,
    EdgeR0UpgradeRecoveredRecord,
    UpgradeProofSubject,
    build_upgrade_reconciliation_commitment,
    evaluate_r0_12,
)

_NOW = datetime(2026, 9, 19, 16, 0, tzinfo=UTC)
_SOURCE_BUILD = "3827cb69b5974a0498c01434eaac2e742c8b0593"
_TARGET_BUILD = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


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
            artifact_digest=_sha("source-artifact"),
            configuration_digest=_sha("source-config"),
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
        notes=("Synthetic W1-12 unit-test manifest.",),
    )


def _queue(
    *,
    depth: int,
    bytes_used: int,
    pending: int,
    synchronized: int = 60,
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


def _phase10(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase10Evaluation:
    return EdgeR0Phase10Evaluation(
        evaluation_id="edge-r0-phase10-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase9_evaluation_id="edge-r0-phase9-passed",
        baseline_id="clock-baseline-001",
        profile_id="clock-profile-001",
        window_id="clock-window-001",
        restoration_id="clock-restoration-001",
        evaluated_at=_NOW,
        transition_profile_observed=True,
        monotonic_order_preserved=True,
        log_checkpoint_order_preserved=True,
        time_quality_preserved=True,
        wall_clock_offsets_observed=True,
        prior_evidence_not_rewritten=True,
        prior_phase_boundaries_preserved=True,
        independent_verification_complete=True,
        restoration_valid=True,
        post_recovery_canary_valid=True,
        r0_11_passed=True,
        issues=(),
    )


def _artifacts():
    manifest = _manifest()
    phase10 = _phase10(manifest)
    pending = (
        EdgeR0PendingUpgradeRecord(
            record_id="upgrade-pending-1",
            event_id="upgrade-event-1",
            idempotency_key="upgrade-idem-1",
            local_proof_sha256=_sha("upgrade-local-proof-1"),
            synchronized_before_upgrade=False,
        ),
        EdgeR0PendingUpgradeRecord(
            record_id="upgrade-pending-2",
            event_id="upgrade-event-2",
            idempotency_key="upgrade-idem-2",
            local_proof_sha256=_sha("upgrade-local-proof-2"),
            synchronized_before_upgrade=False,
        ),
    )
    baseline = EdgeR0UpgradeBaseline(
        baseline_id="upgrade-baseline-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase10_evaluation_id=phase10.evaluation_id,
        phase10_evaluation_sha256=canonical_sha256(phase10.model_dump(mode="json")),
        captured_at=_NOW + timedelta(seconds=1),
        source_build_sha=_SOURCE_BUILD,
        source_artifact_digest=_sha("source-artifact"),
        source_configuration_digest=_sha("source-config"),
        source_version="0.12.0-r0",
        device_identity_id="edge-r0-device-identity",
        signing_key_id="edge-r0-software-key",
        local_checkpoint_index=600,
        local_checkpoint_sha256=_sha("upgrade-local-pre"),
        upstream_checkpoint_index=300,
        upstream_checkpoint_sha256=_sha("upgrade-upstream-pre"),
        log_head_sha256=_sha("upgrade-log-head-pre"),
        historical_record_commitment_sha256=_sha("historical-record-set"),
        data_schema_version="12",
        queue_state=_queue(depth=2, bytes_used=200, pending=2),
        storage_used_bytes=40_000,
        storage_high_watermark_used_bytes=70_000,
        pending_records=pending,
        representative_proof_sha256=(_sha("upgrade-pre-proof"),),
        observer_receipt_sha256=_sha("upgrade-baseline-observer"),
    )
    package = EdgeR0UpgradePackage(
        package_id="upgrade-package-001",
        baseline_id=baseline.baseline_id,
        prepared_at=_NOW + timedelta(seconds=2),
        source_build_sha=_SOURCE_BUILD,
        target_build_sha=_TARGET_BUILD,
        target_artifact_digest=_sha("target-artifact"),
        target_configuration_digest=_sha("target-config"),
        package_digest=_sha("upgrade-package"),
        target_version="0.13.0-r0",
        target_data_schema_version="13",
        migration_plan_sha256=_sha("migration-plan"),
        installer_definition_sha256=_sha("installer-definition"),
        independent_verification_sha256=_sha("package-verification"),
    )
    execution = EdgeR0UpgradeExecution(
        execution_id="upgrade-execution-001",
        baseline_id=baseline.baseline_id,
        package_id=package.package_id,
        started_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=12),
        pre_boot_id="boot-before-upgrade",
        post_boot_id="boot-after-upgrade",
        reboot_required=True,
        installer_receipt_sha256=_sha("installer-receipt"),
        service_restart_receipt_sha256=_sha("service-restart"),
        migration_success=True,
        migration_result_sha256=_sha("migration-result"),
        service_healthy=True,
        installed_build_sha=_TARGET_BUILD,
        installed_artifact_digest=package.target_artifact_digest,
        installed_configuration_digest=package.target_configuration_digest,
        installed_version=package.target_version,
        installed_data_schema_version=package.target_data_schema_version,
        device_identity_id=baseline.device_identity_id,
        signing_key_id=baseline.signing_key_id,
        preserved_historical_record_commitment_sha256=(
            baseline.historical_record_commitment_sha256
        ),
        pre_upgrade_log_head_observed=True,
        pre_upgrade_log_head_sha256=baseline.log_head_sha256,
        local_checkpoint_index=602,
        local_checkpoint_sha256=_sha("upgrade-local-post"),
        upstream_checkpoint_index=302,
        upstream_checkpoint_sha256=_sha("upgrade-upstream-post"),
        final_queue_state=_queue(depth=0, bytes_used=0, pending=0, synchronized=62),
        storage_used_bytes=40_500,
        network_connected=True,
        time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
        observer_receipt_sha256=_sha("upgrade-execution-observer"),
    )
    recovered = tuple(
        EdgeR0UpgradeRecoveredRecord(
            record_id=record.record_id,
            event_id=record.event_id,
            idempotency_key=record.idempotency_key,
            authoritative_local_present=True,
            final_upstream_commit_count=1,
            final_upstream_event_id=record.event_id,
            final_upstream_acceptance_sha256=_sha(
                f"upgrade-final-accept-{record.record_id}"
            ),
            final_proof_sha256=_sha(f"upgrade-final-proof-{record.record_id}"),
            local_marked_synchronized=True,
            recovery_observation_sha256=_sha(f"upgrade-recover-{record.record_id}"),
        )
        for record in pending
    )
    reconciliation = EdgeR0UpgradeReconciliation(
        reconciliation_id="upgrade-reconciliation-001",
        execution_id=execution.execution_id,
        reconciled_at=execution.completed_at + timedelta(seconds=1),
        records=recovered,
        reconciliation_commitment_sha256=build_upgrade_reconciliation_commitment(
            recovered
        ),
    )
    proofs = [
        EdgeR0UpgradeProofReceipt(
            receipt_id="upgrade-pre-proof-receipt",
            subject_kind=UpgradeProofSubject.PRE_UPGRADE,
            subject_id=_sha("upgrade-pre-proof"),
            proof_artifact_sha256=_sha("upgrade-pre-proof"),
            verified_at=reconciliation.reconciled_at + timedelta(seconds=1),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("upgrade-pre-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        )
    ]
    for index, record in enumerate(recovered, start=1):
        proofs.append(
            EdgeR0UpgradeProofReceipt(
                receipt_id=f"upgrade-pending-proof-{index}",
                subject_kind=UpgradeProofSubject.PENDING_RECORD,
                subject_id=record.record_id,
                proof_artifact_sha256=record.final_proof_sha256 or _sha("missing"),
                verified_at=reconciliation.reconciled_at
                + timedelta(seconds=index + 1),
                verifier_id="ets-verify-offline",
                verifier_host_id="bench-controller-001",
                verifier_build_sha256=_sha("verifier-build"),
                verification_result_sha256=_sha(f"upgrade-pending-result-{index}"),
                inclusion_valid=True,
                independent_execution_context=True,
            )
        )
    canary_payload = _sha("upgrade-canary-payload")
    canary = EdgeR0UpgradeCanary(
        canary_id="upgrade-canary-001",
        execution_id=execution.execution_id,
        captured_at=execution.completed_at + timedelta(minutes=1),
        target_build_sha=package.target_build_sha,
        target_configuration_digest=package.target_configuration_digest,
        request_payload_sha256=canary_payload,
        content_hash=canary_payload,
        event_id="upgrade-canary-event",
        proof_artifact_sha256=_sha("upgrade-canary-proof"),
        verified_at=execution.completed_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("upgrade-canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return (
        manifest,
        phase10,
        baseline,
        package,
        execution,
        reconciliation,
        tuple(proofs),
        canary,
    )


def test_r0_12_passes_valid_upgrade_with_pending_state() -> None:
    artifacts = _artifacts()

    result = evaluate_r0_12(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_12_passed is True
    assert result.issues == ()


def test_r0_12_fails_wrong_installed_target() -> None:
    manifest, phase10, baseline, package, execution, rec, proofs, canary = _artifacts()
    broken = execution.model_copy(update={"installed_build_sha": "b" * 40})

    result = evaluate_r0_12(
        manifest,
        phase10,
        baseline,
        package,
        broken,
        rec,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_12_passed is False
    assert result.target_build_installed is False
    assert any("installed target build mismatch" in issue for issue in result.issues)


def test_r0_12_fails_unexpected_identity_change() -> None:
    manifest, phase10, baseline, package, execution, rec, proofs, canary = _artifacts()
    broken = execution.model_copy(update={"device_identity_id": "new-device-identity"})

    result = evaluate_r0_12(
        manifest,
        phase10,
        baseline,
        package,
        broken,
        rec,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_12_passed is False
    assert result.identity_continuity_preserved is False
    assert any("device identity changed unexpectedly" in issue for issue in result.issues)


def test_r0_12_fails_historical_evidence_rewrite() -> None:
    manifest, phase10, baseline, package, execution, rec, proofs, canary = _artifacts()
    broken = execution.model_copy(
        update={
            "preserved_historical_record_commitment_sha256": _sha("rewritten-history")
        }
    )

    result = evaluate_r0_12(
        manifest,
        phase10,
        baseline,
        package,
        broken,
        rec,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_12_passed is False
    assert result.historical_evidence_preserved is False
    assert any("historical record commitment changed" in issue for issue in result.issues)


def test_r0_12_fails_checkpoint_regression() -> None:
    manifest, phase10, baseline, package, execution, rec, proofs, canary = _artifacts()
    broken = execution.model_copy(update={"upstream_checkpoint_index": 299})

    result = evaluate_r0_12(
        manifest,
        phase10,
        baseline,
        package,
        broken,
        rec,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_12_passed is False
    assert result.checkpoints_non_regressing is False
    assert any("upstream checkpoint regressed" in issue for issue in result.issues)


def test_r0_12_fails_pending_record_duplication() -> None:
    manifest, phase10, baseline, package, execution, rec, proofs, canary = _artifacts()
    duplicate = rec.records[0].model_copy(update={"final_upstream_commit_count": 2})
    records = (duplicate, rec.records[1])
    broken = rec.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": (
                build_upgrade_reconciliation_commitment(records)
            ),
        }
    )

    result = evaluate_r0_12(
        manifest,
        phase10,
        baseline,
        package,
        execution,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_12_passed is False
    assert result.pending_state_reconciled is False
    assert any("expected one final logical upstream commit" in issue for issue in result.issues)


def test_r0_12_fails_migration_failure() -> None:
    manifest, phase10, baseline, package, execution, rec, proofs, canary = _artifacts()
    broken = execution.model_copy(update={"migration_success": False})

    result = evaluate_r0_12(
        manifest,
        phase10,
        baseline,
        package,
        broken,
        rec,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_12_passed is False
    assert result.target_build_installed is False
    assert any("declared migration did not succeed" in issue for issue in result.issues)


def test_r0_12_fails_prior_phase_boundary_escape() -> None:
    manifest, phase10, baseline, package, execution, rec, proofs, canary = _artifacts()
    broken = execution.model_copy(
        update={
            "storage_used_bytes": 71_000,
            "network_connected": False,
            "time_quality": TimeQuality.DEVICE_RELATIVE_UNTRUSTED,
        }
    )

    result = evaluate_r0_12(
        manifest,
        phase10,
        baseline,
        package,
        broken,
        rec,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_12_passed is False
    assert result.prior_phase_boundaries_preserved is False
    assert any("R0.8 storage boundary crossed" in issue for issue in result.issues)
    assert any("R0.10 network boundary crossed" in issue for issue in result.issues)
    assert any("R0.11 trusted-time boundary" in issue for issue in result.issues)


def test_r0_12_fails_canary_bound_to_wrong_build() -> None:
    manifest, phase10, baseline, package, execution, rec, proofs, canary = _artifacts()
    broken = canary.model_copy(update={"target_build_sha": "c" * 40})

    result = evaluate_r0_12(
        manifest,
        phase10,
        baseline,
        package,
        execution,
        rec,
        proofs,
        broken,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_12_passed is False
    assert result.post_upgrade_canary_valid is False
    assert any("canary is not bound to target build" in issue for issue in result.issues)
