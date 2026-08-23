from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "azure" / "bootstrap-live-deployment-secrets.ps1"


def test_secret_bootstrap_requires_explicit_live_scope_and_sharepoint_drive() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "[string]$EtsTenantId",
        "[string]$EtsWorkspaceId",
        "[string]$SharePointDriveId",
        "[string]$ImageSourceSha = ''",
        "[string]$ContainerImage = ''",
        "[string]$Q0WorkflowRunId = ''",
        "[string]$Repository = 'ShannonBrayNC/ETS'",
        "[string]$EnvironmentName = 'ets-azure-q1'",
        "[string]$ResourceGroup = 'rg-ets-live-eastus'",
        "[string]$ManagedIdentityName = 'ets-o23bf2d6oq44s-gw-id'",
        "[string]$ExpectedVerifiedDomain = 'echomedia.ai'",
    ):
        assert required in text


def test_secret_bootstrap_composes_identity_apply_before_secret_write() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    orchestration = text.index("provision-live-core-gateway-identity.ps1")
    secret_values = text.index("$secretValues = [ordered]@{")
    secret_write = text.index("Set-ProtectedEnvironmentSecrets -Values $secretValues")
    assert orchestration < secret_values < secret_write

    for required in (
        "if ($Apply)",
        "$parameters.Apply = $true",
        "ready_for_protected_deployment",
        "identity_authorization_incomplete",
        "ready_to_write_protected_secrets",
        "protected_deployment_secrets_ready",
    ):
        assert required in text


def test_secret_bootstrap_writes_exact_protected_environment_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    expected_names = (
        "ETS_LIVE_CORE_SCOPE",
        "ETS_LIVE_AUTH_AUDIENCE",
        "ETS_LIVE_AUTH_ISSUER",
        "ETS_LIVE_AUTH_JWKS_URL",
        "ETS_LIVE_AUTH_TENANT_ID",
        "ETS_LIVE_AUTH_APP_SCOPE_MAP_JSON",
        "ETS_LIVE_TENANT_ID",
        "ETS_LIVE_WORKSPACE_ID",
        "ETS_LIVE_MICROSOFT_TENANT_ID",
        "ETS_LIVE_SHAREPOINT_DRIVE_ID",
    )
    for name in expected_names:
        assert name in text

    for required in (
        "gh secret set -f -",
        "--env $EnvironmentName",
        "--repo $Repository",
        "gh secret list",
        "--json name",
        "--jq '.[].name'",
        "Protected deployment environment is missing expected secret",
    ):
        assert required in text

    for prohibited in (
        "--body",
        "AZURE_CLIENT_SECRET",
        "Application.ReadWrite.All",
        "AppRoleAssignment.ReadWrite.All",
    ):
        assert prohibited not in text


def test_secret_bootstrap_fails_closed_on_identity_and_scope_mismatch() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "Identity auth tenant does not match the active Azure tenant.",
        "Identity orchestration returned an unexpected Gateway managed identity.",
        "Identity orchestration returned a different ETS tenant scope.",
        "Identity orchestration returned a different ETS workspace scope.",
        "Core managed-identity scope must equal <audience>/.default.",
        "Identity orchestration unexpectedly reported reusable credential retention.",
    ):
        assert required in text


def test_secret_bootstrap_dispatch_is_explicit_and_post_secret_write() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    secret_write = text.index("Set-ProtectedEnvironmentSecrets -Values $secretValues")
    dispatch = text.index("gh workflow run live-core-gateway-deployment.yml")
    assert secret_write < dispatch

    for required in (
        "[switch]$DispatchDeployment",
        "-DispatchDeployment requires -Apply.",
        "-DispatchDeployment requires a canonical -ImageSourceSha.",
        "-DispatchDeployment requires the exact private-ACR -ContainerImage digest.",
        "-DispatchDeployment requires a canonical -Q0WorkflowRunId.",
        "--ref main",
        '-f "image_source_sha=$ImageSourceSha"',
        '-f "container_image=$ContainerImage"',
        '-f "q0_workflow_run_id=$Q0WorkflowRunId"',
        "deploymentDispatched = $DeploymentDispatched",
    ):
        assert required in text


def test_secret_bootstrap_retains_only_bounded_public_status() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for required in (
        "reusableCredentialRetained = $false",
        "customerIdentifiersRetained = $false",
        "publicEvidenceSafe = $true",
    ):
        assert required in text

    assert "gatewayManagedIdentityClientId" not in text
    assert "authAppScopeMapJson =" not in text


def test_secret_bootstrap_parses_with_powershell_when_available() -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        return

    command = (
        "$errors=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        f"'{SCRIPT}', [ref]$null, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | Out-String; exit 1 }"
    )
    subprocess.run([pwsh, "-NoProfile", "-Command", command], check=True)
