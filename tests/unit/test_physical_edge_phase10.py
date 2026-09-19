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
from ets.qualification.physical_edge_phase9 import EdgeR0Phase9Evaluation
from ets.qualification.physical_edge_phase10 import (
    ClockFaultKind,
    ClockProofSubject,
    ClockSyncState,
    EdgeR0ClockBaseline,
    EdgeR0ClockFaultProfile,
    EdgeR0ClockFaultStep,
    EdgeR0ClockFaultWindow,
    EdgeR0ClockProofReceipt,
    EdgeR0ClockRecoveryCanary,
    EdgeR0ClockRestoration,
    EdgeR0ClockTransition,
    EdgeR0TimedEvidenceEvent,
    TimeQuality,
    build_timed_event_commitment,
    evaluate_r0_11,
)

_NOW = datetime(2026, 9, 19, 15, 0, tzinfo=UTC)


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
            source_revision="c5689a3a1eaf8bcaf180aa96f24b6efad796ef09",
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
        notes=("Synthetic W1-11 unit-test manifest.",),
    )


def _queue(
    *,
    depth: int = 0,
    bytes_used: int = 0,
    pending: int = 0,
) -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=depth,
        queue_bytes=bytes_used,
        pending=pending,
        in_flight=0,
        retryable_failure=0,
        terminal_failure=0,
        synchronized=50,
        max_items=10,
        max_bytes=10_000,
        oldest_pending_age_seconds=None if pending == 0 else 1.0,
        last_successful_sync=_NOW.isoformat(),
        last_failure=None,
        upstream_status="online",
    )


