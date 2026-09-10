SCRIPT_PATH = "scripts/m365/apply-ets-sharepoint-cross-tenant-stage1.ps1"

with open(SCRIPT_PATH, encoding="utf-8") as script_stream:
    SCRIPT = script_stream.read()


def test_stage1_apply_has_one_explicit_mutation() -> None:
    assert "[switch]$Apply" in SCRIPT
    assert SCRIPT.count("az ad app create") == 1
    assert "--sign-in-audience AzureADMultipleOrgs" in SCRIPT

    forbidden = (
        "az ad sp create",
        "federated-credential create",
        "az ad app permission",
        "appRoleAssignments",
        "servicePrincipals/",
        "New-MgServicePrincipal",
        "New-MgApplicationFederatedIdentityCredential",
        "Sites.Selected",
        "sharepoint.com/sites/",
        "az identity create",
        "az role assignment create",
    )
    for marker in forbidden:
        assert marker not in SCRIPT


def test_stage1_apply_is_bound_to_approved_destination_and_name() -> None:
    assert (
        "$approvedDestinationTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'"
        in SCRIPT
    )
    assert (
        "$approvedApplicationDisplayName = 'ETS Gateway SharePoint Cross-Tenant'"
        in SCRIPT
    )
    assert "DestinationAzureTenantId must match the approved migration destination tenant exactly." in SCRIPT
    assert "ApplicationDisplayName must match the approved Gate 2 application name exactly." in SCRIPT


def test_stage1_apply_fails_closed_and_revalidates_shape() -> None:
    assert "if ($matches.Count -gt 1)" in SCRIPT
    assert "Assert-ApplicationShape -Application $matches[0]" in SCRIPT
    assert "if (-not $Apply)" in SCRIPT
    assert "if ($postMatches.Count -ne 1)" in SCRIPT
    assert "Assert-ApplicationShape -Application $postMatches[0]" in SCRIPT

    required_guards = (
        "passwordCredentials",
        "keyCredentials",
        "requiredResourceAccess",
        "identifierUris",
        "$Application.web.redirectUris",
        "$Application.spa.redirectUris",
        "$Application.publicClient.redirectUris",
    )
    for marker in required_guards:
        assert marker in SCRIPT


def test_stage1_result_explicitly_denies_later_stage_claims() -> None:
    assert "federatedIdentityCredentialCreated = $false" in SCRIPT
    assert "resourceTenantServicePrincipalCreated = $false" in SCRIPT
    assert "graphPermissionAssigned = $false" in SCRIPT
    assert "sharePointPermissionAssigned = $false" in SCRIPT
