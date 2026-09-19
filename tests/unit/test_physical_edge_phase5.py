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
from ets.qualification.physical_edge_phase4 import EdgeR0Phase4Evaluation
from ets.qualification.physical_edge_phase5 import (
    EdgeR0ActiveCaptureWindow,
    EdgeR0ActivePowerObservation,
    EdgeR0ActiveRecoveryCanary,
    EdgeR0ActiveRecoverySnapshot,
    EdgeR0AttemptRecoveryDisposition,
    EdgeR0CaptureAttemptEvidence,
    EdgeR0RecoveredCommitProofReceipt,
    R0CaptureState,
    R0RecoveryDisposition,
    evaluate_r0_6,
)

_NOW = datetime(2026, 9, 19, 0, 10, tzinfo=UTC)
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
            source_revision="b3adf751ab14182fe7993ab7dff65cc920f9d3a2",
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
        notes=("Synthetic W1-6 unit-test manifest.",),
    )


def _queue() -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=0,
        queue_bytes=0,
        pending=0,
        in_flight=0,
        retryable_failure=0,
        terminal_failure=0,
        synchronized=10,
        max_items=10_000,
        max_bytes=128 * 1024 * 1024,
        oldest_pending_age_seconds=None,
        last_successful_sync=_NOW.isoformat(),
        last_failure=None,
        upstream_status="online",
    )


