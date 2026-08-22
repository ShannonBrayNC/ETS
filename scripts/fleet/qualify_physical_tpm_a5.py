#!/usr/bin/env python3
"""Orchestrate FLEET-A5 physical TPM provisioning and dual-layer revocation."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_AZURE_IOT_EXTENSION_VERSION = "0.30.0"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9:._-]{3,160}$")
DENIAL_REASONS = {"quarantined", "revoked", "decommissioned"}


class QualificationError(RuntimeError):
    """Raised when the A5 qualification must fail closed."""


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, check=False, text=True, capture_output=True)
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise QualificationError(f"command failed ({command[0]}): {stderr}")
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualificationError(f"invalid JSON evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise QualificationError(f"unexpected JSON evidence shape: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_azure_tools() -> str:
    if shutil.which("az") is None:
        raise QualificationError("Azure CLI 'az' is required")
    run(["az", "account", "show", "--output", "none"])
    extension = run(
        ["az", "extension", "show", "--name", "azure-iot", "--query", "version", "-o", "tsv"]
    ).stdout.strip()
    if extension != REQUIRED_AZURE_IOT_EXTENSION_VERSION:
        raise QualificationError(
            "azure-iot extension version must be "
            f"{REQUIRED_AZURE_IOT_EXTENSION_VERSION}; found {extension or 'none'}"
        )
    return extension


def load_json_output(command: list[str]) -> dict[str, Any]:
    result = run([*command, "--output", "json"])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise QualificationError("Azure CLI returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise QualificationError("Azure CLI returned an unexpected payload shape")
    return payload


def validate_a4_handoff(payload: dict[str, Any]) -> tuple[str, str, str, str]:
    if payload.get("schema_version") != "ets.fleet.physical-tpm-a4.azure-result.v1":
        raise QualificationError("unexpected A4 Azure-result schema")
    if payload.get("retain_disabled_for_a5") is not True:
        raise QualificationError("A5 requires an explicit retained-disabled A4 handoff")
    if payload.get("fresh_tpm_quote_verified") is not True:
        raise QualificationError("A4 handoff lacks a fresh verified TPM quote")
    if payload.get("tpm_possession_proven") is not True:
        raise QualificationError("A4 handoff lacks TPM possession proof")
    if payload.get("provisioning_status") != "disabled":
        raise QualificationError("A4 handoff must start with DPS enrollment disabled")
    if payload.get("auth_type") != "login":
        raise QualificationError("A4 handoff must use Microsoft Entra data-plane authentication")
    if payload.get("shared_or_sas_credential_used") is not False:
        raise QualificationError("shared/SAS credentials are forbidden")

    registration_id = str(payload.get("provider_registration_id", ""))
    device_id = str(payload.get("canonical_ets_device_id", ""))
    dps_name = str(payload.get("dps_name", ""))
    resource_group = str(payload.get("resource_group", ""))
    if not HEX64_RE.fullmatch(registration_id):
        raise QualificationError("A4 provider registration alias is invalid")
    if not DEVICE_ID_RE.fullmatch(device_id):
        raise QualificationError("canonical ETS device ID is invalid")
    if not dps_name or not resource_group:
        raise QualificationError("A4 handoff is missing the bounded DPS target")
    return registration_id, device_id, dps_name, resource_group


def validate_ets_denial(payload: dict[str, Any], *, device_id: str) -> str:
    if payload.get("device_id") != device_id:
        raise QualificationError("ETS authorization decision is for another device")
    if payload.get("allowed") is not False:
        raise QualificationError("provider revocation requires an ETS denied decision")
    reason = str(payload.get("reason", "")).lower()
    if reason not in DENIAL_REASONS:
        raise QualificationError("ETS denial reason is not a revocation lifecycle state")
    return reason


def dps_show_command(dps_name: str, resource_group: str, registration_id: str) -> list[str]:
    return [
        "az", "iot", "dps", "enrollment", "show",
        "--dps-name", dps_name,
        "--resource-group", resource_group,
        "--enrollment-id", registration_id,
        "--auth-type", "login",
    ]


def validate_dps_enrollment(
    payload: dict[str, Any],
    *,
    registration_id: str,
    device_id: str,
    expected_status: str,
) -> None:
    if payload.get("registrationId") != registration_id:
        raise QualificationError("DPS registration ID mismatch")
    if payload.get("deviceId") != device_id:
        raise QualificationError("DPS canonical device ID mismatch")
    if str(payload.get("provisioningStatus", "")).lower() != expected_status:
        raise QualificationError(f"DPS enrollment is not {expected_status}")
    attestation = payload.get("attestation")
    if not isinstance(attestation, dict) or str(attestation.get("type", "")).lower() != "tpm":
        raise QualificationError("DPS enrollment attestation type is not TPM")


def validate_registration(
    payload: dict[str, Any],
    *,
    registration_id: str,
    device_id: str,
) -> str:
    if payload.get("registrationId") != registration_id:
        raise QualificationError("DPS service registration ID mismatch")
    if payload.get("deviceId") != device_id:
        raise QualificationError("DPS service registration device ID mismatch")
    if str(payload.get("status", "")).lower() != "assigned":
        raise QualificationError("DPS service registration is not assigned")
    assigned_hub = str(payload.get("assignedHub", "")).strip()
    if not assigned_hub.endswith(".azure-devices.net"):
        raise QualificationError("DPS assigned IoT Hub hostname is invalid")
    return assigned_hub


def hub_name_from_hostname(hostname: str) -> str:
    suffix = ".azure-devices.net"
    if not hostname.endswith(suffix):
        raise QualificationError("assigned IoT Hub hostname is invalid")
    hub_name = hostname[: -len(suffix)]
    if not hub_name:
        raise QualificationError("assigned IoT Hub name is empty")
    return hub_name


def validate_hub_identity(
    payload: dict[str, Any],
    *,
    device_id: str,
    expected_status: str,
) -> None:
    observed_id = payload.get("deviceId") or payload.get("device_id")
    if observed_id != device_id:
        raise QualificationError("IoT Hub device identity mismatch")
    if str(payload.get("status", "")).lower() != expected_status:
        raise QualificationError(f"IoT Hub device identity is not {expected_status}")


def validate_device_probe(
    payload: dict[str, Any],
    *,
    phase: str,
    expected_identity_check_success: bool,
) -> None:
    if payload.get("schema_version") != "ets.fleet.physical-tpm-a5.device-probe.v1":
        raise QualificationError("unexpected A5 device-probe schema")
    if payload.get("phase") != phase:
        raise QualificationError("unexpected A5 device probe phase")
    if payload.get("shared_or_sas_credential_used") is not False:
        raise QualificationError("device probe used a forbidden shared/SAS credential")
    if payload.get("private_key_material_exported") is not False:
        raise QualificationError("device probe exported private key material")
    if payload.get("identity_check_succeeded") is not expected_identity_check_success:
        raise QualificationError("device identity connectivity outcome did not match expectation")


def _a4(args: argparse.Namespace) -> tuple[dict[str, Any], str, str, str, str]:
    payload = load_json(args.a4_result.resolve())
    registration_id, device_id, dps_name, resource_group = validate_a4_handoff(payload)
    return payload, registration_id, device_id, dps_name, resource_group


def command_enable(args: argparse.Namespace) -> int:
    _, registration_id, device_id, dps_name, resource_group = _a4(args)
    extension = verify_azure_tools()
    current = load_json_output(dps_show_command(dps_name, resource_group, registration_id))
    validate_dps_enrollment(
        current,
        registration_id=registration_id,
        device_id=device_id,
        expected_status="disabled",
    )
    enabled = load_json_output(
        [
            "az", "iot", "dps", "enrollment", "update",
            "--dps-name", dps_name,
            "--resource-group", resource_group,
            "--enrollment-id", registration_id,
            "--provisioning-status", "enabled",
            "--auth-type", "login",
        ]
    )
    validate_dps_enrollment(
        enabled,
        registration_id=registration_id,
        device_id=device_id,
        expected_status="enabled",
    )
    id_scope = run(
        [
            "az", "iot", "dps", "show",
            "--name", dps_name,
            "--resource-group", resource_group,
            "--query", "properties.idScope",
            "-o", "tsv",
        ]
    ).stdout.strip()
    if not id_scope:
        raise QualificationError("DPS ID Scope could not be resolved")
    result = {
        "schema_version": "ets.fleet.physical-tpm-a5.enable-result.v1",
        "provider_registration_id": registration_id,
        "canonical_ets_device_id": device_id,
        "dps_name": dps_name,
        "resource_group": resource_group,
        "dps_id_scope": id_scope,
        "global_endpoint": "https://global.azure-devices-provisioning.net",
        "reference_client": "azure-iot-edge-1.6-lts",
        "provisioning_attestation": "tpm",
        "dps_status": "enabled",
        "auth_type": "login",
        "azure_iot_extension_version": extension,
        "shared_or_sas_credential_used": False,
        "azure_token_retained": False,
        "enabled_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(args.output_dir / "a5-enable-result.json", result)
    print("A5 DPS enrollment enabled; transfer only the sanitized device configuration.")
    return 0


def command_verify_positive(args: argparse.Namespace) -> int:
    _, registration_id, device_id, dps_name, resource_group = _a4(args)
    verify_azure_tools()
    probe = load_json(args.device_probe.resolve())
    validate_device_probe(
        probe,
        phase="authorized",
        expected_identity_check_success=True,
    )
    enrollment = load_json_output(dps_show_command(dps_name, resource_group, registration_id))
    validate_dps_enrollment(
        enrollment,
        registration_id=registration_id,
        device_id=device_id,
        expected_status="enabled",
    )
    registration = load_json_output(
        [
            "az", "iot", "dps", "enrollment", "registration", "show",
            "--dps-name", dps_name,
            "--resource-group", resource_group,
            "--enrollment-id", registration_id,
            "--auth-type", "login",
        ]
    )
    assigned_hub = validate_registration(
        registration,
        registration_id=registration_id,
        device_id=device_id,
    )
    hub_name = hub_name_from_hostname(assigned_hub)
    hub_identity = load_json_output(
        [
            "az", "iot", "hub", "device-identity", "show",
            "--hub-name", hub_name,
            "--device-id", device_id,
            "--auth-type", "login",
        ]
    )
    validate_hub_identity(hub_identity, device_id=device_id, expected_status="enabled")
    result = {
        "schema_version": "ets.fleet.physical-tpm-a5.positive-result.v1",
        "provider_registration_id": registration_id,
        "canonical_ets_device_id": device_id,
        "assigned_iot_hub": assigned_hub,
        "iot_hub_device_status": "enabled",
        "dps_status": "enabled",
        "dps_registration_status": "assigned",
        "authorized_device_probe_succeeded": True,
        "shared_or_sas_credential_used": False,
        "azure_token_retained": False,
        "verified_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(args.output_dir / "a5-positive-result.json", result)
    print(f"A5 positive provisioning verified on {assigned_hub}.")
    return 0


def command_disable_dps(args: argparse.Namespace) -> int:
    _, registration_id, device_id, dps_name, resource_group = _a4(args)
    verify_azure_tools()
    reason = validate_ets_denial(load_json(args.ets_decision.resolve()), device_id=device_id)
    disabled = load_json_output(
        [
            "az", "iot", "dps", "enrollment", "update",
            "--dps-name", dps_name,
            "--resource-group", resource_group,
            "--enrollment-id", registration_id,
            "--provisioning-status", "disabled",
            "--auth-type", "login",
        ]
    )
    validate_dps_enrollment(
        disabled,
        registration_id=registration_id,
        device_id=device_id,
        expected_status="disabled",
    )
    result = {
        "schema_version": "ets.fleet.physical-tpm-a5.dps-disabled.v1",
        "provider_registration_id": registration_id,
        "canonical_ets_device_id": device_id,
        "ets_authorization_allowed": False,
        "ets_denial_reason": reason,
        "dps_status": "disabled",
        "iot_hub_identity_changed": False,
        "shared_or_sas_credential_used": False,
        "disabled_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(args.output_dir / "a5-dps-disabled.json", result)
    print("DPS disabled. STOP: verify cached IoT Hub reconnect before disabling the Hub identity.")
    return 0


def command_verify_dps_only(args: argparse.Namespace) -> int:
    probe = load_json(args.device_probe.resolve())
    validate_device_probe(
        probe,
        phase="dps-disabled-hub-enabled",
        expected_identity_check_success=True,
    )
    result = {
        "schema_version": "ets.fleet.physical-tpm-a5.dps-only-negative-control.v1",
        "dps_disabled": True,
        "iot_hub_identity_still_enabled": True,
        "device_reconnect_still_succeeded": True,
        "demonstrates_dps_disable_is_not_connection_revocation": True,
        "verified_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(args.output_dir / "a5-dps-only-negative-control.json", result)
    print("Negative control passed: DPS disable alone did not revoke existing Hub authentication.")
    return 0


def command_disable_hub(args: argparse.Namespace) -> int:
    _, _, device_id, _, _ = _a4(args)
    verify_azure_tools()
    reason = validate_ets_denial(load_json(args.ets_decision.resolve()), device_id=device_id)
    positive = load_json(args.positive_result.resolve())
    if positive.get("canonical_ets_device_id") != device_id:
        raise QualificationError("positive A5 evidence is for another ETS device")
    assigned_hub = str(positive.get("assigned_iot_hub", ""))
    hub_name = hub_name_from_hostname(assigned_hub)
    identity = load_json_output(
        [
            "az", "iot", "hub", "device-identity", "update",
            "--hub-name", hub_name,
            "--device-id", device_id,
            "--set", "status=disabled",
            "--auth-type", "login",
        ]
    )
    validate_hub_identity(identity, device_id=device_id, expected_status="disabled")
    result = {
        "schema_version": "ets.fleet.physical-tpm-a5.hub-disabled.v1",
        "canonical_ets_device_id": device_id,
        "assigned_iot_hub": assigned_hub,
        "ets_authorization_allowed": False,
        "ets_denial_reason": reason,
        "iot_hub_device_status": "disabled",
        "shared_or_sas_credential_used": False,
        "disabled_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(args.output_dir / "a5-hub-disabled.json", result)
    print("IoT Hub device identity disabled; run the final device reconnect/reprovision probes.")
    return 0


def command_verify_final(args: argparse.Namespace) -> int:
    _, registration_id, device_id, dps_name, resource_group = _a4(args)
    verify_azure_tools()
    reason = validate_ets_denial(load_json(args.ets_decision.resolve()), device_id=device_id)
    reconnect = load_json(args.reconnect_probe.resolve())
    validate_device_probe(
        reconnect,
        phase="hub-disabled-reconnect",
        expected_identity_check_success=False,
    )
    reprovision = load_json(args.reprovision_probe.resolve())
    validate_device_probe(
        reprovision,
        phase="dps-disabled-reprovision",
        expected_identity_check_success=False,
    )
    positive = load_json(args.positive_result.resolve())
    assigned_hub = str(positive.get("assigned_iot_hub", ""))
    hub_name = hub_name_from_hostname(assigned_hub)

    enrollment = load_json_output(dps_show_command(dps_name, resource_group, registration_id))
    validate_dps_enrollment(
        enrollment,
        registration_id=registration_id,
        device_id=device_id,
        expected_status="disabled",
    )
    hub_identity = load_json_output(
        [
            "az", "iot", "hub", "device-identity", "show",
            "--hub-name", hub_name,
            "--device-id", device_id,
            "--auth-type", "login",
        ]
    )
    validate_hub_identity(hub_identity, device_id=device_id, expected_status="disabled")

    result = {
        "schema_version": "ets.fleet.physical-tpm-a5.final-result.v1",
        "provider_registration_id": registration_id,
        "canonical_ets_device_id": device_id,
        "assigned_iot_hub": assigned_hub,
        "ets_authorization_allowed": False,
        "ets_denial_reason": reason,
        "dps_status": "disabled",
        "iot_hub_device_status": "disabled",
        "reconnect_denied": True,
        "reprovision_denied": True,
        "dual_layer_provider_revocation_qualified": True,
        "end_to_end_physical_fleet_revocation_qualified": True,
        "private_tpm_material_retained": False,
        "device_credential_retained": False,
        "shared_or_sas_credential_used": False,
        "azure_token_retained": False,
        "qualified_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(args.output_dir / "a5-final-result.json", result)
    print("FLEET-A5 qualified: ETS denial + DPS reprovision denial + IoT Hub reconnect denial.")
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--a4-result", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    enable = subparsers.add_parser("enable")
    add_common(enable)
    enable.set_defaults(func=command_enable)

    positive = subparsers.add_parser("verify-positive")
    add_common(positive)
    positive.add_argument("--device-probe", required=True, type=Path)
    positive.set_defaults(func=command_verify_positive)

    disable_dps = subparsers.add_parser("disable-dps")
    add_common(disable_dps)
    disable_dps.add_argument("--ets-decision", required=True, type=Path)
    disable_dps.set_defaults(func=command_disable_dps)

    dps_only = subparsers.add_parser("verify-dps-only")
    dps_only.add_argument("--device-probe", required=True, type=Path)
    dps_only.add_argument("--output-dir", required=True, type=Path)
    dps_only.set_defaults(func=command_verify_dps_only)

    disable_hub = subparsers.add_parser("disable-hub")
    add_common(disable_hub)
    disable_hub.add_argument("--ets-decision", required=True, type=Path)
    disable_hub.add_argument("--positive-result", required=True, type=Path)
    disable_hub.set_defaults(func=command_disable_hub)

    final = subparsers.add_parser("verify-final")
    add_common(final)
    final.add_argument("--ets-decision", required=True, type=Path)
    final.add_argument("--positive-result", required=True, type=Path)
    final.add_argument("--reconnect-probe", required=True, type=Path)
    final.add_argument("--reprovision-probe", required=True, type=Path)
    final.set_defaults(func=command_verify_final)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QualificationError as exc:
        print(f"FLEET-A5 qualification failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
