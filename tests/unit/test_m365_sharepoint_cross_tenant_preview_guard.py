PREVIEW_PATH = "scripts/m365/preview-ets-sharepoint-cross-tenant-bootstrap.ps1"

with open(PREVIEW_PATH, encoding="utf-8") as preview_stream:
    PREVIEW = preview_stream.read()
NORMALIZED_PREVIEW = " ".join(PREVIEW.split()).casefold()
PREVIEW_LINES = set(PREVIEW.splitlines())


def test_preview_contains_no_graph_mutation_methods():
    for method in ("post", "patch", "put", "delete"):
        assert f"-method {method}" not in NORMALIZED_PREVIEW
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
    assert "    [string]$ResourceGroup = 'rg-ets-prod-eastus'," in PREVIEW_LINES
    assert "    [string]$ManagedIdentityName = 'ets-oif5r5ydprrou-gw-id'," in PREVIEW_LINES
    assert (
        "    [string]$SharePointHostname = 'echomediaai.sharepoint.com',"
        in PREVIEW_LINES
    )
    assert "    [string]$SitePath = '/sites/ETS'," in PREVIEW_LINES
    assert "    [string]$ExpectedSiteRole = 'read'," in PREVIEW_LINES
    assert "$SharePointHostname -cne $approvedSharePointHostname" in PREVIEW
    assert "$SitePath -cne $approvedSitePath" in PREVIEW


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
