from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ets.edge.device_identity import build_device_identity
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
from ets.qualification.physical_edge_phase1 import (
    BootTransition,
    EdgeR0ProvisioningReceipt,
    build_identity_snapshot,
    build_provisioning_receipt,
    evaluate_phase1,
)

_NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64
_DIGEST_C = "c" * 64
_DIGEST_D = "d" * 64
_DIGEST_E = "e" * 64
_DIGEST_F = "f" * 64
_BOOT_A = "11111111-1111-4111-8111-111111111111"
_BOOT_B = "22222222-2222-4222-8222-222222222222"


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


def _ready_manifest() -> EdgeCompactR0BenchManifest:
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
            source_revision="ed687ed12ec130b05478249ccd26fd01ca6069d0",
            artifact_digest=_DIGEST_A,
            configuration_digest=_DIGEST_B,
        ),
        trust=EdgeR0TrustPosture(),
        observer=IndependentObserver(
            observer_id="observer-lab-a",
            observer_host_id="bench-controller-001",
            observation_method="controller event journal plus independent receipts",
            independent_from_dut=True,
        ),
        verifier=IndependentVerifier(
            verifier_host_id="bench-controller-001",
            verifier_identity="hqp2-clean-verifier",
            command="python -m ets.hqp_verify",
            independent_from_dut=True,
        ),
        controls=_controls(),
        notes=("Synthetic W1-2 unit-test manifest.",),
    )


def _receipt(manifest: EdgeCompactR0BenchManifest) -> EdgeR0ProvisioningReceipt:
    return build_provisioning_receipt(
        manifest,
        receipt_id="r0-provision-001",
        operator_id="operator-a",
        installation_method="documented USB image installation",
        image_artifact_sha256=_DIGEST_C,
        install_receipt_sha256=_DIGEST_D,
        secret_scan_sha256=_DIGEST_E,
        observer_receipt_sha256=_DIGEST_F,
        started_at=_NOW + timedelta(minutes=5),
        completed_at=_NOW + timedelta(minutes=20),
    )


def test_r0_1_and_r0_2_phase_evidence_passes_across_distinct_boots() -> None:
    manifest = _ready_manifest()
    receipt = _receipt(manifest)
    identity = build_device_identity("11" * 32, "edge-signing-key-001")

    baseline = build_identity_snapshot(
        manifest,
        identity,
        boot_id=_BOOT_A,
        transition=BootTransition.INITIAL_BOOT,
        captured_at=_NOW + timedelta(minutes=21),
    )
    rebooted = build_identity_snapshot(
        manifest,
        identity,
        boot_id=_BOOT_B,
        transition=BootTransition.ORDERLY_REBOOT,
        captured_at=_NOW + timedelta(minutes=30),
        observer_receipt_sha256=_DIGEST_F,
    )

    result = evaluate_phase1(
        manifest,
        receipt,
        (baseline, rebooted),
        evaluated_at=_NOW + timedelta(minutes=31),
    )

    assert result.r0_1_passed is True
    assert result.r0_2_passed is True
    assert result.phase1_passed is True
    assert result.issues == ()
    assert result.stable_device_id == identity["device_id"]
    assert (
        result.stable_public_key_fingerprint_sha256
        == identity["public_key_fingerprint_sha256"]
    )
    assert result.disposition == "phase_evidence_only"


def test_identity_drift_is_retained_as_failed_r0_2_evaluation() -> None:
    manifest = _ready_manifest()
    receipt = _receipt(manifest)
    identity_a = build_device_identity("11" * 32, "edge-signing-key-001")
    identity_b = build_device_identity("22" * 32, "edge-signing-key-002")

    baseline = build_identity_snapshot(
        manifest,
        identity_a,
        boot_id=_BOOT_A,
        transition=BootTransition.INITIAL_BOOT,
        captured_at=_NOW + timedelta(minutes=21),
    )
    drifted = build_identity_snapshot(
        manifest,
        identity_b,
        boot_id=_BOOT_B,
        transition=BootTransition.ORDERLY_REBOOT,
        captured_at=_NOW + timedelta(minutes=30),
        observer_receipt_sha256=_DIGEST_F,
    )

    result = evaluate_phase1(
        manifest,
        receipt,
        (baseline, drifted),
        evaluated_at=_NOW + timedelta(minutes=31),
    )

    assert result.r0_1_passed is True
    assert result.r0_2_passed is False
    assert result.phase1_passed is False
    assert any("identity drift detected in device_id" in issue for issue in result.issues)
    assert any(
        "identity drift detected in public_key_fingerprint_sha256" in issue
        for issue in result.issues
    )


