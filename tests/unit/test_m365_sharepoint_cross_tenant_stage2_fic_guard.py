SCRIPT_PATH = "scripts/m365/apply-ets-sharepoint-cross-tenant-stage2-fic.ps1"

with open(SCRIPT_PATH, encoding="utf-8") as script_stream:
    SCRIPT = script_stream.read()
SCRIPT_LINES = SCRIPT.splitlines()


def test_stage2_has_exactly_one_fic_mutation() -> None:
    assert "[switch]$Apply" in SCRIPT
    assert SCRIPT.count("az ad app federated-credential create") == 1
    assert "api://AzureADTokenExchange" in SCRIPT
    expected_issuer_line = (
        '$expectedIssuer = "https://login.microsoftonline.com/'
        '$approvedDestinationTenantId/v2.0"'
    )
    assert expected_issuer_line in SCRIPT_LINES

    forbidden = (
        "az ad app create",
        "az ad sp create",
        "az ad app permission",
        "appRoleAssignments",
        "servicePrincipals/",
        "Sites.Selected",
        "sharepoint.com/sites/",
        "az identity create",
        "az role assignment create",
    )
    for marker in forbidden:
        assert marker not in SCRIPT


def test_stage2_is_bound_to_stage1_application_and_gateway_identity() -> None:
    assert (
        "$approvedApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a'"
        in SCRIPT
    )
    assert "$approvedManagedIdentityName = 'ets-oif5r5ydprrou-gw-id'" in SCRIPT
    assert "$approvedResourceGroup = 'rg-ets-prod-eastus'" in SCRIPT
    assert (
        "$approvedDestinationTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'"
        in SCRIPT
    )


def test_stage2_uses_live_uami_principal_as_subject_and_exact_audience() -> None:
    assert "$expectedSubject = [string]$identity.principalId" in SCRIPT
    assert "audiences = @($tokenExchangeAudience)" in SCRIPT
    assert "$audiences.Count -ne 1" in SCRIPT
    assert "$audiences[0] -cne $tokenExchangeAudience" in SCRIPT


def test_stage2_fails_closed_on_existing_or_post_create_drift() -> None:
    assert "if ($credentials.Count -gt 1)" in SCRIPT
    assert "Assert-FederatedCredentialShape" in SCRIPT
    assert "if ($postCredentials.Count -ne 1)" in SCRIPT
    assert "Assert-ApplicationShape -Application $application" in SCRIPT
    assert "passwordCredentials" in SCRIPT
    assert "keyCredentials" in SCRIPT
    assert "requiredResourceAccess" in SCRIPT


def test_stage2_result_denies_later_stage_claims() -> None:
    assert "resourceTenantServicePrincipalCreated = $false" in SCRIPT
    assert "graphPermissionAssigned = $false" in SCRIPT
    assert "sharePointPermissionAssigned = $false" in SCRIPT
