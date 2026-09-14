from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ets.core.canonical_json import canonical_sha256
from ets.qualification.edge_corpus import (
    EdgeHardwareQualificationCorpus,
    load_edge_corpus,
    load_edge_profile,
    render_edge_execution_plan,
    seal_edge_lab_run,
    validate_edge_corpus_against_profile,
    validate_edge_run_against_corpus,
)
from ets.qualification.hardware import (
    ArtifactReference,
    AssertionResult,
    BuildIdentity,
    DeviceIdentity,
    EvidenceObjectReference,
    HardwareQualificationRun,
    ObservationRecord,
    ObserverIdentity,
    ProfileBinding,
    QualificationDisposition,
    QualificationEnvironment,
    ResultingStateRecord,
    StateReference,
    StimulusRecord,
    TestExecution,
    TestStatus,
    VerifierResult,
    VerifierStatus,
)
from ets.qualification.profile import HardwareQualificationProfile

_ROOT = Path(__file__).parents[2]
_PROFILE = _ROOT / "docs" / "qualification" / "profiles" / "ets-edge-hardware-qualification-v1.json"
_CORPUS = _ROOT / "docs" / "qualification" / "corpora" / "ets-edge-hqp-corpus-v1.json"
_START = datetime(2026, 9, 14, 1, 30, tzinfo=UTC)
_END = datetime(2026, 9, 14, 2, 30, tzinfo=UTC)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _profile_and_corpus() -> tuple[
    HardwareQualificationProfile,
    EdgeHardwareQualificationCorpus,
]:
    profile = load_edge_profile(_PROFILE.read_bytes())
    corpus = load_edge_corpus(_CORPUS.read_bytes())
    return profile, corpus


