from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

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
from ets.qualification.physical_edge_phase2 import EdgeR0Phase2Evaluation
from ets.qualification.physical_edge_phase3 import (
    EdgeR0OfflineCaptureRecord,
    EdgeR0OfflineProofReceipt,
    EdgeR0UpstreamAcceptanceReceipt,
    EdgeSyncStatusEvidence,
    build_network_loss_observation,
    build_offline_capture_record,
    build_offline_proof_receipt,
    build_offline_window,
    build_reconnect_summary,
    build_upstream_acceptance,
    evaluate_r0_4,
)

_NOW = datetime(2026, 9, 16, 14, 0, tzinfo=UTC)


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
                    vendor="Example Storage",
                    model="Example NVMe",
                    serial="SERIAL-001",
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
            source_revision="f7374e3c4185c682a4f64820d5ba0ebb6e3ab3f8",
            artifact_digest=_sha("edge-artifact"),
            configuration_digest=_sha("edge-config"),
        ),
        trust=EdgeR0TrustPosture(),
        observer=IndependentObserver(
            observer_id="observer-lab-a",
            observer_host_id="bench-controller-001",
            observation_method="controller journal plus external reachability probe",
            independent_from_dut=True,
        ),
        verifier=IndependentVerifier(
            verifier_host_id="bench-controller-001",
            verifier_identity="hqp2-clean-verifier",
            command="python -m ets.hqp_verify",
            independent_from_dut=True,
        ),
        controls=_controls(),
        notes=("Synthetic W1-4 unit-test manifest.",),
    )


