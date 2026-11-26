from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.connectors.enterprise.machine_configuration_equivalence import (
    MANDATORY_SCENARIOS,
    AcceptedDifferenceV1,
    EquivalenceCaseV1,
    MachineConfigurationEquivalenceProfileV1,
    ScenarioObservationV1,
    classify_equivalence_case,
    classify_equivalence_suite,
)

NOW = datetime(2026, 11, 21, 3, 0, tzinfo=UTC)
PROFILE_ID = "mof-to-machine-config-firewall-001"
CONTROL_ID = "windows-firewall-domain-enabled"
TARGET_ID = "vm:pilot-01"
LEGACY_WRITER = "service:azure-automation-state-configuration"
REPLACEMENT_WRITER = "service:azure-machine-configuration"


def _artifact(role: str, marker: str) -> dict[str, object]:
    return {
        "role": role,
        "uri": f"evidence://mig-01/{role}",
        "sha256": marker * 64,
        "size_bytes": 128,
    }


def _profile_payload() -> dict[str, object]:
    roles = (
        "legacy_source",
        "original_mof",
        "recompiled_mof",
        "legacy_module_bundle",
        "lcm_metaconfiguration",
        "replacement_assignment",
        "replacement_package",
    )
    return {
        "schema_version": "ets.microsoft.machine_configuration_equivalence.v1",
        "profile_id": PROFILE_ID,
        "control_id": CONTROL_ID,
        "target_id": TARGET_ID,
        "environment": "disposable_qualification",
        "legacy_runtime": {
            "os_name": "Windows Server",
            "os_version": "2022",
            "engine_name": "Windows PowerShell DSC",
            "engine_version": "5.1.20348.2849",
            "agent_or_lcm_version": "LCM 2.0",
        },
        "replacement_runtime": {
            "os_name": "Windows Server",
            "os_version": "2022",
            "engine_name": "Azure Machine Configuration",
            "engine_version": "1.29.0",
            "agent_or_lcm_version": "Guest Configuration extension 1.29.0",
        },
        "writer_boundary": {
            "legacy_writer_identity": LEGACY_WRITER,
            "replacement_writer_identity": REPLACEMENT_WRITER,
            "simultaneous_writers_prohibited": True,
            "guest_telemetry_required_for_correction": True,
        },
        "retained_artifacts": tuple(
            _artifact(role, hex(index + 1)[2:]) for index, role in enumerate(roles)
        ),
        "retirement_deadline": "2027-09-30",
    }


def _observation(
    runtime: str,
    scenario: str,
    *,
    outcome: str | None = None,
    state_sha256: str | None = "a" * 64,
    evidence_sha256: str | None = None,
) -> ScenarioObservationV1:
    default_outcomes = {
        "initial_application": "applied",
        "recurring_drift": "drift_detected",
        "correction": "corrected",
        "errors": "error",
        "reporting": "reported",
    }
    payload = {
        "profile_id": PROFILE_ID,
        "control_id": CONTROL_ID,
        "target_id": TARGET_ID,
        "runtime": runtime,
        "scenario": scenario,
        "observed_at_utc": NOW - timedelta(minutes=1),
        "active_writer_identity": (
            LEGACY_WRITER if runtime == "legacy_lcm" else REPLACEMENT_WRITER
        ),
        "other_active_writer_identities": (),
        "outcome": outcome or default_outcomes[scenario],
        "state_sha256": state_sha256,
        "error_code": "DSC_RESOURCE_FAILED" if scenario == "errors" else None,
        "report_sha256": "b" * 64 if scenario == "reporting" else None,
        "guest_telemetry_sha256": "c" * 64 if scenario == "correction" else None,
        "evidence_sha256": evidence_sha256
        or ("d" * 64 if runtime == "legacy_lcm" else "e" * 64),
    }
    return ScenarioObservationV1.model_validate(payload)


def _case(scenario: str) -> EquivalenceCaseV1:
    return EquivalenceCaseV1(
        legacy=_observation("legacy_lcm", scenario),
        replacement=_observation("machine_configuration", scenario),
    )


def _profile() -> MachineConfigurationEquivalenceProfileV1:
    return MachineConfigurationEquivalenceProfileV1.model_validate(_profile_payload())


