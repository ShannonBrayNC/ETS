from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path("scripts/fleet/qualify_physical_tpm_a5.py")
SPEC = importlib.util.spec_from_file_location("fleet_a5", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

DEVICE_ID = "ets-edge:1234567890abcdef12345678"
ALIAS = "a" * 64


def _a4() -> dict[str, object]:
    return {
        "schema_version": "ets.fleet.physical-tpm-a4.azure-result.v1",
        "provider_registration_id": ALIAS,
        "canonical_ets_device_id": DEVICE_ID,
        "dps_name": "ets-fleet-dps",
        "resource_group": "rg-fleet",
        "provisioning_status": "disabled",
        "auth_type": "login",
        "fresh_tpm_quote_verified": True,
        "tpm_possession_proven": True,
        "shared_or_sas_credential_used": False,
        "retain_disabled_for_a5": True,
    }


def test_a4_handoff_requires_explicit_retained_disabled_state() -> None:
    result = MODULE.validate_a4_handoff(_a4())
    assert result == (ALIAS, DEVICE_ID, "ets-fleet-dps", "rg-fleet")
    payload = _a4()
    payload["retain_disabled_for_a5"] = False
    with pytest.raises(MODULE.QualificationError):
        MODULE.validate_a4_handoff(payload)


def test_ets_denial_must_be_authoritative_for_same_device() -> None:
    decision = {"allowed": False, "reason": "revoked", "device_id": DEVICE_ID}
    assert MODULE.validate_ets_denial(decision, device_id=DEVICE_ID) == "revoked"
    decision["allowed"] = True
    with pytest.raises(MODULE.QualificationError):
        MODULE.validate_ets_denial(decision, device_id=DEVICE_ID)


def test_dps_enrollment_requires_exact_tpm_identity_and_state() -> None:
    payload = {
        "registrationId": ALIAS,
        "deviceId": DEVICE_ID,
        "provisioningStatus": "enabled",
        "attestation": {"type": "tpm"},
    }
    MODULE.validate_dps_enrollment(
        payload,
        registration_id=ALIAS,
        device_id=DEVICE_ID,
        expected_status="enabled",
    )
    payload["provisioningStatus"] = "disabled"
    with pytest.raises(MODULE.QualificationError):
        MODULE.validate_dps_enrollment(
            payload,
            registration_id=ALIAS,
            device_id=DEVICE_ID,
            expected_status="enabled",
        )


def test_registration_requires_assigned_hub_and_canonical_device() -> None:
    payload = {
        "registrationId": ALIAS,
        "deviceId": DEVICE_ID,
        "status": "assigned",
        "assignedHub": "ets-pilot.azure-devices.net",
    }
    assert (
        MODULE.validate_registration(
            payload,
            registration_id=ALIAS,
            device_id=DEVICE_ID,
        )
        == "ets-pilot.azure-devices.net"
    )


def test_iot_hub_identity_status_is_independent_provider_gate() -> None:
    payload = {"deviceId": DEVICE_ID, "status": "disabled"}
    MODULE.validate_hub_identity(payload, device_id=DEVICE_ID, expected_status="disabled")
    with pytest.raises(MODULE.QualificationError):
        MODULE.validate_hub_identity(payload, device_id=DEVICE_ID, expected_status="enabled")


@pytest.mark.parametrize(
    ("phase", "observed"),
    [
        ("authorized", True),
        ("dps-disabled-hub-enabled", True),
        ("hub-disabled-reconnect", False),
        ("dps-disabled-reprovision", False),
    ],
)
def test_device_probe_has_phase_specific_identity_expectation(
    phase: str,
    observed: bool,
) -> None:
    payload = {
        "schema_version": "ets.fleet.physical-tpm-a5.device-probe.v1",
        "phase": phase,
        "identity_check_succeeded": observed,
        "private_key_material_exported": False,
        "shared_or_sas_credential_used": False,
    }
    MODULE.validate_device_probe(
        payload,
        phase=phase,
        expected_identity_check_success=observed,
    )


def test_dps_commands_force_entra_login_authentication() -> None:
    command = MODULE.dps_show_command("ets-fleet-dps", "rg-fleet", ALIAS)
    assert "--auth-type" in command
    assert "login" in command
    assert "key" not in command
