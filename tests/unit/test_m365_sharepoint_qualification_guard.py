import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUALIFIER = (
    ROOT / "scripts" / "m365" / "test-ets-sharepoint-connector-qualification.ps1"
).read_text(encoding="utf-8")


def test_qualification_script_is_read_only():
    mutating_methods = re.findall(
        r"-Method\s+(POST|PATCH|PUT|DELETE)\b",
        QUALIFIER,
        flags=re.IGNORECASE,
    )
    assert mutating_methods == []
    assert "Invoke-MgGraphRequest -Method GET" in QUALIFIER
    assert "mutationPerformed = $false" in QUALIFIER
    assert "reusableCredentialRetained = $false" in QUALIFIER
    assert "sourcePayloadRetained = $false" in QUALIFIER


def test_qualification_requires_distinct_cross_tenant_contexts():
    assert "DestinationAzureTenantId" in QUALIFIER
    assert "MicrosoftResourceTenantId" in QUALIFIER
    assert "Cross-tenant qualification requires distinct Azure and Microsoft resource tenants" in QUALIFIER
    assert "Active Azure tenant" in QUALIFIER
    assert "Microsoft Graph organization id does not match the expected resource tenant" in QUALIFIER


def test_qualification_requires_multitenant_app_and_exact_federated_credential():
    assert "MicrosoftApplicationId" in QUALIFIER
    assert "AzureADMultipleOrgs" in QUALIFIER
    assert "federatedIdentityCredentials" in QUALIFIER
    assert "https://login.microsoftonline.com/$DestinationAzureTenantId/v2.0" in QUALIFIER
    assert "credential.subject -cne $identity.principalId" in QUALIFIER
    assert "api://AzureADTokenExchange" in QUALIFIER
    assert "Expected exactly one federated identity credential" in QUALIFIER


def test_qualification_requires_echo_media_enterprise_app_provenance():
    assert "appOwnerOrganizationId" in QUALIFIER
    assert "connectorSp.appOwnerOrganizationId -ne $DestinationAzureTenantId" in QUALIFIER
    assert "ExpectedVerifiedDomain = 'echomedia.ai'" in QUALIFIER
    assert "enterpriseApplicationVerified = $true" in QUALIFIER


def test_qualification_requires_sites_selected_and_exact_site_grant():
    assert "Sites.Selected" in QUALIFIER
    assert "Expected exactly one Sites.Selected app-role assignment" in QUALIFIER
    assert "Federated SharePoint application has unexpected additional application permissions" in QUALIFIER
    assert "Expected exactly one site-level permission" in QUALIFIER
    assert "ExpectedSiteRole = 'read'" in QUALIFIER
    assert "siteReadGrantVerified = $true" in QUALIFIER


def test_qualification_does_not_use_azure_or_graph_mutation_commands():
    forbidden_fragments = (
        "az role assignment create",
        "az identity create",
        "az ad app create",
        "az ad app federated-credential create",
        "New-Mg",
        "Update-Mg",
        "Remove-Mg",
    )
    for fragment in forbidden_fragments:
        assert fragment not in QUALIFIER
