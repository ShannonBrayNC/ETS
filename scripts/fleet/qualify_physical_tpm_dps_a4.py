#!/usr/bin/env python3
"""Qualify a physical TPM proof against a disabled Azure DPS enrollment."""

from __future__ import annotations

import argparse
import base64
import hashlib
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


class QualificationError(RuntimeError):
    """Raised when the A4 qualification must fail closed."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, check=False, text=True, capture_output=True)
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise QualificationError(f"command failed ({command[0]}): {stderr}")
    return result


def parse_checksum_file(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        relative = relative.lstrip("*")
        if not HEX64_RE.fullmatch(digest):
            raise QualificationError(f"invalid checksum in {path}: {digest}")
        checksums[relative] = digest
    return checksums


def verify_bundle(bundle: Path, nonce_hex: str) -> dict[str, Any]:
    if not HEX64_RE.fullmatch(nonce_hex):
        raise QualificationError("nonce must be 32 bytes encoded as 64 lowercase hex characters")

    required = (
        "provider/endorsement-key.public.tpm2b",
        "provider/endorsement-key.public.b64",
        "provider/provider-registration-id.txt",
        "attestation-key.public.pem",
        "quote/qualification-nonce.hex",
        "quote/pcr-selection.txt",
        "quote/quote.msg",
        "quote/quote.sig",
        "quote/quote.pcrs",
        "quote/quote-verification.txt",
        "a4-public-manifest.json",
        "a4-private-bundle.sha256",
    )
    for relative in required:
        if not (bundle / relative).is_file():
            raise QualificationError(f"missing A4 bundle artifact: {relative}")

    checksums = parse_checksum_file(bundle / "a4-private-bundle.sha256")
    for relative, expected in checksums.items():
        actual = sha256_file(bundle / relative)
        if actual != expected:
            raise QualificationError(f"bundle checksum mismatch: {relative}")

    manifest = json.loads((bundle / "a4-public-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "ets.fleet.physical-tpm-a4.device-proof.v1":
        raise QualificationError("unexpected A4 device-proof schema")
    if manifest.get("fresh_tpm_quote_verified") is not True:
        raise QualificationError("fresh TPM quote was not verified")
    if manifest.get("tpm_possession_proven") is not True:
        raise QualificationError("TPM possession was not proven")
    if manifest.get("hardware_attested") is not False:
        raise QualificationError("A4 must not claim broad hardware attestation")
    if manifest.get("shared_or_sas_credential_used") is not False:
        raise QualificationError("shared/SAS credentials are forbidden")

    recorded_nonce = (bundle / "quote/qualification-nonce.hex").read_text(encoding="utf-8").strip()
    if recorded_nonce.lower() != nonce_hex:
        raise QualificationError("operator nonce does not match the TPM quote request")
    expected_nonce_hash = sha256_bytes(nonce_hex.encode("ascii"))
    if manifest.get("challenge_sha256") != expected_nonce_hash:
        raise QualificationError("challenge hash does not match operator nonce")

    verification = (bundle / "quote/quote-verification.txt").read_text(encoding="utf-8")
    if "result=verified" not in verification.splitlines():
        raise QualificationError("quote verification result is not verified")
    if f"nonce_sha256={expected_nonce_hash}" not in verification.splitlines():
        raise QualificationError("quote verification is not bound to the operator nonce")

    ek_bytes = (bundle / "provider/endorsement-key.public.tpm2b").read_bytes()
    ek_sha256 = sha256_bytes(ek_bytes)
    provider_registration_id = (
        bundle / "provider/provider-registration-id.txt"
    ).read_text(encoding="utf-8").strip()
    if provider_registration_id != ek_sha256:
        raise QualificationError("DPS provider alias does not equal SHA-256(EK public bytes)")
    if manifest.get("provider_registration_id") != provider_registration_id:
        raise QualificationError("manifest provider alias mismatch")
    if manifest.get("endorsement_key_fingerprint_sha256") != ek_sha256:
        raise QualificationError("manifest EK fingerprint mismatch")

    encoded = (bundle / "provider/endorsement-key.public.b64").read_text(encoding="ascii").strip()
    if base64.b64decode(encoded, validate=True) != ek_bytes:
        raise QualificationError("Base64 EK material does not decode to the collected EK bytes")

    return manifest


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


def validate_enrollment(payload: dict[str, Any], *, registration_id: str, device_id: str) -> None:
    if payload.get("registrationId") != registration_id:
        raise QualificationError("DPS registration ID mismatch")
    if payload.get("deviceId") != device_id:
        raise QualificationError("DPS device ID mismatch")
    if str(payload.get("provisioningStatus", "")).lower() != "disabled":
        raise QualificationError("A4 enrollment must remain disabled")
    attestation = payload.get("attestation")
    if not isinstance(attestation, dict) or str(attestation.get("type", "")).lower() != "tpm":
        raise QualificationError("DPS enrollment attestation type is not TPM")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--nonce-hex", required=True)
    parser.add_argument("--dps-name", required=True)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("fleet-a4-evidence"))
    parser.add_argument(
        "--retain-disabled",
        action="store_true",
        help="retain the disabled enrollment for the explicit FLEET-A5 handoff",
    )
    args = parser.parse_args()

    nonce_hex = args.nonce_hex.lower()
    if not DEVICE_ID_RE.fullmatch(args.device_id):
        raise QualificationError("canonical ETS device ID has an invalid shape")

    manifest = verify_bundle(args.bundle.resolve(), nonce_hex)
    extension_version = verify_azure_tools()
    registration_id = str(manifest["provider_registration_id"])
    ek_base64 = (
        args.bundle.resolve() / "provider/endorsement-key.public.b64"
    ).read_text(encoding="ascii").strip()

    dps_id = run(
        [
            "az",
            "iot",
            "dps",
            "show",
            "--name",
            args.dps_name,
            "--resource-group",
            args.resource_group,
            "--query",
            "id",
            "-o",
            "tsv",
        ]
    ).stdout.strip()
    expected_fragment = (
        f"/resourceGroups/{args.resource_group}/providers/"
        f"Microsoft.Devices/ProvisioningServices/{args.dps_name}"
    )
    if expected_fragment.lower() not in dps_id.lower():
        raise QualificationError("resolved DPS resource does not match the requested target")

    show_command = [
        "az",
        "iot",
        "dps",
        "enrollment",
        "show",
        "--dps-name",
        args.dps_name,
        "--resource-group",
        args.resource_group,
        "--enrollment-id",
        registration_id,
        "--auth-type",
        "login",
    ]
    if run([*show_command, "--output", "none"], check=False).returncode == 0:
        raise QualificationError("qualification enrollment already exists; refusing to overwrite")

    created = False
    cleanup_succeeded = False
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        create_payload = load_json_output(
            [
                "az",
                "iot",
                "dps",
                "enrollment",
                "create",
                "--dps-name",
                args.dps_name,
                "--resource-group",
                args.resource_group,
                "--enrollment-id",
                registration_id,
                "--attestation-type",
                "tpm",
                "--endorsement-key",
                ek_base64,
                "--device-id",
                args.device_id,
                "--provisioning-status",
                "disabled",
                "--auth-type",
                "login",
            ]
        )
        created = True
        validate_enrollment(
            create_payload,
            registration_id=registration_id,
            device_id=args.device_id,
        )
        round_trip = load_json_output(show_command)
        validate_enrollment(round_trip, registration_id=registration_id, device_id=args.device_id)

        evidence = {
            "schema_version": "ets.fleet.physical-tpm-a4.azure-result.v1",
            "provider_registration_id": registration_id,
            "canonical_ets_device_id": args.device_id,
            "dps_name": args.dps_name,
            "resource_group": args.resource_group,
            "dps_resource_id_sha256": sha256_bytes(dps_id.encode("utf-8")),
            "azure_iot_extension_version": extension_version,
            "auth_type": "login",
            "attestation_type": "tpm",
            "provisioning_status": "disabled",
            "fresh_tpm_quote_verified": True,
            "tpm_possession_proven": True,
            "azure_control_plane_qualified": True,
            "device_side_provisioning_qualified": False,
            "hardware_attested": False,
            "shared_or_sas_credential_used": False,
            "raw_endorsement_key_retained": False,
            "azure_token_retained": False,
            "retain_disabled_for_a5": bool(args.retain_disabled),
            "qualified_at_utc": datetime.now(UTC).isoformat(),
        }
        (args.output_dir / "a4-azure-result.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    finally:
        if created and not args.retain_disabled:
            delete = run(
                [
                    "az",
                    "iot",
                    "dps",
                    "enrollment",
                    "delete",
                    "--dps-name",
                    args.dps_name,
                    "--resource-group",
                    args.resource_group,
                    "--enrollment-id",
                    registration_id,
                    "--auth-type",
                    "login",
                    "--output",
                    "none",
                ],
                check=False,
            )
            cleanup_succeeded = delete.returncode == 0
            if not cleanup_succeeded:
                raise QualificationError("qualification enrollment cleanup failed")

    print(f"A4 qualified provider alias: {registration_id}")
    print(f"Canonical ETS device ID: {args.device_id}")
    if args.retain_disabled:
        print("STOP BOUNDARY: enrollment retained disabled for explicit FLEET-A5 handoff.")
    else:
        print(f"Cleanup succeeded: {cleanup_succeeded}")
        print("STOP BOUNDARY: enrollment deleted; no device-side provisioning was attempted.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QualificationError as exc:
        print(f"FLEET-A4 qualification failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
