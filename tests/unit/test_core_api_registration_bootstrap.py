from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "azure" / "ensure-core-api-application.ps1"
RUNBOOK = ROOT / "docs" / "gateway" / "CORE_API_REGISTRATION_BOOTSTRAP_V1.md"


def test_core_api_bootstrap_is_dry_run_first_and_tenant_bound() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "[switch]$Apply",
        "DisplayName = 'ETS Core Live API'",
        "ExpectedVerifiedDomain = 'echomedia.ai'",
        "Microsoft Graph tenant does not match the active Azure subscription tenant.",
        "Refusing to provision the ETS Core API application.",
        "Application.Read.All",
        "Application.ReadWrite.All",
        "mutationRequired = $true",
        "applyRequested = $false",
        "reusableCredentialRetained = $false",
    ):
        assert required in text

    assert "AZURE_CLIENT_SECRET" not in text
    assert "client_secret" not in text.lower()


def test_core_api_bootstrap_creates_a_single_tenant_credential_free_resource_api() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "signInAudience = 'AzureADMyOrg'",
        "ets:component=core",
        "ets:environment=live",
        "ets:owner=lantern-protocol",
        "Core application must not retain password credentials.",
        "Core application must not retain application key credentials.",
        "Core application must not expose delegated OAuth permission scopes.",
        "Core application must not contain pre-authorized delegated clients.",
        "Core application must not contain known delegated client applications.",
        '"api://$($application.appId)"',
        "requestedAccessTokenVersion = 2",
        "Refusing to adopt an unowned application implicitly.",
        "Refusing implicit migration.",
    ):
        assert required in text


def test_core_api_bootstrap_creates_exactly_one_service_principal() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "https://graph.microsoft.com/v1.0/servicePrincipals",
        "Multiple service principals resolve to the ETS Core application ID.",
        "Core service principal creation did not converge to exactly one principal.",
        "servicePrincipalType -ne 'Application'",
        "Core service principal is disabled.",
        "servicePrincipalReady = $true",
        "servicePrincipalCreated = $servicePrincipalCreated",
    ):
        assert required in text


def test_core_api_bootstrap_derives_runtime_auth_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        'coreScope = "$identifierUri/.default"',
        "authAudience = $identifierUri",
        'authIssuer = "https://login.microsoftonline.com/$($context.TenantId)/v2.0"',
        "discovery/v2.0/keys",
        "requestedAccessTokenVersion = 2",
        "coreApplicationId = [string]$application.appId",
        "coreServicePrincipalObjectId = [string]$servicePrincipal.id",
    ):
        assert required in text


def test_core_api_bootstrap_powershell_parses_when_pwsh_is_available() -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("pwsh is not available on this runner")

    path = str(SCRIPT).replace("'", "''")
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


def test_core_api_runbook_keeps_registration_role_assignment_and_deployment_separate() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for required in (
        "ensure-core-api-application.ps1",
        "api://<core-app-id>/.default",
        "ensure-core-evidence-producer-app-role.ps1",
        "provision-gateway-core-evidence-producer.ps1",
        "ETS_AUTH_APP_SCOPE_MAP_JSON",
        "Do not put the Core application ID or Gateway client ID in public release evidence.",
        "does not deploy Core or Gateway",
        "The 72-hour soak clock remains stopped",
    ):
        assert required in text
