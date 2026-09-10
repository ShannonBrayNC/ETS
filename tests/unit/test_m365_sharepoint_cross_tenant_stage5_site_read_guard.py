SCRIPT_PATH = "scripts/m365/apply-ets-sharepoint-cross-tenant-stage5-site-read.ps1"

with open(SCRIPT_PATH, encoding="utf-8") as script_stream:
    SCRIPT = script_stream.read()
NORMALIZED_SCRIPT = " ".join(SCRIPT.split()).casefold()
SCRIPT_LINES = set(SCRIPT.splitlines())


def test_stage5_defaults_to_preview_and_requires_apply_switch():
    assert "[switch]$Apply" in SCRIPT
    assert "mode = if ($Apply) { 'apply' } else { 'preview_only' }" in SCRIPT
    assert "if (-not $Apply)" in SCRIPT


def test_stage5_is_bound_to_exact_tenant_operator_application_and_site():
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
    assert "$approvedOperatorAccount = 'shannon.bray@echomedia.ai'" in SCRIPT_LINES
    assert "$approvedSharePointHostname = 'echomediaai.sharepoint.com'" in SCRIPT_LINES
    assert "$approvedSitePath = '/sites/ETS'" in SCRIPT_LINES
    expected_site_id_line = (
        "$approvedSiteId = 'echomediaai.sharepoint.com,"
        "2604ea4c-3b40-4195-b1a8-e3d7327b7c41,"
        "9ddf1ece-7f81-4258-af25-91e06afaa682'"
    )
    assert expected_site_id_line in SCRIPT_LINES


def test_stage5_only_allows_read_role():
    assert "[ValidateSet('read')]" in SCRIPT
    assert "$SiteRole -cne 'read'" in SCRIPT
    assert "roles = @('read')" in SCRIPT
    assert "broaderSiteRoleAssigned = $false" in SCRIPT
    for role in ("write", "fullcontrol"):
        assert f"roles = @('{role}')" not in NORMALIZED_SCRIPT


def test_stage5_revalidates_sites_selected_before_site_grant():
    assert "Sites.Selected" in SCRIPT
    assert "appRoleAssignments" in SCRIPT
    assert "$selectedAssignments.Count -ne 1" in SCRIPT
    assert "$assignmentSet.Count -ne 1" in SCRIPT


def test_stage5_contains_exactly_one_graph_post_and_no_other_mutation_method():
    assert NORMALIZED_SCRIPT.count("-method post") == 1
    assert (
        '-uri "https://graph.microsoft.com/v1.0/sites/$approvedsiteid/permissions"'
        in NORMALIZED_SCRIPT
    )
    for method in ("patch", "put", "delete"):
        assert f"-method {method}" not in NORMALIZED_SCRIPT


def test_stage5_contains_no_azure_or_identity_provisioning_mutations():
    forbidden_fragments = (
        "az ad app",
        "az ad sp",
        "az role assignment",
        "az identity",
        "federatedIdentityCredentials",
        "appRoleAssignedTo",
        "New-Mg",
        "Update-Mg",
        "Remove-Mg",
    )
    for fragment in forbidden_fragments:
        assert fragment not in SCRIPT


def test_stage5_rechecks_existing_and_post_create_permission_state():
    assert "Get-ConnectorSiteGrants" in SCRIPT
    assert "Assert-ExactReadGrant" in SCRIPT
    assert "$afterPermissions = Invoke-GraphGet" in SCRIPT
    assert "$afterConnectorGrants" in SCRIPT
    assert "Expected exactly one ETS connector grant" in SCRIPT
    assert "not exactly read-only" in SCRIPT


def test_stage5_requires_operator_scopes_for_site_permission_admin():
    assert "    'Application.Read.All'," in SCRIPT_LINES
    assert "    'Organization.Read.All'," in SCRIPT_LINES
    assert "    'Sites.Read.All'," in SCRIPT_LINES
    assert "    'Sites.FullControl.All'" in SCRIPT_LINES
    assert "$missingScopes.Count -gt 0" in SCRIPT
