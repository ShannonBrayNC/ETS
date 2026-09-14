"""Independent clean-room verifier for ETS Hardware Qualification Profile packages.

HQP-2 deliberately re-derives package eligibility from retained bytes and canonical contracts.
The producer-side ``verifier_result`` embedded in an HQP-1 run is retained provenance; this module
does not trust that assertion as proof of its own correctness or independence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.evidence_object.canonical import object_hash
from ets.evidence_object.models import EvidenceObject
from ets.qualification.hardware import (
    HardwareQualificationReport,
    HardwareQualificationRun,
    QualificationDisposition,
    TestStatus,
    build_qualification_report,
)
from ets.qualification.profile import HardwareQualificationProfile, VerifierCheckName

_SHA256_RE = r"^[0-9a-f]{64}$"
_VERIFICATION_CLAIM_BOUNDARY: Literal[
    "bounded_hqp_independent_verification_not_complete_observation_truth_compliance_safety_or_ga_proof"
] = "bounded_hqp_independent_verification_not_complete_observation_truth_compliance_safety_or_ga_proof"


class VerificationCheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INDETERMINATE = "indeterminate"


class VerificationOutcome(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    INDETERMINATE = "indeterminate"


class StrictVerifierModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class QualificationVerificationCheck(StrictVerifierModel):
    check_id: str = Field(min_length=1, max_length=128)
    status: VerificationCheckStatus
    gating: bool
    reason: str = Field(min_length=1, max_length=4096)
    subjects: tuple[str, ...] = ()


class HardwareQualificationVerification(StrictVerifierModel):
    schema_version: Literal["ets.hardware-qualification-verification.v1"] = (
        "ets.hardware-qualification-verification.v1"
    )
    verification_id: str = Field(min_length=1, max_length=256)
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_build_digest_sha256: str = Field(pattern=_SHA256_RE)
    independent_execution_context: bool
    challenge_nonce: str | None = Field(default=None, max_length=512)
    profile_id: str | None = Field(default=None, max_length=256)
    profile_version: str | None = Field(default=None, max_length=128)
    profile_digest_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    run_id: str | None = Field(default=None, max_length=256)
    run_digest_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    report_id: str | None = Field(default=None, max_length=256)
    report_digest_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    claimed_disposition: str | None = Field(default=None, max_length=128)
    eligible_for_claimed_disposition: bool
    outcome: VerificationOutcome
    checks: tuple[QualificationVerificationCheck, ...]
    verified_artifact_ids: tuple[str, ...]
    missing_artifact_ids: tuple[str, ...]
    mismatched_artifact_ids: tuple[str, ...]
    verified_evidence_object_ids: tuple[str, ...]
    invalid_evidence_object_ids: tuple[str, ...]
    trust_boundary: tuple[str, ...]
    verification_digest_sha256: str = Field(pattern=_SHA256_RE)
    claim_boundary: Literal[
        "bounded_hqp_independent_verification_not_complete_observation_truth_compliance_safety_or_ga_proof"
    ] = _VERIFICATION_CLAIM_BOUNDARY

    @model_validator(mode="after")
    def verify_digest(self) -> HardwareQualificationVerification:
        expected = canonical_sha256(
            self.model_dump(mode="json", exclude={"verification_digest_sha256"})
        )
        if self.verification_digest_sha256 != expected:
            raise ValueError("verification_digest_sha256 does not match canonical result payload")
        return self


def verify_hardware_qualification_package(
    *,
    profile_bytes: bytes,
    run_bytes: bytes,
    report_bytes: bytes,
    artifact_payloads: Mapping[str, bytes],
    verifier_id: str,
    verifier_build_digest_sha256: str,
    independent_execution_context: bool,
    challenge_nonce: str | None = None,
) -> HardwareQualificationVerification:
    """Verify one retained HQP package without trusting the DUT or producer narrative."""

    input_digest = hashlib.sha256(
        profile_bytes + b"\x00" + run_bytes + b"\x00" + report_bytes
    ).hexdigest()
    verification_id = f"hqp2-{input_digest[:24]}"
    checks: list[QualificationVerificationCheck] = []
    trust_boundary = [
        "The clean verifier does not trust the DUT runtime or the producer-side verifier_result.",
        "Raw artifact verification is bounded to bytes supplied to this verifier invocation.",
        "HQP-1 does not encode a resulting_state_class field; result linkage can be verified but "
        "profile-level resulting-state semantic labels cannot be independently reconstructed.",
        "HQP-1 artifact references do not define a generic signature envelope; SHA-256 digest "
        "integrity is verified and signature verification is only applicable when a future "
        "contract declares signature material.",
    ]

    _append_check(
        checks,
        "verifier_independence",
        VerificationCheckStatus.PASS
        if independent_execution_context
        else VerificationCheckStatus.FAIL,
        True,
        "Verifier invocation declares an independent execution context."
        if independent_execution_context
        else "Verifier invocation is not independent from the producer/DUT context.",
        (verifier_id,),
    )

    profile = _parse_profile(profile_bytes, checks)
    run = _parse_run(run_bytes, checks)
    report = _parse_report(report_bytes, checks)

    profile_digest: str | None = None
    if profile is not None:
        profile_digest = canonical_sha256(profile.model_dump(mode="json"))

    verified_artifacts: list[str] = []
    missing_artifacts: list[str] = []
    mismatched_artifacts: list[str] = []
    verified_evidence: list[str] = []
    invalid_evidence: list[str] = []

    if profile is not None and run is not None:
        binding_ok = (
            run.profile.profile_id == profile.profile_id
            and run.profile.profile_version == profile.profile_version
            and run.profile.profile_digest_sha256 == profile_digest
        )
        _append_check(
            checks,
            "profile_binding",
            VerificationCheckStatus.PASS if binding_ok else VerificationCheckStatus.FAIL,
            True,
            "Run profile identifier, version, and canonical profile digest match."
            if binding_ok
            else "Run profile binding does not match the supplied canonical profile.",
            (profile.profile_id, run.run_id),
        )

    if run is not None and report is not None:
        try:
            expected_report = build_qualification_report(run, report_id=report.report_id)
            report_ok = expected_report.model_dump(mode="json") == report.model_dump(mode="json")
        except ValueError:
            report_ok = False
        _append_check(
            checks,
            "report_projection",
            VerificationCheckStatus.PASS if report_ok else VerificationCheckStatus.FAIL,
            True,
            "Qualification report is the deterministic projection of the sealed run."
            if report_ok
            else "Qualification report differs from the deterministic sealed-run projection.",
            (report.report_id, run.run_id),
        )

    if run is not None:
        presence_status, digest_status = _verify_artifacts(
            run,
            artifact_payloads,
            verified_artifacts,
            missing_artifacts,
            mismatched_artifacts,
        )
        _append_check(
            checks,
            VerifierCheckName.ARTIFACT_PRESENCE.value,
            presence_status,
            True,
            "All required retained artifacts are present."
            if presence_status is VerificationCheckStatus.PASS
            else "One or more required retained artifacts are missing or withheld.",
            tuple(sorted(missing_artifacts)),
        )
        _append_check(
            checks,
            VerifierCheckName.DIGEST_VALIDITY.value,
            digest_status,
            True,
            "Supplied artifact byte lengths and SHA-256 digests match the run manifest."
            if digest_status is VerificationCheckStatus.PASS
            else "One or more supplied artifacts do not match retained byte-length/SHA-256 claims.",
            tuple(sorted(mismatched_artifacts)),
        )

        evidence_status = _verify_evidence_objects(
            run,
            artifact_payloads,
            verified_evidence,
            invalid_evidence,
        )
        _append_check(
            checks,
            VerifierCheckName.EVIDENCE_OBJECT_BINDING.value,
            evidence_status,
            True,
            "Evidence Object payloads parse and match retained canonical object digests."
            if evidence_status is VerificationCheckStatus.PASS
            else "One or more Evidence Object references cannot be independently reproduced.",
            tuple(sorted(invalid_evidence)),
        )

    if profile is not None and run is not None:
        completion_status, completion_reason = _verify_test_case_completion(profile, run)
        _append_check(
            checks,
            VerifierCheckName.TEST_CASE_COMPLETION.value,
            completion_status,
            True,
            completion_reason,
            tuple(item.test_id for item in run.test_executions),
        )

        linkage_status, linkage_reason = _verify_observation_result_linkage(profile, run)
        _append_check(
            checks,
            VerifierCheckName.OBSERVATION_RESULT_LINKAGE.value,
            linkage_status,
            True,
            linkage_reason,
            tuple(item.test_id for item in run.test_executions),
        )
        _append_check(
            checks,
            "resulting_state_semantic_class",
            VerificationCheckStatus.INDETERMINATE,
            False,
            "HQP-1 retains resulting-state IDs/digests but no explicit resulting_state_class; "
            "semantic class coverage is outside this verifier revision.",
        )

        deviation_status, deviation_reason = _verify_deviation_policy(profile, run)
        _append_check(
            checks,
            VerifierCheckName.DEVIATION_POLICY.value,
            deviation_status,
            True,
            deviation_reason,
            tuple(item.deviation_id for item in run.deviations),
        )

        disposition_status, disposition_reason = _verify_disposition_policy(profile, run)
        _append_check(
            checks,
            VerifierCheckName.DISPOSITION_POLICY.value,
            disposition_status,
            True,
            disposition_reason,
            (run.final_disposition.value,),
        )

    if profile is not None:
        signature_requested = VerifierCheckName.SIGNATURE_VALIDITY in profile.verifier_requirements.checks
        if signature_requested:
            _append_check(
                checks,
                VerifierCheckName.SIGNATURE_VALIDITY.value,
                VerificationCheckStatus.INDETERMINATE,
                False,
                "HQP-1 declares no generic signature envelope. No signature claim is accepted or "
                "rejected by HQP-2; digest integrity remains independently verified.",
            )

    gating_checks = [item for item in checks if item.gating]
    if any(item.status is VerificationCheckStatus.FAIL for item in gating_checks):
        outcome = VerificationOutcome.INVALID
    elif any(item.status is VerificationCheckStatus.INDETERMINATE for item in gating_checks):
        outcome = VerificationOutcome.INDETERMINATE
    else:
        outcome = VerificationOutcome.VALID

    disposition_check = next(
        (item for item in checks if item.check_id == VerifierCheckName.DISPOSITION_POLICY.value),
        None,
    )
    eligible = bool(
        outcome is VerificationOutcome.VALID
        and disposition_check is not None
        and disposition_check.status is VerificationCheckStatus.PASS
    )

    payload: dict[str, object] = {
        "schema_version": "ets.hardware-qualification-verification.v1",
        "verification_id": verification_id,
        "verifier_id": verifier_id,
        "verifier_build_digest_sha256": verifier_build_digest_sha256,
        "independent_execution_context": independent_execution_context,
        "challenge_nonce": challenge_nonce,
        "profile_id": profile.profile_id if profile is not None else None,
        "profile_version": profile.profile_version if profile is not None else None,
        "profile_digest_sha256": profile_digest,
        "run_id": run.run_id if run is not None else None,
        "run_digest_sha256": run.run_digest_sha256 if run is not None else None,
        "report_id": report.report_id if report is not None else None,
        "report_digest_sha256": report.report_digest_sha256 if report is not None else None,
        "claimed_disposition": run.final_disposition.value if run is not None else None,
        "eligible_for_claimed_disposition": eligible,
        "outcome": outcome.value,
        "checks": [item.model_dump(mode="json") for item in checks],
        "verified_artifact_ids": sorted(verified_artifacts),
        "missing_artifact_ids": sorted(missing_artifacts),
        "mismatched_artifact_ids": sorted(mismatched_artifacts),
        "verified_evidence_object_ids": sorted(verified_evidence),
        "invalid_evidence_object_ids": sorted(invalid_evidence),
        "trust_boundary": trust_boundary,
        "claim_boundary": _VERIFICATION_CLAIM_BOUNDARY,
    }
    digest = canonical_sha256(payload)
    payload["verification_digest_sha256"] = digest
    return HardwareQualificationVerification.model_validate_json(
        json.dumps(payload, sort_keys=True, separators=(",", ":"))
    )


def render_hardware_qualification_verification(
    result: HardwareQualificationVerification,
) -> str:
    """Render a deterministic human-readable summary of an HQP-2 result."""

    lines = [
        f"HQP-2 verification: {result.verification_id}",
        f"Outcome: {result.outcome.value}",
        f"Eligible for claimed disposition: {str(result.eligible_for_claimed_disposition).lower()}",
        f"Profile: {result.profile_id or 'unavailable'} @ {result.profile_version or 'unavailable'}",
        f"Run: {result.run_id or 'unavailable'}",
        f"Claimed disposition: {result.claimed_disposition or 'unavailable'}",
        "Checks:",
    ]
    for check in result.checks:
        gate = "gating" if check.gating else "non-gating"
        lines.append(f"- {check.check_id}: {check.status.value} ({gate}) — {check.reason}")
    lines.append("Trust boundary:")
    lines.extend(f"- {item}" for item in result.trust_boundary)
    lines.append(f"Verification digest: {result.verification_digest_sha256}")
    return "\n".join(lines) + "\n"


def _parse_profile(
    raw: bytes,
    checks: list[QualificationVerificationCheck],
) -> HardwareQualificationProfile | None:
    try:
        profile = HardwareQualificationProfile.model_validate_json(raw)
    except ValidationError as exc:
        _append_check(
            checks,
            "profile_schema_conformance",
            VerificationCheckStatus.FAIL,
            True,
            f"Profile failed runtime schema validation: {_compact_validation_error(exc)}",
        )
        return None
    _append_check(
        checks,
        "profile_schema_conformance",
        VerificationCheckStatus.PASS,
        True,
        "Profile conforms to the HQP-0 runtime mirror of the normative v1 schema.",
        (profile.profile_id,),
    )
    return profile


def _parse_run(
    raw: bytes,
    checks: list[QualificationVerificationCheck],
) -> HardwareQualificationRun | None:
    try:
        run = HardwareQualificationRun.model_validate_json(raw)
    except ValidationError as exc:
        _append_check(
            checks,
            "run_schema_conformance",
            VerificationCheckStatus.FAIL,
            True,
            f"Run failed HQP-1 validation: {_compact_validation_error(exc)}",
        )
        return None
    _append_check(
        checks,
        "run_schema_conformance",
        VerificationCheckStatus.PASS,
        True,
        "Run conforms to HQP-1 and its canonical sealed digest verifies.",
        (run.run_id,),
    )
    return run


def _parse_report(
    raw: bytes,
    checks: list[QualificationVerificationCheck],
) -> HardwareQualificationReport | None:
    try:
        report = HardwareQualificationReport.model_validate_json(raw)
    except ValidationError as exc:
        _append_check(
            checks,
            "report_schema_conformance",
            VerificationCheckStatus.FAIL,
            True,
            f"Report failed HQP-1 validation: {_compact_validation_error(exc)}",
        )
        return None
    _append_check(
        checks,
        "report_schema_conformance",
        VerificationCheckStatus.PASS,
        True,
        "Report conforms to HQP-1 and its canonical report digest verifies.",
        (report.report_id,),
    )
    return report


def _verify_artifacts(
    run: HardwareQualificationRun,
    payloads: Mapping[str, bytes],
    verified: list[str],
    missing: list[str],
    mismatched: list[str],
) -> tuple[VerificationCheckStatus, VerificationCheckStatus]:
    presence = VerificationCheckStatus.PASS
    digest = VerificationCheckStatus.PASS
    for artifact in run.artifacts:
        raw = payloads.get(artifact.artifact_id)
        if raw is None:
            if artifact.required:
                missing.append(artifact.artifact_id)
                if artifact.redaction_state == "withheld":
                    if presence is not VerificationCheckStatus.FAIL:
                        presence = VerificationCheckStatus.INDETERMINATE
                else:
                    presence = VerificationCheckStatus.FAIL
            continue
        actual_digest = hashlib.sha256(raw).hexdigest()
        if len(raw) != artifact.byte_length or actual_digest != artifact.sha256:
            mismatched.append(artifact.artifact_id)
            digest = VerificationCheckStatus.FAIL
            continue
        verified.append(artifact.artifact_id)
    return presence, digest


def _verify_evidence_objects(
    run: HardwareQualificationRun,
    payloads: Mapping[str, bytes],
    verified: list[str],
    invalid: list[str],
) -> VerificationCheckStatus:
    if not run.evidence_objects:
        return VerificationCheckStatus.FAIL
    artifact_index = {item.artifact_id: item for item in run.artifacts}
    for reference in run.evidence_objects:
        matched = False
        for artifact_id in reference.artifact_ids:
            artifact = artifact_index.get(artifact_id)
            raw = payloads.get(artifact_id)
            if artifact is None or raw is None or artifact.media_type != "application/json":
                continue
            try:
                evidence = EvidenceObject.model_validate_json(raw)
            except ValidationError:
                continue
            if evidence.identity.evidence_id != reference.evidence_object_id:
                continue
            if object_hash(evidence) != reference.canonical_digest_sha256:
                continue
            matched = True
            break
        if matched:
            verified.append(reference.evidence_object_id)
        else:
            invalid.append(reference.evidence_object_id)
    return VerificationCheckStatus.PASS if not invalid else VerificationCheckStatus.FAIL


def _verify_test_case_completion(
    profile: HardwareQualificationProfile,
    run: HardwareQualificationRun,
) -> tuple[VerificationCheckStatus, str]:
    profile_cases = {item.test_id: item for item in profile.test_cases}
    executions = {item.test_id: item for item in run.test_executions}
    unknown = sorted(set(executions) - set(profile_cases))
    if unknown:
        return VerificationCheckStatus.FAIL, f"Run contains tests not defined by profile: {unknown}."
    for case in profile.test_cases:
        execution = executions.get(case.test_id)
        if execution is None:
            if case.required:
                return VerificationCheckStatus.FAIL, f"Required profile case is missing: {case.test_id}."
            continue
        if execution.required != case.required:
            return VerificationCheckStatus.FAIL, f"Required flag differs for {case.test_id}."
        if case.required and execution.status is TestStatus.NOT_RUN:
            return VerificationCheckStatus.FAIL, f"Required profile case was not run: {case.test_id}."
        if execution.status is TestStatus.PASSED and any(
            not assertion.passed for assertion in execution.assertions
        ):
            return (
                VerificationCheckStatus.FAIL,
                f"Passed execution contains a failed assertion: {case.test_id}.",
            )
    return VerificationCheckStatus.PASS, "Run test inventory and required-case completion match profile."


def _verify_observation_result_linkage(
    profile: HardwareQualificationProfile,
    run: HardwareQualificationRun,
) -> tuple[VerificationCheckStatus, str]:
    profile_cases = {item.test_id: item for item in profile.test_cases}
    stimuli = {item.stimulus_id: item for item in run.stimuli}
    observations = {item.observation_id: item for item in run.observations}
    results = {item.resulting_state_id: item for item in run.resulting_states}
    for execution in run.test_executions:
        case = profile_cases.get(execution.test_id)
        if case is None:
            continue
        case_stimuli = [stimuli[item] for item in execution.stimulus_ids]
        case_observations = [observations[item] for item in execution.observation_ids]
        case_results = [results[item] for item in execution.resulting_state_ids]
        if not case_stimuli:
            return VerificationCheckStatus.FAIL, f"No retained stimulus for {execution.test_id}."
        if not case_results:
            return VerificationCheckStatus.FAIL, f"No retained resulting state for {execution.test_id}."
        if any(item.test_id != execution.test_id for item in case_stimuli):
            return VerificationCheckStatus.FAIL, f"Stimulus cross-links another test for {execution.test_id}."
        if any(item.test_id != execution.test_id for item in case_observations):
            return VerificationCheckStatus.FAIL, f"Observation cross-links another test for {execution.test_id}."
        if any(item.test_id != execution.test_id for item in case_results):
            return VerificationCheckStatus.FAIL, f"Result cross-links another test for {execution.test_id}."
        if not any(item.stimulus_class == case.stimulus_class for item in case_stimuli):
            return (
                VerificationCheckStatus.FAIL,
                f"Required stimulus class is absent for {execution.test_id}: {case.stimulus_class}.",
            )
        observed_classes = {item.observation_class for item in case_observations}
        missing_observations = sorted(set(case.required_observations) - observed_classes)
        if missing_observations:
            return (
                VerificationCheckStatus.FAIL,
                f"Required observation classes are absent for {execution.test_id}: "
                f"{missing_observations}.",
            )
    return (
        VerificationCheckStatus.PASS,
        "Stimulus, observation, and resulting-state references remain inside each test boundary; "
        "required stimulus/observation classes are present.",
    )


def _verify_deviation_policy(
    profile: HardwareQualificationProfile,
    run: HardwareQualificationRun,
) -> tuple[VerificationCheckStatus, str]:
    profile_cases = {item.test_id: item for item in profile.test_cases}
    deviations = {item.deviation_id: item for item in run.deviations}
    completed_at = run.completed_at
    for deviation in run.deviations:
        if deviation.test_id is not None and deviation.test_id not in profile_cases:
            return VerificationCheckStatus.FAIL, f"Deviation targets unknown test: {deviation.test_id}."
        if (
            deviation.expires_at is not None
            and completed_at is not None
            and deviation.expires_at < completed_at
        ):
            return VerificationCheckStatus.FAIL, f"Deviation expired before run completion: {deviation.deviation_id}."
    for execution in run.test_executions:
        if execution.status is not TestStatus.WAIVED:
            continue
        case = profile_cases.get(execution.test_id)
        if case is None or not case.waivable:
            return VerificationCheckStatus.FAIL, f"Non-waivable test was waived: {execution.test_id}."
        attached = [deviations[item] for item in execution.deviation_ids]
        if not attached or not any(item.kind.value == "waiver" for item in attached):
            return VerificationCheckStatus.FAIL, f"Waived test lacks retained waiver: {execution.test_id}."
    if (
        run.final_disposition is QualificationDisposition.QUALIFIED
        and any(item.affects_claim_scope for item in run.deviations)
    ):
        return (
            VerificationCheckStatus.FAIL,
            "Claim-affecting deviation requires qualified_with_deviation.",
        )
    return VerificationCheckStatus.PASS, "Deviation/waiver records are consistent with profile policy."


def _verify_disposition_policy(
    profile: HardwareQualificationProfile,
    run: HardwareQualificationRun,
) -> tuple[VerificationCheckStatus, str]:
    allowed = {item.value for item in profile.disposition_policy.allowed_final_states}
    if run.final_disposition.value not in allowed:
        return (
            VerificationCheckStatus.FAIL,
            f"Claimed disposition is not allowed by profile: {run.final_disposition.value}.",
        )
    if run.final_disposition in {
        QualificationDisposition.QUALIFIED,
        QualificationDisposition.QUALIFIED_WITH_DEVIATION,
    }:
        executions = {item.test_id: item for item in run.test_executions}
        for case in profile.test_cases:
            if not case.required:
                continue
            execution = executions.get(case.test_id)
            if execution is None or execution.status not in {TestStatus.PASSED, TestStatus.WAIVED}:
                return (
                    VerificationCheckStatus.FAIL,
                    f"Qualified claim lacks pass/waiver for required case: {case.test_id}.",
                )
            if execution.status is TestStatus.WAIVED and not case.waivable:
                return VerificationCheckStatus.FAIL, f"Required case is not waivable: {case.test_id}."
        if not run.evidence_objects:
            return VerificationCheckStatus.FAIL, "Qualified claim has no retained Evidence Objects."
    if run.final_disposition is QualificationDisposition.QUALIFIED_WITH_DEVIATION:
        if not run.deviations:
            return (
                VerificationCheckStatus.FAIL,
                "qualified_with_deviation requires at least one retained deviation or waiver.",
            )
    return (
        VerificationCheckStatus.PASS,
        f"Claimed disposition {run.final_disposition.value} is eligible under profile policy.",
    )


def _append_check(
    checks: list[QualificationVerificationCheck],
    check_id: str,
    status: VerificationCheckStatus,
    gating: bool,
    reason: str,
    subjects: tuple[str, ...] = (),
) -> None:
    checks.append(
        QualificationVerificationCheck(
            check_id=check_id,
            status=status,
            gating=gating,
            reason=reason,
            subjects=subjects,
        )
    )


def _compact_validation_error(exc: ValidationError) -> str:
    errors = exc.errors(include_url=False, include_context=False)
    if not errors:
        return "validation failed"
    first = errors[0]
    location = ".".join(str(item) for item in first.get("loc", ())) or "root"
    return f"{location}: {first.get('msg', 'validation failed')}"


def _load_artifact_map(map_path: Path) -> dict[str, bytes]:
    raw = json.loads(map_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("artifact map must be a JSON object of artifact_id to relative path")
    result: dict[str, bytes] = {}
    for artifact_id, relative_path in raw.items():
        if not isinstance(artifact_id, str) or not isinstance(relative_path, str):
            raise ValueError("artifact map keys and values must be strings")
        result[artifact_id] = (map_path.parent / relative_path).read_bytes()
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Independently verify an ETS HQP package")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--artifact-map", type=Path, required=True)
    parser.add_argument("--verifier-id", required=True)
    parser.add_argument("--verifier-build-digest", required=True)
    parser.add_argument("--independent", action="store_true")
    parser.add_argument("--challenge-nonce")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = verify_hardware_qualification_package(
        profile_bytes=args.profile.read_bytes(),
        run_bytes=args.run.read_bytes(),
        report_bytes=args.report.read_bytes(),
        artifact_payloads=_load_artifact_map(args.artifact_map),
        verifier_id=args.verifier_id,
        verifier_build_digest_sha256=args.verifier_build_digest,
        independent_execution_context=args.independent,
        challenge_nonce=args.challenge_nonce,
    )
    if args.format == "text":
        print(render_hardware_qualification_verification(result), end="")
    else:
        print(
            json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    return 0 if result.outcome is VerificationOutcome.VALID else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "HardwareQualificationVerification",
    "QualificationVerificationCheck",
    "VerificationCheckStatus",
    "VerificationOutcome",
    "render_hardware_qualification_verification",
    "verify_hardware_qualification_package",
]
