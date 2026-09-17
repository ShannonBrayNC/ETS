from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from ets.edge.device_identity import EdgeDeviceIdentity
from ets.edge.webhook_adapter import WebhookCaptureReceipt
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
from ets.qualification.physical_edge_phase3 import (
    EdgeR0Phase3Evaluation,
    EdgeSyncStatusEvidence,
)
from ets.qualification.physical_edge_phase4 import (
    build_power_observation,
    build_pre_cut_snapshot,
    build_preserved_proof_receipt,
    build_recovery_canary,
    build_recovery_snapshot,
    evaluate_r0_5,
)

_NOW = datetime(2026, 9, 16, 14, 45, tzinfo=UTC)
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
        notes=("Synthetic W1-5 unit-test manifest.",),
    )


def _phase3(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase3Evaluation:
    return EdgeR0Phase3Evaluation(
        evaluation_id="edge-r0-phase3-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase2_evaluation_id="edge-r0-phase2-passed",
        window_id="offline-window-001",
        evaluated_at=_NOW + timedelta(minutes=1),
        attempted_event_count=10,
        locally_committed_count=10,
        independently_verified_count=10,
        synchronized_exactly_once_count=10,
        r0_4_passed=True,
        issues=(),
        disposition="phase_evidence_only",
        claim_boundary="r0_4_phase_evidence_not_a_physical_qualification_result",
    )


def _identity() -> EdgeDeviceIdentity:
    public_key_hex = "11" * 32
    fingerprint = hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()
    return EdgeDeviceIdentity(
        schema_version="ets.edge.device_identity.v1",
        device_id=f"ets-edge:{fingerprint[:32]}",
        signing_algorithm="ed25519",
        signing_public_key_id="edge-demo-signing-key",
        signing_public_key_hex=public_key_hex,
        public_key_fingerprint_sha256=fingerprint,
        key_custody="software_volume",
        hardware_attested=False,
    )


def _idle_queue(synchronized: int = 10) -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=0,
        queue_bytes=0,
        pending=0,
        in_flight=0,
        retryable_failure=0,
        terminal_failure=0,
        synchronized=synchronized,
        max_items=10_000,
        max_bytes=128 * 1024 * 1024,
        oldest_pending_age_seconds=None,
        last_successful_sync=_NOW.isoformat(),
        last_failure=None,
        upstream_status="online",
    )


def _artifacts():
    manifest = _manifest()
    phase3 = _phase3(manifest)
    identity = _identity()
    pre_cut = build_pre_cut_snapshot(
        manifest,
        phase3,
        identity,
        boot_id=_BOOT_A,
        captured_at=_NOW + timedelta(minutes=2),
        queue_state=_idle_queue(),
        log_head_sha256=_sha("pre-cut-head"),
        representative_proof_sha256=(_sha("proof-a"), _sha("proof-b")),
        observer_receipt_sha256=_sha("pre-cut-observer"),
    )
    power = build_power_observation(
        manifest,
        pre_cut,
        controller_id="bench-controller-001",
        cut_commanded_at=_NOW + timedelta(minutes=3),
        power_loss_observed_at=_NOW + timedelta(minutes=3, seconds=1),
        restore_commanded_at=_NOW + timedelta(minutes=4),
        power_restored_observed_at=_NOW + timedelta(minutes=4, seconds=1),
        controller_receipt_sha256=_sha("power-controller"),
        observer_loss_receipt_sha256=_sha("power-loss-observer"),
        observer_restore_receipt_sha256=_sha("power-restore-observer"),
    )
    recovery = build_recovery_snapshot(
        manifest,
        pre_cut,
        power,
        identity,
        boot_id=_BOOT_B,
        captured_at=_NOW + timedelta(minutes=5),
        queue_state=_idle_queue(),
        pre_cut_log_head_sha256=pre_cut.log_head_sha256,
        pre_cut_log_head_observed=True,
        filesystem_recovery_clean=True,
        recovery_journal_sha256=_sha("recovery-journal"),
        filesystem_check_sha256=_sha("filesystem-check"),
        observer_receipt_sha256=_sha("recovery-observer"),
    )
    preserved = tuple(
        build_preserved_proof_receipt(
            pre_cut,
            proof_artifact_sha256=digest,
            verification_result={"valid": True},
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha(f"result-{index}"),
            verified_at=_NOW + timedelta(minutes=6, seconds=index),
            independent_execution_context=True,
        )
        for index, digest in enumerate(pre_cut.representative_proof_sha256, start=1)
    )
    payload_digest = _sha("canary-payload")
    receipt = WebhookCaptureReceipt(
        event_id="evt_recovery_canary_001",
        evidence_id=f"webhook:r0-controller:{payload_digest[:48]}",
        log_index=100,
        event_hash=_sha("canary-event"),
        content_hash=payload_digest,
        content_hash_alg="sha256",
        byte_size=128,
        event_url="/api/v1/events/evt_recovery_canary_001",
        proof_url="/api/v1/proofs/inclusion/evt_recovery_canary_001",
        bundle_url="/api/v1/bundles/evt_recovery_canary_001",
        tree_head_url="/api/v1/log/head",
        sync_state="pending",
        sync_status_url="/edge/v1/sync/status",
    )
    canary = build_recovery_canary(
        recovery,
        receipt,
        {"valid": True},
        captured_at=_NOW + timedelta(minutes=7),
        request_payload_sha256=payload_digest,
        receipt_artifact_sha256=_sha("canary-receipt"),
        proof_artifact_sha256=_sha("canary-proof"),
        verified_at=_NOW + timedelta(minutes=7, seconds=10),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("canary-result"),
        independent_execution_context=True,
    )
    return manifest, phase3, pre_cut, power, recovery, preserved, canary