def test_profile_retains_complete_legacy_and_replacement_artifact_set() -> None:
    profile = _profile()

    assert {artifact.role for artifact in profile.retained_artifacts} == {
        "legacy_source",
        "original_mof",
        "recompiled_mof",
        "legacy_module_bundle",
        "lcm_metaconfiguration",
        "replacement_assignment",
        "replacement_package",
    }
    assert profile.retirement_deadline == "2027-09-30"


def test_profile_rejects_missing_retained_artifact() -> None:
    payload = deepcopy(_profile_payload())
    artifacts = payload["retained_artifacts"]
    assert isinstance(artifacts, tuple)
    payload["retained_artifacts"] = artifacts[:-1]

    with pytest.raises(ValidationError, match="artifact set is incomplete"):
        MachineConfigurationEquivalenceProfileV1.model_validate(payload)


def test_profile_rejects_duplicate_retained_artifact_role() -> None:
    payload = deepcopy(_profile_payload())
    artifacts = payload["retained_artifacts"]
    assert isinstance(artifacts, tuple)
    payload["retained_artifacts"] = (*artifacts, artifacts[0])

    with pytest.raises(ValidationError, match="roles cannot be duplicated"):
        MachineConfigurationEquivalenceProfileV1.model_validate(payload)


def test_profile_requires_single_writer_and_guest_telemetry_policy() -> None:
    payload = deepcopy(_profile_payload())
    boundary = payload["writer_boundary"]
    assert isinstance(boundary, dict)
    boundary["simultaneous_writers_prohibited"] = False

    with pytest.raises(ValidationError):
        MachineConfigurationEquivalenceProfileV1.model_validate(payload)


def test_exact_observable_semantics_pass() -> None:
    result = classify_equivalence_case(
        _profile(), _case("initial_application"), evaluated_at_utc=NOW
    )

    assert result.classification == "pass"
    assert result.reason == "observable_semantics_match"


def test_unapproved_behavior_difference_fails() -> None:
    case = _case("recurring_drift")
    replacement_payload = case.replacement.model_dump()
    replacement_payload["state_sha256"] = "f" * 64
    changed = case.model_copy(
        update={
            "replacement": ScenarioObservationV1.model_validate(replacement_payload),
        }
    )

    result = classify_equivalence_case(_profile(), changed, evaluated_at_utc=NOW)

    assert result.classification == "fail"
    assert result.reason == "unapproved_behavior_difference"


def test_exact_bound_reviewed_difference_is_accepted() -> None:
    case = _case("recurring_drift")
    replacement_payload = case.replacement.model_dump()
    replacement_payload["state_sha256"] = "f" * 64
    replacement = ScenarioObservationV1.model_validate(replacement_payload)
    approval = AcceptedDifferenceV1(
        scenario="recurring_drift",
        approval_id="change-review-42",
        approved_by="migration-control-owner",
        rationale="Machine Configuration reports the normalized state shape.",
        approved_at_utc=NOW - timedelta(hours=1),
        expires_at_utc=NOW + timedelta(days=30),
        legacy_evidence_sha256=case.legacy.evidence_sha256,
        replacement_evidence_sha256=replacement.evidence_sha256,
    )
    changed = EquivalenceCaseV1(
        legacy=case.legacy,
        replacement=replacement,
        accepted_difference=approval,
    )

    result = classify_equivalence_case(_profile(), changed, evaluated_at_utc=NOW)

    assert result.classification == "accepted_difference"
    assert result.reason == "reviewed_difference_is_exact_bound"


@pytest.mark.parametrize(
    ("approval_change", "reason"),
    [
        ({"legacy_evidence_sha256": "0" * 64}, "accepted_difference_evidence_mismatch"),
        (
            {
                "approved_at_utc": NOW - timedelta(days=2),
                "expires_at_utc": NOW - timedelta(days=1),
            },
            "accepted_difference_not_current",
        ),
    ],
)
def test_misbound_or_expired_difference_fails(
    approval_change: dict[str, object], reason: str
) -> None:
    case = _case("initial_application")
    replacement_payload = case.replacement.model_dump()
    replacement_payload["state_sha256"] = "f" * 64
    replacement = ScenarioObservationV1.model_validate(replacement_payload)
    approval_payload: dict[str, object] = {
        "scenario": "initial_application",
        "approval_id": "change-review-42",
        "approved_by": "migration-control-owner",
        "rationale": "Reviewed difference.",
        "approved_at_utc": NOW - timedelta(hours=1),
        "expires_at_utc": NOW + timedelta(days=30),
        "legacy_evidence_sha256": case.legacy.evidence_sha256,
        "replacement_evidence_sha256": replacement.evidence_sha256,
    }
    approval_payload.update(approval_change)
    changed = EquivalenceCaseV1(
        legacy=case.legacy,
        replacement=replacement,
        accepted_difference=AcceptedDifferenceV1.model_validate(approval_payload),
    )

    result = classify_equivalence_case(_profile(), changed, evaluated_at_utc=NOW)

    assert result.classification == "fail"
    assert result.reason == reason


