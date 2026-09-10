SCRIPT_PATH = "scripts/m365/authorize-ets-sharepoint-stage5-operator.ps1"

with open(SCRIPT_PATH, encoding="utf-8") as script_stream:
    SCRIPT = script_stream.read()
NORMALIZED_SCRIPT = " ".join(SCRIPT.split()).casefold()
SCRIPT_LINES = set(SCRIPT.splitlines())


def test_stage5_operator_authorization_contains_no_graph_resource_mutation_methods():
    for method in ("post", "patch", "put", "delete"):
        assert f"-method {method}" not in NORMALIZED_SCRIPT
    assert "Invoke-MgGraphRequest -Method GET" in SCRIPT
    assert "graphResourceMutationPerformed = $false" in SCRIPT


def test_stage5_operator_authorization_requests_exact_required_scopes():
    assert "    'Application.Read.All'," in SCRIPT_LINES
    assert "    'Organization.Read.All'," in SCRIPT_LINES
    assert "    'Sites.Read.All'," in SCRIPT_LINES
    assert "    'Sites.FullControl.All'" in SCRIPT_LINES
    assert "$missingScopes.Count -gt 0" in SCRIPT


def test_stage5_operator_authorization_is_bound_to_exact_resource_tenant_operator_and_site():
    assert "$approvedResourceTenantId = '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe'" in SCRIPT_LINES
    assert "$approvedApplicationId = '0be62a70-45b5-405d-92b6-ca0ce3af953a'" in SCRIPT_LINES
    assert "$approvedOperatorAccount = 'shannon.bray@echomedia.ai'" in SCRIPT_LINES
    assert "$approvedVerifiedDomain = 'echomedia.ai'" in SCRIPT_LINES
    assert "$approvedSharePointHostname = 'echomediaai.sharepoint.com'" in SCRIPT_LINES
    assert "$approvedSitePath = '/sites/ETS'" in SCRIPT_LINES
    expected_site_id_line = (
        "$approvedSiteId = 'echomediaai.sharepoint.com,"
        "2604ea4c-3b40-4195-b1a8-e3d7327b7c41,"
        "9ddf1ece-7f81-4258-af25-91e06afaa682'"
    )
    assert expected_site_id_line in SCRIPT_LINES


def test_stage5_operator_authorization_verifies_site_and_permission_state_read_only():
    assert "Resolved SharePoint site ID does not match the approved ETS site identity." in SCRIPT
    assert "Resolved SharePoint site URL does not match the approved ETS site URL." in SCRIPT
    assert "sharepoint_site_read_grant" in SCRIPT
    assert "ready_for_read_only_qualification" in SCRIPT
    assert "siteGrantPresent = $SiteGrantPresent" in SCRIPT


def test_stage5_operator_authorization_does_not_create_site_permission_or_change_connector():
    forbidden_fragments = (
        "New-Mg",
        "Update-Mg",
        "Remove-Mg",
        "az ad app",
        "az ad sp",
        "az role assignment",
        "appRoleAssignedTo",
        "federatedIdentityCredentials",
        "-Apply",
    )
    for fragment in forbidden_fragments:
        assert fragment not in SCRIPT