def _complete_draft_run() -> HardwareQualificationRun:
    profile, corpus = _profile_and_corpus()
    profile_digest = canonical_sha256(profile.model_dump(mode="json"))
    corpus_cases = {case.test_id: case for case in corpus.cases}

    artifacts: list[ArtifactReference] = []
    stimuli: list[StimulusRecord] = []
    observations: list[ObservationRecord] = []
    results: list[ResultingStateRecord] = []
    evidence_objects: list[EvidenceObjectReference] = []
    executions: list[TestExecution] = []

    start_artifact_id = "artifact-start-state"
    artifacts.append(
        ArtifactReference(
            artifact_id=start_artifact_id,
            artifact_role="starting_state_snapshot",
            media_type="application/json",
            sha256=_sha256("starting-state"),
            byte_length=32,
            retention_locator="fixture://starting-state",
            redaction_state="none",
            required=True,
            secret_material_embedded=False,
            private_key_embedded=False,
        )
    )

    for profile_case in profile.test_cases:
        corpus_case = corpus_cases[profile_case.test_id]
        case_artifact_ids: list[str] = []

        for role in corpus_case.required_artifact_roles:
            artifact_id = f"artifact-{profile_case.test_id.lower()}-{role}"
            case_artifact_ids.append(artifact_id)
            artifacts.append(
                ArtifactReference(
                    artifact_id=artifact_id,
                    artifact_role=role,
                    media_type="application/json",
                    sha256=_sha256(artifact_id),
                    byte_length=len(artifact_id),
                    retention_locator=f"fixture://{artifact_id}",
                    redaction_state="none",
                    required=True,
                    secret_material_embedded=False,
                    private_key_embedded=False,
                )
            )

        stimulus_id = f"stimulus-{profile_case.test_id.lower()}"
        stimuli.append(
            StimulusRecord(
                stimulus_id=stimulus_id,
                test_id=profile_case.test_id,
                issued_at=_START,
                authority_reference="authority://edge-hqp-lab-controller",
                stimulus_class=profile_case.stimulus_class,
                canonical_digest_sha256=_sha256(stimulus_id),
                artifact_ids=(case_artifact_ids[0],),
            )
        )

        observation_ids: list[str] = []
        for observation_class in profile_case.required_observations:
            observation_id = f"observation-{profile_case.test_id.lower()}-{observation_class}"
            observation_ids.append(observation_id)
            observations.append(
                ObservationRecord(
                    observation_id=observation_id,
                    test_id=profile_case.test_id,
                    observer_id="observer-independent-lab",
                    observed_at=_END,
                    observation_class=observation_class,
                    canonical_digest_sha256=_sha256(observation_id),
                    artifact_ids=(case_artifact_ids[0],),
                    uncertainty_statement=(
                        "Synthetic conformance fixture only; not physical evidence."
                    ),
                )
            )

        result_id = f"result-{profile_case.test_id.lower()}"
        results.append(
            ResultingStateRecord(
                resulting_state_id=result_id,
                test_id=profile_case.test_id,
                observed_at=_END,
                canonical_digest_sha256=_sha256(result_id),
                artifact_ids=(case_artifact_ids[-1],),
            )
        )

        evidence_artifact_id = f"artifact-evidence-{profile_case.test_id.lower()}"
        artifacts.append(
            ArtifactReference(
                artifact_id=evidence_artifact_id,
                artifact_role="evidence_object",
                media_type="application/json",
                sha256=_sha256(evidence_artifact_id),
                byte_length=len(evidence_artifact_id),
                retention_locator=f"fixture://{evidence_artifact_id}",
                redaction_state="none",
                required=True,
                secret_material_embedded=False,
                private_key_embedded=False,
            )
        )
        case_artifact_ids.append(evidence_artifact_id)

        evidence_object_id = f"evidence-{profile_case.test_id.lower()}"
        evidence_objects.append(
            EvidenceObjectReference(
                evidence_object_id=evidence_object_id,
                evidence_class="edge-hardware-qualification-case",
                canonical_digest_sha256=_sha256(evidence_object_id),
                artifact_ids=(evidence_artifact_id,),
            )
        )

        executions.append(
            TestExecution(
                test_id=profile_case.test_id,
                required=True,
                status=TestStatus.PASSED,
                started_at=_START,
                completed_at=_END,
                starting_state_id="edge-start-state",
                stimulus_ids=(stimulus_id,),
                observation_ids=tuple(observation_ids),
                resulting_state_ids=(result_id,),
                evidence_object_ids=(evidence_object_id,),
                artifact_ids=tuple(case_artifact_ids),
                assertions=tuple(
                    AssertionResult(
                        assertion_id=assertion_id,
                        passed=True,
                        reason="Synthetic HQP-3 conformance fixture assertion.",
                    )
                    for assertion_id in corpus_case.assertion_ids
                ),
                deviation_ids=(),
            )
        )

    return HardwareQualificationRun(
        run_id="edge-hqp3-conformance-run",
        profile=ProfileBinding(
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_digest_sha256=profile_digest,
        ),
        device=DeviceIdentity(
            device_id="edge-rt0-fixture-dut",
            manufacturer="ETS Test Lab",
            model="EDGE-RT0 Synthetic Fixture",
            hardware_revision="fixture-rev-a",
            serial_or_asset_id="EDGE-RT0-FIXTURE-001",
            firmware={
                "boot_firmware": "fixture-uefi-1",
                "storage_model_firmware": "fixture-nvme-1",
                "tpm_or_signer_profile": "fixture-software-signer-not-a-hardware-claim",
            },
            identity_digest_sha256=_sha256("edge-rt0-fixture-dut"),
        ),
        environment=QualificationEnvironment(
            environment_id="edge-hqp3-synthetic-conformance",
            dimensions={
                "power_source": "synthetic",
                "power_control_method": "synthetic",
                "network_topology": "synthetic",
                "network_fault_injection_method": "synthetic",
                "storage_filesystem": "synthetic",
                "os_kernel_runtime": "synthetic",
                "time_source": "synthetic",
                "ambient_condition": "synthetic",
                "upstream_verifier_endpoint": "synthetic",
            },
            environment_digest_sha256=_sha256("edge-hqp3-synthetic-environment"),
        ),
        build=BuildIdentity(
            repository="ShannonBrayNC/ETS",
            commit_sha="a" * 40,
            artifact_digest_sha256=_sha256("edge-hqp3-build"),
            configuration_digest_sha256=_sha256("edge-hqp3-config"),
            sbom_artifact_id=None,
        ),
        observers=(
            ObserverIdentity(
                observer_id="observer-independent-lab",
                observer_kind="machine",
                role="independent-lab-observer",
                signing_identity="did:example:edge-hqp3-observer",
            ),
        ),
        started_at=_START,
        completed_at=None,
        starting_states=(
            StateReference(
                state_id="edge-start-state",
                canonical_digest_sha256=_sha256("edge-start-state"),
                artifact_ids=(start_artifact_id,),
            ),
        ),
        stimuli=tuple(stimuli),
        observations=tuple(observations),
        resulting_states=tuple(results),
        artifacts=tuple(artifacts),
        evidence_objects=tuple(evidence_objects),
        test_executions=tuple(executions),
        deviations=(),
        verifier_result=VerifierResult(
            status=VerifierStatus.NOT_RUN,
            independent_execution_context=False,
            reason="HQP-3 producer package has not yet been independently verified.",
        ),
        final_disposition=QualificationDisposition.IN_PROGRESS,
        run_digest_sha256=None,
        credentials_embedded=False,
        private_keys_embedded=False,
    )


