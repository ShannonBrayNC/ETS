from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path("scripts/fleet/qualify_physical_tpm_dps_a4.py")
SPEC = importlib.util.spec_from_file_location("fleet_a4", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _bundle(tmp_path: Path, nonce: str) -> Path:
    bundle = tmp_path
    (bundle / "provider").mkdir()
    (bundle / "quote").mkdir()
    ek = b"ets-test-ek-public"
    alias = MODULE.sha256_bytes(ek)
    (bundle / "provider/endorsement-key.public.tpm2b").write_bytes(ek)
    import base64

    (bundle / "provider/endorsement-key.public.b64").write_text(
        base64.b64encode(ek).decode("ascii") + "\n", encoding="ascii"
    )
    (bundle / "provider/provider-registration-id.txt").write_text(alias + "\n")
    (bundle / "attestation-key.public.pem").write_text("AK PUBLIC\n")
    (bundle / "quote/qualification-nonce.hex").write_text(nonce + "\n")
    (bundle / "quote/pcr-selection.txt").write_text("sha256:0,2,4,7\n")
    for name, content in (("quote.msg", b"m"), ("quote.sig", b"s"), ("quote.pcrs", b"p")):
        (bundle / "quote" / name).write_bytes(content)
    nonce_hash = MODULE.sha256_bytes(nonce.encode("ascii"))
    (bundle / "quote/quote-verification.txt").write_text(
        f"nonce_sha256={nonce_hash}\nresult=verified\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "ets.fleet.physical-tpm-a4.device-proof.v1",
        "provider_registration_id": alias,
        "endorsement_key_fingerprint_sha256": alias,
        "challenge_sha256": nonce_hash,
        "fresh_tpm_quote_verified": True,
        "tpm_possession_proven": True,
        "hardware_attested": False,
        "shared_or_sas_credential_used": False,
    }
    (bundle / "a4-public-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    files = [
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
    ]
    (bundle / "a4-private-bundle.sha256").write_text(
        "".join(f"{MODULE.sha256_file(bundle / rel)}  {rel}\n" for rel in files),
        encoding="utf-8",
    )
    return bundle


def test_verify_bundle_accepts_fresh_nonce_bound_tpm_proof(tmp_path: Path) -> None:
    nonce = "a" * 64
    manifest = MODULE.verify_bundle(_bundle(tmp_path, nonce), nonce)
    assert manifest["fresh_tpm_quote_verified"] is True


def test_verify_bundle_rejects_operator_nonce_mismatch(tmp_path: Path) -> None:
    nonce = "a" * 64
    with pytest.raises(MODULE.QualificationError):
        MODULE.verify_bundle(_bundle(tmp_path, nonce), "b" * 64)


def test_verify_bundle_rejects_alias_not_derived_from_ek(tmp_path: Path) -> None:
    nonce = "a" * 64
    bundle = _bundle(tmp_path, nonce)
    (bundle / "provider/provider-registration-id.txt").write_text("b" * 64 + "\n")
    with pytest.raises(MODULE.QualificationError):
        MODULE.verify_bundle(bundle, nonce)


def test_validate_enrollment_requires_disabled_tpm_and_canonical_device() -> None:
    payload = {
        "registrationId": "a" * 64,
        "deviceId": "ets-edge:1234567890abcdef12345678",
        "provisioningStatus": "disabled",
        "attestation": {"type": "tpm"},
    }
    MODULE.validate_enrollment(
        payload,
        registration_id="a" * 64,
        device_id="ets-edge:1234567890abcdef12345678",
    )
    payload["provisioningStatus"] = "enabled"
    with pytest.raises(MODULE.QualificationError):
        MODULE.validate_enrollment(
            payload,
            registration_id="a" * 64,
            device_id="ets-edge:1234567890abcdef12345678",
        )
