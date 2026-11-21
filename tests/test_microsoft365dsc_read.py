from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.connectors.enterprise.microsoft365dsc_read import (
    M365DscReadObservationV1,
    M365DscReadProfileV1,
    assess_m365dsc_read,
)

NOW = datetime(2026, 11, 20, 21, 0, tzinfo=UTC)
DESIRED = "a" * 64
OBSERVED_DRIFT = "b" * 64


def _pin(name: str, version: str) -> dict[str, object]:
    return {
        "name": name,
        "version": version,
        "source": f"https://example.invalid/{name}/{version}",
        "sha256": "c" * 64,
    }


def _profile() -> dict[str, object]:
    return {
        "schema_version": "ets.microsoft.m365dsc.read.v1",
        "profile_id": "m365dsc-exchange-transport-rule-001",
        "environment": "disposable_qualification",
        "tenant_id": "tenant-a",
        "target_id": "tenant-a/exchange/transport-rule/pilot-rule",
        "desired_property_sha256": DESIRED,
        "freshness_threshold_seconds": 900,
        "runtime": {
            "os_name": "Windows Server",
            "os_version": "2025",
            "powershell_edition": "Core",
            "powershell_version": "7.6.1",
            "microsoft365dsc_module": _pin("Microsoft365DSC", "1.26.1105.1"),
            "dependencies": (_pin("ExchangeOnlineManagement", "3.9.0"),),
            "uses_windows_powershell_lcm": False,
            "lcm_bridge": None,
        },
        "authority": {
            "collector_identity": "app:m365dsc-read-test",
            "get_test_permissions": ("Exchange.ManageAsApp.Read",),
            "write_permissions": (),
        },
        "resource": {
            "resource_name": "EXOTransportRule",
            "module_name": "Microsoft365DSC",
            "module_version": "1.26.1105.1",
            "workload": "ExchangeOnline",
            "target_property": "TransportRule:pilot-rule/State",
            "qualification": "supported",
            "allowed_operations": ("Get", "Test"),
        },
        "native_readback": {
            "reader_identity": "app:exchange-native-reader",
            "workload": "ExchangeOnline",
            "api_version": "ExchangeOnlineManagement/3.9.0",
            "endpoint_family": "Get-TransportRule",
            "read_permissions": ("Exchange.ManageAsApp.Read",),
            "observed_property": "TransportRule:pilot-rule/State",
        },
        "frozen_predecessors": (
            {
                "profile_id": "m365dsc-exchange-transport-rule-000",
                "profile_sha256": "d" * 64,
                "module_version": "1.26.1022.1",
                "status": "frozen",
            },
        ),
    }


def _observation(
    *,
    desired: bool = True,
    collector_outcome: str = "success",
    readback_outcome: str = "success",
    collected_at: datetime = NOW - timedelta(seconds=30),
) -> M365DscReadObservationV1:
    return M365DscReadObservationV1.model_validate(
        {
            "profile_id": "m365dsc-exchange-transport-rule-001",
            "target_id": "tenant-a/exchange/transport-rule/pilot-rule",
            "desired_property_sha256": DESIRED,
            "collector_identity": "app:m365dsc-read-test",
            "reader_identity": "app:exchange-native-reader",
            "collected_at_utc": collected_at,
            "collector_outcome": collector_outcome,
            "test_in_desired_state": desired if collector_outcome == "success" else None,
            "native_readback_outcome": readback_outcome,
            "native_property_sha256": (
                (DESIRED if desired else OBSERVED_DRIFT)
                if readback_outcome == "success"
                else None
            ),
        }
    )


def test_profile_pins_runtime_resource_authority_and_native_readback() -> None:
    profile = M365DscReadProfileV1.model_validate(_profile())

    assert profile.runtime.powershell_version == "7.6.1"
    assert profile.resource.allowed_operations == ("Get", "Test")
    assert profile.authority.write_permissions == ()
    assert profile.native_readback.reader_identity != profile.authority.collector_identity
    assert profile.frozen_predecessors[0].status == "frozen"


@pytest.mark.parametrize("version", ["7.5.9", "5.1.0", "latest"])
def test_profile_requires_exact_powershell_76_or_newer(version: str) -> None:
    payload = deepcopy(_profile())
    runtime = payload["runtime"]
    assert isinstance(runtime, dict)
    runtime["powershell_version"] = version

    with pytest.raises(ValidationError, match="7.6.0 or newer|exact semantic version"):
        M365DscReadProfileV1.model_validate(payload)