def test_same_linux_boot_cannot_satisfy_identity_persistence_gate() -> None:
    manifest = _ready_manifest()
    receipt = _receipt(manifest)
    identity = build_device_identity("11" * 32, "edge-signing-key-001")

    baseline = build_identity_snapshot(
        manifest,
        identity,
        boot_id=_BOOT_A,
        transition=BootTransition.INITIAL_BOOT,
        captured_at=_NOW + timedelta(minutes=21),
    )
    same_boot = build_identity_snapshot(
        manifest,
        identity,
        boot_id=_BOOT_A,
        transition=BootTransition.ORDERLY_REBOOT,
        captured_at=_NOW + timedelta(minutes=30),
        observer_receipt_sha256=_DIGEST_F,
    )

    result = evaluate_phase1(
        manifest,
        receipt,
        (baseline, same_boot),
        evaluated_at=_NOW + timedelta(minutes=31),
    )

    assert result.r0_2_passed is False
    assert any("two distinct Linux boot IDs" in issue for issue in result.issues)


def test_provisioning_binding_drift_fails_r0_1_without_rewriting_receipt() -> None:
    manifest = _ready_manifest()
    receipt = _receipt(manifest).model_copy(
        update={"edge_artifact_sha256": "9" * 64}
    )
    identity = build_device_identity("11" * 32, "edge-signing-key-001")
    baseline = build_identity_snapshot(
        manifest,
        identity,
        boot_id=_BOOT_A,
        transition=BootTransition.INITIAL_BOOT,
        captured_at=_NOW + timedelta(minutes=21),
    )
    rebooted = build_identity_snapshot(
        manifest,
        identity,
        boot_id=_BOOT_B,
        transition=BootTransition.ORDERLY_REBOOT,
        captured_at=_NOW + timedelta(minutes=30),
        observer_receipt_sha256=_DIGEST_F,
    )

    result = evaluate_phase1(
        manifest,
        receipt,
        (baseline, rebooted),
        evaluated_at=_NOW + timedelta(minutes=31),
    )

    assert result.r0_1_passed is False
    assert result.r0_2_passed is True
    assert result.phase1_passed is False
    assert any("Edge artifact digest does not match" in issue for issue in result.issues)


def test_phase_evidence_cannot_start_from_draft_bench_manifest() -> None:
    manifest = _ready_manifest().model_copy(
        update={"manifest_state": ManifestState.DRAFT}
    )

    with pytest.raises(ValueError, match="not ready for R0.1"):
        _receipt(manifest)


def test_orderly_reboot_snapshot_requires_independent_observer_receipt() -> None:
    manifest = _ready_manifest()
    identity = build_device_identity("11" * 32, "edge-signing-key-001")

    with pytest.raises(ValueError, match="external observer receipt"):
        build_identity_snapshot(
            manifest,
            identity,
            boot_id=_BOOT_B,
            transition=BootTransition.ORDERLY_REBOOT,
            captured_at=_NOW + timedelta(minutes=30),
        )


def test_identity_snapshot_contains_public_identity_only() -> None:
    manifest = _ready_manifest()
    identity = build_device_identity("11" * 32, "edge-signing-key-001")
    snapshot = build_identity_snapshot(
        manifest,
        identity,
        boot_id=_BOOT_A,
        transition=BootTransition.INITIAL_BOOT,
        captured_at=_NOW + timedelta(minutes=21),
    )
    payload = snapshot.model_dump(mode="json")

    assert payload["key_custody"] == "software_volume"
    assert payload["hardware_attested"] is False
    assert payload["credentials_embedded"] is False
    assert payload["private_keys_embedded"] is False
    assert "private_key" not in json_keys(payload)


def json_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(json_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(json_keys(item))
        return keys
    return set()