def _phase4(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase4Evaluation:
    return EdgeR0Phase4Evaluation(
        evaluation_id="edge-r0-phase4-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase3_evaluation_id="edge-r0-phase3-passed",
        pre_cut_snapshot_id="edge-r0-precut-idle",
        power_observation_id="edge-r0-idle-power",
        recovery_snapshot_id="edge-r0-idle-recovery",
        evaluated_at=_NOW,
        preserved_proof_count=2,
        identity_preserved=True,
        queue_semantics_preserved=True,
        committed_evidence_preserved=True,
        post_recovery_canary_valid=True,
        r0_5_passed=True,
        issues=(),
    )


def _attempts() -> tuple[EdgeR0CaptureAttemptEvidence, ...]:
    committed_payload = _sha("request-1")
    return (
        EdgeR0CaptureAttemptEvidence(
            attempt_id="attempt-1",
            window_id="active-window-001",
            sequence_number=1,
            attempted_at=_NOW + timedelta(seconds=1),
            request_payload_sha256=committed_payload,
            client_attempt_receipt_sha256=_sha("client-1"),
            pre_cut_state=R0CaptureState.AUTHORITATIVELY_COMMITTED,
            event_id="event-1",
            event_hash=_sha("event-1"),
            content_hash=committed_payload,
            commit_receipt_sha256=_sha("commit-1"),
            proof_artifact_sha256=_sha("proof-1"),
        ),
        EdgeR0CaptureAttemptEvidence(
            attempt_id="attempt-2",
            window_id="active-window-001",
            sequence_number=2,
            attempted_at=_NOW + timedelta(seconds=2),
            request_payload_sha256=_sha("request-2"),
            client_attempt_receipt_sha256=_sha("client-2"),
            pre_cut_state=R0CaptureState.IN_FLIGHT_UNACKNOWLEDGED,
        ),
    )


def _artifacts():
    manifest = _manifest()
    phase4 = _phase4(manifest)
    attempts = _attempts()
    window = EdgeR0ActiveCaptureWindow(
        window_id="active-window-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase4_evaluation_id=phase4.evaluation_id,
        phase4_evaluation_sha256=canonical_sha256(phase4.model_dump(mode="json")),
        started_at=_NOW,
        cut_boundary_at=_NOW + timedelta(seconds=3),
        boot_id=_BOOT_A,
        device_id="ets-edge:test-device",
        signing_public_key_id="edge-demo-signing-key",
        signing_public_key_hex="11" * 32,
        public_key_fingerprint_sha256=_sha("public-key"),
        starting_log_head_sha256=_sha("starting-head"),
        starting_queue_state=_queue(),
        controller_timeline_sha256=_sha("controller-timeline"),
        attempts=attempts,
    )
    power = EdgeR0ActivePowerObservation(
        observation_id="active-power-001",
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
        controller_receipt_sha256=_sha("controller-power"),
        observer_loss_receipt_sha256=_sha("loss-observer"),
        observer_restore_receipt_sha256=_sha("restore-observer"),
    )
    recovery = EdgeR0ActiveRecoverySnapshot(
        snapshot_id="active-recovery-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        window_id=window.window_id,
        power_observation_id=power.observation_id,
        recovered_at=window.cut_boundary_at + timedelta(minutes=2),
        boot_id=_BOOT_B,
        device_id=window.device_id,
        signing_public_key_id=window.signing_public_key_id,
        signing_public_key_hex=window.signing_public_key_hex,
        public_key_fingerprint_sha256=window.public_key_fingerprint_sha256,
        recovered_log_head_sha256=_sha("recovered-head"),
        queue_state=_queue(),
        filesystem_recovery_clean=True,
        recovery_journal_sha256=_sha("journal"),
        filesystem_check_sha256=_sha("fs-check"),
        observer_receipt_sha256=_sha("recovery-observer"),
    )
    dispositions = (
        EdgeR0AttemptRecoveryDisposition(
            attempt_id="attempt-1",
            sequence_number=1,
            disposition=R0RecoveryDisposition.COMMITTED_BEFORE_CUT_PRESERVED,
            authoritative_commit_count=1,
            recovered_event_id="event-1",
            recovered_proof_sha256=_sha("proof-1"),
            recovery_observation_sha256=_sha("recover-attempt-1"),
        ),
        EdgeR0AttemptRecoveryDisposition(
            attempt_id="attempt-2",
            sequence_number=2,
            disposition=R0RecoveryDisposition.UNACKNOWLEDGED_ABSENT,
            authoritative_commit_count=0,
            recovery_observation_sha256=_sha("recover-attempt-2"),
        ),
    )
    proofs = (
        EdgeR0RecoveredCommitProofReceipt(
            receipt_id="proof-receipt-1",
            attempt_id="attempt-1",
            proof_artifact_sha256=_sha("proof-1"),
            verified_at=recovery.recovered_at + timedelta(seconds=1),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("proof-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        ),
    )
    payload = _sha("canary-payload")
    canary = EdgeR0ActiveRecoveryCanary(
        canary_id="active-canary-001",
        recovery_snapshot_id=recovery.snapshot_id,
        captured_at=recovery.recovered_at + timedelta(minutes=1),
        request_payload_sha256=payload,
        content_hash=payload,
        event_id="canary-event",
        event_hash=_sha("canary-event"),
        proof_artifact_sha256=_sha("canary-proof"),
        verified_at=recovery.recovered_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return manifest, phase4, window, power, recovery, dispositions, proofs, canary


def test_r0_6_passes_with_preserved_commit_and_explicit_unacknowledged_absence() -> None:
    artifacts = _artifacts()

    result = evaluate_r0_6(*artifacts, evaluated_at=_NOW + timedelta(minutes=4))

    assert result.r0_6_passed is True
    assert result.pre_cut_committed_count == 1
    assert result.recovered_commit_count == 1
    assert result.independently_verified_commit_count == 1
    assert result.issues == ()


def test_r0_6_fails_on_silent_loss_of_acknowledged_commit() -> None:
    manifest, phase4, window, power, recovery, dispositions, proofs, canary = _artifacts()
    lost = dispositions[0].model_copy(
        update={
            "disposition": R0RecoveryDisposition.UNACKNOWLEDGED_ABSENT,
            "authoritative_commit_count": 0,
            "recovered_event_id": None,
            "recovered_proof_sha256": None,
        }
    )

    result = evaluate_r0_6(
        manifest,
        phase4,
        window,
        power,
        recovery,
        (lost, dispositions[1]),
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_6_passed is False
    assert result.acknowledged_commits_preserved is False
    assert any("acknowledged pre-cut commit not preserved" in issue for issue in result.issues)


def test_r0_6_fails_on_duplicate_authoritative_commit() -> None:
    manifest, phase4, window, power, recovery, dispositions, proofs, canary = _artifacts()
    duplicate = dispositions[0].model_copy(update={"authoritative_commit_count": 2})

    result = evaluate_r0_6(
        manifest,
        phase4,
        window,
        power,
        recovery,
        (duplicate, dispositions[1]),
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_6_passed is False
    assert result.no_duplicate_authoritative_commits is False
    assert any("duplicate authoritative commit" in issue for issue in result.issues)


def test_r0_6_rejects_retroactive_acknowledgement_of_in_flight_attempt() -> None:
    manifest, phase4, window, power, recovery, dispositions, proofs, canary = _artifacts()
    retroactive = EdgeR0AttemptRecoveryDisposition(
        attempt_id="attempt-2",
        sequence_number=2,
        disposition=R0RecoveryDisposition.COMMITTED_BEFORE_CUT_PRESERVED,
        authoritative_commit_count=1,
        recovered_event_id="event-2",
        recovered_proof_sha256=_sha("proof-2"),
        recovery_observation_sha256=_sha("recover-attempt-2-retroactive"),
    )
    proof2 = EdgeR0RecoveredCommitProofReceipt(
        receipt_id="proof-receipt-2",
        attempt_id="attempt-2",
        proof_artifact_sha256=_sha("proof-2"),
        verified_at=recovery.recovered_at + timedelta(seconds=2),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("proof-result-2"),
        inclusion_valid=True,
        independent_execution_context=True,
    )

    result = evaluate_r0_6(
        manifest,
        phase4,
        window,
        power,
        recovery,
        (dispositions[0], retroactive),
        (*proofs, proof2),
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_6_passed is False
    assert any("retroactively classified" in issue for issue in result.issues)


def test_r0_6_fails_when_attempt_classification_is_missing() -> None:
    manifest, phase4, window, power, recovery, dispositions, proofs, canary = _artifacts()

    result = evaluate_r0_6(
        manifest,
        phase4,
        window,
        power,
        recovery,
        (dispositions[0],),
        proofs,
        canary,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_6_passed is False
    assert result.attempt_classification_complete is False
    assert any("missing recovery dispositions" in issue for issue in result.issues)
