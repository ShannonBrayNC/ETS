SCRIPT_PATH = (
    "scripts/m365/apply-ets-sharepoint-cross-tenant-stage3-resource-enterprise-app.ps1"
)

with open(SCRIPT_PATH, encoding="utf-8") as script_stream:
    SCRIPT = script_stream.read()
SCRIPT_LINES = set(SCRIPT.splitlines())


def test_stage3_has_exactly_one_enterprise_app_mutation() -> None:
    assert "[switch]$Apply" in SCRIPT
    assert SCRIPT.count("az ad sp create") == 1
    assert "        stage = 'resource_enterprise_application'" in SCRIPT_LINES


def test_stage3_is_bound_to_resource_tenant_application_and_operator() -> None:
    assert (
        "$approvedResourceTenantId = '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe'"
        in SCRIPT_LINES
    )
    assert (
        "$approvedDestinationTenantId = '0d20cf0f-3498-46c1-a0db-69b09c634cc2'"
        in SCRIPT_LINES
    )
    assert (
        "$approvedApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a'"
        in SCRIPT_LINES
    )
    assert "$approvedVerifiedDomain = 'echomedia.ai'" in SCRIPT_LINES
    assert "$approvedOperatorAccount = 'shannon.bray@echomedia.ai'" in SCRIPT_LINES


def test_stage3_verifies_exact_resource_tenant_before_mutation() -> None:
    assert "$account.tenantId -cne $approvedResourceTenantId" in SCRIPT
    assert "$account.user.name -ine $approvedOperatorAccount" in SCRIPT
    assert "$organizations.Count -ne 1" in SCRIPT
    assert "$organizations[0].id -cne $approvedResourceTenantId" in SCRIPT
    assert "$_ .name" not in SCRIPT
    assert "$_ .name -ieq" not in SCRIPT
    assert "$_.name -ieq $approvedVerifiedDomain" in SCRIPT


def test_stage3_rejects_duplicates_and_rechecks_created_service_principal() -> None:
    assert "$matches = @(Get-ResourceTenantServicePrincipals)" in SCRIPT
    assert "$postMatches = @(Get-ResourceTenantServicePrincipals)" in SCRIPT
    assert "$matches.Count -gt 1" in SCRIPT
    assert "$postMatches.Count -ne 1" in SCRIPT
    assert "Assert-ServicePrincipalShape" in SCRIPT
    assert "$ServicePrincipal.servicePrincipalType -cne 'Application'" in SCRIPT
    assert "$ServicePrincipal.accountEnabled -ne $true" in SCRIPT
    assert "$ServicePrincipal.appOwnerOrganizationId -cne $approvedDestinationTenantId" in SCRIPT


def test_stage3_excludes_later_gate_mutations() -> None:
    forbidden = (
        "appRoleAssignments",
        "appRoleAssignedTo",
        "Sites.Selected",
        "sharepoint.com/sites/",
        "federatedIdentityCredentials",
        "federated-credential create",
        "az ad app create",
        "az ad app permission",
        "az role assignment create",
        "az identity create",
        "passwordCredentials",
        "keyCredentials",
    )
    for marker in forbidden:
        assert marker not in SCRIPT


def test_stage3_reports_later_stages_as_not_performed() -> None:
    assert "graphPermissionAssigned = $false" in SCRIPT
    assert "sharePointPermissionAssigned = $false" in SCRIPT
    assert "publicEvidenceSafe = $false" in SCRIPT
