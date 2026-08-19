from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "infra" / "azure" / "ets-live-auth-qualification-client.bicep"
CONVERGE = ROOT / "scripts" / "azure" / "converge-live-core-v2-audience.ps1"


def test_live_authorization_uses_v2_api_client_id_as_audience() -> None:
    text = CLIENT.read_text(encoding="utf-8")

    for required in (
        'scope_prefix = "api://"',
        'scope_suffix = "/.default"',
        "expected_audience = scope[len(scope_prefix) : -len(scope_suffix)]",
        "audience.casefold() != expected_audience.casefold()",
        "managed identity token audience did not match ETS Core",
    ):
        assert required in text

    assert 'expected_audience = scope[:-len("/.default")]' not in text


def test_live_audience_convergence_is_dry_run_first_and_narrow() -> None:
    text = CONVERGE.read_text(encoding="utf-8")

    for required in (
        "[switch]$Apply",
        "ready_to_converge_v2_audience",
        "live_core_v2_audience_ready",
        "ETS_LIVE_AUTH_AUDIENCE",
        '"ETS_AUTH_AUDIENCE=$coreApplicationId"',
        "audienceShape = 'application_id_guid'",
        "scopeShape = 'api://<application-id>/.default'",
        "reusableCredentialRetained = $false",
        "customerIdentifiersRetained = $false",
    ):
        assert required in text

    assert "az containerapp update" in text
    assert "gh secret set ETS_LIVE_AUTH_AUDIENCE" in text
    assert "AZURE_CLIENT_SECRET" not in text
    assert "client_secret" not in text.lower()


def test_live_audience_convergence_powershell_parses_when_pwsh_is_available() -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("pwsh is not available on this runner")

    path = str(CONVERGE).replace("'", "''")
    command = (
        "$errors=$null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{path}', "
        "[ref]$null, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
    )
    subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
    )
