import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = (
    ROOT / "scripts" / "m365" / "preview-ets-sharepoint-cross-tenant-bootstrap.ps1"
).read_text(encoding="utf-8")


def test_preview_contains_no_graph_mutation_methods():
    mutating_methods = re.findall(
        r"-Method\s+(POST|PATCH|PUT|DELETE)\b",
        PREVIEW,
        flags=re.IGNORECASE,
    )
    assert mutating_methods == []
    assert "Invoke-MgGraphRequest -Method GET" in PREVIEW
    assert "mutationPerformed = $false" in PREVIEW


def test_preview_contains_no_azure_or_graph_provisioning_commands():
    forbidden_fragments = (
        "az ad app create",
        "az ad sp create",
        "az ad app federated-credential create",
        "az identity create",
        "az role assignment create",
        "New-Mg",
        "Update-Mg",
        "Remove-Mg",
        "-Apply",
    )
    for fragment in forbidden_fragments:
        assert fragment not in PREVIEW


def test_preview_is_bound_to_known_destination_identity_and_site_defaults():
    assert "rg-ets-prod-eastus" in PREVIEW
    assert "ets-oif5r5ydprrou-gw-id" in PREVIEW
    assert "echomediaai.sharepoint.com" in PREVIEW
    assert "'/sites/ETS'" in PREVIEW
    assert "ExpectedSiteRole = 'read'" in PREVIEW


def test_preview_requires_exact_cross_tenant_federation_contract():
    assert "AzureADMultipleOrgs" in PREVIEW
    assert "federatedIdentityCredentials" in PREVIEW
    assert "https://login.microsoftonline.com/$DestinationAzureTenantId/v2.0" in PREVIEW
    assert "subject -ceq $identity.principalId" in PREVIEW
    assert "api://AzureADTokenExchange" in PREVIEW
    assert "appOwnerOrganizationId -ne $DestinationAzureTenantId" in PREVIEW


def test_preview_requires_minimal_resource_permissions():
    assert "Sites.Selected" in PREVIEW
    assert "unexpected Graph permission set" in PREVIEW
    assert "sharepoint_site_read_grant" in PREVIEW
    assert "ready_for_read_only_qualification" in PREVIEW


def test_preview_reports_first_missing_stage_without_applying_it():
    expected_stages = (
        "destination_multitenant_application",
        "destination_multitenant_application_configuration",
        "destination_federated_identity_credential",
        "resource_enterprise_application",
        "resource_sites_selected_assignment",
        "sharepoint_site_read_grant",
    )
    for stage in expected_stages:
        assert stage in PREVIEW
    assert "mode = 'preview_only'" in PREVIEW
    assert "mutationRequired = $MutationRequired" in PREVIEW
