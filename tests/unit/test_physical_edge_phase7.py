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
from ets.qualification.physical_edge_phase6 import EdgeR0Phase6Evaluation
from ets.qualification.physical_edge_phase7 import (
    EdgeR0PressureIngressAttempt,
    EdgeR0PressureRecoveryRecord,
    EdgeR0StorageBaseline,
    EdgeR0StoragePressureWindow,
    EdgeR0StorageProofReceipt,
    EdgeR0StorageRecoveryCanary,
    EdgeR0StorageRestoration,
    EdgeR0StorageTransitionObservation,
    PressureIngressDisposition,
    StoragePressureBand,
    StorageProofSubject,
    evaluate_r0_8,
)

_NOW = datetime(2026, 9, 19, 1, 5, tzinfo=UTC)


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
            source_revision="e7a5caabe6f09514bf8d0fe7ebba4ebe96b382d7",
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
        notes=("Synthetic W1-8 unit-test manifest.",),
    )


def _queue(
    *,
    depth: int = 0,
    bytes_used: int = 0,
    pending: int = 0,
    synchronized: int = 20,
) -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=depth,
        queue_bytes=bytes_used,
        pending=pending,
        in_flight=0,
        retryable_failure=0,
        terminal_failure=0,
        synchronized=synchronized,
        max_items=10_000,
        max_bytes=128 * 1024 * 1024,
        oldest_pending_age_seconds=None if pending == 0 else 1.0,
        last_successful_sync=_NOW.isoformat(),
        last_failure=None,
        upstream_status="online",
    )


