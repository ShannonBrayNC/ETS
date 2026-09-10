from pathlib import Path


SCRIPT_PATH = Path("scripts/m365/test-ets-sharepoint-connector-qualification.ps1")
SCRIPT = SCRIPT_PATH.read_text(encoding="utf-8")
SCRIPT_LINES = set(SCRIPT.splitlines())
NORMALIZED_SCRIPT = " ".join(SCRIPT.split()).casefold()


def test_resource_tenant_qualification_requests_site_read_and_permission_admin_scopes():
    assert "    'Sites.Read.All'," in SCRIPT_LINES
    assert "    'Sites.FullControl.All'" in SCRIPT_LINES


def test_qualification_remains_read_only():
    for method in ("post", "patch", "put", "delete"):
        assert f"-method {method}" not in NORMALIZED_SCRIPT
    assert "mutationPerformed = $false" in SCRIPT


def test_qualification_checks_exact_sites_selected_and_site_read_grant():
    assert "Sites.Selected" in SCRIPT
    assert "$assignmentSet.Count -ne 1" in SCRIPT
    assert "$siteGrants.Count -ne 1" in SCRIPT
    assert "siteReadGrantVerified = $true" in SCRIPT
