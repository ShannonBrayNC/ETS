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
from ets.qualification.physical_edge_phase7 import EdgeR0Phase7Evaluation
from ets.qualification.physical_edge_phase8 import (
    EdgeR0QueueAttempt,
    EdgeR0QueueBaseline,
    EdgeR0QueueProofReceipt,
    EdgeR0QueueRecovery,
    EdgeR0QueueRecoveryCanary,
    EdgeR0QueueRecoveryRecord,
    EdgeR0QueueSample,
    EdgeR0QueueSaturationWindow,
    EdgeR0QueueWorkloadDefinition,
    QueueAttemptDisposition,
    QueueProofSubject,
    evaluate_r0_9,
)

_NOW = datetime(2026, 9, 19, 14, 20, tzinfo=UTC)


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
            source_revision="f1c329d3341b7dcaba821460b62eff585373067a",
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
        notes=("Synthetic W1-9 unit-test manifest.",),
    )


def _queue(
    *,
    depth: int,
    bytes_used: int,
    pending: int,
    max_items: int = 3,
    max_bytes: int = 300,
) -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=depth,
        queue_bytes=bytes_used,
        pending=pending,
        in_flight=0,
        retryable_failure=0,
        terminal_failure=0,
        synchronized=20,
        max_items=max_items,
        max_bytes=max_bytes,
        oldest_pending_age_seconds=None if pending == 0 else 1.0,
        last_successful_sync=_NOW.isoformat(),
        last_failure=None,
        upstream_status="online",
    )