def test_windows_powershell_lcm_requires_explicit_ps7_bridge() -> None:
    payload = deepcopy(_profile())
    runtime = payload["runtime"]
    assert isinstance(runtime, dict)
    runtime["uses_windows_powershell_lcm"] = True

    with pytest.raises(ValidationError, match="explicit PS7 bridge"):
        M365DscReadProfileV1.model_validate(payload)


@pytest.mark.parametrize("permission", ["Directory.ReadWrite.All", "Write.Configuration"])
def test_get_test_authority_rejects_write_capable_permissions(permission: str) -> None:
    payload = deepcopy(_profile())
    authority = payload["authority"]
    assert isinstance(authority, dict)
    authority["get_test_permissions"] = (permission,)

    with pytest.raises(ValidationError, match="write-capable"):
        M365DscReadProfileV1.model_validate(payload)


def test_get_test_authority_rejects_separate_write_grants() -> None:
    payload = deepcopy(_profile())
    authority = payload["authority"]
    assert isinstance(authority, dict)
    authority["write_permissions"] = ("Exchange.ManageAsApp",)

    with pytest.raises(ValidationError, match="cannot include write permissions"):
        M365DscReadProfileV1.model_validate(payload)


def test_resource_must_bind_to_pinned_module() -> None:
    payload = deepcopy(_profile())
    resource = payload["resource"]
    assert isinstance(resource, dict)
    resource["module_version"] = "1.26.1201.1"

    with pytest.raises(ValidationError, match="pinned Microsoft365DSC module"):
        M365DscReadProfileV1.model_validate(payload)


def test_native_readback_requires_separate_identity() -> None:
    payload = deepcopy(_profile())
    native = payload["native_readback"]
    assert isinstance(native, dict)
    native["reader_identity"] = "app:m365dsc-read-test"

    with pytest.raises(ValidationError, match="identity separate from the collector"):
        M365DscReadProfileV1.model_validate(payload)


@pytest.mark.parametrize(
    ("desired", "verdict", "reason"),
    [
        (True, "compliant", "test_and_native_readback_agree"),
        (False, "drift", "test_reports_drift_and_native_readback_agrees"),
    ],
)
def test_assessment_requires_test_and_native_readback_agreement(
    desired: bool, verdict: str, reason: str
) -> None:
    profile = M365DscReadProfileV1.model_validate(_profile())

    result = assess_m365dsc_read(profile, _observation(desired=desired), evaluated_at_utc=NOW)

    assert result.verdict == verdict
    assert result.reason == reason


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [
        ("authority_revoked", "collection_authority_revoked"),
        ("unsupported", "unsupported_resource"),
        ("runtime_failure", "collector_failed"),
    ],
)
def test_collector_failures_are_unknown(outcome: str, reason: str) -> None:
    profile = M365DscReadProfileV1.model_validate(_profile())

    result = assess_m365dsc_read(
        profile, _observation(collector_outcome=outcome), evaluated_at_utc=NOW
    )

    assert result.verdict == "unknown"
    assert result.reason == reason


def test_failed_native_readback_is_unknown() -> None:
    profile = M365DscReadProfileV1.model_validate(_profile())

    result = assess_m365dsc_read(
        profile, _observation(readback_outcome="authority_revoked"), evaluated_at_utc=NOW
    )

    assert result.verdict == "unknown"
    assert result.reason == "native_readback_unavailable"


def test_dsc_and_native_readback_disagreement_is_unknown() -> None:
    profile = M365DscReadProfileV1.model_validate(_profile())
    payload = _observation(desired=True).model_dump()
    payload["native_property_sha256"] = OBSERVED_DRIFT

    result = assess_m365dsc_read(
        profile, M365DscReadObservationV1.model_validate(payload), evaluated_at_utc=NOW
    )

    assert result.verdict == "unknown"
    assert result.reason == "test_and_native_readback_disagree"


def test_stale_observation_is_unknown() -> None:
    profile = M365DscReadProfileV1.model_validate(_profile())

    result = assess_m365dsc_read(
        profile,
        _observation(collected_at=NOW - timedelta(seconds=901)),
        evaluated_at_utc=NOW,
    )

    assert result.verdict == "unknown"
    assert result.reason == "stale_observation"
    assert result.observation_age_seconds == 901


def test_cross_profile_observation_is_unknown() -> None:
    profile = M365DscReadProfileV1.model_validate(_profile())
    payload = _observation().model_dump()
    payload["target_id"] = "tenant-b/exchange/transport-rule/pilot-rule"

    result = assess_m365dsc_read(
        profile, M365DscReadObservationV1.model_validate(payload), evaluated_at_utc=NOW
    )

    assert result.verdict == "unknown"
    assert result.reason == "observation_binding_mismatch"
