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
from ets.qualification.physical_edge_phase5 import EdgeR0Phase5Evaluation
from ets.qualification.physical_edge_phase6 import (
    EdgeR0ActiveSyncWindow,
    EdgeR0PendingSyncRecord,
    EdgeR0PreSyncSet,
    EdgeR0RecoveredSyncRecord,
    EdgeR0SyncAttemptState,
    EdgeR0SyncPowerObservation,
    EdgeR0SyncProofReceipt,
    EdgeR0SyncRecoveryCanary,
    EdgeR0SyncRecoveryReconciliation,
    build_reconciliation_commitment,
    evaluate_r0_7,
)

_NOW = datetime(2026, 9, 19, 0, 40, tzinfo=UTC)
_BOOT_A = "11111111-1111-4111-8111-111111111111"
_BOOT_B = "22222222-2222-4222-8222-222222222222"


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
            source_revision="c8348d012ec23a2dca5777acb96b1f88af611453",
            artifact_digest=_sha("edge-artifact"),
            configuration_digest=_sha("edge-config"),
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
        notes=("Synthetic W1-7 unit-test manifest.",),
    )


def _phase5(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase5Evaluation:
    return EdgeR0Phase5Evaluation(
        evaluation_id="edge-r0-phase5-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase4_evaluation_id="edge-r0-phase4-passed",
        window_id="active-capture-window-001",
        power_observation_id="active-capture-power-001",
        recovery_snapshot_id="active-capture-recovery-001",
        evaluated_at=_NOW,
        attempted_count=2,
        pre_cut_committed_count=1,
        recovered_commit_count=1,
        independently_verified_commit_count=1,
        acknowledged_commits_preserved=True,
        attempt_classification_complete=True,
        no_duplicate_authoritative_commits=True,
        identity_preserved=True,
        post_recovery_canary_valid=True,
        r0_6_passed=True,
        issues=(),
    )


def _pending_queue() -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=2,
        queue_bytes=2048,
        pending=2,
        in_flight=0,
        retryable_failure=0,
        terminal_failure=0,
        synchronized=10,
        max_items=10_000,
        max_bytes=128 * 1024 * 1024,
        oldest_pending_age_seconds=1.0,
        last_successful_sync=_NOW.isoformat(),
        last_failure=None,
        upstream_status="online",
    )


def _final_queue() -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=0,
        queue_bytes=0,
        pending=0,
        in_flight=0,
        retryable_failure=0,
        terminal_failure=0,
        synchronized=12,
        max_items=10_000,
        max_bytes=128 * 1024 * 1024,
        oldest_pending_age_seconds=None,
        last_successful_sync=(_NOW + timedelta(minutes=4)).isoformat(),
        last_failure=None,
        upstream_status="online",
    )


def _pending_records() -> tuple[EdgeR0PendingSyncRecord, ...]:
    return (
        EdgeR0PendingSyncRecord(
            record_id="record-1",
            event_id="event-1",
            sequence_number=1,
            local_record_sha256=_sha("record-1"),
            proof_artifact_sha256=_sha("proof-1"),
            idempotency_key="idem-1",
        ),
        EdgeR0PendingSyncRecord(
            record_id="record-2",
            event_id="event-2",
            sequence_number=2,
            local_record_sha256=_sha("record-2"),
            proof_artifact_sha256=_sha("proof-2"),
            idempotency_key="idem-2",
        ),
    )


def _recovered_records() -> tuple[EdgeR0RecoveredSyncRecord, ...]:
    return (
        EdgeR0RecoveredSyncRecord(
            record_id="record-1",
            event_id="event-1",
            idempotency_key="idem-1",
            authoritative_local_present=True,
            transport_attempt_count=1,
            final_upstream_commit_count=1,
            final_upstream_event_id="event-1",
            final_upstream_acceptance_sha256=_sha("accept-1"),
            final_proof_sha256=_sha("proof-1"),
            local_marked_synchronized=True,
            recovery_observation_sha256=_sha("recover-record-1"),
        ),
        EdgeR0RecoveredSyncRecord(
            record_id="record-2",
            event_id="event-2",
            idempotency_key="idem-2",
            authoritative_local_present=True,
            transport_attempt_count=2,
            final_upstream_commit_count=1,
            final_upstream_event_id="event-2",
            final_upstream_acceptance_sha256=_sha("accept-2"),
            final_proof_sha256=_sha("proof-2"),
            local_marked_synchronized=True,
            recovery_observation_sha256=_sha("recover-record-2"),
        ),
    )