def _phase2(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase2Evaluation:
    return EdgeR0Phase2Evaluation(
        evaluation_id="edge-r0-phase2-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        phase1_evaluation_id="edge-r0-phase1-passed",
        session_id="edge-r0-r03-001",
        evaluated_at=_NOW,
        attempted_event_count=100,
        authoritative_ack_count=100,
        committed_record_count=100,
        independently_verified_count=100,
        r0_3_passed=True,
        issues=(),
        disposition="phase_evidence_only",
        claim_boundary="r0_3_phase_evidence_not_a_physical_qualification_result",
    )


def _queue(
    *,
    depth: int,
    pending: int = 0,
    retryable: int = 0,
    terminal: int = 0,
    synchronized: int = 0,
    upstream: str,
) -> EdgeSyncStatusEvidence:
    return EdgeSyncStatusEvidence(
        queue_depth=depth,
        queue_bytes=depth * 512,
        pending=pending,
        in_flight=0,
        retryable_failure=retryable,
        terminal_failure=terminal,
        synchronized=synchronized,
        max_items=10_000,
        max_bytes=128 * 1024 * 1024,
        oldest_pending_age_seconds=1.0 if depth else None,
        last_successful_sync=None,
        last_failure=None,
        upstream_status=upstream,
    )


def _fixture() -> tuple[
    EdgeCompactR0BenchManifest,
    EdgeR0Phase2Evaluation,
    object,
    object,
    tuple[EdgeR0OfflineCaptureRecord, ...],
    tuple[EdgeR0OfflineProofReceipt, ...],
    object,
    tuple[EdgeR0UpstreamAcceptanceReceipt, ...],
]:
    manifest = _manifest()
    phase2 = _phase2(manifest)
    observation = build_network_loss_observation(
        manifest,
        observer_id="observer-lab-a",
        controller_id="bench-controller-001",
        loss_started_at=_NOW + timedelta(minutes=1),
        loss_confirmed_at=_NOW + timedelta(minutes=1, seconds=2),
        controller_receipt_sha256=_sha("loss-controller"),
        independent_observation_sha256=_sha("loss-observer"),
    )
    window = build_offline_window(
        manifest,
        phase2,
        observation,
        window_id="edge-r0-r04-window-001",
        started_at=_NOW + timedelta(minutes=1, seconds=3),
        completed_at=_NOW + timedelta(minutes=2),
        attempted_event_count=10,
        pre_loss_queue=_queue(depth=0, synchronized=100, upstream="online"),
        outage_queue=_queue(depth=10, pending=10, synchronized=100, upstream="offline"),
        resource_observation_sha256=_sha("offline-resource-observation"),
    )

    captures: list[EdgeR0OfflineCaptureRecord] = []
    proofs: list[EdgeR0OfflineProofReceipt] = []
    acceptances: list[EdgeR0UpstreamAcceptanceReceipt] = []
    for sequence in range(1, 11):
        payload_digest = _sha(f"offline-payload-{sequence}")
        receipt = WebhookCaptureReceipt(
            event_id=f"evt_offline_{sequence:04d}",
            evidence_id=f"webhook:r0-controller:{payload_digest[:48]}",
            log_index=100 + sequence,
            event_hash=_sha(f"offline-event-{sequence}"),
            content_hash=payload_digest,
            content_hash_alg="sha256",
            byte_size=64 + sequence,
            event_url=f"/api/v1/events/evt_offline_{sequence:04d}",
            proof_url=f"/api/v1/proofs/inclusion/evt_offline_{sequence:04d}",
            bundle_url=f"/api/v1/bundles/evt_offline_{sequence:04d}",
            tree_head_url="/api/v1/log/head",
            sync_state="pending",
            sync_status_url="/edge/v1/sync/status",
        )
        record = build_offline_capture_record(
            window,
            receipt,
            sequence_number=sequence,
            captured_at=window.started_at + timedelta(seconds=sequence * 3),
            request_payload_sha256=payload_digest,
            receipt_artifact_sha256=_sha(f"offline-receipt-{sequence}"),
            proof_artifact_sha256=_sha(f"offline-proof-{sequence}"),
        )
        captures.append(record)
        proofs.append(
            build_offline_proof_receipt(
                record,
                {"valid": True},
                verifier_id="ets-verify-offline",
                verifier_host_id="bench-controller-001",
                verifier_build_sha256=_sha("verifier-build"),
                verification_result_sha256=_sha(f"verify-{sequence}"),
                verified_at=_NOW + timedelta(minutes=2, seconds=sequence),
                independent_execution_context=True,
            )
        )
        acceptances.append(
            build_upstream_acceptance(
                record,
                idempotency_key=f"idem-offline-{sequence:04d}",
                accepted_at=_NOW + timedelta(minutes=3, seconds=sequence),
                acknowledgement_hash=_sha(f"ack-{sequence}"),
                upstream_artifact_sha256=_sha(f"upstream-{sequence}"),
                upstream_observer_id="upstream-observer-001",
            )
        )

    reconnect = build_reconnect_summary(
        window,
        reconnect_observed_at=_NOW + timedelta(minutes=3),
        sync_completed_at=_NOW + timedelta(minutes=3, seconds=20),
        independent_reconnect_observation_sha256=_sha("reconnect-observation"),
        initial_queue=_queue(depth=10, pending=10, synchronized=100, upstream="online"),
        final_queue=_queue(depth=0, synchronized=110, upstream="online"),
        sync_run_artifact_sha256=(_sha("sync-run-1"),),
    )
    return (
        manifest,
        phase2,
        observation,
        window,
        tuple(captures),
        tuple(proofs),
        reconnect,
        tuple(acceptances),
    )


def test_r0_4_passes_for_offline_capture_reconnect_and_exact_once_sync() -> None:
    manifest, phase2, observation, window, captures, proofs, reconnect, acceptances = _fixture()
    result = evaluate_r0_4(
        manifest,
        phase2,
        observation,
        window,
        captures,
        proofs,
        reconnect,
        acceptances,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_4_passed is True
    assert result.issues == ()
    assert result.locally_committed_count == 10
    assert result.independently_verified_count == 10
    assert result.synchronized_exactly_once_count == 10
    assert result.disposition == "phase_evidence_only"


def test_missing_upstream_acceptance_fails_r0_4() -> None:
    manifest, phase2, observation, window, captures, proofs, reconnect, acceptances = _fixture()
    result = evaluate_r0_4(
        manifest,
        phase2,
        observation,
        window,
        captures,
        proofs,
        reconnect,
        acceptances[:-1],
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_4_passed is False
    assert result.synchronized_exactly_once_count == 9
    assert any("missing upstream acceptance" in issue for issue in result.issues)


def test_unresolved_post_reconnect_backlog_fails_r0_4() -> None:
    manifest, phase2, observation, window, captures, proofs, reconnect, acceptances = _fixture()
    reconnect = reconnect.model_copy(
        update={
            "final_queue": _queue(
                depth=1,
                retryable=1,
                synchronized=109,
                upstream="online",
            )
        }
    )
    result = evaluate_r0_4(
        manifest,
        phase2,
        observation,
        window,
        captures,
        proofs,
        reconnect,
        acceptances,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_4_passed is False
    assert any("backlog remains" in issue for issue in result.issues)
    assert any("failed queue state" in issue for issue in result.issues)


def test_non_independent_offline_proof_fails_r0_4() -> None:
    manifest, phase2, observation, window, captures, proofs, reconnect, acceptances = _fixture()
    changed = list(proofs)
    changed[0] = changed[0].model_copy(update={"independent_execution_context": False})
    result = evaluate_r0_4(
        manifest,
        phase2,
        observation,
        window,
        captures,
        tuple(changed),
        reconnect,
        acceptances,
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_4_passed is False
    assert result.independently_verified_count == 9
    assert any("independent proof verification failed" in issue for issue in result.issues)


def test_duplicate_idempotency_key_fails_r0_4() -> None:
    manifest, phase2, observation, window, captures, proofs, reconnect, acceptances = _fixture()
    changed = list(acceptances)
    changed[1] = changed[1].model_copy(update={"idempotency_key": changed[0].idempotency_key})
    result = evaluate_r0_4(
        manifest,
        phase2,
        observation,
        window,
        captures,
        proofs,
        reconnect,
        tuple(changed),
        evaluated_at=_NOW + timedelta(minutes=4),
    )

    assert result.r0_4_passed is False
    assert any("duplicate idempotency keys" in issue for issue in result.issues)


def test_offline_capture_rejects_synchronized_receipt() -> None:
    _, _, _, window, _, _, _, _ = _fixture()
    payload_digest = _sha("bad-offline-payload")
    receipt = WebhookCaptureReceipt(
        event_id="evt_bad_offline",
        evidence_id="webhook:r0-controller:bad",
        log_index=999,
        event_hash=_sha("bad-event"),
        content_hash=payload_digest,
        content_hash_alg="sha256",
        byte_size=64,
        event_url="/api/v1/events/evt_bad_offline",
        proof_url="/api/v1/proofs/inclusion/evt_bad_offline",
        bundle_url="/api/v1/bundles/evt_bad_offline",
        tree_head_url="/api/v1/log/head",
        sync_state="synchronized",
        sync_status_url="/edge/v1/sync/status",
    )
    with pytest.raises(ValueError, match="pending or retryable_failure"):
        build_offline_capture_record(
            window,
            receipt,
            sequence_number=1,
            captured_at=window.started_at + timedelta(seconds=3),
            request_payload_sha256=payload_digest,
            receipt_artifact_sha256=_sha("bad-receipt"),
            proof_artifact_sha256=_sha("bad-proof"),
        )
