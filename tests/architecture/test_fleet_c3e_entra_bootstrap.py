from __future__ import annotations

import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "azure" / "ensure-fleet-entra-application.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "fleet-c3d-live-deploy.yml"
DOC = ROOT / "docs" / "fleet" / "ETS_FLEET_C3E_ENTRA_BOOTSTRAP.md"

ROLE_IDS = {
    "Fleet.Viewer": "19292461-7726-5197-acd4-6da5cf9d5440",
    "Fleet.Operator": "b1c406fc-6d94-5397-a37d-7b23192f052f",
    "Fleet.SecurityAdmin": "cd7b83d7-7fbe-5b30-811d-5b6b8fa79fb4",
}


def test_fleet_role_ids_are_deterministic_uuid5_values() -> None:
    for role, expected in ROLE_IDS.items():
        actual = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"https://lanternprotocol.net/ets/fleet/{role}",
        )
        assert str(actual) == expected


def test_delegated_bootstrap_uses_process_scoped_graph_and_explicit_apply() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "[switch]$Apply" in source
    assert "Application.Read.All" in source
    assert "Application.ReadWrite.All" in source
    assert "-ContextScope Process" in source
    assert "Connect-MgGraph" in source
    assert "Disconnect-MgGraph" in source
    assert "ExpectedVerifiedDomain = 'echomedia.ai'" in source
    assert "AzureADMyOrg" in source
    assert "enableIdTokenIssuance = $true" in source
    assert "enableAccessTokenIssuance = $false" in source
    assert "mutationRequired" in source
    assert "delegatedBootstrap = $true" in source
    assert "githubGraphWriteRequired = $false" in source


def test_delegated_bootstrap_has_exact_user_role_contract() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    for role, role_id in ROLE_IDS.items():
        assert role in source
        assert role_id in source
    assert "allowedMemberTypes = @('User')" in source
    assert "Refusing implicit role migration" in source


def test_delegated_bootstrap_rejects_reusable_and_delegated_credentials() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "passwordCredentials" in source
    assert "keyCredentials" in source
    assert "oauth2PermissionScopes" in source
    assert "preAuthorizedApplications" in source
    assert "knownClientApplications" in source
    assert "reusableCredentialRetained = $false" in source
    assert "clientSecret" not in source
    assert "privateKey" not in source


def test_c3d_deployment_identity_has_no_directory_admin_commands() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "entra_client_id" in source
    assert "github_graph_write_required=false" in source
    assert "az ad app" not in lowered
    assert "az ad sp" not in lowered
    assert "graph.microsoft.com" not in lowered
    assert "connect-mggraph" not in lowered
    assert "application.readwrite" not in lowered
    assert "provision_entra_application" not in source
    assert "entra_application_display_name" not in source


def test_c3e_runbook_keeps_public_hostname_out_of_scope() -> None:
    source = DOC.read_text(encoding="utf-8")
    assert "fleetClientId" in source
    assert "Application.ReadWrite.All" in source
    assert "GitHub Actions Azure workload identity does not receive that permission" in source
    assert "does not activate EasyAuth" in source
    assert "fleet.lanternprotocol.net" in source
