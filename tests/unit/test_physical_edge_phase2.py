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
from ets.qualification.physical_edge_phase1 import EdgeR0Phase1Evaluation
from ets.qualification.physical_edge_phase2 import (
    EdgeR0CaptureRecord,
    EdgeR0IndependentProofReceipt,
    EdgeR0SustainedCaptureSession,
    build_capture_record,
    build_capture_session,
    build_proof_receipt,
    evaluate_r0_3,
)

_NOW = datetime(2026, 9, 16, 13, 30, tzinfo=UTC)


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
            source_revision="bbfe7622c2fae4b8d6956b5288ec672f3b9fc021",
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
        notes=("Synthetic W1-3 unit-test manifest.",),
    )


def _phase1(manifest: EdgeCompactR0BenchManifest) -> EdgeR0Phase1Evaluation:
    return EdgeR0Phase1Evaluation(
        evaluation_id="edge-r0-phase1-passed",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-001",
        evaluated_at=_NOW + timedelta(minutes=10),
        provisioning_receipt_id="provisioning-001",
        identity_snapshot_ids=("identity-a", "identity-b"),
        r0_1_passed=True,
        r0_2_passed=True,
        phase1_passed=True,
        stable_device_id="ets-edge:0123456789abcdef0123456789abcdef",
        stable_public_key_fingerprint_sha256=_sha("public-key"),
        issues=(),
        disposition="phase_evidence_only",
        claim_boundary="r0_1_r0_2_phase_evidence_not_a_physical_qualification_result",
    )


def _session(
    manifest: EdgeCompactR0BenchManifest,
    phase1: EdgeR0Phase1Evaluation,
) -> EdgeR0SustainedCaptureSession:
    return build_capture_session(
        manifest,
        phase1,
        session_id="edge-r0-r03-001",
        source_id="r0-controller",
        controller_id="bench-controller-001",
        started_at=_NOW + timedelta(minutes=20),
        completed_at=_NOW + timedelta(minutes=22),
        attempted_event_count=100,
        workload_plan_sha256=_sha("workload-plan"),
        resource_observation_sha256=_sha("resource-observation"),
        controller_receipt_sha256=_sha("controller-receipt"),
    )


def _capture_records(
    session: EdgeR0SustainedCaptureSession,
    count: int = 100,
) -> tuple[EdgeR0CaptureRecord, ...]:
    records: list[EdgeR0CaptureRecord] = []
    for sequence in range(1, count + 1):
        payload_digest = _sha(f"payload-{sequence}")
        receipt = WebhookCaptureReceipt(
            event_id=f"evt_webhook_{sequence:04d}",
            evidence_id=f"webhook:r0-controller:{payload_digest[:48]}",
            log_index=sequence - 1,
            event_hash=_sha(f"event-{sequence}"),
            content_hash=payload_digest,
            content_hash_alg="sha256",
            byte_size=32 + sequence,
            event_url=f"/api/v1/events/evt_webhook_{sequence:04d}",
            proof_url=f"/api/v1/proofs/inclusion/evt_webhook_{sequence:04d}",
            bundle_url=f"/api/v1/bundles/evt_webhook_{sequence:04d}",
            tree_head_url="/api/v1/log/head",
            sync_state="pending",
            sync_status_url="/edge/v1/sync/status",
        )
        records.append(
            build_capture_record(
                session,
                receipt,
                sequence_number=sequence,
                captured_at=session.started_at + timedelta(seconds=sequence),
                request_payload_sha256=payload_digest,
                receipt_artifact_sha256=_sha(f"receipt-{sequence}"),
                event_artifact_sha256=_sha(f"event-artifact-{sequence}"),
                proof_artifact_sha256=_sha(f"proof-artifact-{sequence}"),
                bundle_artifact_sha256=_sha(f"bundle-artifact-{sequence}"),
                tree_head_artifact_sha256=_sha(f"tree-head-{sequence}"),
            )
        )
    return tuple(records)


