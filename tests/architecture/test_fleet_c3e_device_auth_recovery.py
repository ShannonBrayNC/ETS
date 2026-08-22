from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "scripts" / "azure" / "ensure-fleet-entra-application-device-auth.ps1"
GOVERNED = ROOT / "scripts" / "azure" / "ensure-fleet-entra-application.ps1"
DOC = ROOT / "docs" / "fleet" / "ETS_FLEET_C3E_DEVICE_AUTH_RECOVERY.md"


def test_device_auth_wrapper_is_explicit_and_process_scoped() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert "[switch]$Apply" in source
    assert "UseDeviceAuthentication = $true" in source
    assert "[ValidateSet('Process')]" in source
    assert "Microsoft.Graph.Authentication\\Connect-MgGraph" in source
    assert "& $delegateScript -Apply:$Apply" in source


def test_device_auth_wrapper_delegates_governance_to_c3e_script() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    governed = GOVERNED.read_text(encoding="utf-8")
    assert "ensure-fleet-entra-application.ps1" in source
    assert "Application.Read.All" not in source
    assert "Application.ReadWrite.All" not in source
    assert "Application.Read.All" in governed
    assert "Application.ReadWrite.All" in governed
    assert "ExpectedVerifiedDomain = 'echomedia.ai'" in governed


def test_device_auth_recovery_adds_no_reusable_credential_path() -> None:
    source = WRAPPER.read_text(encoding="utf-8").lower()
    forbidden = (
        "clientsecret",
        "passwordcredential",
        "keycredential",
        "certificate",
        "accesstoken",
        "refreshtoken",
        "application.readwrite.all",
    )
    for token in forbidden:
        assert token not in source


def test_device_auth_recovery_is_documented_as_operator_selected() -> None:
    source = DOC.read_text(encoding="utf-8")
    assert "-Apply" in source
    assert "device-code" in source.lower()
    assert "does not automatically fall back" in source
    assert "GitHub Actions Azure workload identity" in source
    assert "does not receive Microsoft Graph write permission" in source
