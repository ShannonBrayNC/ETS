from pathlib import Path

DEVICE = Path("scripts/fleet/prepare_physical_tpm_a4.sh")
OPERATOR = Path("scripts/fleet/qualify_physical_tpm_dps_a4.py")
DOC = Path("docs/fleet/ETS_FLEET_PHYSICAL_TPM_A4.md")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_device_side_is_non_destructive_and_has_no_azure_credentials() -> None:
    text = read(DEVICE)
    assert "collect_dps_tpm_identity.sh" in text
    assert "request_tpm_quote.sh" in text
    assert "verify_tpm_quote.sh" in text
    assert "NONCE_HEX must be exactly 32 bytes" in text
    for forbidden in (
        "az login",
        "az iot dps",
        "connection string",
        "tpm2_clear",
        "tpm2_createek",
        "tpm2_evictcontrol",
        "tpm2_nvdefine",
        "tpm2_pcrallocate",
    ):
        assert forbidden not in text


def test_operator_uses_entra_login_and_disabled_tpm_only() -> None:
    text = read(OPERATOR)
    assert '"--auth-type",\n                "login"' in text
    assert '"--attestation-type",\n                "tpm"' in text
    assert '"--provisioning-status",\n                "disabled"' in text
    assert "REQUIRED_AZURE_IOT_EXTENSION_VERSION = \"0.30.0\"" in text
    for forbidden in (
        "--auth-type key",
        "connection-string",
        "--primary-key",
        "--secondary-key",
        "symmetricKey",
    ):
        assert forbidden not in text


def test_operator_fails_closed_on_existing_enrollment_and_defaults_cleanup() -> None:
    text = read(OPERATOR)
    assert "qualification enrollment already exists; refusing to overwrite" in text
    assert "if created and not args.retain_disabled" in text
    assert '"enrollment",\n                    "delete"' in text
    assert "qualification enrollment cleanup failed" in text


def test_a4_claim_boundary_does_not_assert_full_hardware_or_device_provisioning() -> None:
    device = read(DEVICE)
    operator = read(OPERATOR)
    assert '"hardware_attested": false' in device
    assert '"device_side_provisioning_qualified": false' in device
    assert '"hardware_attested": False' in operator
    assert '"device_side_provisioning_qualified": False' in operator


def test_document_preserves_a5_separation() -> None:
    text = read(DOC)
    assert "does not prove device-side DPS provisioning" in text
    assert "FLEET-A5" in text
    assert "disabled" in text
    assert "Microsoft Entra" in text
