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
    EdgeR0IdentityRecoveryEvidence,
    EdgeR0Phase13Evaluation,
    EdgeR0PreRebuildRecord,
    EdgeR0ReattachedRecord,
    EdgeR0RebuildObservation,
    EdgeR0RecoveryBaseline,
    EdgeR0RecoveryCanary,
    EdgeR0RecoveryMedia,
    EdgeR0RecoveryProofReceipt,
    EdgeR0RecoveryReattachment,
    IdentityRecoveryMode,
    LocalHistoryMode,
    RecoveryProofSubject,
    build_recovery_reattachment_commitment,
    evaluate_r0_14,
)

_NOW = datetime(2026, 9, 19, 18, 0, tzinfo=UTC)
_BUILD = "a8b64eaf6a5cf0539e879df5cb575187b9cff472"


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
            artifact_digest=_sha("recovery-current-artifact"),
            configuration_digest=_sha("recovery-current-config"),
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
        notes=("Synthetic W1-14 unit-test manifest.",),
    )


def _queue(
    *,
    depth: int = 0,
    bytes_used: int = 0,
    pending: int = 0,
    synchronized: int = 80,
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


def _phase12(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase12Evaluation:
    return EdgeR0Phase12Evaluation(
        evaluation_id="edge-r0-phase12-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase11_evaluation_id="edge-r0-phase11-passed",
        baseline_id="rollback-baseline-001",
        target_id="failed-target-001",
        failure_id="upgrade-failure-001",
        rollback_id="rollback-execution-001",
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


def _artifacts() -> tuple[
    EdgeCompactR0BenchManifest,
    EdgeR0Phase12Evaluation,
    EdgeR0RecoveryBaseline,
    EdgeR0RecoveryMedia,
    EdgeR0RebuildObservation,
    EdgeR0IdentityRecoveryEvidence,
    EdgeR0RecoveryReattachment,
    tuple[EdgeR0RecoveryProofReceipt, ...],
    EdgeR0RecoveryCanary,
]:
    manifest = _manifest()
    phase12 = _phase12(manifest)
    identity_material = _sha("recovery-identity-material")
    synchronized_records = (
        EdgeR0PreRebuildRecord(
            record_id="recovery-record-1",
            event_id="recovery-event-1",
            idempotency_key="recovery-idem-1",
            original_identity_id="edge-r0-device-identity",
            upstream_acceptance_sha256=_sha("recovery-accept-1"),
            proof_artifact_sha256=_sha("recovery-proof-1"),
        ),
        EdgeR0PreRebuildRecord(
            record_id="recovery-record-2",
            event_id="recovery-event-2",
            idempotency_key="recovery-idem-2",
            original_identity_id="edge-r0-device-identity",
            upstream_acceptance_sha256=_sha("recovery-accept-2"),
            proof_artifact_sha256=_sha("recovery-proof-2"),
        ),
    )
    baseline = EdgeR0RecoveryBaseline(
        baseline_id="recovery-baseline-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase12_evaluation_id=phase12.evaluation_id,
        phase12_evaluation_sha256=canonical_sha256(phase12.model_dump(mode="json")),
        captured_at=_NOW + timedelta(seconds=1),
        current_build_sha=_BUILD,
        current_artifact_digest=_sha("recovery-current-artifact"),
        current_configuration_digest=_sha("recovery-current-config"),
        current_version="0.14.0-r0",
        current_data_schema_version="14",
        current_runtime_id="ubuntu-24.04-x86_64",
        device_identity_id="edge-r0-device-identity",
        signing_key_id="edge-r0-software-key",
        identity_material_commitment_sha256=identity_material,
        local_checkpoint_index=800,
        local_checkpoint_sha256=_sha("recovery-local-pre"),
        upstream_checkpoint_index=400,
        upstream_checkpoint_sha256=_sha("recovery-upstream-pre"),
        log_head_sha256=_sha("recovery-log-head-pre"),
        historical_record_commitment_sha256=_sha("recovery-history"),
        queue_state=_queue(),
        storage_used_bytes=40_000,
        storage_high_watermark_used_bytes=70_000,
        synchronized_records=synchronized_records,
        representative_proof_sha256=(_sha("recovery-pre-proof"),),
        off_dut_evidence_copy_sha256=_sha("recovery-offdut-copy"),
        observer_receipt_sha256=_sha("recovery-baseline-observer"),
    )
    media = EdgeR0RecoveryMedia(
        media_id="recovery-media-001",
        baseline_id=baseline.baseline_id,
        prepared_at=_NOW,
        target_asset_id=baseline.asset_id,
        image_build_sha=_BUILD,
        image_artifact_digest=baseline.current_artifact_digest,
        image_configuration_digest=baseline.current_configuration_digest,
        media_image_digest=_sha("recovery-media-image"),
        configuration_template_digest=_sha("recovery-template"),
        expected_version=baseline.current_version,
        expected_data_schema_version=baseline.current_data_schema_version,
        expected_runtime_id=baseline.current_runtime_id,
        source_provenance="immutable qualified recovery image from controlled build",
        media_creation_receipt_sha256=_sha("recovery-media-create"),
        independent_verification_sha256=_sha("recovery-media-verify"),
    )
    rebuild = EdgeR0RebuildObservation(
        rebuild_id="rebuild-001",
        baseline_id=baseline.baseline_id,
        media_id=media.media_id,
        started_at=_NOW + timedelta(seconds=2),
        completed_at=_NOW + timedelta(seconds=12),
        target_asset_id=baseline.asset_id,
        target_storage_id="nvme0n1:TEST-SERIAL",
        observed_media_image_digest=media.media_image_digest,
        media_boot_receipt_sha256=_sha("recovery-media-boot"),
        partition_filesystem_result_sha256=_sha("recovery-partition-result"),
        partition_filesystem_success=True,
        installed_build_sha=media.image_build_sha,
        installed_artifact_digest=media.image_artifact_digest,
        installed_configuration_digest=media.image_configuration_digest,
        installed_version=media.expected_version,
        installed_data_schema_version=media.expected_data_schema_version,
        installed_runtime_id=media.expected_runtime_id,
        resulting_boot_id="boot-after-recovery-media",
        service_healthy=True,
        build_independently_identified=True,
        controller_receipt_sha256=_sha("rebuild-controller"),
        external_observer_receipt_sha256=_sha("rebuild-external-observer"),
        independently_observed=True,
    )
    identity = EdgeR0IdentityRecoveryEvidence(
        identity_recovery_id="identity-recovery-001",
        rebuild_id=rebuild.rebuild_id,
        mode=IdentityRecoveryMode.RESTORE_EXISTING_IDENTITY,
        observed_at=rebuild.completed_at + timedelta(seconds=1),
        pre_device_identity_id=baseline.device_identity_id,
        pre_signing_key_id=baseline.signing_key_id,
        post_device_identity_id=baseline.device_identity_id,
        post_signing_key_id=baseline.signing_key_id,
        recovery_material_sha256=identity_material,
        continuity_binding_sha256=_sha("recovery-continuity-binding"),
        upstream_enrollment_updated=False,
        historical_identity_attribution_preserved=True,
        post_recovery_identity_attribution_correct=True,
        observer_receipt_sha256=_sha("identity-recovery-observer"),
    )
    reattached_records = tuple(
        EdgeR0ReattachedRecord(
            record_id=record.record_id,
            event_id=record.event_id,
            idempotency_key=record.idempotency_key,
            original_identity_id=record.original_identity_id,
            upstream_record_present=True,
            final_upstream_commit_count=1,
            final_upstream_event_id=record.event_id,
            upstream_acceptance_sha256=record.upstream_acceptance_sha256,
            proof_artifact_sha256=record.proof_artifact_sha256,
            authoritative_local_present_after_rebuild=True,
            local_marked_synchronized=True,
            replayed_as_new_logical_event=False,
            invented_upstream_acknowledgement=False,
            reattachment_observation_sha256=_sha(
                f"recovery-reattach-{record.record_id}"
            ),
        )
        for record in synchronized_records
    )
    reattachment = EdgeR0RecoveryReattachment(
        reattachment_id="reattachment-001",
        rebuild_id=rebuild.rebuild_id,
        identity_recovery_id=identity.identity_recovery_id,
        reattached_at=identity.observed_at + timedelta(seconds=2),
        local_history_mode=LocalHistoryMode.RESTORED,
        local_history_limitation_explicit=False,
        restored_local_history_commitment_sha256=(
            baseline.historical_record_commitment_sha256
        ),
        upstream_historical_commitment_verified=True,
        local_checkpoint_index=802,
        local_checkpoint_sha256=_sha("recovery-local-post"),
        upstream_checkpoint_index=402,
        upstream_checkpoint_sha256=_sha("recovery-upstream-post"),
        records=reattached_records,
        final_queue_state=_queue(synchronized=82),
        storage_used_bytes=40_500,
        network_connected=True,
        time_quality=TimeQuality.TRUSTED_SYNCHRONIZED,
        software_state_unambiguous=True,
        reconciliation_commitment_sha256=build_recovery_reattachment_commitment(
            reattached_records
        ),
        observer_receipt_sha256=_sha("reattachment-observer"),
    )
    proofs = [
        EdgeR0RecoveryProofReceipt(
            receipt_id="recovery-pre-proof-receipt",
            subject_kind=RecoveryProofSubject.PRE_REBUILD,
            subject_id=_sha("recovery-pre-proof"),
            proof_artifact_sha256=_sha("recovery-pre-proof"),
            verified_at=reattachment.reattached_at + timedelta(seconds=1),
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            verification_result_sha256=_sha("recovery-pre-result"),
            inclusion_valid=True,
            independent_execution_context=True,
        )
    ]
    for index, record in enumerate(reattached_records, start=1):
        proofs.append(
            EdgeR0RecoveryProofReceipt(
                receipt_id=f"recovery-record-proof-{index}",
                subject_kind=RecoveryProofSubject.REATTACHED_RECORD,
                subject_id=record.record_id,
                proof_artifact_sha256=record.proof_artifact_sha256 or _sha("missing"),
                verified_at=reattachment.reattached_at
                + timedelta(seconds=index + 1),
                verifier_id="ets-verify-offline",
                verifier_host_id="bench-controller-001",
                verifier_build_sha256=_sha("verifier-build"),
                verification_result_sha256=_sha(f"recovery-record-result-{index}"),
                inclusion_valid=True,
                independent_execution_context=True,
            )
        )
    canary_payload = _sha("recovery-canary-payload")
    canary = EdgeR0RecoveryCanary(
        canary_id="recovery-canary-001",
        reattachment_id=reattachment.reattachment_id,
        captured_at=reattachment.reattached_at + timedelta(minutes=1),
        identity_recovery_mode=identity.mode,
        post_rebuild_identity_id=identity.post_device_identity_id,
        rebuilt_build_sha=rebuild.installed_build_sha,
        rebuilt_configuration_digest=rebuild.installed_configuration_digest,
        request_payload_sha256=canary_payload,
        content_hash=canary_payload,
        event_id="recovery-canary-event",
        proof_artifact_sha256=_sha("recovery-canary-proof"),
        synchronized=True,
        verified_at=reattachment.reattached_at + timedelta(minutes=1, seconds=1),
        verifier_id="ets-verify-offline",
        verifier_host_id="bench-controller-001",
        verifier_build_sha256=_sha("verifier-build"),
        verification_result_sha256=_sha("recovery-canary-result"),
        inclusion_valid=True,
        independent_execution_context=True,
    )
    return (
        manifest,
        phase12,
        baseline,
        media,
        rebuild,
        identity,
        reattachment,
        tuple(proofs),
        canary,
    )


def _evaluate(
    artifacts: tuple[
        EdgeCompactR0BenchManifest,
        EdgeR0Phase12Evaluation,
        EdgeR0RecoveryBaseline,
        EdgeR0RecoveryMedia,
        EdgeR0RebuildObservation,
        EdgeR0IdentityRecoveryEvidence,
        EdgeR0RecoveryReattachment,
        tuple[EdgeR0RecoveryProofReceipt, ...],
        EdgeR0RecoveryCanary,
    ],
) -> EdgeR0Phase13Evaluation:
    return evaluate_r0_14(
        *artifacts,
        evaluated_at=_NOW + timedelta(minutes=3),
    )


def test_r0_14_passes_recovery_media_identity_restore() -> None:
    result = _evaluate(_artifacts())

    assert result.r0_14_passed is True
    assert result.issues == ()


def test_r0_14_passes_identity_rotation_with_binding() -> None:
    artifacts = list(_artifacts())
    identity = artifacts[5]
    rotated = identity.model_copy(
        update={
            "mode": IdentityRecoveryMode.ROTATE_IDENTITY_WITH_BINDING,
            "post_device_identity_id": "edge-r0-device-identity-rotated",
            "post_signing_key_id": "edge-r0-software-key-rotated",
            "recovery_material_sha256": None,
            "continuity_binding_sha256": None,
            "old_to_new_binding_sha256": _sha("old-to-new-identity-binding"),
            "upstream_enrollment_updated": True,
        }
    )
    artifacts[5] = rotated
    reattachment = artifacts[6].model_copy(
        update={"identity_recovery_id": rotated.identity_recovery_id}
    )
    artifacts[6] = reattachment
    artifacts[8] = artifacts[8].model_copy(
        update={
            "identity_recovery_mode": rotated.mode,
            "post_rebuild_identity_id": rotated.post_device_identity_id,
        }
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is True
    assert result.identity_recovery_valid is True


def test_r0_14_fails_wrong_media_digest() -> None:
    artifacts = list(_artifacts())
    artifacts[4] = artifacts[4].model_copy(
        update={"observed_media_image_digest": _sha("wrong-media-image")}
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is False
    assert result.rebuild_target_valid is False
    assert any("recovery-media digest mismatch" in issue for issue in result.issues)


def test_r0_14_fails_wrong_rebuilt_target_build() -> None:
    artifacts = list(_artifacts())
    artifacts[4] = artifacts[4].model_copy(update={"installed_build_sha": "b" * 40})

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is False
    assert result.rebuilt_software_valid is False
    assert any("rebuilt build mismatch" in issue for issue in result.issues)


def test_r0_14_fails_silent_identity_drift() -> None:
    artifacts = list(_artifacts())
    artifacts[5] = artifacts[5].model_copy(
        update={"post_device_identity_id": "silently-drifted-identity"}
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is False
    assert result.identity_recovery_valid is False
    assert any("restored device identity differs" in issue for issue in result.issues)


def test_r0_14_fails_rotation_without_binding() -> None:
    artifacts = list(_artifacts())
    identity = artifacts[5]
    artifacts[5] = identity.model_copy(
        update={
            "mode": IdentityRecoveryMode.ROTATE_IDENTITY_WITH_BINDING,
            "post_device_identity_id": "edge-r0-device-identity-rotated",
            "post_signing_key_id": "edge-r0-software-key-rotated",
            "recovery_material_sha256": None,
            "continuity_binding_sha256": None,
            "old_to_new_binding_sha256": None,
            "upstream_enrollment_updated": True,
        }
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is False
    assert result.identity_recovery_valid is False
    assert any("rotation lacks old-to-new binding" in issue for issue in result.issues)


def test_r0_14_fails_historical_evidence_rewrite() -> None:
    artifacts = list(_artifacts())
    artifacts[6] = artifacts[6].model_copy(
        update={
            "restored_local_history_commitment_sha256": _sha("rewritten-history")
        }
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is False
    assert result.historical_evidence_preserved is False
    assert any("historical commitment mismatch" in issue for issue in result.issues)


def test_r0_14_fails_replay_duplication() -> None:
    artifacts = list(_artifacts())
    reattachment = artifacts[6]
    first = reattachment.records[0].model_copy(
        update={"replayed_as_new_logical_event": True}
    )
    records = (first, reattachment.records[1])
    artifacts[6] = reattachment.model_copy(
        update={
            "records": records,
            "reconciliation_commitment_sha256": (
                build_recovery_reattachment_commitment(records)
            ),
        }
    )

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is False
    assert result.no_logical_replay_or_invented_ack is False
    assert any("replayed as new" in issue for issue in result.issues)


def test_r0_14_fails_checkpoint_regression() -> None:
    artifacts = list(_artifacts())
    artifacts[6] = artifacts[6].model_copy(update={"upstream_checkpoint_index": 399})

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is False
    assert result.checkpoints_consistent is False
    assert any("upstream checkpoint regressed" in issue for issue in result.issues)


def test_r0_14_fails_unresolved_final_queue() -> None:
    artifacts = list(_artifacts())
    dirty = _queue(depth=1, bytes_used=100, pending=1, synchronized=81)
    artifacts[6] = artifacts[6].model_copy(update={"final_queue_state": dirty})

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is False
    assert result.prior_phase_boundaries_preserved is False
    assert any("final queue did not reconcile cleanly" in issue for issue in result.issues)


def test_r0_14_fails_post_rebuild_canary() -> None:
    artifacts = list(_artifacts())
    artifacts[8] = artifacts[8].model_copy(update={"inclusion_valid": False})

    result = _evaluate(tuple(artifacts))

    assert result.r0_14_passed is False
    assert result.post_rebuild_canary_valid is False
    assert any("canary did not independently verify" in issue for issue in result.issues)