@pytest.mark.parametrize("violation", ["wrong_writer", "second_writer"])
def test_writer_boundary_violation_fails(violation: str) -> None:
    case = _case("correction")
    replacement_payload = case.replacement.model_dump()
    if violation == "wrong_writer":
        replacement_payload["active_writer_identity"] = "service:unexpected-writer"
    else:
        replacement_payload["other_active_writer_identities"] = (LEGACY_WRITER,)
    changed = case.model_copy(
        update={
            "replacement": ScenarioObservationV1.model_validate(replacement_payload),
        }
    )

    result = classify_equivalence_case(_profile(), changed, evaluated_at_utc=NOW)

    assert result.classification == "fail"
    assert result.reason == "single_writer_boundary_violated"


def test_missing_guest_correction_telemetry_is_inconclusive() -> None:
    case = _case("correction")
    payload = case.replacement.model_dump()
    payload["guest_telemetry_sha256"] = None
    changed = case.model_copy(
        update={"replacement": ScenarioObservationV1.model_validate(payload)}
    )

    result = classify_equivalence_case(_profile(), changed, evaluated_at_utc=NOW)

    assert result.classification == "inconclusive"
    assert result.reason == "guest_correction_telemetry_missing"


def test_missing_report_evidence_is_inconclusive() -> None:
    case = _case("reporting")
    payload = case.legacy.model_dump()
    payload["report_sha256"] = None
    changed = case.model_copy(update={"legacy": ScenarioObservationV1.model_validate(payload)})

    result = classify_equivalence_case(_profile(), changed, evaluated_at_utc=NOW)

    assert result.classification == "inconclusive"
    assert result.reason == "report_evidence_missing"


def test_unavailable_runtime_evidence_is_inconclusive() -> None:
    case = _case("initial_application")
    payload = case.legacy.model_dump()
    payload["outcome"] = "unavailable"
    changed = case.model_copy(update={"legacy": ScenarioObservationV1.model_validate(payload)})

    result = classify_equivalence_case(_profile(), changed, evaluated_at_utc=NOW)

    assert result.classification == "inconclusive"
    assert result.reason == "runtime_evidence_unavailable"


def test_cross_target_evidence_is_inconclusive() -> None:
    case = _case("initial_application")
    payload = case.replacement.model_dump()
    payload["target_id"] = "vm:other"
    changed = case.model_copy(
        update={"replacement": ScenarioObservationV1.model_validate(payload)}
    )

    result = classify_equivalence_case(_profile(), changed, evaluated_at_utc=NOW)

    assert result.classification == "inconclusive"
    assert result.reason == "observation_binding_mismatch"


def test_complete_five_scenario_suite_passes() -> None:
    cases = tuple(_case(scenario) for scenario in MANDATORY_SCENARIOS)

    result = classify_equivalence_suite(_profile(), cases, evaluated_at_utc=NOW)

    assert result.classification == "pass"
    assert result.missing_scenarios == ()
    assert len(result.scenario_results) == 5


def test_missing_scenario_makes_suite_inconclusive() -> None:
    cases = tuple(_case(scenario) for scenario in MANDATORY_SCENARIOS[:-1])

    result = classify_equivalence_suite(_profile(), cases, evaluated_at_utc=NOW)

    assert result.classification == "inconclusive"
    assert result.missing_scenarios == ("reporting",)


def test_suite_rejects_duplicate_scenarios() -> None:
    case = _case("initial_application")

    with pytest.raises(ValueError, match="cannot be duplicated"):
        classify_equivalence_suite(_profile(), (case, case), evaluated_at_utc=NOW)


def test_error_observation_requires_error_code() -> None:
    payload = _observation("legacy_lcm", "errors").model_dump()
    payload["error_code"] = None

    with pytest.raises(ValidationError, match="require an error code"):
        ScenarioObservationV1.model_validate(payload)
