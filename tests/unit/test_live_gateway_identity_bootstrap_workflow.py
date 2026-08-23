from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "live-gateway-identity-bootstrap.yml"


def test_live_gateway_identity_bootstrap_is_manual_protected_and_least_privilege() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "workflow_dispatch:",
        "contents: read",
        "id-token: write",
        "issues: write",
        "environment: ets-azure-q1",
        'test "$GITHUB_REF" = "refs/heads/main"',
        'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"',
    ):
        assert required in text

    for prohibited in (
        "contents: write",
        "packages: write",
        "pull-requests: write",
        "AZURE_CLIENT_SECRET",
        "Application.ReadWrite.All",
        "AppRoleAssignment.ReadWrite.All",
    ):
        assert prohibited not in text


def test_live_gateway_identity_bootstrap_uses_bounded_non_customer_seeds() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "RESOURCE_GROUP: rg-ets-live-eastus",
        "ENVIRONMENT_NAME: ets-live",
        "CONNECTOR_INSTANCE_ID: m365-sharepoint-primary",
        "etsEnvironment=live",
        "etsOwner=lantern-protocol",
        "etsPurpose=hosted-gateway",
        "existing resource group is missing required ownership tag",
        "infra/azure/ets-gateway-identity.bicep",
    ):
        assert required in text

    assert "echomedia" not in text.lower()
    assert "sharepoint.com" not in text.lower()


def test_live_gateway_identity_bootstrap_precreates_three_distinct_runtime_identities() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        '"schema_version": "ets.live_gateway.identity_bootstrap.v2"',
        "directoryManagedIdentityName.value",
        "directoryManagedIdentityClientId.value",
        "purviewManagedIdentityName.value",
        "purviewManagedIdentityClientId.value",
        "separated Microsoft identity {key} values are not distinct",
        '"directory_identity_ready": True',
        '"purview_identity_ready": True',
        '"gateway_client_id_retained": False',
        '"gateway_principal_id_retained": False',
        '"directory_client_id_retained": False',
        '"purview_client_id_retained": False',
        '"reusable_credential_retained": False',
    ):
        assert required in text


def test_live_gateway_identity_bootstrap_keeps_release_claims_false() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        '"core_producer_role_assigned": False',
        '"directory_app_roles_assigned": False',
        '"purview_app_roles_assigned": False',
        '"core_scope_map_configured": False',
        '"azure_runtime_deployed": False',
        '"m365_source_to_proof_claimed": False',
        '"soak_clock_started": False',
        "Core \\`evidence_producer\\` role assigned: **false**",
        "72-hour soak clock started: **false**",
    ):
        assert required in text