def _phase7(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase7Evaluation:
    return EdgeR0Phase7Evaluation(
        evaluation_id="edge-r0-phase7-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase6_evaluation_id="edge-r0-phase6-passed",
        baseline_id="storage-baseline-001",
        window_id="storage-window-001",
        restoration_id="storage-restoration-001",
        evaluated_at=_NOW,
        attempted_count=4,
        pressure_committed_count=1,
        rejected_backpressure_count=2,
        watermarks_observed=True,
        recovery_headroom_preserved=True,
        backpressure_before_unsafe_ack=True,
        attempt_reconciliation_complete=True,
        acknowledged_commits_preserved=True,
        preexisting_evidence_preserved=True,
        history_not_rewritten=True,
        normal_operation_restored=True,
        post_recovery_canary_valid=True,
        r0_8_passed=True,
        issues=(),
    )


def _artifacts():
    manifest = _manifest()
    phase7 = _phase7(manifest)
    baseline = EdgeR0QueueBaseline(
        baseline_id="queue-baseline-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase7_evaluation_id=phase7.evaluation_id,
        phase7_evaluation_sha256=canonical_sha256(phase7.model_dump(mode="json")),
        captured_at=_NOW + timedelta(seconds=1),
        max_items=3,
        max_bytes=300,
        queue_state=_queue(depth=0, bytes_used=0, pending=0),
        storage_used_bytes=40_000,
        storage_high_watermark_used_bytes=70_000,
        local_checkpoint_index=300,
        local_checkpoint_sha256=_sha("queue-checkpoint-pre"),
        log_head_sha256=_sha("queue-log-head-pre"),
        representative_proof_sha256=(_sha("queue-pre-proof"),),
        observer_receipt_sha256=_sha("queue-baseline-observer"),
    )
    attempts = (
        EdgeR0QueueAttempt(
            attempt_id="queue-attempt-1",
            sequence_number=1,
            attempted_at=_NOW + timedelta(seconds=3),
            payload_bytes=100,
            request_payload_sha256=_sha("queue-request-1"),
            response_artifact_sha256=_sha("queue-response-1"),
            disposition=QueueAttemptDisposition.AUTHORITATIVELY_ACCEPTED,
            event_id="queue-event-1",
            content_hash=_sha("queue-request-1"),
            proof_artifact_sha256=_sha("queue-proof-1"),
        ),
        EdgeR0QueueAttempt(
            attempt_id="queue-attempt-2",
            sequence_number=2,
            attempted_at=_NOW + timedelta(seconds=4),
            payload_bytes=100,
            request_payload_sha256=_sha("queue-request-2"),
            response_artifact_sha256=_sha("queue-response-2"),
            disposition=QueueAttemptDisposition.AUTHORITATIVELY_ACCEPTED,
            event_id="queue-event-2",
            content_hash=_sha("queue-request-2"),
            proof_artifact_sha256=_sha("queue-proof-2"),
        ),
        EdgeR0QueueAttempt(
            attempt_id="queue-attempt-3",
            sequence_number=3,
            attempted_at=_NOW + timedelta(seconds=5),
            payload_bytes=100,
            request_payload_sha256=_sha("queue-request-3"),
            response_artifact_sha256=_sha("queue-response-3"),
            disposition=QueueAttemptDisposition.AUTHORITATIVELY_ACCEPTED,
            event_id="queue-event-3",
            content_hash=_sha("queue-request-3"),
            proof_artifact_sha256=_sha("queue-proof-3"),
        ),
        EdgeR0QueueAttempt(
            attempt_id="queue-attempt-4",
            sequence_number=4,
            attempted_at=_NOW + timedelta(seconds=6),
            payload_bytes=100,
            request_payload_sha256=_sha("queue-request-4"),
            response_artifact_sha256=_sha("queue-response-4"),
            disposition=QueueAttemptDisposition.REJECTED_BACKPRESSURE,
            backpressure_signal="HTTP_429",
            retry_after_seconds=2,
        ),
    )
    workload = EdgeR0QueueWorkloadDefinition(
        workload_id="queue-workload-001",
        baseline_id=baseline.baseline_id,
        generated_at=_NOW + timedelta(seconds=2),
        request_count=4,
        total_payload_bytes=400,
        max_duration_seconds=30,
        deterministic_seed_sha256=_sha("queue-seed"),
        generator_definition_sha256=_sha("queue-generator"),
        operator_stop_condition="stop on declared queue bound or resource alarm",
        controller_start_receipt_sha256=_sha("queue-start"),
        controller_stop_receipt_sha256=_sha("queue-stop"),
    )
    samples = (
        EdgeR0QueueSample(
            sample_id="queue-sample-0",
            workload_id=workload.workload_id,
            sample_index=0,
            observed_at=_NOW + timedelta(seconds=2),
            queue_depth=0,
            queue_bytes=0,
            pending=0,
            in_flight=0,
            retryable_failure=0,
            terminal_failure=0,
            storage_used_bytes=40_000,
            rss_bytes=128 * 1024 * 1024,
            backpressure_active=False,
            observer_receipt_sha256=_sha("queue-sample-0"),
        ),
        EdgeR0QueueSample(
            sample_id="queue-sample-1",
            workload_id=workload.workload_id,
            sample_index=1,
            observed_at=_NOW + timedelta(seconds=5),
            queue_depth=3,
            queue_bytes=300,
            pending=3,
            in_flight=0,
            retryable_failure=0,
            terminal_failure=0,
            storage_used_bytes=40_300,
            rss_bytes=130 * 1024 * 1024,
            backpressure_active=True,
            observer_receipt_sha256=_sha("queue-sample-1"),
        ),
        EdgeR0QueueSample(
            sample_id="queue-sample-2",
            workload_id=workload.workload_id,
            sample_index=2,
            observed_at=_NOW + timedelta(seconds=6),
            queue_depth=3,
            queue_bytes=300,
            pending=3,
            in_flight=0,
            retryable_failure=0,
            terminal_failure=0,
            storage_used_bytes=40_300,
            rss_bytes=131 * 1024 * 1024,
            backpressure_active=True,
            observer_receipt_sha256=_sha("queue-sample-2"),
        ),
    )
    window = EdgeR0QueueSaturationWindow(
        window_id="queue-window-001",
        baseline_id=baseline.baseline_id,
        workload_id=workload.workload_id,
        started_at=_NOW + timedelta(seconds=2),
        completed_at=_NOW + timedelta(seconds=7),
        samples=samples,
        attempts=attempts,
        first_limit_sample_id="queue-sample-1",
        first_backpressure_attempt_id="queue-attempt-4",
        controller_timeline_sha256=_sha("queue-timeline"),
    )
    recovery_records = tuple(
        EdgeR0QueueRecoveryRecord(
            attempt_id=attempt.attempt_id,
            authoritative_commit_count=(
                1
                if attempt.disposition
                is QueueAttemptDisposition.AUTHORITATIVELY_ACCEPTED
                else 0
            ),
            recovered_event_id=(
                attempt.event_id
                if attempt.disposition
                is QueueAttemptDisposition.AUTHORITATIVELY_ACCEPTED
                else None
            ),
            recovered_proof_sha256=(
                attempt.proof_artifact_sha256
                if attempt.disposition
                is QueueAttemptDisposition.AUTHORITATIVELY_ACCEPTED
                else None
            ),
            recovery_observation_sha256=_sha(f"queue-recovery-{attempt.attempt_id}"),
        )
        for attempt in attempts
    )
    recovery = EdgeR0QueueRecovery(
        recovery_id="queue-recovery-001",
        baseline_id=baseline.baseline_id,
        window_id=window.window_id,
        recovered_at=_NOW + timedelta(seconds=10),
        final_queue_state=_queue(depth=0, bytes_used=0, pending=0),
        storage_used_bytes=40_100,
        rss_bytes=129 * 1024 * 1024,
        local_checkpoint_index=303,
        local_checkpoint_sha256=_sha("queue-checkpoint-post"),
        pre_saturation_log_head_sha256=baseline.log_head_sha256,
        pre_saturation_log_head_observed=True,
        records=recovery_records,
        recovery_receipt_sha256=_sha("queue-recovery-receipt"),
    )
    proofs = [
        EdgeR0QueueProofReceipt(
            receipt_id="queue-pre-proof-receipt",
            subject_kind=QueueProofSubject.PRE_SATURATION,
            subject_id=_sha("queue-pre-proof"),
            proof_artifact_sha256=_sha("queue-pre-proof"),
            verified_at=recovery.recovered_at + timedelta(seconds=1),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("queue-pre-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        )
    ]
    for index, attempt in enumerate(attempts[:3], start=1):
        proofs.append(
            EdgeR0QueueProofReceipt(
                receipt_id=f"queue-attempt-proof-{index}",
                subject_kind=QueueProofSubject.SATURATION_ATTEMPT,
                subject_id=attempt.attempt_id,
                proof_artifact_sha256=attempt.proof_artifact_sha256 or _sha("missing"),
                verified_at=recovery.recovered_at + timedelta(seconds=index + 1),
                verifier_id="ets-verify-offline",
                verifier_host_id="bench-controller-001",
                verifier_build_sha256=_sha("verifier-build"),
                verification_result_sha256=_sha(f"queue-attempt-result-{index}"),
                inclusion_valid=True,
                independent_execution_context=True,
            )
        )
    canary_payload = _sha("queue-canary-payload")
    canary = EdgeR0QueueRecoveryCanary(
        canary_id="queue-canary-001",
        recovery_id=recovery.recovery_id,
        captured_at=recovery.recovered_at + timedelta(minutes=1),
        request_payload_sha256=canary_payload,
        content_hash=canary_payload,
        event_id="queue-canary-event",
        proof_artifact_sha256=_sha("queue-canary-proof"),
        verified_at=recovery.recovered_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("queue-canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return (
        manifest,
        phase7,
        baseline,
        workload,
        window,
        recovery,
        tuple(proofs),
        canary,
    )


def test_r0_9_passes_bounded_queue_saturation() -> None:
    artifacts = _artifacts()

    result = evaluate_r0_9(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_9_passed is True
    assert result.accepted_count == 3
    assert result.rejected_count == 1
    assert result.issues == ()


def test_r0_9_fails_queue_bound_escape() -> None:
    manifest, phase7, baseline, workload, window, recovery, proofs, canary = _artifacts()
    bad = window.samples[2].model_copy(update={"queue_depth": 4, "queue_bytes": 400})
    broken_window = window.model_copy(update={"samples": (*window.samples[:2], bad)})

    result = evaluate_r0_9(
        manifest,
        phase7,
        baseline,
        workload,
        broken_window,
        recovery,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_9_passed is False
    assert result.queue_bounds_enforced is False
    assert any("queue item bound exceeded" in issue for issue in result.issues)


def test_r0_9_fails_without_explicit_backpressure() -> None:
    manifest, phase7, baseline, workload, window, recovery, proofs, canary = _artifacts()
    last = EdgeR0QueueAttempt(
        attempt_id="queue-attempt-4",
        sequence_number=4,
        attempted_at=_NOW + timedelta(seconds=6),
        payload_bytes=100,
        request_payload_sha256=_sha("queue-request-4"),
        response_artifact_sha256=_sha("queue-response-4"),
        disposition=QueueAttemptDisposition.NON_AUTHORITATIVE_UNACKNOWLEDGED,
    )
    broken_window = window.model_copy(update={"attempts": (*window.attempts[:3], last)})

    result = evaluate_r0_9(
        manifest,
        phase7,
        baseline,
        workload,
        broken_window,
        recovery,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_9_passed is False
    assert result.explicit_backpressure_observed is False
    assert any("first backpressure attempt" in issue for issue in result.issues)


def test_r0_9_fails_rejected_attempt_promoted_to_commit() -> None:
    manifest, phase7, baseline, workload, window, recovery, proofs, canary = _artifacts()
    promoted = EdgeR0QueueRecoveryRecord(
        attempt_id="queue-attempt-4",
        authoritative_commit_count=1,
        recovered_event_id="unexpected-event",
        recovered_proof_sha256=_sha("unexpected-proof"),
        recovery_observation_sha256=_sha("promoted-recovery"),
    )
    broken = recovery.model_copy(update={"records": (*recovery.records[:3], promoted)})

    result = evaluate_r0_9(
        manifest,
        phase7,
        baseline,
        workload,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_9_passed is False
    assert result.attempt_reconciliation_complete is False
    assert any("rejected attempt later became committed" in issue for issue in result.issues)


def test_r0_9_fails_if_storage_pressure_boundary_is_crossed() -> None:
    manifest, phase7, baseline, workload, window, recovery, proofs, canary = _artifacts()
    bad = window.samples[2].model_copy(update={"storage_used_bytes": 71_000})
    broken_window = window.model_copy(update={"samples": (*window.samples[:2], bad)})

    result = evaluate_r0_9(
        manifest,
        phase7,
        baseline,
        workload,
        broken_window,
        recovery,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_9_passed is False
    assert result.storage_boundary_not_crossed is False
    assert any("storage high watermark crossed" in issue for issue in result.issues)


def test_r0_9_fails_accepted_record_loss() -> None:
    manifest, phase7, baseline, workload, window, recovery, proofs, canary = _artifacts()
    lost = EdgeR0QueueRecoveryRecord(
        attempt_id="queue-attempt-1",
        authoritative_commit_count=0,
        recovery_observation_sha256=_sha("lost-accepted-record"),
    )
    broken = recovery.model_copy(update={"records": (lost, *recovery.records[1:])})

    result = evaluate_r0_9(
        manifest,
        phase7,
        baseline,
        workload,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_9_passed is False
    assert result.accepted_records_preserved is False
    assert any("accepted record not preserved exactly once" in issue for issue in result.issues)


def test_r0_9_fails_residual_queue_after_recovery() -> None:
    manifest, phase7, baseline, workload, window, recovery, proofs, canary = _artifacts()
    dirty = _queue(depth=1, bytes_used=100, pending=1)
    broken = recovery.model_copy(update={"final_queue_state": dirty})

    result = evaluate_r0_9(
        manifest,
        phase7,
        baseline,
        workload,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_9_passed is False
    assert result.final_queue_clean is False
    assert any("final queue state is not clean" in issue for issue in result.issues)


def test_r0_9_fails_missing_preexisting_proof() -> None:
    manifest, phase7, baseline, workload, window, recovery, proofs, canary = _artifacts()

    result = evaluate_r0_9(
        manifest,
        phase7,
        baseline,
        workload,
        window,
        recovery,
        proofs[1:],
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_9_passed is False
    assert result.preexisting_evidence_preserved is False
    assert any("missing pre-saturation proof" in issue for issue in result.issues)
