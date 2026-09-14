from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.qualification.hardware import (
    ArtifactReference,
    AssertionResult,
    BuildIdentity,
    DeviationKind,
    DeviationRecord,
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
    build_qualification_report,
    seal_qualification_run,
)

_ZERO = "0" * 64
_ONE = "1" * 64
_TWO = "2" * 64
_THREE = "3" * 64
_FOUR = "4" * 64
_FIVE = "5" * 64
_SIX = "6" * 64
_SEVEN = "7" * 64
_EIGHT = "8" * 64
_NINE = "9" * 64
_START = datetime(2026, 9, 13, 20, 0, tzinfo=UTC)
_END = _START + timedelta(minutes=5)


def _artifact(artifact_id: str, digest: str) -> ArtifactReference:
    return ArtifactReference(
        artifact_id=artifact_id,
        artifact_role=artifact_id,
        media_type="application/json",
        sha256=digest,
        byte_length=128,
        retention_locator=f"artifact://{artifact_id}",
    )


def _draft_run(
    *,
    test_status: TestStatus = TestStatus.PASSED,
    deviations: tuple[DeviationRecord, ...] = (),
) -> HardwareQualificationRun:
    artifacts = (
        _artifact("artifact-start", _ZERO),
        _artifact("artifact-stimulus", _ONE),
        _artifact("artifact-observation", _TWO),
        _artifact("artifact-result", _THREE),
        _artifact("artifact-evidence", _FOUR),
        _artifact("artifact-approval", _FIVE),
    )
    execution = TestExecution(
        test_id="EDGE-HQP-DUR-001",
        required=True,
        status=test_status,
        started_at=_START,
        completed_at=_END,
        starting_state_id="state-start",
        stimulus_ids=("stimulus-1",),
        observation_ids=("observation-1",),
        resulting_state_ids=("result-1",),
        evidence_object_ids=("evidence-object-1",),
        artifact_ids=(
            "artifact-start",
            "artifact-stimulus",
            "artifact-observation",
            "artifact-result",
            "artifact-evidence",
        ),
        assertions=(
            AssertionResult(
                assertion_id="committed-record-recoverable",
                passed=test_status is TestStatus.PASSED,
                reason="Retained test assertion result.",
            ),
        ),
        deviation_ids=tuple(item.deviation_id for item in deviations),
    )
    return HardwareQualificationRun(
        run_id="edge-hqp-example-run-001",
        profile=ProfileBinding(
            profile_id="ets.edge.hardware-qualification.v1",
            profile_version="0.1.0-draft",
            profile_digest_sha256=_SIX,
        ),
        device=DeviceIdentity(
            device_id="edge-reference-001",
            manufacturer="ETS Lab",
            model="Edge Reference",
            hardware_revision="rev-a",
            serial_or_asset_id="LAB-EDGE-001",
            firmware={"uefi": "1.0.0", "tpm": "7.2.0"},
            identity_digest_sha256=_SEVEN,
        ),
        environment=QualificationEnvironment(
            environment_id="lab-bench-a",
            dimensions={
                "power_source": "controlled-ac",
                "network_topology": "isolated-lab-vlan",
                "time_source": "lab-ntp",
            },
            environment_digest_sha256=_EIGHT,
        ),
        build=BuildIdentity(
            repository="ShannonBrayNC/ETS",
            commit_sha="a" * 40,
            artifact_digest_sha256=_NINE,
            configuration_digest_sha256=_ZERO,
            sbom_artifact_id=None,
        ),
        observers=(
            ObserverIdentity(
                observer_id="observer-lab-controller",
                observer_kind="machine",
                role="independent-lab-observer",
                signing_identity="did:example:lab-controller",
            ),
        ),
        started_at=_START,
        completed_at=None,
        starting_states=(
            StateReference(
                state_id="state-start",
                canonical_digest_sha256=_ONE,
                artifact_ids=("artifact-start",),
            ),
        ),
        stimuli=(
            StimulusRecord(
                stimulus_id="stimulus-1",
                test_id="EDGE-HQP-DUR-001",
                issued_at=_START + timedelta(minutes=1),
                authority_reference="authority://lab-runner/001",
                stimulus_class="bounded_restart",
                canonical_digest_sha256=_TWO,
                artifact_ids=("artifact-stimulus",),
            ),
        ),
        observations=(
            ObservationRecord(
                observation_id="observation-1",
                test_id="EDGE-HQP-DUR-001",
                observer_id="observer-lab-controller",
                observed_at=_START + timedelta(minutes=2),
                observation_class="post-restart-record-observation",
                canonical_digest_sha256=_THREE,
                artifact_ids=("artifact-observation",),
                uncertainty_statement="Observation is bounded to the retained lab interface.",
            ),
        ),
        resulting_states=(
            ResultingStateRecord(
                resulting_state_id="result-1",
                test_id="EDGE-HQP-DUR-001",
                observed_at=_START + timedelta(minutes=3),
                canonical_digest_sha256=_FOUR,
                artifact_ids=("artifact-result",),
            ),
        ),
        artifacts=artifacts,
        evidence_objects=(
            EvidenceObjectReference(
                evidence_object_id="evidence-object-1",
                evidence_class="hardware-qualification-result",
                canonical_digest_sha256=_FIVE,
                artifact_ids=("artifact-evidence",),
            ),
        ),
        test_executions=(execution,),
        deviations=deviations,
        verifier_result=VerifierResult(
            status=VerifierStatus.VALID,
            verifier_id="ets-hqp-verifier-test-fixture",
            verifier_build_digest_sha256=_SIX,
            independent_execution_context=True,
            verification_digest_sha256=_SEVEN,
            challenge_nonce="fixture-challenge-001",
            reason="Fixture verifier independently reproduced the retained package bindings.",
        ),
        final_disposition=QualificationDisposition.IN_PROGRESS,
        run_digest_sha256=None,
    )


