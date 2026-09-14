from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from ets.core.canonical_json import canonical_sha256
from ets.evidence_object.canonical import object_hash
from ets.evidence_object.models import EvidenceObject
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
    build_qualification_report,
    seal_qualification_run,
)
from ets.qualification.profile import HardwareQualificationProfile
from ets.qualification.verifier import (
    VerificationCheckStatus,
    VerificationOutcome,
    render_hardware_qualification_verification,
    verify_hardware_qualification_package,
)

_START = datetime(2026, 9, 13, 20, 0, tzinfo=UTC)
_END = datetime(2026, 9, 13, 20, 5, tzinfo=UTC)
_VERIFIER_BUILD = hashlib.sha256(b"hqp2-clean-verifier-build").hexdigest()


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _artifact(artifact_id: str, raw: bytes) -> ArtifactReference:
    return ArtifactReference(
        artifact_id=artifact_id,
        artifact_role=artifact_id,
        media_type="application/json",
        sha256=_sha256(raw),
        byte_length=len(raw),
        retention_locator=f"artifact://{artifact_id}",
        redaction_state="none",
        required=True,
        secret_material_embedded=False,
        private_key_embedded=False,
    )


def _package() -> tuple[bytes, bytes, bytes, dict[str, bytes]]:
    profile_payload = {
        "schema_version": "1.0",
        "base_profile": "ets.hardware-qualification.v1",
        "profile_id": "ets.test.hardware-qualification.v1",
        "profile_version": "1.0.0-test",
        "title": "HQP-2 clean-room verifier fixture",
        "purpose": "Exercise deterministic independent verification.",
        "product_scope": ["ETS Test DUT"],
        "capability_boundary": {
            "capability_states_are_independent": True,
            "qualification_states": ["not_tested", "qualified", "failed"],
            "claim_statement": "Qualification is bounded to this fixture DUT and build.",
        },
        "device_constraints": {
            "claim_critical_fields": ["manufacturer", "model", "hardware_revision"],
            "cross_revision_qualification_allowed": False,
            "equivalence_profile_required": True,
        },
        "environment_dimensions": ["power_source", "network_topology", "time_source"],
        "evidence_requirements": {
            "evidence_object_binding_required": True,
            "required_classes": [
                "dut_identity",
                "environment",
                "build_identity",
                "observer_identity",
                "starting_state",
                "stimulus",
                "observations",
                "resulting_state",
                "verifier_output",
                "qualification_report",
            ],
            "missing_required_evidence_policy": "invalid",
            "external_artifacts_allowed": True,
            "raw_artifact_digest_required": True,
        },
        "verifier_requirements": {
            "independent_verification_required_for": ["qualified", "qualified_with_deviation"],
            "immutable_verifier_identity_required": True,
            "checks": [
                "schema_conformance",
                "artifact_presence",
                "digest_validity",
                "signature_validity",
                "evidence_object_binding",
                "test_case_completion",
                "observation_result_linkage",
                "deviation_policy",
                "disposition_policy",
            ],
            "dut_runtime_may_be_trusted": False,
        },
        "test_cases": [
            {
                "test_id": "TEST-HQP-001",
                "title": "Retained state survives a bounded restart",
                "purpose": "Exercise the common evidence chain.",
                "required": True,
                "stimulus_class": "controlled_restart",
                "required_observations": ["post_restart_record_presence"],
                "required_resulting_state": ["committed_record_recoverable"],
                "pass_criteria": ["The retained record is independently reproducible."],
                "failure_policy": "fail",
                "waivable": False,
            }
        ],
        "disposition_policy": {
            "allowed_final_states": [
                "lab_tested",
                "qualified",
                "qualified_with_deviation",
                "failed",
            ],
            "missing_required_case_policy": "invalid",
            "deviation_state": "qualified_with_deviation",
            "non_waivable_failure_blocks_qualification": True,
        },
        "validity_policy": {
            "requalify_on_claim_critical_change": True,
            "supersession_must_be_explicit": True,
            "historical_results_immutable": True,
            "maximum_validity_days": None,
            "additional_requalification_triggers": ["verifier_contract_change"],
        },
        "non_claims": ["complete_observation", "semantic_truth", "general_availability"],
        "traceability": {
            "tracking_issue": "#795",
            "source_requirements": ["#790", "#794"],
            "authoritative_roadmap": "docs/PUBLIC_ROADMAP_STATUS.md",
            "review_references": [],
        },
    }
    profile_bytes = _json_bytes(profile_payload)
    profile = HardwareQualificationProfile.model_validate_json(profile_bytes)
    profile_digest = canonical_sha256(profile.model_dump(mode="json"))

    start_raw = _json_bytes({"state": "start"})
    stimulus_raw = _json_bytes({"action": "restart"})
    observation_raw = _json_bytes({"record_present": True})
    result_raw = _json_bytes({"state": "recovered"})

    evidence_payload = {
        "schema_id": "https://lanternprotocol.org/schemas/ets/evidence-object/v1",
        "identity": {
            "evidence_id": "evidence-object-1",
            "version": 1,
            "namespace": "org.lanternprotocol.hqp2.test",
            "evidence_type": "hardware-qualification-result",
            "schema_version": "ets.evidence-object.v1",
        },
        "created_at": "2026-09-13T20:04:00Z",
        "claims": [],
        "assertions": [],
        "contexts": [],
        "relationships": [],
        "integrity": [],
        "verifications": [],
        "policy_refs": [],
        "lifecycle": [],
        "extensions": {"fixture": "hqp2"},
    }
    evidence = EvidenceObject.model_validate_json(_json_bytes(evidence_payload))
    evidence_raw = _json_bytes(evidence.model_dump(mode="json", exclude_none=True))

    artifact_payloads = {
        "artifact-start": start_raw,
        "artifact-stimulus": stimulus_raw,
        "artifact-observation": observation_raw,
        "artifact-result": result_raw,
        "artifact-evidence": evidence_raw,
    }
    artifacts = tuple(_artifact(artifact_id, raw) for artifact_id, raw in artifact_payloads.items())

    draft = HardwareQualificationRun(
        run_id="hqp2-fixture-run-001",
        profile=ProfileBinding(
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_digest_sha256=profile_digest,
        ),
        device=DeviceIdentity(
            device_id="dut-hqp2-001",
            manufacturer="ETS Lab",
            model="HQP2 Fixture",
            hardware_revision="rev-a",
            serial_or_asset_id="HQP2-001",
            firmware={"uefi": "1.0.0"},
            identity_digest_sha256=_sha256(b"fixture-device-identity"),
        ),
        environment=QualificationEnvironment(
            environment_id="clean-room-fixture",
            dimensions={
                "power_source": "controlled-ac",
                "network_topology": "isolated",
                "time_source": "fixture-clock",
            },
            environment_digest_sha256=_sha256(b"fixture-environment"),
        ),
        build=BuildIdentity(
            repository="ShannonBrayNC/ETS",
            commit_sha="a" * 40,
            artifact_digest_sha256=_sha256(b"dut-build"),
            configuration_digest_sha256=_sha256(b"dut-config"),
            sbom_artifact_id=None,
        ),
        observers=(
            ObserverIdentity(
                observer_id="observer-clean-room",
                observer_kind="machine",
                role="independent-observer",
                signing_identity="did:example:hqp2-observer",
            ),
        ),
        started_at=_START,
        completed_at=None,
        starting_states=(
            StateReference(
                state_id="state-start",
                canonical_digest_sha256=canonical_sha256(json.loads(start_raw)),
                artifact_ids=("artifact-start",),
            ),
        ),
        stimuli=(
            StimulusRecord(
                stimulus_id="stimulus-1",
                test_id="TEST-HQP-001",
                issued_at=_START,
                authority_reference="authority://fixture/1",
                stimulus_class="controlled_restart",
                canonical_digest_sha256=canonical_sha256(json.loads(stimulus_raw)),
                artifact_ids=("artifact-stimulus",),
            ),
        ),
        observations=(
            ObservationRecord(
                observation_id="observation-1",
                test_id="TEST-HQP-001",
                observer_id="observer-clean-room",
                observed_at=_END,
                observation_class="post_restart_record_presence",
                canonical_digest_sha256=canonical_sha256(json.loads(observation_raw)),
                artifact_ids=("artifact-observation",),
                uncertainty_statement="Bounded to the retained fixture interface.",
            ),
        ),
        resulting_states=(
            ResultingStateRecord(
                resulting_state_id="result-1",
                test_id="TEST-HQP-001",
                observed_at=_END,
                canonical_digest_sha256=canonical_sha256(json.loads(result_raw)),
                artifact_ids=("artifact-result",),
            ),
        ),
        artifacts=artifacts,
        evidence_objects=(
            EvidenceObjectReference(
                evidence_object_id="evidence-object-1",
                evidence_class="hardware-qualification-result",
                canonical_digest_sha256=object_hash(evidence),
                artifact_ids=("artifact-evidence",),
            ),
        ),
        test_executions=(
            TestExecution(
                test_id="TEST-HQP-001",
                required=True,
                status=TestStatus.PASSED,
                started_at=_START,
                completed_at=_END,
                starting_state_id="state-start",
                stimulus_ids=("stimulus-1",),
                observation_ids=("observation-1",),
                resulting_state_ids=("result-1",),
                evidence_object_ids=("evidence-object-1",),
                artifact_ids=tuple(artifact_payloads),
                assertions=(
                    AssertionResult(
                        assertion_id="committed_record_recoverable",
                        passed=True,
                        reason="Fixture result is retained and reproducible.",
                    ),
                ),
                deviation_ids=(),
            ),
        ),
        deviations=(),
        verifier_result=VerifierResult(
            status=VerifierStatus.NOT_RUN,
            independent_execution_context=False,
            reason="Draft run awaiting producer-side verifier retention.",
        ),
        final_disposition=QualificationDisposition.IN_PROGRESS,
        run_digest_sha256=None,
        credentials_embedded=False,
        private_keys_embedded=False,
    )
    producer_verified = draft.model_copy(
        update={
            "verifier_result": VerifierResult(
                status=VerifierStatus.VALID,
                verifier_id="producer-verifier-fixture",
                verifier_build_digest_sha256=_sha256(b"producer-verifier-build"),
                independent_execution_context=True,
                verification_digest_sha256=_sha256(b"producer-verification-result"),
                challenge_nonce="producer-fixture-nonce",
                reason="Retained producer-side verifier provenance for the fixture.",
            )
        }
    )
    run = seal_qualification_run(
        producer_verified,
        final_disposition=QualificationDisposition.QUALIFIED,
        completed_at=_END,
    )
    report = build_qualification_report(run)
    return (
        profile_bytes,
        _json_bytes(run.model_dump(mode="json")),
        _json_bytes(report.model_dump(mode="json")),
        artifact_payloads,
    )


