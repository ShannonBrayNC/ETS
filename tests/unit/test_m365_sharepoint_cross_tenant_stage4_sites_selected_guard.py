SCRIPT_PATH = "scripts/m365/apply-ets-sharepoint-cross-tenant-stage4-sites-selected.ps1"

with open(SCRIPT_PATH, encoding="utf-8") as script_stream:
    SCRIPT = script_stream.read()
SCRIPT_LINES = set(SCRIPT.splitlines())
NORMALIZED_SCRIPT = " ".join(SCRIPT.split()).casefold()


def test_stage4_is_bound_to_approved_resource_tenant_and_application():
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
    assert (
        "$approvedOperatorAccount = 'shannon.bray@echomedia.ai'"
        in SCRIPT_LINES
    )


def test_stage4_allows_only_one_graph_mutation_method():
    assert NORMALIZED_SCRIPT.count("-method post") == 1
    for method in ("patch", "put", "delete"):
        assert f"-method {method}" not in NORMALIZED_SCRIPT
    assert "sites.fullcontrol.all" not in NORMALIZED_SCRIPT
    assert "/permissions" not in NORMALIZED_SCRIPT


def test_stage4_resolves_exact_sites_selected_application_role():
    assert "$sitesSelectedRoleValue = 'Sites.Selected'" in SCRIPT_LINES
    assert "@($_.allowedMemberTypes) -contains 'Application'" in SCRIPT
    assert "Microsoft Graph Sites.Selected application role did not resolve uniquely." in SCRIPT


def test_stage4_refuses_unexpected_existing_graph_permissions():
    assert "Connector enterprise application has an unexpected Graph permission set." in SCRIPT
    assert "$assignments.Count -ne 1 -or $selectedAssignments.Count -ne 1" in SCRIPT
    assert "$postAssignments.Count -ne 1 -or $postSelectedAssignments.Count -ne 1" in SCRIPT


def test_stage4_defaults_to_preview_and_requires_apply_for_mutation():
    assert "[switch]$Apply" in SCRIPT
    assert "if (-not $Apply)" in SCRIPT
    assert "mode = if ($Apply) { 'apply' } else { 'preview_only' }" in SCRIPT
    assert "stage = 'resource_sites_selected_assignment'" in SCRIPT


def test_stage4_does_not_create_later_stage_permissions_or_identity_objects():
    forbidden = (
        "az ad sp create",
        "az ad app create",
        "federated-credential create",
        "sites.fullcontrol.all",
        "sharepoint_site_read_grant",
        "az role assignment create",
    )
    for fragment in forbidden:
        assert fragment not in NORMALIZED_SCRIPT
    assert "sharePointPermissionAssigned = $false" in SCRIPT