def test_seal_and_report_are_deterministic() -> None:
    draft = _draft_run()
    sealed = seal_qualification_run(
        draft,
        final_disposition=QualificationDisposition.QUALIFIED,
        completed_at=_END,
    )
    report_a = build_qualification_report(sealed)
    report_b = build_qualification_report(sealed)

    assert sealed.run_digest_sha256 is not None
    assert sealed.final_disposition is QualificationDisposition.QUALIFIED
    assert report_a == report_b
    assert report_a.report_digest_sha256 == report_b.report_digest_sha256
    assert report_a.required_case_ids == ("EDGE-HQP-DUR-001",)
    assert report_a.passed_case_ids == ("EDGE-HQP-DUR-001",)
    assert report_a.failed_case_ids == ()
    assert report_a.verifier_status is VerifierStatus.VALID


def test_valid_verifier_must_be_independent() -> None:
    with pytest.raises(ValidationError, match="independent context"):
        VerifierResult(
            status=VerifierStatus.VALID,
            verifier_id="self-verifier",
            verifier_build_digest_sha256=_ZERO,
            independent_execution_context=False,
            verification_digest_sha256=_ONE,
            reason="The DUT attempted to verify itself.",
        )


def test_dangling_observation_reference_invalidates_package() -> None:
    draft = _draft_run()
    bad_execution = draft.test_executions[0].model_copy(
        update={"observation_ids": ("missing-observation",)}
    )
    payload = draft.model_dump(mode="python")
    payload["test_executions"] = (bad_execution,)

    with pytest.raises(ValidationError, match="unknown test observation"):
        HardwareQualificationRun.model_validate(payload)


def test_failed_required_case_cannot_be_qualified() -> None:
    draft = _draft_run(test_status=TestStatus.FAILED)

    with pytest.raises(ValidationError, match="every required case"):
        seal_qualification_run(
            draft,
            final_disposition=QualificationDisposition.QUALIFIED,
            completed_at=_END,
        )


def test_claim_affecting_deviation_requires_deviation_disposition() -> None:
    deviation = DeviationRecord(
        deviation_id="deviation-001",
        kind=DeviationKind.DEVIATION,
        test_id="EDGE-HQP-DUR-001",
        rationale="Fixture demonstrates claim-scope handling.",
        approved_by="lab-reviewer",
        approval_artifact_id="artifact-approval",
        affects_claim_scope=True,
        expires_at=None,
    )
    draft = _draft_run(deviations=(deviation,))

    with pytest.raises(ValidationError, match="qualified_with_deviation"):
        seal_qualification_run(
            draft,
            final_disposition=QualificationDisposition.QUALIFIED,
            completed_at=_END,
        )

    sealed = seal_qualification_run(
        draft,
        final_disposition=QualificationDisposition.QUALIFIED_WITH_DEVIATION,
        completed_at=_END,
    )
    report = build_qualification_report(sealed)
    assert report.final_disposition is QualificationDisposition.QUALIFIED_WITH_DEVIATION
    assert report.deviation_ids == ("deviation-001",)


def test_tampered_run_digest_is_rejected() -> None:
    sealed = seal_qualification_run(
        _draft_run(),
        final_disposition=QualificationDisposition.QUALIFIED,
        completed_at=_END,
    )
    payload = sealed.model_dump(mode="python")
    payload["run_digest_sha256"] = _ZERO

    with pytest.raises(ValidationError, match="run_digest_sha256"):
        HardwareQualificationRun.model_validate(payload)
