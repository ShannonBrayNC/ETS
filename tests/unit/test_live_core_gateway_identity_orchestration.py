from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "azure" / "provision-live-core-gateway-identity.ps1"


def test_live_identity_orchestration_uses_confirmed_gateway_and_explicit_ets_scope() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "[Parameter(Mandatory = $true)]\n    [ValidateLength(1, 128)]\n    [string]$EtsTenantId",
        "[Parameter(Mandatory = $true)]\n    [ValidateLength(1, 128)]\n    [string]$EtsWorkspaceId",
        "[string]$ResourceGroup = 'rg-ets-live-eastus'",
        "[string]$ManagedIdentityName = 'ets-o23bf2d6oq44s-gw-id'",
        "[string]$CoreDisplayName = 'ETS Core Live API'",
        "[string]$ExpectedVerifiedDomain = 'echomedia.ai'",
    ):
        assert required in text


def test_live_identity_orchestration_composes_governed_child_steps() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    registration = text.index("ensure-core-api-application.ps1")
    role = text.index("ensure-core-evidence-producer-app-role.ps1")
    assignment = text.index("provision-gateway-core-evidence-producer.ps1")
    assert registration < role < assignment

    for required in (
        "if ($Apply)",
        "$appParameters.Apply = $true",
        "$roleParameters.Apply = $true",
        "$assignmentParameters.Apply = $true",
        "core_api_registration",
        "core_evidence_producer_role",
        "gateway_evidence_producer_assignment",
        "ready_for_protected_deployment",
    ):
        assert required in text


def test_live_identity_orchestration_builds_exact_server_owned_scope_map() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "$gatewayClientId = [string]$assignment.managedIdentityClientId",
        "$scopeMap[$gatewayClientId] = [ordered]@{",
        "tenant_id = $etsTenant",
        "workspace_id = $etsWorkspace",
        "authAppScopeMapJson = $scopeMapJson",
        "coreScope = [string]$app.coreScope",
        "authAudience = [string]$app.authAudience",
        "authIssuer = [string]$app.authIssuer",
        "authJwksUrl = [string]$app.authJwksUrl",
        "authTenantId = [string]$app.tenantId",
    ):
        assert required in text


def test_live_identity_orchestration_retains_no_reusable_credentials() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "reusableCredentialRetained = $false" in text
    assert "publicEvidenceSafe = $false" in text
    for prohibited in (
        "AZURE_CLIENT_SECRET",
        "clientSecret",
        "passwordCredential",
        "secretText",
    ):
        assert prohibited not in text


def test_live_identity_orchestration_parses_when_pwsh_is_available() -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        return

    command = (
        "$errors = $null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        f"'{SCRIPT.as_posix()}', [ref]$null, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
    )
    completed = subprocess.run(
        [pwsh, "-NoLogo", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