def _phase9(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase9Evaluation:
    return EdgeR0Phase9Evaluation(
        evaluation_id="edge-r0-phase9-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase8_evaluation_id="edge-r0-phase8-passed",
        baseline_id="network-baseline-001",
        profile_id="network-profile-001",
        window_id="network-window-001",
        reconciliation_id="network-reconciliation-001",
        evaluated_at=_NOW,
        intended_record_count=3,
        fault_profile_observed=True,
        observer_agreement_preserved=True,
        no_invented_remote_acknowledgement=True,
        local_authoritative_records_preserved=True,
        idempotent_reconciliation=True,
        checkpoints_non_regressing=True,
        queue_storage_boundaries_preserved=True,
        retry_resource_envelope_preserved=True,
        independent_verification_complete=True,
        final_backlog_clear=True,
        post_recovery_canary_valid=True,
        r0_10_passed=True,
        issues=(),
    )


def _artifacts():
    manifest = _manifest()
    phase9 = _phase9(manifest)
    baseline = EdgeR0ClockBaseline(
        baseline_id="clock-baseline-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase9_evaluation_id=phase9.evaluation_id,
        phase9_evaluation_sha256=canonical_sha256(phase9.model_dump(mode="json")),
        captured_at=_NOW + timedelta(seconds=1),
        boot_id="boot-001",
        wall_clock_utc=_NOW + timedelta(seconds=1),
        monotonic_ns=1_000_000_000,
        external_utc=_NOW + timedelta(seconds=1),
        sync_state=ClockSyncState.SYNCHRONIZED,
        time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
        local_checkpoint_index=500,
        local_checkpoint_sha256=_sha("clock-checkpoint-pre"),
        log_head_sha256=_sha("clock-log-head-pre"),
        queue_state=_queue(),
        queue_item_limit=10,
        queue_byte_limit=10_000,
        storage_used_bytes=40_000,
        storage_high_watermark_used_bytes=70_000,
        representative_proof_sha256=(_sha("clock-pre-proof"),),
        observer_receipt_sha256=_sha("clock-baseline-observer"),
    )
    steps = (
        EdgeR0ClockFaultStep(
            step_id="clock-step-1",
            sequence_number=1,
            kind=ClockFaultKind.FORWARD_JUMP,
            requested_offset_seconds=3600,
            max_duration_seconds=30,
            offset_tolerance_seconds=2,
            expected_sync_state=ClockSyncState.UNSYNCHRONIZED,
            expected_time_quality=TimeQuality.EXTERNALLY_BOUNDED_UNSYNCHRONIZED,
            controller_receipt_sha256=_sha("clock-step-1"),
        ),
        EdgeR0ClockFaultStep(
            step_id="clock-step-2",
            sequence_number=2,
            kind=ClockFaultKind.BACKWARD_ROLLBACK,
            requested_offset_seconds=-3600,
            max_duration_seconds=30,
            offset_tolerance_seconds=2,
            expected_sync_state=ClockSyncState.UNSYNCHRONIZED,
            expected_time_quality=TimeQuality.EXTERNALLY_BOUNDED_UNSYNCHRONIZED,
            controller_receipt_sha256=_sha("clock-step-2"),
        ),
        EdgeR0ClockFaultStep(
            step_id="clock-step-3",
            sequence_number=3,
            kind=ClockFaultKind.UNSYNCHRONIZED,
            requested_offset_seconds=0,
            max_duration_seconds=30,
            offset_tolerance_seconds=2,
            expected_sync_state=ClockSyncState.UNSYNCHRONIZED,
            expected_time_quality=TimeQuality.DEVICE_RELATIVE_UNTRUSTED,
            controller_receipt_sha256=_sha("clock-step-3"),
        ),
        EdgeR0ClockFaultStep(
            step_id="clock-step-4",
            sequence_number=4,
            kind=ClockFaultKind.RESTORE,
            requested_offset_seconds=0,
            max_duration_seconds=30,
            offset_tolerance_seconds=2,
            expected_sync_state=ClockSyncState.SYNCHRONIZED,
            expected_time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
            controller_receipt_sha256=_sha("clock-step-4"),
        ),
    )
    profile = EdgeR0ClockFaultProfile(
        profile_id="clock-profile-001",
        baseline_id=baseline.baseline_id,
        generated_at=_NOW + timedelta(seconds=2),
        max_total_duration_seconds=120,
        steps=steps,
        controller_definition_sha256=_sha("clock-controller-definition"),
        operator_stop_condition="stop on observer disagreement or prior-boundary escape",
    )

    transitions = []
    events = []
    offsets = (3600, -3600, 0, 0)
    qualities = (
        TimeQuality.EXTERNALLY_BOUNDED_UNSYNCHRONIZED,
        TimeQuality.EXTERNALLY_BOUNDED_UNSYNCHRONIZED,
        TimeQuality.DEVICE_RELATIVE_UNTRUSTED,
        TimeQuality.TRUSTED_SYNCHRONIZED,
    )
    sync_states = (
        ClockSyncState.UNSYNCHRONIZED,
        ClockSyncState.UNSYNCHRONIZED,
        ClockSyncState.UNSYNCHRONIZED,
        ClockSyncState.SYNCHRONIZED,
    )
    for index, step in enumerate(steps, start=1):
        external_time = _NOW + timedelta(seconds=3 * index)
        wall_time = external_time + timedelta(seconds=offsets[index - 1])
        monotonic = 1_000_000_000 + index * 1_000_000_000
        transitions.append(
            EdgeR0ClockTransition(
                transition_id=f"clock-transition-{index}",
                profile_id=profile.profile_id,
                step_id=step.step_id,
                sequence_number=index,
                commanded_at=external_time - timedelta(milliseconds=200),
                observed_at=external_time,
                dut_wall_clock_utc=wall_time,
                monotonic_ns=monotonic,
                external_utc=external_time,
                observed_sync_state=sync_states[index - 1],
                observed_time_quality=qualities[index - 1],
                queue_depth=0,
                queue_bytes=0,
                storage_used_bytes=40_000,
                network_connected=True,
                controller_receipt_sha256=_sha(f"clock-controller-{index}"),
                external_observer_receipt_sha256=_sha(f"clock-external-{index}"),
                dut_observation_sha256=_sha(f"clock-dut-{index}"),
            )
        )
        payload = _sha(f"clock-event-payload-{index}")
        events.append(
            EdgeR0TimedEvidenceEvent(
                event_id=f"clock-event-{index}",
                sequence_number=index,
                fault_step_id=step.step_id,
                captured_wall_clock_utc=wall_time + timedelta(milliseconds=100),
                monotonic_ns=monotonic + 100_000_000,
                external_utc=external_time + timedelta(milliseconds=100),
                sync_state=sync_states[index - 1],
                time_quality=qualities[index - 1],
                request_payload_sha256=payload,
                content_hash=payload,
                proof_artifact_sha256=_sha(f"clock-event-proof-{index}"),
                local_checkpoint_index=500 + index,
                log_head_sha256=_sha(f"clock-log-head-{index}"),
            )
        )

    event_tuple = tuple(events)
    window = EdgeR0ClockFaultWindow(
        window_id="clock-window-001",
        baseline_id=baseline.baseline_id,
        profile_id=profile.profile_id,
        started_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=13),
        transitions=tuple(transitions),
        events=event_tuple,
        event_commitment_sha256=build_timed_event_commitment(event_tuple),
        controller_timeline_sha256=_sha("clock-controller-timeline"),
    )
    restoration = EdgeR0ClockRestoration(
        restoration_id="clock-restoration-001",
        baseline_id=baseline.baseline_id,
        window_id=window.window_id,
        restored_at=_NOW + timedelta(seconds=15),
        wall_clock_utc=_NOW + timedelta(seconds=15),
        external_utc=_NOW + timedelta(seconds=15),
        monotonic_ns=6_000_000_000,
        sync_state=ClockSyncState.SYNCHRONIZED,
        time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
        restored_offset_tolerance_seconds=2,
        preserved_event_commitment_sha256=window.event_commitment_sha256,
        pre_fault_log_head_sha256=baseline.log_head_sha256,
        pre_fault_log_head_observed=True,
        final_checkpoint_index=504,
        final_checkpoint_sha256=_sha("clock-checkpoint-final"),
        final_queue_state=_queue(),
        storage_used_bytes=40_100,
        network_connected=True,
        observer_receipt_sha256=_sha("clock-restoration-observer"),
    )
    proofs = [
        EdgeR0ClockProofReceipt(
            receipt_id="clock-pre-proof-receipt",
            subject_kind=ClockProofSubject.PRE_FAULT,
            subject_id=_sha("clock-pre-proof"),
            proof_artifact_sha256=_sha("clock-pre-proof"),
            verified_at=restoration.restored_at + timedelta(seconds=1),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("clock-pre-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        )
    ]
    for index, event in enumerate(event_tuple, start=1):
        proofs.append(
            EdgeR0ClockProofReceipt(
                receipt_id=f"clock-event-proof-receipt-{index}",
                subject_kind=ClockProofSubject.FAULT_EVENT,
                subject_id=event.event_id,
                proof_artifact_sha256=event.proof_artifact_sha256,
                verified_at=restoration.restored_at + timedelta(seconds=index + 1),
                verifier_id="ets-verify-offline",
                verifier_host_id="bench-controller-001",
                verifier_build_sha256=_sha("verifier-build"),
                verification_result_sha256=_sha(f"clock-event-result-{index}"),
                inclusion_valid=True,
                independent_execution_context=True,
            )
        )
    canary_payload = _sha("clock-canary-payload")
    canary = EdgeR0ClockRecoveryCanary(
        canary_id="clock-canary-001",
        restoration_id=restoration.restoration_id,
        captured_at=restoration.restored_at + timedelta(minutes=1),
        request_payload_sha256=canary_payload,
        content_hash=canary_payload,
        event_id="clock-canary-event",
        time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
        proof_artifact_sha256=_sha("clock-canary-proof"),
        verified_at=restoration.restored_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("clock-canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return (
        manifest,
        phase9,
        baseline,
        profile,
        window,
        restoration,
        tuple(proofs),
        canary,
    )


def test_r0_11_passes_clock_fault_and_restoration() -> None:
    artifacts = _artifacts()

    result = evaluate_r0_11(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_11_passed is True
    assert result.issues == ()


def test_r0_11_fails_monotonic_regression() -> None:
    manifest, phase9, baseline, profile, window, restoration, proofs, canary = _artifacts()
    bad = window.events[2].model_copy(update={"monotonic_ns": 2_000_000_000})
    events = (*window.events[:2], bad, window.events[3])
    broken = window.model_copy(
        update={
            "events": events,
            "event_commitment_sha256": build_timed_event_commitment(events),
        }
    )

    result = evaluate_r0_11(
        manifest,
        phase9,
        baseline,
        profile,
        broken,
        restoration,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_11_passed is False
    assert result.monotonic_order_preserved is False
    assert any("event monotonic ordering regressed" in x for x in result.issues)


def test_r0_11_fails_time_quality_upgrade_during_unsync() -> None:
    manifest, phase9, baseline, profile, window, restoration, proofs, canary = _artifacts()
    bad = window.events[1].model_copy(
        update={"time_quality": TimeQuality.TRUSTED_SYNCHRONIZED}
    )
    events = (window.events[0], bad, *window.events[2:])
    broken = window.model_copy(
        update={
            "events": events,
            "event_commitment_sha256": build_timed_event_commitment(events),
        }
    )

    result = evaluate_r0_11(
        manifest,
        phase9,
        baseline,
        profile,
        broken,
        restoration,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_11_passed is False
    assert result.time_quality_preserved is False
    assert any("event time-quality mismatch" in x for x in result.issues)


def test_r0_11_fails_unobserved_requested_offset() -> None:
    manifest, phase9, baseline, profile, window, restoration, proofs, canary = _artifacts()
    transition = window.transitions[0]
    bad = transition.model_copy(
        update={"dut_wall_clock_utc": transition.external_utc + timedelta(seconds=1200)}
    )
    broken = window.model_copy(
        update={"transitions": (bad, *window.transitions[1:])}
    )

    result = evaluate_r0_11(
        manifest,
        phase9,
        baseline,
        profile,
        broken,
        restoration,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_11_passed is False
    assert result.wall_clock_offsets_observed is False
    assert any("requested wall-clock offset not observed" in x for x in result.issues)


def test_r0_11_fails_rewritten_event_commitment() -> None:
    manifest, phase9, baseline, profile, window, restoration, proofs, canary = _artifacts()
    broken_restoration = restoration.model_copy(
        update={"preserved_event_commitment_sha256": _sha("rewritten-events")}
    )

    result = evaluate_r0_11(
        manifest,
        phase9,
        baseline,
        profile,
        window,
        broken_restoration,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_11_passed is False
    assert result.prior_evidence_not_rewritten is False
    assert any("restoration rewrote" in x for x in result.issues)


def test_r0_11_fails_checkpoint_regression() -> None:
    manifest, phase9, baseline, profile, window, restoration, proofs, canary = _artifacts()
    bad = window.events[2].model_copy(update={"local_checkpoint_index": 500})
    events = (*window.events[:2], bad, window.events[3])
    broken = window.model_copy(
        update={
            "events": events,
            "event_commitment_sha256": build_timed_event_commitment(events),
        }
    )

    result = evaluate_r0_11(
        manifest,
        phase9,
        baseline,
        profile,
        broken,
        restoration,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_11_passed is False
    assert result.log_checkpoint_order_preserved is False
    assert any("event checkpoint regressed" in x for x in result.issues)


def test_r0_11_fails_prior_phase_boundary_crossing() -> None:
    manifest, phase9, baseline, profile, window, restoration, proofs, canary = _artifacts()
    bad = window.transitions[1].model_copy(
        update={"queue_depth": 11, "storage_used_bytes": 71_000}
    )
    transitions = (window.transitions[0], bad, *window.transitions[2:])
    broken = window.model_copy(update={"transitions": transitions})

    result = evaluate_r0_11(
        manifest,
        phase9,
        baseline,
        profile,
        broken,
        restoration,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_11_passed is False
    assert result.prior_phase_boundaries_preserved is False
    assert any("R0.9 queue boundary crossed" in x for x in result.issues)
    assert any("R0.8 storage boundary crossed" in x for x in result.issues)


def test_r0_11_fails_untrusted_post_recovery_canary() -> None:
    manifest, phase9, baseline, profile, window, restoration, proofs, canary = _artifacts()
    failed = canary.model_copy(
        update={"time_quality": TimeQuality.DEVICE_RELATIVE_UNTRUSTED}
    )

    result = evaluate_r0_11(
        manifest,
        phase9,
        baseline,
        profile,
        window,
        restoration,
        proofs,
        failed,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_11_passed is False
    assert result.post_recovery_canary_valid is False
    assert any("canary did not use restored trusted time quality" in x for x in result.issues)