def _proof_receipts(
    records: tuple[EdgeR0CaptureRecord, ...],
) -> tuple[EdgeR0IndependentProofReceipt, ...]:
    return tuple(
        build_proof_receipt(
            record,
            {"valid": True, "standing_status": "checkpoint_only"},
            verifier_id="ets-verify-offline",
            verifier_host_id="bench-controller-001",
            verifier_build_sha256=_sha("verifier-build"),
            proof_artifact_sha256=record.proof_artifact_sha256,
            verification_result_sha256=_sha(f"verification-result-{record.sequence_number}"),
            verified_at=_NOW + timedelta(minutes=30, seconds=record.sequence_number),
            independent_execution_context=True,
        )
        for record in records
    )


def test_r0_3_passes_for_complete_sustained_capture_and_independent_verification() -> None:
    manifest = _manifest()
    phase1 = _phase1(manifest)
    session = _session(manifest, phase1)
    records = _capture_records(session)
    receipts = _proof_receipts(records)

    result = evaluate_r0_3(
        manifest,
        phase1,
        session,
        records,
        receipts,
        evaluated_at=_NOW + timedelta(minutes=40),
    )

    assert result.r0_3_passed is True
    assert result.issues == ()
    assert result.attempted_event_count == 100
    assert result.authoritative_ack_count == 100
    assert result.committed_record_count == 100
    assert result.independently_verified_count == 100
    assert result.disposition == "phase_evidence_only"


def test_acknowledgement_commit_divergence_fails_r0_3() -> None:
    manifest = _manifest()
    phase1 = _phase1(manifest)
    session = _session(manifest, phase1)
    records = _capture_records(session, count=99)
    receipts = _proof_receipts(records)

    result = evaluate_r0_3(
        manifest,
        phase1,
        session,
        records,
        receipts,
        evaluated_at=_NOW + timedelta(minutes=40),
    )

    assert result.r0_3_passed is False
    assert any("acknowledgement/commit count" in issue for issue in result.issues)
    assert any("every attempted sequence" in issue for issue in result.issues)


def test_missing_independent_proof_receipt_fails_r0_3() -> None:
    manifest = _manifest()
    phase1 = _phase1(manifest)
    session = _session(manifest, phase1)
    records = _capture_records(session)
    receipts = _proof_receipts(records[:-1])

    result = evaluate_r0_3(
        manifest,
        phase1,
        session,
        records,
        receipts,
        evaluated_at=_NOW + timedelta(minutes=40),
    )

    assert result.r0_3_passed is False
    assert result.independently_verified_count == 99
    assert any("missing independent proof verification" in issue for issue in result.issues)


def test_non_independent_verifier_fails_r0_3() -> None:
    manifest = _manifest()
    phase1 = _phase1(manifest)
    session = _session(manifest, phase1)
    records = _capture_records(session)
    receipts = list(_proof_receipts(records))
    receipts[0] = receipts[0].model_copy(update={"independent_execution_context": False})

    result = evaluate_r0_3(
        manifest,
        phase1,
        session,
        records,
        tuple(receipts),
        evaluated_at=_NOW + timedelta(minutes=40),
    )

    assert result.r0_3_passed is False
    assert result.independently_verified_count == 99
    assert any("verifier was not independent" in issue for issue in result.issues)


def test_capture_session_bound_to_wrong_dut_fails_r0_3() -> None:
    manifest = _manifest()
    phase1 = _phase1(manifest)
    session = _session(manifest, phase1).model_copy(update={"asset_id": "EDGE-R0-999"})
    records = _capture_records(session)
    receipts = _proof_receipts(records)

    result = evaluate_r0_3(
        manifest,
        phase1,
        session,
        records,
        receipts,
        evaluated_at=_NOW + timedelta(minutes=40),
    )

    assert result.r0_3_passed is False
    assert any("different DUT manifest" in issue for issue in result.issues)


def test_r0_3_session_rejects_smoke_test_scale() -> None:
    manifest = _manifest()
    phase1 = _phase1(manifest)

    with pytest.raises(ValueError, match="at least 100 attempted events"):
        build_capture_session(
            manifest,
            phase1,
            session_id="too-small",
            source_id="r0-controller",
            controller_id="bench-controller-001",
            started_at=_NOW,
            completed_at=_NOW + timedelta(minutes=2),
            attempted_event_count=99,
            workload_plan_sha256=_sha("workload-plan"),
            resource_observation_sha256=_sha("resource-observation"),
            controller_receipt_sha256=_sha("controller-receipt"),
        )