def test_r0_5_passes_for_idle_hard_power_recovery() -> None:
    manifest, phase3, pre_cut, power, recovery, preserved, canary = _artifacts()

    result = evaluate_r0_5(
        manifest,
        phase3,
        pre_cut,
        power,
        recovery,
        preserved,
        canary,
        evaluated_at=_NOW + timedelta(minutes=8),
    )

    assert result.r0_5_passed is True
    assert result.issues == ()
    assert result.identity_preserved is True
    assert result.queue_semantics_preserved is True
    assert result.committed_evidence_preserved is True
    assert result.post_recovery_canary_valid is True
    assert result.preserved_proof_count == 2
    assert result.disposition == "phase_evidence_only"


def test_pre_cut_rejects_non_idle_queue() -> None:
    manifest = _manifest()
    phase3 = _phase3(manifest)
    busy = _idle_queue().model_copy(update={"queue_depth": 1, "pending": 1})

    with pytest.raises(ValueError, match="idle synchronization queue"):
        build_pre_cut_snapshot(
            manifest,
            phase3,
            _identity(),
            boot_id=_BOOT_A,
            captured_at=_NOW + timedelta(minutes=2),
            queue_state=busy,
            log_head_sha256=_sha("head"),
            representative_proof_sha256=(_sha("proof"),),
            observer_receipt_sha256=_sha("observer"),
        )


def test_identity_drift_fails_r0_5() -> None:
    manifest, phase3, pre_cut, power, recovery, preserved, canary = _artifacts()
    recovery = recovery.model_copy(update={"device_id": "ets-edge:drifted"})

    result = evaluate_r0_5(
        manifest,
        phase3,
        pre_cut,
        power,
        recovery,
        preserved,
        canary.model_copy(update={"recovery_snapshot_id": recovery.snapshot_id}),
        evaluated_at=_NOW + timedelta(minutes=8),
    )

    assert result.r0_5_passed is False
    assert result.identity_preserved is False
    assert any("identity changed" in issue for issue in result.issues)


def test_same_boot_id_after_power_loss_fails_r0_5() -> None:
    manifest, phase3, pre_cut, power, recovery, preserved, canary = _artifacts()
    recovery = recovery.model_copy(update={"boot_id": pre_cut.boot_id})

    result = evaluate_r0_5(
        manifest,
        phase3,
        pre_cut,
        power,
        recovery,
        preserved,
        canary.model_copy(update={"recovery_snapshot_id": recovery.snapshot_id}),
        evaluated_at=_NOW + timedelta(minutes=8),
    )

    assert result.r0_5_passed is False
    assert any("boot ID did not change" in issue for issue in result.issues)


def test_missing_preserved_proof_fails_r0_5() -> None:
    manifest, phase3, pre_cut, power, recovery, preserved, canary = _artifacts()

    result = evaluate_r0_5(
        manifest,
        phase3,
        pre_cut,
        power,
        recovery,
        preserved[:-1],
        canary,
        evaluated_at=_NOW + timedelta(minutes=8),
    )

    assert result.r0_5_passed is False
    assert result.committed_evidence_preserved is False
    assert any("missing preserved-proof" in issue for issue in result.issues)


def test_recovered_queue_regression_fails_r0_5() -> None:
    manifest, phase3, pre_cut, power, recovery, preserved, canary = _artifacts()
    recovery = recovery.model_copy(
        update={
            "queue_state": _idle_queue().model_copy(
                update={"queue_depth": 1, "retryable_failure": 1}
            )
        }
    )

    result = evaluate_r0_5(
        manifest,
        phase3,
        pre_cut,
        power,
        recovery,
        preserved,
        canary.model_copy(update={"recovery_snapshot_id": recovery.snapshot_id}),
        evaluated_at=_NOW + timedelta(minutes=8),
    )

    assert result.r0_5_passed is False
    assert result.queue_semantics_preserved is False
    assert any("queue contains unresolved work" in issue for issue in result.issues)


def test_non_independent_canary_fails_r0_5() -> None:
    manifest, phase3, pre_cut, power, recovery, preserved, canary = _artifacts()
    canary = canary.model_copy(update={"independent_execution_context": False})

    result = evaluate_r0_5(
        manifest,
        phase3,
        pre_cut,
        power,
        recovery,
        preserved,
        canary,
        evaluated_at=_NOW + timedelta(minutes=8),
    )

    assert result.r0_5_passed is False
    assert result.post_recovery_canary_valid is False
    assert any("canary proof did not verify independently" in issue for issue in result.issues)