def _artifacts():
    manifest = _manifest()
    phase5 = _phase5(manifest)
    pending_records = _pending_records()
    pre_sync = EdgeR0PreSyncSet(
        set_id="pre-sync-set-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase5_evaluation_id=phase5.evaluation_id,
        phase5_evaluation_sha256=canonical_sha256(phase5.model_dump(mode="json")),
        captured_at=_NOW + timedelta(seconds=1),
        boot_id=_BOOT_A,
        device_id="ets-edge:test-device",
        signing_public_key_id="edge-demo-signing-key",
        signing_public_key_hex="11" * 32,
        public_key_fingerprint_sha256=_sha("public-key"),
        local_checkpoint_index=100,
        local_checkpoint_sha256=_sha("local-checkpoint-pre"),
        upstream_checkpoint_index=50,
        upstream_checkpoint_sha256=_sha("upstream-checkpoint-pre"),
        queue_state=_pending_queue(),
        records=pending_records,
        source_commitment_sha256=_sha("pre-sync-source"),
    )
    attempts = (
        EdgeR0SyncAttemptState(
            record_id="record-1",
            idempotency_key="idem-1",
            transport_attempt_count=1,
            upstream_accepted_before_cut=True,
            upstream_acceptance_sha256=_sha("precut-accept-1"),
            local_ack_applied_before_cut=False,
        ),
        EdgeR0SyncAttemptState(
            record_id="record-2",
            idempotency_key="idem-2",
            transport_attempt_count=1,
            upstream_accepted_before_cut=False,
            local_ack_applied_before_cut=False,
        ),
    )
    window = EdgeR0ActiveSyncWindow(
        window_id="sync-window-001",
        pre_sync_set_id=pre_sync.set_id,
        pre_sync_set_sha256=canonical_sha256(pre_sync.model_dump(mode="json")),
        sync_run_id="sync-run-before-cut",
        started_at=_NOW + timedelta(seconds=2),
        cut_boundary_at=_NOW + timedelta(seconds=3),
        controller_timeline_sha256=_sha("controller-timeline"),
        attempts=attempts,
    )
    power = EdgeR0SyncPowerObservation(
        observation_id="sync-power-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        window_id=window.window_id,
        window_sha256=canonical_sha256(window.model_dump(mode="json")),
        power_control_id="r0-power-control",
        observer_id="observer-lab-a",
        controller_id="bench-controller-001",
        cut_commanded_at=window.cut_boundary_at,
        power_loss_observed_at=window.cut_boundary_at + timedelta(seconds=1),
        restore_commanded_at=window.cut_boundary_at + timedelta(minutes=1),
        power_restored_observed_at=window.cut_boundary_at + timedelta(
            minutes=1,
            seconds=1,
        ),
        controller_receipt_sha256=_sha("power-controller"),
        observer_loss_receipt_sha256=_sha("power-loss-observer"),
        observer_restore_receipt_sha256=_sha("power-restore-observer"),
    )
    recovered_records = _recovered_records()
    recovery = EdgeR0SyncRecoveryReconciliation(
        reconciliation_id="sync-reconciliation-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        pre_sync_set_id=pre_sync.set_id,
        power_observation_id=power.observation_id,
        recovered_at=_NOW + timedelta(minutes=2),
        boot_id=_BOOT_B,
        device_id=pre_sync.device_id,
        signing_public_key_id=pre_sync.signing_public_key_id,
        signing_public_key_hex=pre_sync.signing_public_key_hex,
        public_key_fingerprint_sha256=pre_sync.public_key_fingerprint_sha256,
        local_checkpoint_index=102,
        local_checkpoint_sha256=_sha("local-checkpoint-final"),
        upstream_checkpoint_index=52,
        upstream_checkpoint_sha256=_sha("upstream-checkpoint-final"),
        final_queue_state=_final_queue(),
        resumed_sync_run_ids=("sync-run-after-recovery",),
        records=recovered_records,
        reconciliation_commitment_sha256=build_reconciliation_commitment(
            recovered_records
        ),
        filesystem_recovery_clean=True,
        recovery_observation_sha256=_sha("sync-recovery-observer"),
    )
    proofs = tuple(
        EdgeR0SyncProofReceipt(
            receipt_id=f"sync-proof-receipt-{index}",
            record_id=record.record_id,
            proof_artifact_sha256=record.final_proof_sha256 or _sha("missing-proof"),
            verified_at=recovery.recovered_at + timedelta(seconds=index),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha(f"verification-{index}"),
            inclusion_valid=True,
            independent_execution_context=True,
        )
        for index, record in enumerate(recovered_records, start=1)
    )
    canary_payload = _sha("canary-payload")
    canary = EdgeR0SyncRecoveryCanary(
        canary_id="sync-canary-001",
        reconciliation_id=recovery.reconciliation_id,
        captured_at=recovery.recovered_at + timedelta(minutes=1),
        request_payload_sha256=canary_payload,
        content_hash=canary_payload,
        event_id="canary-event",
        final_upstream_commit_count=1,
        upstream_acceptance_sha256=_sha("canary-accept"),
        local_marked_synchronized=True,
        proof_artifact_sha256=_sha("canary-proof"),
        verified_at=recovery.recovered_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("canary-verification"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return manifest, phase5, pre_sync, window, power, recovery, proofs, canary


def test_r0_7_passes_clean_interrupted_and_resumed_sync() -> None:
    artifacts = _artifacts()

    result = evaluate_r0_7(*artifacts, evaluated_at=_NOW + timedelta(minutes=4))

    assert result.r0_7_passed is True
    assert result.intended_record_count == 2
    assert result.final_upstream_record_count == 2
    assert result.independently_verified_record_count == 2
    assert result.issues == ()


def test_r0_7_fails_duplicate_upstream_logical_commit() -> None:
    manifest, phase5, pre_sync, window, power, recovery, proofs, canary = _artifacts()
    first = recovery.records[0].model_copy(update={"final_upstream_commit_count": 2})
    records = (first, recovery.records[1])
    broken = recovery.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": build_reconciliation_commitment(records),
        }
    )

    result = evaluate_r0_7(
        manifest,
        phase5,
        pre_sync,
        window,
        power,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_7_passed is False
    assert result.exactly_once_logical_reconciliation is False
    assert any("exactly one logical upstream commit" in issue for issue in result.issues)


def test_r0_7_fails_false_local_synchronized_acknowledgement() -> None:
    manifest, phase5, pre_sync, window, power, recovery, proofs, canary = _artifacts()
    first = EdgeR0RecoveredSyncRecord(
        record_id="record-1",
        event_id="event-1",
        idempotency_key="idem-1",
        authoritative_local_present=True,
        transport_attempt_count=1,
        final_upstream_commit_count=0,
        local_marked_synchronized=True,
        recovery_observation_sha256=_sha("false-local-ack"),
    )
    records = (first, recovery.records[1])
    broken = recovery.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": build_reconciliation_commitment(records),
        }
    )

    result = evaluate_r0_7(
        manifest,
        phase5,
        pre_sync,
        window,
        power,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_7_passed is False
    assert result.local_acknowledgements_supported is False
    assert any("lacks upstream acceptance evidence" in issue for issue in result.issues)


def test_r0_7_fails_when_pending_item_disappears_after_reboot() -> None:
    manifest, phase5, pre_sync, window, power, recovery, proofs, canary = _artifacts()
    records = (recovery.records[0],)
    broken = recovery.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": build_reconciliation_commitment(records),
        }
    )

    result = evaluate_r0_7(
        manifest,
        phase5,
        pre_sync,
        window,
        power,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_7_passed is False
    assert result.local_set_preserved is False
    assert any("recovered set is missing records" in issue for issue in result.issues)


def test_r0_7_fails_checkpoint_regression() -> None:
    manifest, phase5, pre_sync, window, power, recovery, proofs, canary = _artifacts()
    broken = recovery.model_copy(update={"upstream_checkpoint_index": 49})

    result = evaluate_r0_7(
        manifest,
        phase5,
        pre_sync,
        window,
        power,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_7_passed is False
    assert result.checkpoints_non_regressing is False
    assert any("upstream checkpoint regressed" in issue for issue in result.issues)


def test_r0_7_fails_unknown_injected_record() -> None:
    manifest, phase5, pre_sync, window, power, recovery, proofs, canary = _artifacts()
    injected = EdgeR0RecoveredSyncRecord(
        record_id="record-injected",
        event_id="event-injected",
        idempotency_key="idem-injected",
        authoritative_local_present=True,
        transport_attempt_count=1,
        final_upstream_commit_count=1,
        final_upstream_event_id="event-injected",
        final_upstream_acceptance_sha256=_sha("accept-injected"),
        final_proof_sha256=_sha("proof-injected"),
        local_marked_synchronized=True,
        recovery_observation_sha256=_sha("recover-injected"),
    )
    records = (*recovery.records, injected)
    broken = recovery.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": build_reconciliation_commitment(records),
        }
    )

    result = evaluate_r0_7(
        manifest,
        phase5,
        pre_sync,
        window,
        power,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_7_passed is False
    assert result.local_set_preserved is False
    assert any("recovered set contains unknown records" in issue for issue in result.issues)


def test_r0_7_fails_unresolved_final_backlog() -> None:
    manifest, phase5, pre_sync, window, power, recovery, proofs, canary = _artifacts()
    backlog = recovery.final_queue_state.model_copy(
        update={"queue_depth": 1, "queue_bytes": 512, "pending": 1}
    )
    broken = recovery.model_copy(update={"final_queue_state": backlog})

    result = evaluate_r0_7(
        manifest,
        phase5,
        pre_sync,
        window,
        power,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_7_passed is False
    assert result.final_backlog_clear is False
    assert any("backlog/checkpoint state is not clean" in issue for issue in result.issues)


def test_r0_7_fails_identity_drift() -> None:
    manifest, phase5, pre_sync, window, power, recovery, proofs, canary = _artifacts()
    broken = recovery.model_copy(update={"device_id": "ets-edge:different-device"})

    result = evaluate_r0_7(
        manifest,
        phase5,
        pre_sync,
        window,
        power,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_7_passed is False
    assert result.identity_preserved is False
    assert any("device identity changed" in issue for issue in result.issues)


def test_r0_7_fails_post_recovery_canary() -> None:
    manifest, phase5, pre_sync, window, power, recovery, proofs, canary = _artifacts()
    failed_canary = canary.model_copy(update={"inclusion_valid": False})

    result = evaluate_r0_7(
        manifest,
        phase5,
        pre_sync,
        window,
        power,
        recovery,
        proofs,
        failed_canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_7_passed is False
    assert result.post_recovery_canary_valid is False
    assert any("canary did not verify independently" in issue for issue in result.issues)