def _phase6(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase6Evaluation:
    return EdgeR0Phase6Evaluation(
        evaluation_id="edge-r0-phase6-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase5_evaluation_id="edge-r0-phase5-passed",
        pre_sync_set_id="pre-sync-set-001",
        window_id="sync-window-001",
        power_observation_id="sync-power-001",
        reconciliation_id="sync-reconciliation-001",
        evaluated_at=_NOW,
        intended_record_count=2,
        final_upstream_record_count=2,
        independently_verified_record_count=2,
        local_set_preserved=True,
        exactly_once_logical_reconciliation=True,
        local_acknowledgements_supported=True,
        checkpoints_non_regressing=True,
        reconciliation_commitment_valid=True,
        final_backlog_clear=True,
        identity_preserved=True,
        post_recovery_canary_valid=True,
        r0_7_passed=True,
        issues=(),
    )


def _artifacts():
    manifest = _manifest()
    phase6 = _phase6(manifest)
    baseline = EdgeR0StorageBaseline(
        baseline_id="storage-baseline-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase6_evaluation_id=phase6.evaluation_id,
        phase6_evaluation_sha256=canonical_sha256(phase6.model_dump(mode="json")),
        captured_at=_NOW + timedelta(seconds=1),
        storage_control_id="r0-storage-control",
        filesystem_id="qualification-volume-001",
        device_id="nvme0n1p-test",
        mount_point="/var/lib/ets-qualification",
        total_bytes=100_000,
        used_bytes=50_000,
        free_bytes=50_000,
        high_watermark_used_bytes=70_000,
        critical_watermark_used_bytes=85_000,
        reserved_recovery_bytes=10_000,
        local_checkpoint_index=200,
        local_checkpoint_sha256=_sha("checkpoint-pre"),
        log_head_sha256=_sha("log-head-pre"),
        queue_state=_queue(),
        representative_proof_sha256=(_sha("pre-proof-1"), _sha("pre-proof-2")),
        observer_receipt_sha256=_sha("baseline-observer"),
    )
    high = EdgeR0StorageTransitionObservation(
        transition_id="storage-high-001",
        baseline_id=baseline.baseline_id,
        baseline_sha256=canonical_sha256(baseline.model_dump(mode="json")),
        band=StoragePressureBand.HIGH,
        started_at=_NOW + timedelta(seconds=2),
        observed_at=_NOW + timedelta(seconds=3),
        total_bytes=100_000,
        used_bytes=75_000,
        free_bytes=25_000,
        edge_storage_state="degraded",
        backpressure_active=True,
        authoritative_ingress_enabled=True,
        reserved_headroom_preserved=True,
        controller_receipt_sha256=_sha("high-controller"),
        independent_measurement_sha256=_sha("high-measurement"),
        edge_observation_sha256=_sha("high-edge"),
    )
    critical = EdgeR0StorageTransitionObservation(
        transition_id="storage-critical-001",
        baseline_id=baseline.baseline_id,
        baseline_sha256=canonical_sha256(baseline.model_dump(mode="json")),
        band=StoragePressureBand.CRITICAL,
        started_at=_NOW + timedelta(seconds=4),
        observed_at=_NOW + timedelta(seconds=5),
        total_bytes=100_000,
        used_bytes=87_000,
        free_bytes=13_000,
        edge_storage_state="critical_backpressure",
        backpressure_active=True,
        authoritative_ingress_enabled=False,
        reserved_headroom_preserved=True,
        controller_receipt_sha256=_sha("critical-controller"),
        independent_measurement_sha256=_sha("critical-measurement"),
        edge_observation_sha256=_sha("critical-edge"),
    )
    committed_payload = _sha("pressure-request-1")
    attempts = (
        EdgeR0PressureIngressAttempt(
            attempt_id="pressure-attempt-1",
            sequence_number=1,
            band=StoragePressureBand.HIGH,
            attempted_at=_NOW + timedelta(seconds=3, microseconds=100),
            request_payload_sha256=committed_payload,
            response_artifact_sha256=_sha("response-1"),
            disposition=PressureIngressDisposition.AUTHORITATIVELY_COMMITTED,
            event_id="pressure-event-1",
            event_hash=_sha("pressure-event-1"),
            content_hash=committed_payload,
            proof_artifact_sha256=_sha("pressure-proof-1"),
        ),
        EdgeR0PressureIngressAttempt(
            attempt_id="pressure-attempt-2",
            sequence_number=2,
            band=StoragePressureBand.HIGH,
            attempted_at=_NOW + timedelta(seconds=4),
            request_payload_sha256=_sha("pressure-request-2"),
            response_artifact_sha256=_sha("response-2"),
            disposition=PressureIngressDisposition.REJECTED_BACKPRESSURE,
            backpressure_signal="HTTP_429",
            retry_after_seconds=5,
        ),
        EdgeR0PressureIngressAttempt(
            attempt_id="pressure-attempt-3",
            sequence_number=3,
            band=StoragePressureBand.CRITICAL,
            attempted_at=_NOW + timedelta(seconds=5, microseconds=100),
            request_payload_sha256=_sha("pressure-request-3"),
            response_artifact_sha256=_sha("response-3"),
            disposition=PressureIngressDisposition.REJECTED_BACKPRESSURE,
            backpressure_signal="HTTP_507",
        ),
        EdgeR0PressureIngressAttempt(
            attempt_id="pressure-attempt-4",
            sequence_number=4,
            band=StoragePressureBand.CRITICAL,
            attempted_at=_NOW + timedelta(seconds=6),
            request_payload_sha256=_sha("pressure-request-4"),
            response_artifact_sha256=_sha("response-4"),
            disposition=PressureIngressDisposition.NON_AUTHORITATIVE_UNACKNOWLEDGED,
        ),
    )
    window = EdgeR0StoragePressureWindow(
        window_id="storage-pressure-window-001",
        baseline_id=baseline.baseline_id,
        high_transition_id=high.transition_id,
        critical_transition_id=critical.transition_id,
        started_at=high.observed_at,
        completed_at=_NOW + timedelta(seconds=7),
        attempts=attempts,
        controller_timeline_sha256=_sha("pressure-timeline"),
    )
    recovery_records = (
        EdgeR0PressureRecoveryRecord(
            attempt_id="pressure-attempt-1",
            authoritative_commit_count=1,
            recovered_event_id="pressure-event-1",
            recovered_proof_sha256=_sha("pressure-proof-1"),
            recovery_observation_sha256=_sha("recover-pressure-1"),
        ),
        EdgeR0PressureRecoveryRecord(
            attempt_id="pressure-attempt-2",
            authoritative_commit_count=0,
            recovery_observation_sha256=_sha("recover-pressure-2"),
        ),
        EdgeR0PressureRecoveryRecord(
            attempt_id="pressure-attempt-3",
            authoritative_commit_count=0,
            recovery_observation_sha256=_sha("recover-pressure-3"),
        ),
        EdgeR0PressureRecoveryRecord(
            attempt_id="pressure-attempt-4",
            authoritative_commit_count=0,
            recovery_observation_sha256=_sha("recover-pressure-4"),
        ),
    )
    restoration = EdgeR0StorageRestoration(
        restoration_id="storage-restoration-001",
        baseline_id=baseline.baseline_id,
        critical_transition_id=critical.transition_id,
        restored_at=_NOW + timedelta(seconds=8),
        total_bytes=100_000,
        used_bytes=55_000,
        free_bytes=45_000,
        normal_range_restored=True,
        cleanup_receipt_sha256=_sha("cleanup"),
        independent_measurement_sha256=_sha("restored-measurement"),
        pre_pressure_log_head_sha256=baseline.log_head_sha256,
        pre_pressure_log_head_observed=True,
        post_recovery_checkpoint_index=201,
        post_recovery_checkpoint_sha256=_sha("checkpoint-post"),
        final_queue_state=_queue(synchronized=21),
        recovery_records=recovery_records,
    )
    proofs = (
        EdgeR0StorageProofReceipt(
            receipt_id="storage-proof-pre-1",
            subject_kind=StorageProofSubject.PRE_PRESSURE,
            subject_id=_sha("pre-proof-1"),
            proof_artifact_sha256=_sha("pre-proof-1"),
            verified_at=restoration.restored_at + timedelta(seconds=1),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("pre-result-1"),
            inclusion_valid=True,
            independent_execution_context=True,
        ),
        EdgeR0StorageProofReceipt(
            receipt_id="storage-proof-pre-2",
            subject_kind=StorageProofSubject.PRE_PRESSURE,
            subject_id=_sha("pre-proof-2"),
            proof_artifact_sha256=_sha("pre-proof-2"),
            verified_at=restoration.restored_at + timedelta(seconds=2),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("pre-result-2"),
            inclusion_valid=True,
            independent_execution_context=True,
        ),
        EdgeR0StorageProofReceipt(
            receipt_id="storage-proof-attempt-1",
            subject_kind=StorageProofSubject.PRESSURE_ATTEMPT,
            subject_id="pressure-attempt-1",
            proof_artifact_sha256=_sha("pressure-proof-1"),
            verified_at=restoration.restored_at + timedelta(seconds=3),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("pressure-result-1"),
            inclusion_valid=True,
            independent_execution_context=True,
        ),
    )
    canary_payload = _sha("storage-canary-payload")
    canary = EdgeR0StorageRecoveryCanary(
        canary_id="storage-canary-001",
        restoration_id=restoration.restoration_id,
        captured_at=restoration.restored_at + timedelta(minutes=1),
        request_payload_sha256=canary_payload,
        content_hash=canary_payload,
        event_id="storage-canary-event",
        proof_artifact_sha256=_sha("storage-canary-proof"),
        verified_at=restoration.restored_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("storage-canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return (
        manifest,
        phase6,
        baseline,
        high,
        critical,
        window,
        restoration,
        proofs,
        canary,
    )


def test_r0_8_passes_bounded_storage_pressure_and_recovery() -> None:
    artifacts = _artifacts()

    result = evaluate_r0_8(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_8_passed is True
    assert result.pressure_committed_count == 1
    assert result.rejected_backpressure_count == 2
    assert result.issues == ()


def test_r0_8_fails_authoritative_commit_at_critical_watermark() -> None:
    manifest, phase6, baseline, high, critical, window, restoration, proofs, canary = (
        _artifacts()
    )
    payload = _sha("critical-unsafe-payload")
    unsafe = EdgeR0PressureIngressAttempt(
        attempt_id="pressure-attempt-3",
        sequence_number=3,
        band=StoragePressureBand.CRITICAL,
        attempted_at=_NOW + timedelta(seconds=5, microseconds=100),
        request_payload_sha256=payload,
        response_artifact_sha256=_sha("critical-unsafe-response"),
        disposition=PressureIngressDisposition.AUTHORITATIVELY_COMMITTED,
        event_id="critical-unsafe-event",
        event_hash=_sha("critical-unsafe-event"),
        content_hash=payload,
        proof_artifact_sha256=_sha("critical-unsafe-proof"),
    )
    attempts = (window.attempts[0], window.attempts[1], unsafe, window.attempts[3])
    broken_window = window.model_copy(update={"attempts": attempts})
    recovered = EdgeR0PressureRecoveryRecord(
        attempt_id="pressure-attempt-3",
        authoritative_commit_count=1,
        recovered_event_id="critical-unsafe-event",
        recovered_proof_sha256=_sha("critical-unsafe-proof"),
        recovery_observation_sha256=_sha("recover-critical-unsafe"),
    )
    recovery_records = (
        restoration.recovery_records[0],
        restoration.recovery_records[1],
        recovered,
        restoration.recovery_records[3],
    )
    broken_restoration = restoration.model_copy(
        update={"recovery_records": recovery_records}
    )
    unsafe_proof = EdgeR0StorageProofReceipt(
        receipt_id="unsafe-proof",
        subject_kind=StorageProofSubject.PRESSURE_ATTEMPT,
        subject_id="pressure-attempt-3",
        proof_artifact_sha256=_sha("critical-unsafe-proof"),
        verified_at=restoration.restored_at + timedelta(seconds=4),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("unsafe-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )

    result = evaluate_r0_8(
        manifest,
        phase6,
        baseline,
        high,
        critical,
        broken_window,
        broken_restoration,
        (*proofs, unsafe_proof),
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_8_passed is False
    assert result.backpressure_before_unsafe_ack is False
    assert any("critical-band attempt was authoritatively committed" in x for x in result.issues)


def test_r0_8_fails_when_reserved_recovery_headroom_is_violated() -> None:
    manifest, phase6, baseline, high, critical, window, restoration, proofs, canary = (
        _artifacts()
    )
    broken_critical = critical.model_copy(
        update={
            "used_bytes": 92_000,
            "free_bytes": 8_000,
            "reserved_headroom_preserved": False,
        }
    )

    result = evaluate_r0_8(
        manifest,
        phase6,
        baseline,
        high,
        broken_critical,
        window,
        restoration,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_8_passed is False
    assert result.recovery_headroom_preserved is False
    assert any("reserved recovery headroom was violated" in x for x in result.issues)


def test_r0_8_fails_silent_loss_of_acknowledged_commit() -> None:
    manifest, phase6, baseline, high, critical, window, restoration, proofs, canary = (
        _artifacts()
    )
    lost = EdgeR0PressureRecoveryRecord(
        attempt_id="pressure-attempt-1",
        authoritative_commit_count=0,
        recovery_observation_sha256=_sha("lost-commit"),
    )
    records = (lost, *restoration.recovery_records[1:])
    broken = restoration.model_copy(update={"recovery_records": records})

    result = evaluate_r0_8(
        manifest,
        phase6,
        baseline,
        high,
        critical,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_8_passed is False
    assert result.acknowledged_commits_preserved is False
    assert any("acknowledged commit was not preserved exactly once" in x for x in result.issues)


def test_r0_8_fails_if_rejected_attempt_later_appears_committed() -> None:
    manifest, phase6, baseline, high, critical, window, restoration, proofs, canary = (
        _artifacts()
    )
    unexpected = EdgeR0PressureRecoveryRecord(
        attempt_id="pressure-attempt-3",
        authoritative_commit_count=1,
        recovered_event_id="unexpected-event",
        recovered_proof_sha256=_sha("unexpected-proof"),
        recovery_observation_sha256=_sha("unexpected-observation"),
    )
    records = (
        restoration.recovery_records[0],
        restoration.recovery_records[1],
        unexpected,
        restoration.recovery_records[3],
    )
    broken = restoration.model_copy(update={"recovery_records": records})
    unexpected_proof = EdgeR0StorageProofReceipt(
        receipt_id="unexpected-proof-receipt",
        subject_kind=StorageProofSubject.PRESSURE_ATTEMPT,
        subject_id="pressure-attempt-3",
        proof_artifact_sha256=_sha("unexpected-proof"),
        verified_at=restoration.restored_at + timedelta(seconds=4),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("unexpected-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )

    result = evaluate_r0_8(
        manifest,
        phase6,
        baseline,
        high,
        critical,
        window,
        broken,
        (*proofs, unexpected_proof),
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_8_passed is False
    assert result.attempt_reconciliation_complete is False
    assert any("explicitly rejected attempt later became committed" in x for x in result.issues)


def test_r0_8_fails_when_preexisting_proof_is_missing() -> None:
    manifest, phase6, baseline, high, critical, window, restoration, proofs, canary = (
        _artifacts()
    )

    result = evaluate_r0_8(
        manifest,
        phase6,
        baseline,
        high,
        critical,
        window,
        restoration,
        proofs[1:],
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_8_passed is False
    assert result.preexisting_evidence_preserved is False
    assert any("missing pre-pressure proof verification" in x for x in result.issues)


def test_r0_8_fails_history_rewrite_or_checkpoint_regression() -> None:
    manifest, phase6, baseline, high, critical, window, restoration, proofs, canary = (
        _artifacts()
    )
    broken = restoration.model_copy(
        update={
            "pre_pressure_log_head_sha256": _sha("rewritten-head"),
            "post_recovery_checkpoint_index": 199,
        }
    )

    result = evaluate_r0_8(
        manifest,
        phase6,
        baseline,
        high,
        critical,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_8_passed is False
    assert result.history_not_rewritten is False
    assert any("log-head digest changed" in x for x in result.issues)
    assert any("checkpoint regressed" in x for x in result.issues)


def test_r0_8_fails_unresolved_queue_after_space_restoration() -> None:
    manifest, phase6, baseline, high, critical, window, restoration, proofs, canary = (
        _artifacts()
    )
    backlog = _queue(depth=1, bytes_used=512, pending=1, synchronized=20)
    broken = restoration.model_copy(update={"final_queue_state": backlog})

    result = evaluate_r0_8(
        manifest,
        phase6,
        baseline,
        high,
        critical,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_8_passed is False
    assert result.normal_operation_restored is False
    assert any("did not return to normal operating range" in x for x in result.issues)


def test_r0_8_fails_post_recovery_canary() -> None:
    manifest, phase6, baseline, high, critical, window, restoration, proofs, canary = (
        _artifacts()
    )
    failed_canary = canary.model_copy(update={"inclusion_valid": False})

    result = evaluate_r0_8(
        manifest,
        phase6,
        baseline,
        high,
        critical,
        window,
        restoration,
        proofs,
        failed_canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_8_passed is False
    assert result.post_recovery_canary_valid is False
    assert any("canary did not verify independently" in x for x in result.issues)
