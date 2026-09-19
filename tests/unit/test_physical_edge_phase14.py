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
from ets.qualification.physical_edge_phase13 import EdgeR0Phase13Evaluation
from ets.qualification.physical_edge_phase14 import (
    EdgeR0Phase14Evaluation,
    EdgeR0SoakAttempt,
    EdgeR0SoakBaseline,
    EdgeR0SoakCanary,
    EdgeR0SoakFinalRecord,
    EdgeR0SoakProfile,
    EdgeR0SoakProofReceipt,
    EdgeR0SoakReconciliation,
    EdgeR0SoakSample,
    EdgeR0SoakWindow,
    SoakDisposition,
    SoakProofSubject,
    build_soak_reconciliation_commitment,
    build_soak_workload_commitment,
    evaluate_r0_15,
)

_NOW = datetime(2026, 9, 19, 19, 0, tzinfo=UTC)
_BUILD = "1f06212705db2f3b35eb613b240ee4d0c5d85c43"


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
            source_revision=_BUILD,
            artifact_digest=_sha("soak-artifact"),
            configuration_digest=_sha("soak-config"),
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
        notes=("Synthetic W1-15 unit-test manifest.",),
    )


def _queue(
    *,
    depth: int = 0,
    bytes_used: int = 0,
    pending: int = 0,
    synchronized: int = 90,
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


def _phase13(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase13Evaluation:
    return EdgeR0Phase13Evaluation(
        evaluation_id="edge-r0-phase13-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase12_evaluation_id="edge-r0-phase12-passed",
        baseline_id="recovery-baseline-001",
        media_id="recovery-media-001",
        rebuild_id="rebuild-001",
        identity_recovery_id="identity-recovery-001",
        reattachment_id="reattachment-001",
        evaluated_at=_NOW,
        media_provenance_valid=True,
        rebuild_target_valid=True,
        rebuilt_software_valid=True,
        identity_recovery_valid=True,
        trust_posture_preserved=True,
        historical_evidence_preserved=True,
        upstream_reattachment_valid=True,
        checkpoints_consistent=True,
        no_logical_replay_or_invented_ack=True,
        prior_phase_boundaries_preserved=True,
        independent_verification_complete=True,
        post_rebuild_canary_valid=True,
        r0_14_passed=True,
        issues=(),
    )


def _attempt(
    *,
    sequence: int,
    second: int,
    disposition: SoakDisposition,
) -> EdgeR0SoakAttempt:
    accepted = disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED
    rejected = disposition is SoakDisposition.REJECTED_BACKPRESSURE
    return EdgeR0SoakAttempt(
        attempt_id=f"soak-attempt-{sequence}",
        sequence_number=sequence,
        attempted_at=_NOW + timedelta(seconds=second),
        event_id=f"soak-event-{sequence}",
        idempotency_key=f"soak-idem-{sequence}",
        payload_bytes=100,
        request_payload_sha256=_sha(f"soak-payload-{sequence}"),
        disposition=disposition,
        local_authoritative_commit=accepted,
        local_proof_sha256=_sha(f"soak-local-proof-{sequence}") if accepted else None,
        explicit_backpressure_signal=rejected,
    )


def _sample(
    *,
    sequence: int,
    second: int,
    attempted: int,
    accepted: int,
    rejected: int,
    cumulative_attempted: int,
    cumulative_accepted: int,
    cumulative_rejected: int,
    local_checkpoint: int,
    upstream_checkpoint: int,
    synchronized: int,
) -> EdgeR0SoakSample:
    return EdgeR0SoakSample(
        sample_id=f"soak-sample-{sequence}",
        sequence_number=sequence,
        observed_at=_NOW + timedelta(seconds=second),
        elapsed_monotonic_seconds=float(second),
        attempted_since_prior=attempted,
        accepted_since_prior=accepted,
        rejected_since_prior=rejected,
        unacknowledged_since_prior=0,
        cumulative_attempted=cumulative_attempted,
        cumulative_accepted=cumulative_accepted,
        cumulative_rejected=cumulative_rejected,
        cumulative_unacknowledged=0,
        cumulative_authoritative_commits=cumulative_accepted,
        cumulative_synchronized=synchronized,
        queue_state=_queue(synchronized=synchronized),
        local_checkpoint_index=local_checkpoint,
        local_checkpoint_sha256=_sha(f"soak-local-cp-{sequence}"),
        upstream_checkpoint_index=upstream_checkpoint,
        upstream_checkpoint_sha256=_sha(f"soak-upstream-cp-{sequence}"),
        storage_used_bytes=40_000 + (sequence * 300),
        storage_free_bytes=100_000 - (sequence * 300),
        process_rss_bytes=(128 + sequence) * 1024 * 1024,
        cpu_percent=15.0 + sequence,
        host_load_1m=0.5 + (sequence / 10),
        temperature_c=55.0 + sequence,
        retry_attempts_last_minute=2,
        network_connected=True,
        time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
        service_healthy=True,
        service_restart_count=0,
        build_sha=_BUILD,
        configuration_digest=_sha("soak-config"),
        device_identity_id="edge-r0-device-identity",
        signing_key_id="edge-r0-software-key",
        identity_profile="software_volume",
        hardware_attested=False,
        secure_boot_verified=False,
        hardware_key_protection=False,
        observer_receipt_sha256=_sha(f"soak-sample-observer-{sequence}"),
    )


def _artifacts() -> tuple[
    EdgeCompactR0BenchManifest,
    EdgeR0Phase13Evaluation,
    EdgeR0SoakBaseline,
    EdgeR0SoakProfile,
    EdgeR0SoakWindow,
    EdgeR0SoakReconciliation,
    tuple[EdgeR0SoakProofReceipt, ...],
    EdgeR0SoakCanary,
]:
    manifest = _manifest()
    phase13 = _phase13(manifest)
    baseline = EdgeR0SoakBaseline(
        baseline_id="soak-baseline-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase13_evaluation_id=phase13.evaluation_id,
        phase13_evaluation_sha256=canonical_sha256(phase13.model_dump(mode="json")),
        captured_at=_NOW - timedelta(seconds=1),
        build_sha=_BUILD,
        artifact_digest=_sha("soak-artifact"),
        configuration_digest=_sha("soak-config"),
        runtime_id="ubuntu-24.04-x86_64",
        device_identity_id="edge-r0-device-identity",
        signing_key_id="edge-r0-software-key",
        local_checkpoint_index=900,
        local_checkpoint_sha256=_sha("soak-local-baseline"),
        upstream_checkpoint_index=450,
        upstream_checkpoint_sha256=_sha("soak-upstream-baseline"),
        log_head_sha256=_sha("soak-log-head"),
        historical_record_commitment_sha256=_sha("soak-history"),
        queue_state=_queue(),
        storage_used_bytes=40_000,
        storage_free_bytes=100_000,
        storage_high_watermark_used_bytes=70_000,
        process_rss_bytes=128 * 1024 * 1024,
        cpu_percent=10.0,
        host_load_1m=0.4,
        temperature_c=54.0,
        reachability_rtt_ms=12.0,
        representative_proof_sha256=(_sha("soak-pre-proof"),),
        observer_receipt_sha256=_sha("soak-baseline-observer"),
    )
    profile = EdgeR0SoakProfile(
        profile_id="soak-profile-001",
        baseline_id=baseline.baseline_id,
        frozen_at=_NOW - timedelta(milliseconds=500),
        planned_duration_seconds=60.0,
        sample_interval_seconds=20.0,
        max_sample_gap_seconds=25.0,
        max_event_count=10,
        max_payload_bytes=2_000,
        max_event_rate_per_second=1.0,
        max_storage_growth_bytes=5_000,
        max_queue_items=10,
        max_queue_bytes=10_000,
        max_rss_growth_bytes=64 * 1024 * 1024,
        max_retry_attempts_per_minute=10,
        max_service_restarts=0,
        max_temperature_c=80.0,
        workload_definition_sha256=_sha("soak-workload-definition"),
        controller_definition_sha256=_sha("soak-controller-definition"),
        operator_stop_condition="stop on evidence, resource, thermal, or service alarm",
    )
    attempts = (
        _attempt(
            sequence=1,
            second=5,
            disposition=SoakDisposition.AUTHORITATIVE_ACCEPTED,
        ),
        _attempt(
            sequence=2,
            second=15,
            disposition=SoakDisposition.AUTHORITATIVE_ACCEPTED,
        ),
        _attempt(
            sequence=3,
            second=35,
            disposition=SoakDisposition.REJECTED_BACKPRESSURE,
        ),
        _attempt(
            sequence=4,
            second=50,
            disposition=SoakDisposition.AUTHORITATIVE_ACCEPTED,
        ),
    )
    samples = (
        _sample(
            sequence=1,
            second=0,
            attempted=0,
            accepted=0,
            rejected=0,
            cumulative_attempted=0,
            cumulative_accepted=0,
            cumulative_rejected=0,
            local_checkpoint=900,
            upstream_checkpoint=450,
            synchronized=90,
        ),
        _sample(
            sequence=2,
            second=20,
            attempted=2,
            accepted=2,
            rejected=0,
            cumulative_attempted=2,
            cumulative_accepted=2,
            cumulative_rejected=0,
            local_checkpoint=902,
            upstream_checkpoint=452,
            synchronized=92,
        ),
        _sample(
            sequence=3,
            second=40,
            attempted=1,
            accepted=0,
            rejected=1,
            cumulative_attempted=3,
            cumulative_accepted=2,
            cumulative_rejected=1,
            local_checkpoint=902,
            upstream_checkpoint=452,
            synchronized=92,
        ),
        _sample(
            sequence=4,
            second=60,
            attempted=1,
            accepted=1,
            rejected=0,
            cumulative_attempted=4,
            cumulative_accepted=3,
            cumulative_rejected=1,
            local_checkpoint=903,
            upstream_checkpoint=453,
            synchronized=93,
        ),
    )
    window = EdgeR0SoakWindow(
        window_id="soak-window-001",
        baseline_id=baseline.baseline_id,
        profile_id=profile.profile_id,
        started_at=_NOW,
        completed_at=_NOW + timedelta(seconds=60),
        attempts=attempts,
        samples=samples,
        workload_commitment_sha256=build_soak_workload_commitment(attempts),
        observer_timeline_sha256=_sha("soak-observer-timeline"),
    )
    final_records = tuple(
        EdgeR0SoakFinalRecord(
            attempt_id=attempt.attempt_id,
            event_id=attempt.event_id,
            idempotency_key=attempt.idempotency_key,
            final_disposition=attempt.disposition,
            authoritative_local_present=(
                attempt.disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED
            ),
            final_upstream_commit_count=(
                1
                if attempt.disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED
                else 0
            ),
            final_upstream_event_id=(
                attempt.event_id
                if attempt.disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED
                else None
            ),
            final_upstream_acceptance_sha256=(
                _sha(f"soak-final-accept-{attempt.attempt_id}")
                if attempt.disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED
                else None
            ),
            final_proof_sha256=(
                _sha(f"soak-final-proof-{attempt.attempt_id}")
                if attempt.disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED
                else None
            ),
            local_marked_synchronized=(
                attempt.disposition is SoakDisposition.AUTHORITATIVE_ACCEPTED
            ),
            replayed_or_duplicated=False,
            final_observation_sha256=_sha(f"soak-final-observation-{attempt.attempt_id}"),
        )
        for attempt in attempts
    )
    reconciliation = EdgeR0SoakReconciliation(
        reconciliation_id="soak-reconciliation-001",
        window_id=window.window_id,
        reconciled_at=window.completed_at + timedelta(seconds=2),
        actual_duration_seconds=60.0,
        records=final_records,
        final_local_checkpoint_index=903,
        final_local_checkpoint_sha256=_sha("soak-local-final"),
        final_upstream_checkpoint_index=453,
        final_upstream_checkpoint_sha256=_sha("soak-upstream-final"),
        preserved_log_head_observed=True,
        preserved_pre_soak_log_head_sha256=baseline.log_head_sha256,
        preserved_historical_record_commitment_sha256=(
            baseline.historical_record_commitment_sha256
        ),
        final_queue_state=_queue(synchronized=93),
        final_storage_used_bytes=42_000,
        final_storage_free_bytes=98_000,
        final_process_rss_bytes=132 * 1024 * 1024,
        final_network_connected=True,
        final_time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
        final_service_healthy=True,
        final_build_sha=baseline.build_sha,
        final_configuration_digest=baseline.configuration_digest,
        final_device_identity_id=baseline.device_identity_id,
        final_signing_key_id=baseline.signing_key_id,
        final_identity_profile=baseline.identity_profile,
        final_hardware_attested=False,
        final_secure_boot_verified=False,
        final_hardware_key_protection=False,
        reconciliation_commitment_sha256=build_soak_reconciliation_commitment(
            final_records
        ),
        observer_receipt_sha256=_sha("soak-reconciliation-observer"),
    )
    proofs = [
        EdgeR0SoakProofReceipt(
            receipt_id="soak-pre-proof-receipt",
            subject_kind=SoakProofSubject.PRE_SOAK,
            subject_id=_sha("soak-pre-proof"),
            proof_artifact_sha256=_sha("soak-pre-proof"),
            verified_at=_NOW + timedelta(seconds=10),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("soak-pre-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        )
    ]
    for index, record in enumerate(final_records, start=1):
        if record.final_disposition is not SoakDisposition.AUTHORITATIVE_ACCEPTED:
            continue
        proofs.append(
            EdgeR0SoakProofReceipt(
                receipt_id=f"soak-record-proof-{index}",
                subject_kind=SoakProofSubject.SOAK_RECORD,
                subject_id=record.attempt_id,
                proof_artifact_sha256=record.final_proof_sha256 or _sha("missing"),
                verified_at=_NOW + timedelta(seconds=15 * index),
                verifier_id="ets-verify-offline",
                verifier_host_id="bench-controller-001",
                verifier_build_sha256=_sha("verifier-build"),
                verification_result_sha256=_sha(f"soak-record-result-{index}"),
                inclusion_valid=True,
                independent_execution_context=True,
            )
        )
    canary_payload = _sha("soak-canary-payload")
    canary = EdgeR0SoakCanary(
        canary_id="soak-canary-001",
        reconciliation_id=reconciliation.reconciliation_id,
        captured_at=reconciliation.reconciled_at + timedelta(minutes=1),
        build_sha=baseline.build_sha,
        configuration_digest=baseline.configuration_digest,
        device_identity_id=baseline.device_identity_id,
        request_payload_sha256=canary_payload,
        content_hash=canary_payload,
        event_id="soak-canary-event",
        proof_artifact_sha256=_sha("soak-canary-proof"),
        synchronized=True,
        verified_at=reconciliation.reconciled_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("soak-canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return (
        manifest,
        phase13,
        baseline,
        profile,
        window,
        reconciliation,
        tuple(proofs),
        canary,
    )


def _evaluate(
    artifacts: tuple[
        EdgeCompactR0BenchManifest,
        EdgeR0Phase13Evaluation,
        EdgeR0SoakBaseline,
        EdgeR0SoakProfile,
        EdgeR0SoakWindow,
        EdgeR0SoakReconciliation,
        tuple[EdgeR0SoakProofReceipt, ...],
        EdgeR0SoakCanary,
    ],
) -> EdgeR0Phase14Evaluation:
    return evaluate_r0_15(
        *artifacts,
        evaluated_at=_NOW + timedelta(minutes=5),
    )


def test_r0_15_passes_bounded_endurance_soak() -> None:
    result = _evaluate(_artifacts())

    assert result.r0_15_passed is True
    assert result.issues == ()


def test_r0_15_fails_excessive_sample_gap() -> None:
    artifacts = list(_artifacts())
    window = artifacts[4]
    sample = window.samples[2].model_copy(
        update={
            "observed_at": _NOW + timedelta(seconds=50),
            "elapsed_monotonic_seconds": 50.0,
        }
    )
    artifacts[4] = window.model_copy(
        update={"samples": (*window.samples[:2], sample, window.samples[3])}
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.sampling_continuity_valid is False
    assert any("sample gap" in issue for issue in result.issues)


def test_r0_15_fails_silent_accepted_record_loss() -> None:
    artifacts = list(_artifacts())
    reconciliation = artifacts[5]
    lost = reconciliation.records[0].model_copy(
        update={"authoritative_local_present": False}
    )
    records = (lost, *reconciliation.records[1:])
    artifacts[5] = reconciliation.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": (
                build_soak_reconciliation_commitment(records)
            ),
        }
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.accepted_records_preserved is False
    assert any("accepted record lost locally" in issue for issue in result.issues)


def test_r0_15_fails_logical_duplication() -> None:
    artifacts = list(_artifacts())
    reconciliation = artifacts[5]
    duplicate = reconciliation.records[1].model_copy(
        update={"replayed_or_duplicated": True}
    )
    records = (
        reconciliation.records[0],
        duplicate,
        *reconciliation.records[2:],
    )
    artifacts[5] = reconciliation.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": (
                build_soak_reconciliation_commitment(records)
            ),
        }
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.no_logical_duplication_or_promotion is False
    assert any("logical replay/duplication" in issue for issue in result.issues)


def test_r0_15_fails_checkpoint_regression() -> None:
    artifacts = list(_artifacts())
    window = artifacts[4]
    sample = window.samples[2].model_copy(update={"local_checkpoint_index": 899})
    artifacts[4] = window.model_copy(
        update={"samples": (*window.samples[:2], sample, window.samples[3])}
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.checkpoints_monotonic is False
    assert any("local checkpoint regressed" in issue for issue in result.issues)


def test_r0_15_fails_storage_and_queue_escape() -> None:
    artifacts = list(_artifacts())
    window = artifacts[4]
    overloaded_queue = _queue(depth=11, bytes_used=11_000, pending=11)
    sample = window.samples[2].model_copy(
        update={
            "queue_state": overloaded_queue,
            "storage_used_bytes": 71_000,
        }
    )
    artifacts[4] = window.model_copy(
        update={"samples": (*window.samples[:2], sample, window.samples[3])}
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.resource_envelope_preserved is False
    assert any("queue envelope exceeded" in issue for issue in result.issues)
    assert any("R0.8 storage boundary crossed" in issue for issue in result.issues)


def test_r0_15_fails_resource_growth_escape() -> None:
    artifacts = list(_artifacts())
    window = artifacts[4]
    sample = window.samples[1].model_copy(
        update={"process_rss_bytes": 300 * 1024 * 1024}
    )
    artifacts[4] = window.model_copy(
        update={"samples": (window.samples[0], sample, *window.samples[2:])}
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.resource_envelope_preserved is False
    assert any("RSS envelope exceeded" in issue for issue in result.issues)


def test_r0_15_fails_identity_trust_drift() -> None:
    artifacts = list(_artifacts())
    window = artifacts[4]
    sample = window.samples[3].model_copy(
        update={"device_identity_id": "unexpected-soak-identity"}
    )
    artifacts[4] = window.model_copy(
        update={"samples": (*window.samples[:3], sample)}
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.identity_trust_state_preserved is False
    assert any("identity/trust/software drift" in issue for issue in result.issues)


def test_r0_15_fails_history_rewrite() -> None:
    artifacts = list(_artifacts())
    artifacts[5] = artifacts[5].model_copy(
        update={
            "preserved_historical_record_commitment_sha256": _sha("rewritten-history")
        }
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.history_preserved is False
    assert any("historical record commitment changed" in issue for issue in result.issues)


def test_r0_15_fails_final_backlog() -> None:
    artifacts = list(_artifacts())
    dirty = _queue(depth=1, bytes_used=100, pending=1, synchronized=92)
    artifacts[5] = artifacts[5].model_copy(update={"final_queue_state": dirty})

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.final_backlog_clear is False
    assert any("final synchronization backlog is not clean" in issue for issue in result.issues)


def test_r0_15_fails_post_soak_canary() -> None:
    artifacts = list(_artifacts())
    artifacts[7] = artifacts[7].model_copy(update={"inclusion_valid": False})

    result = _evaluate(tuple(artifacts))

    assert result.r0_15_passed is False
    assert result.post_soak_canary_valid is False
    assert any("canary did not independently verify" in issue for issue in result.issues)
