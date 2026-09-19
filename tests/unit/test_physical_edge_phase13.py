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
from ets.qualification.physical_edge_phase12 import EdgeR0Phase12Evaluation
from ets.qualification.physical_edge_phase13 import (
    EdgeR0IdentityRecovery,
    EdgeR0ReattachedRecord,
    EdgeR0Reattachment,
    EdgeR0RebuildBaseline,
    EdgeR0RebuildCanary,
    EdgeR0RebuildObservation,
    EdgeR0RebuildPendingRecord,
    EdgeR0RebuildProofReceipt,
    EdgeR0RecoveryMedia,
    IdentityRecoveryMode,
    RebuildProofSubject,
    evaluate_r0_14,
)

_NOW = datetime(2026, 9, 19, 18, 0, tzinfo=UTC)
_BUILD = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _queue(*, pending: int = 0) -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=pending,
        queue_bytes=pending * 256,
        pending=pending,
        in_flight=0,
        retryable_failure=0,
        terminal_failure=0,
        synchronized=90,
        max_items=10,
        max_bytes=10_000,
        oldest_pending_age_seconds=None if pending == 0 else 1.0,
        last_successful_sync=_NOW.isoformat(),
        last_failure=None,
        upstream_status="online",
    )


def _manifest() -> EdgeCompactR0BenchManifest:
    controls = tuple(
        BenchControl(
            kind=kind,
            control_id=f"r0-{kind.value}-control",
            method=f"isolated {kind.value} qualification control",
            independent_observation_method=f"external {kind.value} observer",
            destructive_or_disruptive=True,
            operator_approval_required=True,
            bootstrap_cli_executes_action=False,
        )
        for kind in BenchControlKind
    )
    return EdgeCompactR0BenchManifest(
        manifest_id="edge-r0-lab-001",
        qualification_class="EDGE_COMPACT_R0",
        manifest_state=ManifestState.READY_FOR_QUALIFICATION,
        collected_at=_NOW,
        dut=EdgeR0Dut(
            manufacturer="Example",
            model="Mini PC",
            hardware_revision="rev-a",
            asset_id="EDGE-R0-001",
            cpu_architecture="x86_64",
            cpu_model="Example CPU",
            memory_bytes=16 * 1024**3,
            storage=(
                StorageDevice(
                    name="nvme0n1",
                    vendor="Example",
                    model="NVMe",
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
            artifact_digest=_sha("artifact"),
            configuration_digest=_sha("config"),
        ),
        trust=EdgeR0TrustPosture(),
        observer=IndependentObserver(
            observer_id="observer-a",
            observer_host_id="bench-controller-001",
            observation_method="external receipts",
            independent_from_dut=True,
        ),
        verifier=IndependentVerifier(
            verifier_host_id="bench-controller-001",
            verifier_identity="hqp2-clean-verifier",
            command="python -m ets.hqp_verify",
            independent_from_dut=True,
        ),
        controls=controls,
        notes=("Synthetic W1-14 test manifest.",),
    )


def _phase12(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase12Evaluation:
    return EdgeR0Phase12Evaluation(
        evaluation_id="edge-r0-phase12-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase11_evaluation_id="edge-r0-phase11-passed",
        baseline_id="rollback-baseline-001",
        target_id="failed-target-001",
        failure_id="failure-001",
        rollback_id="rollback-001",
        reconciliation_id="rollback-reconciliation-001",
        evaluated_at=_NOW,
        failure_observed=True,
        no_false_target_success=True,
        recovery_build_valid=True,
        identity_continuity_preserved=True,
        trust_posture_preserved=True,
        historical_evidence_preserved=True,
        pending_state_reconciled=True,
        checkpoints_non_regressing=True,
        no_ambiguous_half_upgrade=True,
        prior_phase_boundaries_preserved=True,
        independent_verification_complete=True,
        post_recovery_canary_valid=True,
        r0_13_passed=True,
        issues=(),
    )


def _artifacts():
    manifest = _manifest()
    phase12 = _phase12(manifest)
    pending = EdgeR0RebuildPendingRecord(
        record_id="pending-1",
        event_id="event-1",
        idempotency_key="idem-1",
        local_proof_sha256=_sha("local-proof-1"),
    )
    baseline = EdgeR0RebuildBaseline(
        baseline_id="rebuild-baseline-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase12_evaluation_id=phase12.evaluation_id,
        phase12_evaluation_sha256=canonical_sha256(phase12.model_dump(mode="json")),
        captured_at=_NOW + timedelta(seconds=1),
        build_sha=_BUILD,
        artifact_digest=_sha("recovery-artifact"),
        configuration_digest=_sha("recovery-config"),
        runtime_version="0.14.0-r0",
        data_schema_version="14",
        device_identity_id="edge-r0-device",
        signing_key_id="edge-r0-key",
        identity_material_commitment_sha256=_sha("identity-material"),
        local_checkpoint_index=900,
        local_checkpoint_sha256=_sha("local-checkpoint"),
        upstream_checkpoint_index=450,
        upstream_checkpoint_sha256=_sha("upstream-checkpoint"),
        log_head_sha256=_sha("log-head"),
        historical_record_commitment_sha256=_sha("history"),
        queue_state=_queue(pending=1),
        storage_used_bytes=40_000,
        storage_high_watermark_used_bytes=80_000,
        pending_records=(pending,),
        representative_proof_sha256=(_sha("pre-proof"),),
        observer_receipt_sha256=_sha("baseline-observer"),
    )
    media = EdgeR0RecoveryMedia(
        media_id="recovery-media-001",
        baseline_id=baseline.baseline_id,
        prepared_at=_NOW + timedelta(seconds=2),
        source_provenance_sha256=_sha("media-source"),
        image_build_sha=_BUILD,
        image_artifact_digest=_sha("recovery-artifact"),
        image_digest=_sha("media-image"),
        configuration_template_digest=_sha("recovery-config"),
        expected_runtime_version="0.14.0-r0",
        expected_data_schema_version="14",
        verification_receipt_sha256=_sha("media-verification"),
    )
    rebuild = EdgeR0RebuildObservation(
        rebuild_id="rebuild-001",
        baseline_id=baseline.baseline_id,
        media_id=media.media_id,
        started_at=_NOW + timedelta(seconds=3),
        completed_at=_NOW + timedelta(seconds=8),
        target_device_id="nvme0n1",
        target_matches_manifest=True,
        media_image_digest=media.image_digest,
        media_boot_receipt_sha256=_sha("media-boot"),
        filesystem_creation_receipt_sha256=_sha("filesystem"),
        installed_build_sha=media.image_build_sha,
        installed_artifact_digest=media.image_artifact_digest,
        installed_configuration_digest=media.configuration_template_digest,
        installed_runtime_version=media.expected_runtime_version,
        installed_data_schema_version=media.expected_data_schema_version,
        resulting_boot_id="boot-after-rebuild",
        service_healthy=True,
        independently_observed=True,
        controller_receipt_sha256=_sha("rebuild-controller"),
        observer_receipt_sha256=_sha("rebuild-observer"),
    )
    identity = EdgeR0IdentityRecovery(
        identity_recovery_id="identity-recovery-001",
        rebuild_id=rebuild.rebuild_id,
        mode=IdentityRecoveryMode.RESTORE_EXISTING_IDENTITY,
        prior_device_identity_id=baseline.device_identity_id,
        prior_signing_key_id=baseline.signing_key_id,
        resulting_device_identity_id=baseline.device_identity_id,
        resulting_signing_key_id=baseline.signing_key_id,
        recovery_material_commitment_sha256=(
            baseline.identity_material_commitment_sha256
        ),
        continuity_receipt_sha256=_sha("identity-continuity"),
        upstream_enrollment_updated=False,
        historical_identity_attribution_preserved=True,
    )
    record = EdgeR0ReattachedRecord(
        record_id=pending.record_id,
        event_id=pending.event_id,
        idempotency_key=pending.idempotency_key,
        authoritative_local_present=True,
        final_upstream_commit_count=1,
        final_upstream_event_id=pending.event_id,
        final_proof_sha256=_sha("final-proof-1"),
        invented_upstream_acknowledgement=False,
        observation_sha256=_sha("reattached-record"),
    )
    reattachment = EdgeR0Reattachment(
        reattachment_id="reattachment-001",
        rebuild_id=rebuild.rebuild_id,
        completed_at=_NOW + timedelta(seconds=10),
        historical_record_commitment_sha256=(
            baseline.historical_record_commitment_sha256
        ),
        pre_rebuild_log_head_observed=True,
        pre_rebuild_log_head_sha256=baseline.log_head_sha256,
        local_history_restored=True,
        local_checkpoint_index=901,
        local_checkpoint_sha256=_sha("local-checkpoint-after"),
        upstream_checkpoint_index=451,
        upstream_checkpoint_sha256=_sha("upstream-checkpoint-after"),
        records=(record,),
        final_queue_state=_queue(),
        storage_used_bytes=42_000,
        network_connected=True,
        time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
        software_state_unambiguous=True,
        observer_receipt_sha256=_sha("reattachment-observer"),
    )
    proofs = (
        EdgeR0RebuildProofReceipt(
            receipt_id="proof-pre",
            subject_kind=RebuildProofSubject.PRE_REBUILD,
            subject_id=_sha("pre-proof"),
            proof_artifact_sha256=_sha("pre-proof"),
            verified_at=_NOW + timedelta(seconds=11),
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier"),
            verification_result_sha256=_sha("pre-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        ),
        EdgeR0RebuildProofReceipt(
            receipt_id="proof-record",
            subject_kind=RebuildProofSubject.REATTACHED_RECORD,
            subject_id=record.record_id,
            proof_artifact_sha256=_sha("final-proof-1"),
            verified_at=_NOW + timedelta(seconds=12),
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier"),
            verification_result_sha256=_sha("record-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        ),
    )
    payload = _sha("canary-payload")
    canary = EdgeR0RebuildCanary(
        canary_id="rebuild-canary-001",
        rebuild_id=rebuild.rebuild_id,
        captured_at=_NOW + timedelta(seconds=13),
        device_identity_id=identity.resulting_device_identity_id,
        build_sha=rebuild.installed_build_sha,
        configuration_digest=rebuild.installed_configuration_digest,
        request_payload_sha256=payload,
        content_hash=payload,
        event_id="canary-event",
        proof_artifact_sha256=_sha("canary-proof"),
        synchronized=True,
        verified_at=_NOW + timedelta(seconds=14),
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier"),
        verification_result_sha256=_sha("canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return manifest, phase12, baseline, media, rebuild, identity, reattachment, proofs, canary


def _evaluate(artifacts):
    return evaluate_r0_14(*artifacts, evaluated_at=_NOW + timedelta(minutes=2))


def test_r0_14_passes_recovery_media_rebuild_and_reattachment() -> None:
    result = _evaluate(_artifacts())
    assert result.r0_14_passed is True
    assert result.issues == ()


def test_r0_14_fails_wrong_recovery_media_digest() -> None:
    artifacts = list(_artifacts())
    artifacts[4] = artifacts[4].model_copy(update={"media_image_digest": _sha("wrong")})
    result = _evaluate(tuple(artifacts))
    assert result.recovery_media_valid is False
    assert any("image digest mismatch" in issue for issue in result.issues)


def test_r0_14_fails_silent_identity_drift() -> None:
    artifacts = list(_artifacts())
    identity = artifacts[5]
    artifacts[5] = identity.model_copy(update={"prior_device_identity_id": "other-device"})
    result = _evaluate(tuple(artifacts))
    assert result.identity_recovery_valid is False
    assert any("prior device identity" in issue for issue in result.issues)


def test_r0_14_rotation_requires_binding_and_preserves_attribution() -> None:
    artifacts = list(_artifacts())
    old = artifacts[5]
    artifacts[5] = EdgeR0IdentityRecovery(
        identity_recovery_id=old.identity_recovery_id,
        rebuild_id=old.rebuild_id,
        mode=IdentityRecoveryMode.ROTATE_IDENTITY_WITH_BINDING,
        prior_device_identity_id=old.prior_device_identity_id,
        prior_signing_key_id=old.prior_signing_key_id,
        resulting_device_identity_id="edge-r0-device-rotated",
        resulting_signing_key_id="edge-r0-key-rotated",
        old_to_new_binding_sha256=_sha("old-to-new"),
        upstream_enrollment_updated=True,
        historical_identity_attribution_preserved=False,
    )
    result = _evaluate(tuple(artifacts))
    assert result.identity_recovery_valid is False
    assert any("historical attribution" in issue for issue in result.issues)


def test_r0_14_fails_historical_evidence_rewrite() -> None:
    artifacts = list(_artifacts())
    artifacts[6] = artifacts[6].model_copy(
        update={"historical_record_commitment_sha256": _sha("rewritten-history")}
    )
    result = _evaluate(tuple(artifacts))
    assert result.historical_evidence_preserved is False


def test_r0_14_fails_replay_duplication() -> None:
    artifacts = list(_artifacts())
    reattachment = artifacts[6]
    duplicated = reattachment.records[0].model_copy(
        update={"final_upstream_commit_count": 2}
    )
    artifacts[6] = reattachment.model_copy(update={"records": (duplicated,)})
    result = _evaluate(tuple(artifacts))
    assert result.upstream_reattachment_valid is False
    assert any("exactly once" in issue for issue in result.issues)


def test_r0_14_fails_prior_phase_guardrail_escape() -> None:
    artifacts = list(_artifacts())
    artifacts[6] = artifacts[6].model_copy(update={"network_connected": False})
    result = _evaluate(tuple(artifacts))
    assert result.prior_phase_boundaries_preserved is False


def test_r0_14_fails_missing_pre_rebuild_proof() -> None:
    artifacts = list(_artifacts())
    artifacts[7] = artifacts[7][1:]
    result = _evaluate(tuple(artifacts))
    assert result.independent_verification_complete is False
    assert any("missing pre-rebuild proof" in issue for issue in result.issues)


def test_r0_14_fails_wrong_identity_canary() -> None:
    artifacts = list(_artifacts())
    artifacts[8] = artifacts[8].model_copy(
        update={"device_identity_id": "wrong-canary-identity"}
    )
    result = _evaluate(tuple(artifacts))
    assert result.post_rebuild_canary_valid is False
    assert any("wrong recovered identity" in issue for issue in result.issues)
