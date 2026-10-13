from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

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
from ets.qualification.physical_edge_final import (
    BuildTransitionKind,
    HistoricalRunState,
    QualificationIndexClaimV1,
    R0HistoricalRunReference,
    R0HqpPackageBinding,
    R0PhaseEvidenceSelection,
    R0PhaseId,
    Wave1R0PublicationReceipt,
    assemble_wave1_r0_package,
    build_operator_trace,
    build_qualification_index_claim,
    evaluate_wave1_r0_publication,
)
from ets.qualification.profile import FinalQualificationState
from ets.qualification.verifier import (
    HardwareQualificationVerification,
    VerificationOutcome,
)

_NOW = datetime(2026, 9, 19, 20, 0, tzinfo=UTC)
_BUILD_A = "a" * 40
_BUILD_B = "b" * 40
_CONFIG_A = hashlib.sha256(b"config-a").hexdigest()
_CONFIG_B = hashlib.sha256(b"config-b").hexdigest()


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
        manifest_id="edge-r0-final-lab-001",
        qualification_class="EDGE_COMPACT_R0",
        manifest_state=ManifestState.READY_FOR_QUALIFICATION,
        collected_at=_NOW,
        dut=EdgeR0Dut(
            manufacturer="Example Manufacturer",
            model="Example Mini PC",
            hardware_revision="rev-a",
            asset_id="EDGE-R0-FINAL-001",
            cpu_architecture="x86_64",
            cpu_model="Example CPU",
            memory_bytes=16 * 1024**3,
            storage=(
                StorageDevice(
                    name="nvme0n1",
                    vendor="Example Storage",
                    model="Example NVMe",
                    serial="FINAL-SERIAL",
                    firmware="1.0",
                    size_bytes=512 * 1024**3,
                    transport="nvme",
                ),
            ),
            network=(
                NetworkInterface(
                    name="enp1s0",
                    mac_address="02:00:00:00:00:10",
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
            hostname="edge-r0-final",
        ),
        build=EdgeBuildBinding(
            source_revision=_BUILD_A,
            artifact_digest=_sha("artifact-a"),
            configuration_digest=_CONFIG_A,
        ),
        trust=EdgeR0TrustPosture(),
        observer=IndependentObserver(
            observer_id="observer-final",
            observer_host_id="controller-final",
            observation_method="independent qualification controller",
            independent_from_dut=True,
        ),
        verifier=IndependentVerifier(
            verifier_host_id="controller-final",
            verifier_identity="hqp2-clean-verifier",
            command="python -m ets.hqp_verify",
            independent_from_dut=True,
        ),
        controls=_controls(),
        notes=("Synthetic final-gate unit-test manifest.",),
    )


def _evaluation_id(number: int) -> str:
    if number in {1, 2}:
        return "edge-r0-phase1-shared"
    return f"edge-r0-phase{number - 1}-selected"


def _phases() -> tuple[R0PhaseEvidenceSelection, ...]:
    items: list[R0PhaseEvidenceSelection] = []
    current_build = _BUILD_A
    current_config = _CONFIG_A
    identity = "edge-r0-device-identity"

    for number, phase_id in enumerate(R0PhaseId, start=1):
        source_build = current_build
        source_config = current_config
        transition = BuildTransitionKind.UNCHANGED
        transition_digest: str | None = None

        if number == 12:
            current_build = _BUILD_B
            current_config = _CONFIG_B
            transition = BuildTransitionKind.VALID_UPGRADE
            transition_digest = _sha("r0-12-upgrade-binding")
        elif number == 13:
            current_build = _BUILD_A
            current_config = _CONFIG_A
            transition = BuildTransitionKind.ROLLBACK_RECOVERY
            transition_digest = _sha("r0-13-rollback-binding")
        elif number == 14:
            transition = BuildTransitionKind.RECOVERY_REBUILD
            transition_digest = _sha("r0-14-recovery-binding")

        before = 1000 + ((number - 1) * 10)
        after = before + 5
        predecessor = items[-1].evaluation_id if items else None
        evaluation_id = _evaluation_id(number)
        evaluation_digest = (
            _sha("phase1-shared-evaluation")
            if number in {1, 2}
            else _sha(f"phase-{number}-evaluation")
        )
        schema_phase = 1 if number in {1, 2} else number - 1
        items.append(
            R0PhaseEvidenceSelection(
                phase_id=phase_id,
                evaluation_id=evaluation_id,
                evaluation_schema_version=(
                    f"ets.edge-compact-r0-phase{schema_phase}-evaluation.v1"
                ),
                manifest_id="edge-r0-final-lab-001",
                asset_id="EDGE-R0-FINAL-001",
                evaluated_at=_NOW + timedelta(minutes=number),
                evaluation_sha256=evaluation_digest,
                predecessor_evaluation_id=predecessor,
                claim_boundary=f"r0_{number}_phase_evidence_only",
                source_build_sha=source_build,
                resulting_build_sha=current_build,
                source_configuration_digest=source_config,
                resulting_configuration_digest=current_config,
                build_transition=transition,
                transition_binding_sha256=transition_digest,
                identity_before=identity,
                identity_after=identity,
                local_checkpoint_before=before,
                local_checkpoint_after=after,
                upstream_checkpoint_before=before,
                upstream_checkpoint_after=after,
                artifact_sha256=(_sha(f"phase-{number}-artifact"),),
                observer_receipt_sha256=(_sha(f"phase-{number}-observer"),),
                verifier_receipt_sha256=(_sha(f"phase-{number}-verifier"),),
                external_observation_required=True,
                independent_verification_required=True,
            )
        )
    return tuple(items)


def _verification(hqp: R0HqpPackageBinding) -> HardwareQualificationVerification:
    payload: dict[str, object] = {
        "schema_version": "ets.hardware-qualification-verification.v1",
        "verification_id": "hqp2-final-verification",
        "verifier_id": "hqp2-clean-verifier",
        "verifier_build_digest_sha256": _sha("hqp2-verifier-build"),
        "independent_execution_context": True,
        "challenge_nonce": "final-wave1-challenge",
        "profile_id": hqp.profile_id,
        "profile_version": hqp.profile_version,
        "profile_digest_sha256": hqp.profile_digest_sha256,
        "run_id": hqp.run_id,
        "run_digest_sha256": hqp.run_digest_sha256,
        "report_id": hqp.report_id,
        "report_digest_sha256": hqp.report_digest_sha256,
        "claimed_disposition": "qualified",
        "eligible_for_claimed_disposition": True,
        "outcome": VerificationOutcome.VALID.value,
        "checks": [],
        "verified_artifact_ids": ["artifact-manifest"],
        "missing_artifact_ids": [],
        "mismatched_artifact_ids": [],
        "verified_evidence_object_ids": list(hqp.evidence_object_ids),
        "invalid_evidence_object_ids": [],
        "trust_boundary": [
            "Verifier runs independently from the DUT.",
            "Digest verification is bounded to retained package bytes.",
        ],
        "claim_boundary": (
            "bounded_hqp_independent_verification_not_complete_observation_truth_"
            "compliance_safety_or_ga_proof"
        ),
    }
    payload["verification_digest_sha256"] = canonical_sha256(payload)
    return HardwareQualificationVerification.model_validate_json(json.dumps(payload))


def _package():
    manifest = _manifest()
    phases = _phases()
    trace = build_operator_trace(
        trace_id="operator-trace-001",
        manifest_id=manifest.manifest_id,
        asset_id="EDGE-R0-FINAL-001",
        source_observation_id="source-observation-001",
        source_artifact_sha256=_sha("source-artifact"),
        ingress_receipt_sha256=_sha("ingress-receipt"),
        event_id="representative-event-001",
        evidence_object_id="evidence-object-001",
        evidence_object_sha256=_sha("evidence-object"),
        proof_artifact_sha256=_sha("representative-proof"),
        export_bundle_sha256=_sha("export-bundle"),
        independent_verification_sha256=_sha("operator-independent-verification"),
        reviewer_id="independent-reviewer",
        reviewed_at=_NOW + timedelta(hours=1),
    )
    hqp = R0HqpPackageBinding(
        profile_id="ets.edge.hardware-qualification.v1",
        profile_version="1.0",
        profile_digest_sha256=_sha("profile"),
        run_id="edge-r0-final-hqp-run",
        run_digest_sha256=_sha("hqp-run"),
        report_id="edge-r0-final-hqp-report",
        report_digest_sha256=_sha("hqp-report"),
        run_package_locator="evidence/wave1/r0/hqp-run.json",
        qualification_report_locator="evidence/wave1/r0/hqp-report.json",
        artifact_manifest_digest_sha256=_sha("artifact-manifest"),
        evidence_object_ids=("evidence-object-001",),
        hqp_input_package_sha256=_sha("hqp-input-package"),
    )
    historical = (
        R0HistoricalRunReference(
            run_id="failed-run-001",
            state=HistoricalRunState.FAILED,
            package_sha256=_sha("failed-run-package"),
            reason="Earlier bounded physical run failed a declared gate.",
        ),
    )
    package = assemble_wave1_r0_package(
        manifest,
        phases=phases,
        operator_trace=trace,
        historical_runs=historical,
        hqp=hqp,
        runtime_id="ubuntu-24.04-x86_64",
        final_build_sha=_BUILD_A,
        final_artifact_digest=_sha("artifact-a"),
        final_configuration_digest=_CONFIG_A,
        created_at=_NOW + timedelta(hours=2),
    )
    return package, hqp


def _published_artifacts():
    package, hqp = _package()
    verification = _verification(hqp)
    claim = build_qualification_index_claim(
        package,
        verification,
        capability_maturity="prototype",
        verification_result_locator="evidence/wave1/r0/hqp2-verification.json",
        effective_at=_NOW + timedelta(hours=3),
    )
    publication = Wave1R0PublicationReceipt(
        claim_id=claim.claim_id,
        qualification_state=claim.qualification_state,
        registry_locator="docs/qualification/qualification-index-v1.json",
        registry_artifact_sha256=_sha("published-index"),
        published_at=_NOW + timedelta(hours=4),
        package_root_sha256=package.package_root_sha256,
        hqp2_verification_digest_sha256=verification.verification_digest_sha256,
        publication_observer_sha256=_sha("publication-observer"),
    )
    return package, verification, claim, publication


def test_final_wave1_r0_publication_gate_passes() -> None:
    package, verification, claim, publication = _published_artifacts()

    result = evaluate_wave1_r0_publication(
        package,
        verification,
        claim,
        publication,
        evaluated_at=_NOW + timedelta(hours=5),
    )

    assert result.wave1_r0_publication_gate_passed is True
    assert result.qualification_state is FinalQualificationState.QUALIFIED
    assert result.issues == ()


def test_final_package_rejects_missing_phase() -> None:
    package, _ = _package()
    raw = package.model_dump(mode="python")
    raw["phases"] = raw["phases"][:-1]
    raw["package_root_sha256"] = _sha("not-relevant")

    with pytest.raises(ValidationError):
        package.__class__.model_validate(raw)


def test_final_package_rejects_broken_predecessor_chain() -> None:
    package, _ = _package()
    raw = package.model_dump(mode="python")
    raw["phases"][5]["predecessor_evaluation_id"] = "wrong-predecessor"
    raw["package_root_sha256"] = _sha("not-relevant")

    with pytest.raises(ValidationError, match="predecessor"):
        package.__class__.model_validate(raw)


def test_final_package_rejects_wrong_dut_phase() -> None:
    package, _ = _package()
    raw = package.model_dump(mode="python")
    raw["phases"][8]["asset_id"] = "OTHER-DUT"
    raw["package_root_sha256"] = _sha("not-relevant")

    with pytest.raises(ValidationError, match="another DUT"):
        package.__class__.model_validate(raw)


def test_final_package_rejects_checkpoint_regression_between_phases() -> None:
    package, _ = _package()
    raw = package.model_dump(mode="python")
    raw["phases"][8]["local_checkpoint_before"] = 1
    raw["package_root_sha256"] = _sha("not-relevant")

    with pytest.raises(ValidationError, match="checkpoint regressed"):
        package.__class__.model_validate(raw)


def test_publication_fails_invalid_hqp2_result() -> None:
    package, verification, claim, publication = _published_artifacts()
    failed = verification.model_copy(
        update={
            "outcome": VerificationOutcome.INVALID,
            "eligible_for_claimed_disposition": False,
        }
    )

    result = evaluate_wave1_r0_publication(
        package,
        failed,
        claim,
        publication,
        evaluated_at=_NOW + timedelta(hours=5),
    )

    assert result.wave1_r0_publication_gate_passed is False
    assert result.hqp2_independent_and_valid is False
    assert result.hqp2_disposition_eligible is False


def test_publication_fails_wrong_hqp_run_binding() -> None:
    package, verification, claim, publication = _published_artifacts()
    failed = verification.model_copy(update={"run_digest_sha256": _sha("wrong-run")})

    result = evaluate_wave1_r0_publication(
        package,
        failed,
        claim,
        publication,
        evaluated_at=_NOW + timedelta(hours=5),
    )

    assert result.wave1_r0_publication_gate_passed is False
    assert result.hqp_package_binding_valid is False
    assert any("run digest" in issue for issue in result.issues)


def test_publication_fails_wrong_index_state() -> None:
    package, verification, claim, publication = _published_artifacts()
    failed_claim = claim.model_copy(
        update={"qualification_state": FinalQualificationState.FAILED}
    )

    result = evaluate_wave1_r0_publication(
        package,
        verification,
        failed_claim,
        publication,
        evaluated_at=_NOW + timedelta(hours=5),
    )

    assert result.wave1_r0_publication_gate_passed is False
    assert result.index_claim_valid is False
    assert any("qualification state" in issue for issue in result.issues)


def test_publication_fails_wrong_package_receipt_binding() -> None:
    package, verification, claim, publication = _published_artifacts()
    failed_publication = publication.model_copy(
        update={"package_root_sha256": _sha("other-package")}
    )

    result = evaluate_wave1_r0_publication(
        package,
        verification,
        claim,
        failed_publication,
        evaluated_at=_NOW + timedelta(hours=5),
    )

    assert result.wave1_r0_publication_gate_passed is False
    assert result.publication_receipt_valid is False


def test_qualified_with_deviation_maps_to_hqp5_state() -> None:
    package, hqp = _package()
    verification = _verification(hqp).model_copy(
        update={"claimed_disposition": "qualified_with_deviation"}
    )
    claim = build_qualification_index_claim(
        package,
        verification,
        capability_maturity="prototype",
        verification_result_locator="evidence/wave1/r0/hqp2-verification.json",
        effective_at=_NOW + timedelta(hours=3),
    )

    assert isinstance(claim, QualificationIndexClaimV1)
    assert (
        claim.qualification_state
        is FinalQualificationState.QUALIFIED_WITH_DEVIATION
    )
