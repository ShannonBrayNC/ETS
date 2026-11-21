from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.connectors.enterprise.dsc3_read_test import (
    Dsc3ReadTestProfileV1,
    Dsc3RunObservationV1,
    assess_dsc3_read_test,
)

NOW = datetime(2026, 11, 20, 18, 0, tzinfo=UTC)
SHA = "a" * 64


def _pin(name: str, *, qualification: str = "supported") -> dict[str, object]:
    return {
        "name": name,
        "version": "1.0.0",
        "source": f"https://example.invalid/{name}",
        "sha256": SHA,
        "qualification": qualification,
    }


def _profile() -> dict[str, object]:
    return {
        "schema_version": "ets.microsoft.dsc3.read_test.v1",
        "profile_id": "dsc3-host-control-001",
        "environment": "disposable_qualification",
        "execution_mode": "standalone_dsc3",
        "operation": "config_test",
        "resident_lcm_present": False,
        "desired_configuration_sha256": SHA,
        "scheduler": {
            "scheduler_name": "systemd:ets-dsc3-host-control-001.timer",
            "execution_identity": "svc-ets-dsc-reader",
            "interval_seconds": 900,
            "timeout_seconds": 120,
            "overlap_policy": "skip_if_running",
            "reboot_policy": "run_when_available",
            "freshness_threshold_seconds": 1200,
        },
        "runtime": {
            "os_name": "Ubuntu",
            "os_version": "24.04.1",
            "os_architecture": "x86_64",
            "dsc_executable": _pin("dsc"),
            "resources": (_pin("Microsoft.OSInfo"),),
            "adapters": (),
            "schemas": (_pin("Microsoft.DSC/2024/04/config"),),
            "dependencies": (_pin("libicu"),),
        },
    }


def _observation(
    *,
    desired: bool = True,
    exit_code: int = 0,
    include_structured: bool = True,
    completed_at: datetime = NOW - timedelta(seconds=30),
) -> Dsc3RunObservationV1:
    result = None
    if include_structured:
        result = {
            "in_desired_state": desired,
            "resources": (
                {
                    "resource_name": "Microsoft.OSInfo",
                    "in_desired_state": desired,
                    "differing_properties": () if desired else ("family",),
                },
            ),
        }
    return Dsc3RunObservationV1.model_validate(
        {
            "profile_id": "dsc3-host-control-001",
            "desired_configuration_sha256": SHA,
            "started_at_utc": completed_at - timedelta(seconds=5),
            "completed_at_utc": completed_at,
            "process_exit_code": exit_code,
            "structured_result": result,
        }
    )


def test_profile_pins_runtime_and_owns_schedule() -> None:
    profile = Dsc3ReadTestProfileV1.model_validate(_profile())

    assert profile.execution_mode == "standalone_dsc3"
    assert profile.resident_lcm_present is False
    assert profile.scheduler.overlap_policy == "skip_if_running"
    assert profile.runtime.dsc_executable.version == "1.0.0"


def test_production_excludes_proof_of_concept_resource() -> None:
    payload = deepcopy(_profile())
    payload["environment"] = "production"
    runtime = payload["runtime"]
    assert isinstance(runtime, dict)
    runtime["resources"] = (_pin("Microsoft.Windows/Registry", qualification="proof_of_concept"),)

    with pytest.raises(ValidationError, match="excluded from production"):
        Dsc3ReadTestProfileV1.model_validate(payload)


def test_production_rejects_registry_poc_even_if_mislabeled_supported() -> None:
    payload = deepcopy(_profile())
    payload["environment"] = "production"
    runtime = payload["runtime"]
    assert isinstance(runtime, dict)
    runtime["resources"] = (_pin("Microsoft.Windows/Registry"),)

    with pytest.raises(ValidationError, match="excluded from production"):
        Dsc3ReadTestProfileV1.model_validate(payload)


def test_scheduler_requires_timeout_shorter_than_interval() -> None:
    payload = deepcopy(_profile())
    scheduler = payload["scheduler"]
    assert isinstance(scheduler, dict)
    scheduler["timeout_seconds"] = scheduler["interval_seconds"]

    with pytest.raises(ValidationError, match="shorter than interval"):
        Dsc3ReadTestProfileV1.model_validate(payload)