def test_edge_profile_and_corpus_are_one_to_one() -> None:
    profile, corpus = _profile_and_corpus()

    validate_edge_corpus_against_profile(profile, corpus)

    assert len(profile.test_cases) == 17
    assert len(corpus.cases) == 17
    assert tuple(case.test_id for case in profile.test_cases) == corpus.case_order
    assert corpus.reference_target_class.target_class_id == "EDGE-RT0"


def test_edge_corpus_retains_all_historical_requirement_sources() -> None:
    _, corpus = _profile_and_corpus()
    sources = {ref for case in corpus.cases for ref in case.requirement_refs}

    assert {"#140", "#141", "#142", "#143", "#144", "#145"} <= sources


def test_complete_synthetic_capture_validates_and_seals_lab_tested() -> None:
    profile, corpus = _profile_and_corpus()
    run = _complete_draft_run()

    validate_edge_run_against_corpus(profile, corpus, run)
    sealed, report = seal_edge_lab_run(profile, corpus, run, completed_at=_END)

    assert sealed.final_disposition is QualificationDisposition.LAB_TESTED
    assert sealed.run_digest_sha256 is not None
    assert report.final_disposition is QualificationDisposition.LAB_TESTED
    assert report.run_digest_sha256 == sealed.run_digest_sha256
    assert set(report.passed_case_ids) == set(corpus.case_order)


def test_missing_claim_critical_firmware_field_is_rejected() -> None:
    profile, corpus = _profile_and_corpus()
    run = _complete_draft_run()
    firmware = {
        key: value
        for key, value in run.device.firmware.items()
        if key != "boot_firmware"
    }
    device = run.device.model_copy(update={"firmware": firmware})

    with pytest.raises(ValueError, match="claim-critical firmware"):
        validate_edge_run_against_corpus(
            profile,
            corpus,
            run.model_copy(update={"device": device}),
        )


def test_missing_required_case_artifact_role_is_rejected() -> None:
    profile, corpus = _profile_and_corpus()
    run = _complete_draft_run()
    execution = run.test_executions[0]
    target_case = next(case for case in corpus.cases if case.test_id == execution.test_id)
    required_role = target_case.required_artifact_roles[0]
    artifacts_by_id = {artifact.artifact_id: artifact for artifact in run.artifacts}
    retained_ids = tuple(
        artifact_id
        for artifact_id in execution.artifact_ids
        if artifacts_by_id[artifact_id].artifact_role != required_role
    )
    mutated_execution = execution.model_copy(update={"artifact_ids": retained_ids})
    executions = (mutated_execution, *run.test_executions[1:])

    with pytest.raises(ValueError, match="missing required artifact roles"):
        validate_edge_run_against_corpus(
            profile,
            corpus,
            run.model_copy(update={"test_executions": executions}),
        )


def test_failed_required_case_cannot_be_sealed_as_lab_tested() -> None:
    profile, corpus = _profile_and_corpus()
    run = _complete_draft_run()
    failed = run.test_executions[3].model_copy(update={"status": TestStatus.FAILED})
    executions = (*run.test_executions[:3], failed, *run.test_executions[4:])
    mutated = run.model_copy(update={"test_executions": executions})

    with pytest.raises(ValueError, match="failed"):
        seal_edge_lab_run(profile, corpus, mutated, completed_at=_END)


def test_execution_plan_is_deterministic_and_explicit_about_claim_boundary() -> None:
    corpus = EdgeHardwareQualificationCorpus.model_validate_json(_CORPUS.read_bytes())

    first = render_edge_execution_plan(corpus)
    second = render_edge_execution_plan(corpus)

    assert first == second
    assert "EDGE-HQP-PWR-001 [physical_fault_injection]" in first
    assert "bounded_edge_hardware_qualification_corpus_not_a_physical_qualification_result" in first


def test_profile_json_is_stable_utf8_json() -> None:
    payload = json.loads(_PROFILE.read_text(encoding="utf-8"))

    assert payload["profile_id"] == "ets.edge.hardware-qualification.v1"
    assert payload["profile_version"] == "1.0.0"
