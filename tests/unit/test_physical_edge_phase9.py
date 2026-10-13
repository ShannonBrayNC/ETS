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
from ets.qualification.physical_edge_phase8 import EdgeR0Phase8Evaluation
from ets.qualification.physical_edge_phase9 import (
    EdgeR0InstabilityRecord,
    EdgeR0NetworkBaseline,
    EdgeR0NetworkFaultProfile,
    EdgeR0NetworkInstabilityWindow,
    EdgeR0NetworkProofReceipt,
    EdgeR0NetworkReconciliation,
    EdgeR0NetworkRecoveredRecord,
    EdgeR0NetworkRecoveryCanary,
    EdgeR0NetworkTransition,
    NetworkProofSubject,
    NetworkState,
    build_network_reconciliation_commitment,
    evaluate_r0_10,
)

_NOW = datetime(2026, 9, 19, 14, 30, tzinfo=UTC)


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
            source_revision="4f1cb06566eb6437f9e030b8ec5927f67701b4af",
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
        notes=("Synthetic W1-10 unit-test manifest.",),
    )


def _queue(
    *,
    depth: int = 0,
    bytes_used: int = 0,
    pending: int = 0,
    synchronized: int = 40,
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


def _phase8(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase8Evaluation:
    return EdgeR0Phase8Evaluation(
        evaluation_id="edge-r0-phase8-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase7_evaluation_id="edge-r0-phase7-passed",
        baseline_id="queue-baseline-001",
        workload_id="queue-workload-001",
        window_id="queue-window-001",
        recovery_id="queue-recovery-001",
        evaluated_at=_NOW,
        attempted_count=4,
        accepted_count=3,
        rejected_count=1,
        queue_bounds_enforced=True,
        explicit_backpressure_observed=True,
        storage_boundary_not_crossed=True,
        resource_growth_bounded=True,
        attempt_reconciliation_complete=True,
        accepted_records_preserved=True,
        preexisting_evidence_preserved=True,
        history_not_rewritten=True,
        final_queue_clean=True,
        post_recovery_canary_valid=True,
        r0_9_passed=True,
        issues=(),
    )


def _transition(
    *,
    profile_id: str,
    sequence: int,
    cycle: int,
    state: NetworkState,
    second: int,
    edge_state: NetworkState | None = None,
    external_state: NetworkState | None = None,
    queue_depth: int = 2,
    queue_bytes: int = 200,
    storage_used_bytes: int = 40_000,
    rss_bytes: int = 130 * 1024 * 1024,
    retries: int = 4,
) -> EdgeR0NetworkTransition:
    return EdgeR0NetworkTransition(
        transition_id=f"transition-{sequence}",
        profile_id=profile_id,
        sequence_number=sequence,
        cycle_number=cycle,
        commanded_state=state,
        commanded_at=_NOW + timedelta(seconds=second),
        externally_observed_state=external_state or state,
        externally_observed_at=_NOW + timedelta(seconds=second, milliseconds=100),
        edge_reported_state=edge_state or state,
        edge_reported_at=_NOW + timedelta(seconds=second, milliseconds=200),
        added_latency_ms=100 if state is NetworkState.CONNECTED else 0,
        jitter_ms=20 if state is NetworkState.CONNECTED else 0,
        packet_loss_percent=5 if state is NetworkState.CONNECTED else 100,
        queue_depth=queue_depth,
        queue_bytes=queue_bytes,
        storage_used_bytes=storage_used_bytes,
        rss_bytes=rss_bytes,
        retry_attempts_last_minute=retries,
        controller_receipt_sha256=_sha(f"controller-{sequence}"),
        external_observer_receipt_sha256=_sha(f"observer-{sequence}"),
        edge_observation_sha256=_sha(f"edge-{sequence}"),
    )


def _artifacts():
    manifest = _manifest()
    phase8 = _phase8(manifest)
    baseline = EdgeR0NetworkBaseline(
        baseline_id="network-baseline-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase8_evaluation_id=phase8.evaluation_id,
        phase8_evaluation_sha256=canonical_sha256(phase8.model_dump(mode="json")),
        captured_at=_NOW + timedelta(seconds=1),
        interface_name="enp1s0",
        interface_mac="02:00:00:00:00:01",
        upstream_target="https://gateway.example.test",
        local_checkpoint_index=400,
        local_checkpoint_sha256=_sha("network-local-pre"),
        upstream_checkpoint_index=200,
        upstream_checkpoint_sha256=_sha("network-upstream-pre"),
        queue_state=_queue(),
        queue_item_limit=10,
        queue_byte_limit=10_000,
        storage_used_bytes=40_000,
        storage_high_watermark_used_bytes=70_000,
        baseline_rss_bytes=128 * 1024 * 1024,
        reachability_rtt_ms=15.0,
        representative_proof_sha256=(_sha("network-pre-proof"),),
        observer_receipt_sha256=_sha("network-baseline-observer"),
    )
    profile = EdgeR0NetworkFaultProfile(
        profile_id="network-profile-001",
        baseline_id=baseline.baseline_id,
        generated_at=_NOW + timedelta(seconds=2),
        disconnect_cycle_count=2,
        max_disconnect_seconds=5.0,
        max_added_latency_ms=250.0,
        max_jitter_ms=50.0,
        max_packet_loss_percent=100.0,
        max_total_duration_seconds=30.0,
        max_retry_attempts_per_minute=20,
        max_rss_growth_bytes=128 * 1024 * 1024,
        controller_definition_sha256=_sha("network-controller"),
        operator_stop_condition="stop on queue/storage/resource boundary or observer fault",
    )
    transitions = (
        _transition(
            profile_id=profile.profile_id,
            sequence=1,
            cycle=1,
            state=NetworkState.DISCONNECTED,
            second=3,
        ),
        _transition(
            profile_id=profile.profile_id,
            sequence=2,
            cycle=1,
            state=NetworkState.CONNECTED,
            second=6,
        ),
        _transition(
            profile_id=profile.profile_id,
            sequence=3,
            cycle=2,
            state=NetworkState.DISCONNECTED,
            second=9,
        ),
        _transition(
            profile_id=profile.profile_id,
            sequence=4,
            cycle=2,
            state=NetworkState.CONNECTED,
            second=12,
        ),
    )
    records = (
        EdgeR0InstabilityRecord(
            record_id="network-record-1",
            sequence_number=1,
            event_id="network-event-1",
            idempotency_key="network-idem-1",
            captured_at=_NOW + timedelta(seconds=4),
            request_payload_sha256=_sha("network-payload-1"),
            content_hash=_sha("network-payload-1"),
            local_proof_sha256=_sha("network-local-proof-1"),
            sync_attempted=True,
            network_state_at_sync_attempt=NetworkState.DISCONNECTED,
            upstream_accepted_during_window=False,
            local_ack_applied_during_window=False,
        ),
        EdgeR0InstabilityRecord(
            record_id="network-record-2",
            sequence_number=2,
            event_id="network-event-2",
            idempotency_key="network-idem-2",
            captured_at=_NOW + timedelta(seconds=7),
            request_payload_sha256=_sha("network-payload-2"),
            content_hash=_sha("network-payload-2"),
            local_proof_sha256=_sha("network-local-proof-2"),
            sync_attempted=True,
            network_state_at_sync_attempt=NetworkState.CONNECTED,
            upstream_accepted_during_window=True,
            upstream_acceptance_sha256=_sha("network-accept-2"),
            local_ack_applied_during_window=True,
        ),
        EdgeR0InstabilityRecord(
            record_id="network-record-3",
            sequence_number=3,
            event_id="network-event-3",
            idempotency_key="network-idem-3",
            captured_at=_NOW + timedelta(seconds=10),
            request_payload_sha256=_sha("network-payload-3"),
            content_hash=_sha("network-payload-3"),
            local_proof_sha256=_sha("network-local-proof-3"),
            sync_attempted=True,
            network_state_at_sync_attempt=NetworkState.DISCONNECTED,
            upstream_accepted_during_window=False,
            local_ack_applied_during_window=False,
        ),
    )
    window = EdgeR0NetworkInstabilityWindow(
        window_id="network-window-001",
        baseline_id=baseline.baseline_id,
        profile_id=profile.profile_id,
        started_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=13),
        transitions=transitions,
        records=records,
        controller_timeline_sha256=_sha("network-timeline"),
    )
    recovered_records = tuple(
        EdgeR0NetworkRecoveredRecord(
            record_id=record.record_id,
            event_id=record.event_id,
            idempotency_key=record.idempotency_key,
            authoritative_local_present=True,
            final_upstream_commit_count=1,
            final_upstream_event_id=record.event_id,
            final_upstream_acceptance_sha256=_sha(f"final-accept-{record.record_id}"),
            final_proof_sha256=_sha(f"final-proof-{record.record_id}"),
            local_marked_synchronized=True,
            recovery_observation_sha256=_sha(f"recover-{record.record_id}"),
        )
        for record in records
    )
    reconciliation = EdgeR0NetworkReconciliation(
        reconciliation_id="network-reconciliation-001",
        baseline_id=baseline.baseline_id,
        window_id=window.window_id,
        recovered_at=_NOW + timedelta(seconds=16),
        local_checkpoint_index=403,
        local_checkpoint_sha256=_sha("network-local-final"),
        upstream_checkpoint_index=203,
        upstream_checkpoint_sha256=_sha("network-upstream-final"),
        final_queue_state=_queue(synchronized=43),
        storage_used_bytes=40_500,
        rss_bytes=129 * 1024 * 1024,
        max_retry_attempts_per_minute_observed=6,
        records=recovered_records,
        reconciliation_commitment_sha256=build_network_reconciliation_commitment(
            recovered_records
        ),
    )
    proofs = [
        EdgeR0NetworkProofReceipt(
            receipt_id="network-pre-proof-receipt",
            subject_kind=NetworkProofSubject.PRE_INSTABILITY,
            subject_id=_sha("network-pre-proof"),
            proof_artifact_sha256=_sha("network-pre-proof"),
            verified_at=reconciliation.recovered_at + timedelta(seconds=1),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("network-pre-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        )
    ]
    for index, record in enumerate(recovered_records, start=1):
        proofs.append(
            EdgeR0NetworkProofReceipt(
                receipt_id=f"network-record-proof-{index}",
                subject_kind=NetworkProofSubject.INSTABILITY_RECORD,
                subject_id=record.record_id,
                proof_artifact_sha256=record.final_proof_sha256 or _sha("missing"),
                verified_at=reconciliation.recovered_at + timedelta(seconds=index + 1),
                verifier_id="ets-verify-offline",
                verifier_host_id="bench-controller-001",
                verifier_build_sha256=_sha("verifier-build"),
                verification_result_sha256=_sha(f"network-record-result-{index}"),
                inclusion_valid=True,
                independent_execution_context=True,
            )
        )
    canary_payload = _sha("network-canary-payload")
    canary = EdgeR0NetworkRecoveryCanary(
        canary_id="network-canary-001",
        reconciliation_id=reconciliation.reconciliation_id,
        captured_at=reconciliation.recovered_at + timedelta(minutes=1),
        request_payload_sha256=canary_payload,
        content_hash=canary_payload,
        event_id="network-canary-event",
        proof_artifact_sha256=_sha("network-canary-proof"),
        verified_at=reconciliation.recovered_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("network-canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return (
        manifest,
        phase8,
        baseline,
        profile,
        window,
        reconciliation,
        tuple(proofs),
        canary,
    )


def test_r0_10_passes_repeated_network_instability() -> None:
    artifacts = _artifacts()

    result = evaluate_r0_10(*artifacts, evaluated_at=_NOW + timedelta(minutes=3))

    assert result.r0_10_passed is True
    assert result.intended_record_count == 3
    assert result.issues == ()


def test_r0_10_fails_controller_observer_contradiction() -> None:
    manifest, phase8, baseline, profile, window, recovery, proofs, canary = _artifacts()
    bad = window.transitions[0].model_copy(
        update={"externally_observed_state": NetworkState.CONNECTED}
    )
    broken_window = window.model_copy(
        update={"transitions": (bad, *window.transitions[1:])}
    )

    result = evaluate_r0_10(
        manifest,
        phase8,
        baseline,
        profile,
        broken_window,
        recovery,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_10_passed is False
    assert result.observer_agreement_preserved is False
    assert any("controller/external observer contradiction" in x for x in result.issues)


def test_r0_10_fails_invented_ack_while_disconnected() -> None:
    manifest, phase8, baseline, profile, window, recovery, proofs, canary = _artifacts()
    bad = window.records[0].model_copy(
        update={
            "upstream_accepted_during_window": True,
            "upstream_acceptance_sha256": _sha("invented-accept"),
            "local_ack_applied_during_window": True,
        }
    )
    broken_window = window.model_copy(update={"records": (bad, *window.records[1:])})

    result = evaluate_r0_10(
        manifest,
        phase8,
        baseline,
        profile,
        broken_window,
        recovery,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_10_passed is False
    assert result.no_invented_remote_acknowledgement is False
    assert any("acknowledgement claimed while disconnected" in x for x in result.issues)


def test_r0_10_fails_lost_local_authoritative_record() -> None:
    manifest, phase8, baseline, profile, window, recovery, proofs, canary = _artifacts()
    lost = recovery.records[0].model_copy(update={"authoritative_local_present": False})
    records = (lost, *recovery.records[1:])
    broken = recovery.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": (
                build_network_reconciliation_commitment(records)
            ),
        }
    )

    result = evaluate_r0_10(
        manifest,
        phase8,
        baseline,
        profile,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_10_passed is False
    assert result.local_authoritative_records_preserved is False
    assert any("local authoritative record disappeared" in x for x in result.issues)


def test_r0_10_fails_logical_duplicate_after_reconnect() -> None:
    manifest, phase8, baseline, profile, window, recovery, proofs, canary = _artifacts()
    duplicate = recovery.records[0].model_copy(update={"final_upstream_commit_count": 2})
    records = (duplicate, *recovery.records[1:])
    broken = recovery.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": (
                build_network_reconciliation_commitment(records)
            ),
        }
    )

    result = evaluate_r0_10(
        manifest,
        phase8,
        baseline,
        profile,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_10_passed is False
    assert result.idempotent_reconciliation is False
    assert any("expected one final logical upstream commit" in x for x in result.issues)


def test_r0_10_fails_checkpoint_regression() -> None:
    manifest, phase8, baseline, profile, window, recovery, proofs, canary = _artifacts()
    broken = recovery.model_copy(update={"upstream_checkpoint_index": 199})

    result = evaluate_r0_10(
        manifest,
        phase8,
        baseline,
        profile,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_10_passed is False
    assert result.checkpoints_non_regressing is False
    assert any("upstream checkpoint regressed" in x for x in result.issues)


def test_r0_10_fails_retry_resource_escape() -> None:
    manifest, phase8, baseline, profile, window, recovery, proofs, canary = _artifacts()
    bad = window.transitions[2].model_copy(update={"retry_attempts_last_minute": 21})
    transitions = (*window.transitions[:2], bad, window.transitions[3])
    broken_window = window.model_copy(update={"transitions": transitions})

    result = evaluate_r0_10(
        manifest,
        phase8,
        baseline,
        profile,
        broken_window,
        recovery,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_10_passed is False
    assert result.retry_resource_envelope_preserved is False
    assert any("retry-rate envelope exceeded" in x for x in result.issues)


def test_r0_10_fails_queue_or_storage_cross_boundary() -> None:
    manifest, phase8, baseline, profile, window, recovery, proofs, canary = _artifacts()
    bad = window.transitions[1].model_copy(
        update={"queue_depth": 11, "storage_used_bytes": 71_000}
    )
    transitions = (window.transitions[0], bad, *window.transitions[2:])
    broken_window = window.model_copy(update={"transitions": transitions})

    result = evaluate_r0_10(
        manifest,
        phase8,
        baseline,
        profile,
        broken_window,
        recovery,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_10_passed is False
    assert result.queue_storage_boundaries_preserved is False
    assert any("R0.9 queue boundary crossed" in x for x in result.issues)
    assert any("R0.8 storage boundary crossed" in x for x in result.issues)


def test_r0_10_fails_unresolved_final_backlog() -> None:
    manifest, phase8, baseline, profile, window, recovery, proofs, canary = _artifacts()
    dirty = _queue(depth=1, bytes_used=100, pending=1, synchronized=42)
    broken = recovery.model_copy(update={"final_queue_state": dirty})

    result = evaluate_r0_10(
        manifest,
        phase8,
        baseline,
        profile,
        window,
        broken,
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_10_passed is False
    assert result.final_backlog_clear is False
    assert any("final synchronization backlog is not clean" in x for x in result.issues)


def test_r0_10_fails_post_recovery_canary() -> None:
    manifest, phase8, baseline, profile, window, recovery, proofs, canary = _artifacts()
    failed_canary = canary.model_copy(update={"inclusion_valid": False})

    result = evaluate_r0_10(
        manifest,
        phase8,
        baseline,
        profile,
        window,
        recovery,
        proofs,
        failed_canary,
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert result.r0_10_passed is False
    assert result.post_recovery_canary_valid is False
    assert any("canary did not independently verify" in x for x in result.issues)