@pytest.mark.parametrize(
    ("desired", "verdict", "reason"),
    [
        (True, "compliant", "structured_test_compliant"),
        (False, "drift", "structured_test_drift"),
    ],
)
def test_successful_process_uses_structured_resource_result(
    desired: bool, verdict: str, reason: str
) -> None:
    profile = Dsc3ReadTestProfileV1.model_validate(_profile())

    assessment = assess_dsc3_read_test(
        profile, _observation(desired=desired), evaluated_at_utc=NOW
    )

    assert assessment.verdict == verdict
    assert assessment.reason == reason


def test_nonzero_process_exit_is_unknown_even_with_structured_drift() -> None:
    profile = Dsc3ReadTestProfileV1.model_validate(_profile())

    assessment = assess_dsc3_read_test(
        profile, _observation(desired=False, exit_code=1), evaluated_at_utc=NOW
    )

    assert assessment.verdict == "unknown"
    assert assessment.reason == "process_failed"


def test_missing_structured_output_is_unknown_even_with_zero_exit() -> None:
    profile = Dsc3ReadTestProfileV1.model_validate(_profile())

    assessment = assess_dsc3_read_test(
        profile, _observation(include_structured=False), evaluated_at_utc=NOW
    )

    assert assessment.verdict == "unknown"
    assert assessment.reason == "structured_output_missing"


@pytest.mark.parametrize("field", ["profile_id", "desired_configuration_sha256"])
def test_observation_must_bind_to_profile_and_configuration(field: str) -> None:
    profile = Dsc3ReadTestProfileV1.model_validate(_profile())
    payload = _observation().model_dump()
    payload[field] = "different-profile" if field == "profile_id" else "b" * 64
    observation = Dsc3RunObservationV1.model_validate(payload)

    assessment = assess_dsc3_read_test(profile, observation, evaluated_at_utc=NOW)

    assert assessment.verdict == "unknown"
    assert assessment.reason == "observation_binding_mismatch"


def test_observation_requires_complete_profile_resource_set() -> None:
    profile_payload = _profile()
    runtime = profile_payload["runtime"]
    assert isinstance(runtime, dict)
    runtime["resources"] = (
        _pin("Microsoft.OSInfo"),
        _pin("Microsoft.HostName"),
    )
    profile = Dsc3ReadTestProfileV1.model_validate(profile_payload)

    assessment = assess_dsc3_read_test(profile, _observation(), evaluated_at_utc=NOW)

    assert assessment.verdict == "unknown"
    assert assessment.reason == "observation_binding_mismatch"


def test_stale_success_becomes_unknown() -> None:
    profile = Dsc3ReadTestProfileV1.model_validate(_profile())
    observation = _observation(completed_at=NOW - timedelta(seconds=1201))

    assessment = assess_dsc3_read_test(profile, observation, evaluated_at_utc=NOW)

    assert assessment.verdict == "unknown"
    assert assessment.reason == "stale_checker"
    assert assessment.observation_age_seconds == 1201


def test_missed_checker_is_unknown_and_retains_last_success() -> None:
    profile = Dsc3ReadTestProfileV1.model_validate(_profile())
    last_success = NOW - timedelta(hours=2)

    assessment = assess_dsc3_read_test(
        profile,
        None,
        evaluated_at_utc=NOW,
        last_successful_completed_at_utc=last_success,
    )

    assert assessment.verdict == "unknown"
    assert assessment.reason == "missed_or_dead_checker"
    assert assessment.last_successful_completed_at_utc == last_success


def test_inconsistent_structured_aggregate_is_rejected() -> None:
    payload = {
        "profile_id": "dsc3-host-control-001",
        "desired_configuration_sha256": SHA,
        "started_at_utc": NOW - timedelta(seconds=10),
        "completed_at_utc": NOW,
        "process_exit_code": 0,
        "structured_result": {
            "in_desired_state": True,
            "resources": (
                {
                    "resource_name": "Microsoft.OSInfo",
                    "in_desired_state": False,
                    "differing_properties": ("family",),
                },
            ),
        },
    }

    with pytest.raises(ValidationError, match="must match all resource results"):
        Dsc3RunObservationV1.model_validate(payload)
