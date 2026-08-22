from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GATEWAY_BICEP = ROOT / "infra" / "azure" / "ets-gateway.bicep"
IDENTITY_BICEP = ROOT / "infra" / "azure" / "ets-gateway-identity.bicep"
BOOTSTRAP = ROOT / "scripts" / "azure" / "provision-microsoft-p0-connector-app-roles.ps1"
RUNBOOK = ROOT / "docs" / "connectors" / "MICROSOFT_P0_IDENTITY_BOOTSTRAP_V1.md"

GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"
MANAGEMENT_APP_ID = "c5393580-f805-4401-95e8-94b7a6ef2fc2"


def test_prebootstrap_creates_three_deterministically_named_identities() -> None:
    text = IDENTITY_BICEP.read_text(encoding="utf-8")

    for required in (
        "take('ets-${resourceToken}-gw-id', 128)",
        "take('ets-${resourceToken}-gw-dir-id', 128)",
        "take('ets-${resourceToken}-gw-pur-id', 128)",
        "resource directoryIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31'",
        "resource purviewIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31'",
        "output directoryManagedIdentityClientId",
        "output directoryManagedIdentityPrincipalId",
        "output purviewManagedIdentityClientId",
        "output purviewManagedIdentityPrincipalId",
    ):
        assert required in text


def test_gateway_attaches_separated_runtime_identities_with_main_lifecycle() -> None:
    text = GATEWAY_BICEP.read_text(encoding="utf-8")

    for required in (
        "'${directoryIdentity.id}': {}",
        "'${purviewIdentity.id}': {}",
        "identity: directoryIdentity.id\n          lifecycle: 'Main'",
        "identity: purviewIdentity.id\n          lifecycle: 'Main'",
        "name: 'ETS_GATEWAY_DIRECTORY_MANAGED_IDENTITY_CLIENT_ID'",
        "value: directoryIdentity.properties.clientId",
        "name: 'ETS_GATEWAY_PURVIEW_MANAGED_IDENTITY_CLIENT_ID'",
        "value: purviewIdentity.properties.clientId",
        "identity: registryPullIdentity.id\n          lifecycle: 'None'",
    ):
        assert required in text


def test_identity_templates_output_metadata_without_credential_material() -> None:
    outputs: list[str] = []
    for path in (IDENTITY_BICEP, GATEWAY_BICEP):
        outputs.extend(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("output ")
        )

    joined = "\n".join(outputs).lower()
    for required in (
        "directorymanagedidentityclientid",
        "directorymanagedidentityprincipalid",
        "purviewmanagedidentityclientid",
        "purviewmanagedidentityprincipalid",
    ):
        assert required in joined
    for prohibited in ("secret", "password", "token", "credential"):
        assert prohibited not in joined


def test_bootstrap_resolves_exact_resource_apps_and_roles_dynamically() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")

    for required in (
        GRAPH_APP_ID,
        MANAGEMENT_APP_ID,
        "User.Read.All",
        "Group.Read.All",
        "ActivityFeed.Read",
        "Get-RequiredAppRole",
        "@($_.allowedMemberTypes) -contains 'Application'",
        "does not expose exactly one ",
        "enabled application role",
        "immutable role id",
    ):
        assert required in text

    for hardcoded_role_id in (
        "df021288-bdef-4463-88db-98f22de89214",
        "5b567255-7703-4780-807c-7be8301ae99b",
    ):
        assert hardcoded_role_id not in text


def test_bootstrap_is_preview_first_and_uses_apply_only_write_scope() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")

    for required in (
        "[switch]$Apply",
        "[string]$SharePointManagedIdentityName",
        "$requiredScopes.Add('Application.Read.All')",
        "if ($Apply) {\n    $requiredScopes.Add('AppRoleAssignment.ReadWrite.All')",
        "-ContextScope Process",
        "mutationRequired = $true",
        "applyRequested = $false",
        "appRoleAssignedTo",
        "Wait-ForExactAssignmentConvergence",
        "converge within the bounded retry limit.",
        "reusableCredentialRetained = $false",
        "sourcePayloadRetained = $false",
    ):
        assert required in text

    for prohibited in (
        "Directory.Read.All",
        "Application.ReadWrite.All",
        "AZURE_CLIENT_SECRET",
        "client_secret",
    ):
        assert prohibited not in text


def test_bootstrap_fails_closed_on_identity_or_permission_drift() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")

    for required in (
        "ExpectedVerifiedDomain = 'echomedia.ai'",
        "Microsoft Graph tenant does not match the active Azure subscription tenant.",
        "service-principal object id differs from its Azure",
        "servicePrincipalType ManagedIdentity",
        "SharePoint, directory, and Purview must use distinct user-assigned identities.",
        "sharePointPermissionsChanged = $false",
        "unexpected application permission",
        "Refusing implicit permission broadening or normalization.",
        "duplicate",
        "Microsoft Graph collection exceeded the bounded pagination limit.",
        "for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++)",
        "Start-Sleep -Seconds $DelaySeconds",
    ):
        assert required in text


def test_bootstrap_powershell_parses_when_pwsh_is_available() -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("PowerShell is not available in this environment")

    script_path = str(BOOTSTRAP).replace("'", "''")
    command = (
        "$tokens = $null; $errors = $null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{script_path}', "
        "[ref]$tokens, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { "
        "$errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_runbook_preserves_preview_evidence_and_live_qualification_boundaries() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for required in (
        "preview-first",
        "Application.Read.All",
        "AppRoleAssignment.ReadWrite.All",
        "organization-get?view=graph-rest-1.0",
        "serviceprincipal-list-approleassignments?view=graph-rest-1.0",
        "-SharePointManagedIdentityName",
        "does not request `Directory.Read.All`",
        "ActivityFeed.ReadDlp",
        "ServiceHealth.Read",
        "any application permission outside its exact allowlist",
        "Raw operator output can contain managed-identity identifiers",
        "does not prove token acquisition",
        "does not start the 72-hour soak",
        "next #543 slice",
    ):
        assert required in text