def _verify(
    profile_bytes: bytes,
    run_bytes: bytes,
    report_bytes: bytes,
    artifact_payloads: dict[str, bytes],
    *,
    independent: bool = True,
):
    return verify_hardware_qualification_package(
        profile_bytes=profile_bytes,
        run_bytes=run_bytes,
        report_bytes=report_bytes,
        artifact_payloads=artifact_payloads,
        verifier_id="hqp2-clean-verifier-test",
        verifier_build_digest_sha256=_VERIFIER_BUILD,
        independent_execution_context=independent,
        challenge_nonce="clean-room-challenge-001",
    )


def test_clean_room_verifier_reproduces_eligible_qualification() -> None:
    profile_bytes, run_bytes, report_bytes, artifacts = _package()
    result = _verify(profile_bytes, run_bytes, report_bytes, artifacts)

    assert result.outcome is VerificationOutcome.VALID
    assert result.eligible_for_claimed_disposition is True
    assert result.claimed_disposition == "qualified"
    assert set(result.verified_artifact_ids) == set(artifacts)
    assert result.verified_evidence_object_ids == ("evidence-object-1",)
    assert not result.invalid_evidence_object_ids
    assert any(
        check.check_id == "resulting_state_semantic_class"
        and check.status is VerificationCheckStatus.INDETERMINATE
        and not check.gating
        for check in result.checks
    )


