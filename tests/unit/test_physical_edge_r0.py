from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

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
    assert_ready_for_qualification,
    load_manifest,
    readiness_issues,
)

_ROOT = Path(__file__).parents[2]
_TEMPLATE = (
    _ROOT
    / "docs"
    / "qualification"
    / "manifests"
    / "edge-compact-r0-template.json"
)
_NOW = datetime(2026, 9, 15, 23, 50, tzinfo=UTC)
_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64


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
            os_version_id="22.04",
            os_pretty_name="Ubuntu 22.04",
            kernel_release="6.8.0-test",
            python_version="3.12.10",
            hostname="edge-r0-001",
        ),
        build=EdgeBuildBinding(
            source_revision="51b5c0dc73b4402900530ade40c9ec569228c4e4",
            artifact_digest=_DIGEST_A,
            configuration_digest=_DIGEST_B,
        ),
        trust=EdgeR0TrustPosture(),
        observer=IndependentObserver(
            observer_id="observer-lab-a",
            observer_host_id="bench-controller-001",
            observation_method=(
                "controller event journal plus independent link/power receipts"
            ),
            independent_from_dut=True,
        ),
        verifier=IndependentVerifier(
            verifier_host_id="bench-controller-001",
            verifier_identity="hqp2-clean-verifier",
            command="python -m ets.hqp_verify",
            independent_from_dut=True,
        ),
        controls=_controls(),
        notes=("Synthetic unit-test manifest; not physical qualification evidence.",),
    )


def test_completed_manifest_is_ready_to_begin_physical_corpus() -> None:
    manifest = _ready_manifest()

    assert readiness_issues(manifest) == ()
    assert_ready_for_qualification(manifest)


def test_repository_template_is_deliberately_blocked() -> None:
    manifest = load_manifest(_TEMPLATE.read_bytes())
    issues = readiness_issues(manifest)

    assert manifest.manifest_state is ManifestState.DRAFT
    assert issues
    assert "manifest_state must be ready_for_qualification before physical execution" in issues
    assert "claim-critical DUT fields have not been confirmed by an operator" in issues
    assert "Edge artifact SHA-256 digest is missing" in issues
    assert "external observer is not declared independent from the DUT" in issues


def test_complete_manifest_stays_blocked_until_operator_promotes_state() -> None:
    manifest = _ready_manifest().model_copy(
        update={"manifest_state": ManifestState.DRAFT}
    )

    assert readiness_issues(manifest) == (
        "manifest_state must be ready_for_qualification before physical execution",
    )


def test_ready_declaration_with_missing_build_is_rejected_by_readiness_gate() -> None:
    manifest = _ready_manifest().model_copy(
        update={
            "build": EdgeBuildBinding(
                source_revision=None,
                artifact_digest=None,
                configuration_digest=None,
            )
        }
    )

    issues = readiness_issues(manifest)
    assert "Edge source revision is missing" in issues
    assert "manifest declares ready_for_qualification while readiness blockers remain" in issues
    with pytest.raises(ValueError, match="not ready"):
        assert_ready_for_qualification(manifest)


def test_r0_trust_posture_cannot_claim_hardware_attestation() -> None:
    with pytest.raises(ValueError):
        EdgeR0TrustPosture(hardware_attested=True)  # type: ignore[arg-type]


def test_disruptive_control_requires_operator_approval() -> None:
    with pytest.raises(ValueError, match="operator approval"):
        BenchControl(
            kind=BenchControlKind.POWER,
            control_id="unsafe-power-control",
            method="switched PDU",
            independent_observation_method="external power meter",
            destructive_or_disruptive=True,
            operator_approval_required=False,
            bootstrap_cli_executes_action=False,
        )


def test_dut_cannot_be_its_own_observer_or_verifier_host() -> None:
    manifest = _ready_manifest().model_copy(
        update={
            "observer": IndependentObserver(
                observer_id="observer-on-dut",
                observer_host_id="EDGE-R0-001",
                observation_method="invalid same-host observation",
                independent_from_dut=True,
            )
        }
    )

    expected = "DUT asset_id must not also identify the observer/verifier host"
    assert expected in readiness_issues(manifest)
