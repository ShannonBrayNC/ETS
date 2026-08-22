from __future__ import annotations

from pathlib import Path

OPERATOR = Path("scripts/fleet/qualify_physical_tpm_a5.py")
PREPARE = Path("scripts/fleet/prepare_physical_tpm_a5_device.sh")
PROBE = Path("scripts/fleet/run_physical_tpm_a5_probe.sh")
DOC = Path("docs/fleet/ETS_FLEET_PHYSICAL_TPM_A5.md")


def test_a5_operator_forbids_shared_key_and_connection_string_paths() -> None:
    text = OPERATOR.read_text(encoding="utf-8")
    for forbidden in (
        "--auth-type key",
        "connection-string",
        "--primary-key",
        "--secondary-key",
        "SharedAccessKey",
        "symmetric_key",
        "device-identity connection-string",
    ):
        assert forbidden not in text
    assert '"--auth-type", "login"' in text


def test_a5_device_profile_is_tpm_only_and_uses_supported_reference_client() -> None:
    prepare = PREPARE.read_text(encoding="utf-8")
    probe = PROBE.read_text(encoding="utf-8")
    assert 'method = "tpm"' in prepare
    assert "azure-iot-edge-1.6-lts" in prepare
    assert "IoT Edge 1.6 LTS" in probe
    assert "AlwaysOnStartup" in prepare
    assert "Dynamic" in prepare
    for forbidden in ("symmetric_key", "connection_string", "SharedAccessKey"):
        assert forbidden not in prepare
        assert forbidden not in probe


def test_a5_requires_dual_layer_provider_revocation() -> None:
    text = OPERATOR.read_text(encoding="utf-8")
    assert "disable-dps" in text
    assert "verify-dps-only" in text
    assert "disable-hub" in text
    assert "hub-disabled-reconnect" in text
    assert "dps-disabled-reprovision" in text
    assert "dual_layer_provider_revocation_qualified" in text


def test_a5_ets_denial_precedes_provider_revocation() -> None:
    text = OPERATOR.read_text(encoding="utf-8")
    assert "validate_ets_denial" in text
    assert 'DENIAL_REASONS = {"quarantined", "revoked", "decommissioned"}' in text
    assert "provider revocation requires an ETS denied decision" in text


def test_a5_does_not_treat_iot_hub_connection_state_as_authoritative() -> None:
    operator = OPERATOR.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    assert "connectionState" not in operator
    assert "connectionState" in doc
    assert "not used as qualification truth" in doc


def test_a5_keeps_raw_device_logs_local() -> None:
    probe = PROBE.read_text(encoding="utf-8")
    assert 'mkdir -p "$output_dir/private"' in probe
    assert '"private_logs_retained_locally": True' in probe
    assert "identity_stdout_sha256" in probe
    assert "identity_stderr_sha256" in probe