def test_artifact_tamper_blocks_qualification() -> None:
    profile_bytes, run_bytes, report_bytes, artifacts = _package()
    tampered = dict(artifacts)
    tampered["artifact-result"] += b"tamper"

    result = _verify(profile_bytes, run_bytes, report_bytes, tampered)

    assert result.outcome is VerificationOutcome.INVALID
    assert result.eligible_for_claimed_disposition is False
    assert result.mismatched_artifact_ids == ("artifact-result",)


def test_profile_digest_mismatch_blocks_qualification() -> None:
    profile_bytes, run_bytes, report_bytes, artifacts = _package()
    profile = json.loads(profile_bytes)
    profile["purpose"] = "Mutated after the run was sealed."

    result = _verify(_json_bytes(profile), run_bytes, report_bytes, artifacts)

    assert result.outcome is VerificationOutcome.INVALID
    binding = next(check for check in result.checks if check.check_id == "profile_binding")
    assert binding.status is VerificationCheckStatus.FAIL


def test_non_independent_invocation_cannot_validate_qualification() -> None:
    profile_bytes, run_bytes, report_bytes, artifacts = _package()

    result = _verify(profile_bytes, run_bytes, report_bytes, artifacts, independent=False)

    assert result.outcome is VerificationOutcome.INVALID
    assert result.eligible_for_claimed_disposition is False


def test_verification_output_and_human_render_are_deterministic() -> None:
    package = _package()
    first = _verify(*package)
    second = _verify(*package)

    assert first == second
    assert first.verification_digest_sha256 == second.verification_digest_sha256
    text = render_hardware_qualification_verification(first)
    assert "Outcome: valid" in text
    assert first.verification_digest_sha256 in text
