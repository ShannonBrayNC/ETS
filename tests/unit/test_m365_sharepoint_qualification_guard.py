from pathlib import Path
import re

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


def test_qualification_requires_destination_tenant_match():
    assert "ExpectedTenantId" in QUALIFIER
    assert "Active Azure tenant" in QUALIFIER
    assert "Microsoft Graph organization id does not match" in QUALIFIER


def test_qualification_requires_sites_selected_and_exact_site_grant():
    assert "Sites.Selected" in QUALIFIER
    assert "Expected exactly one Sites.Selected app-role assignment" in QUALIFIER
    assert "Expected exactly one site-level permission" in QUALIFIER
    assert "ExpectedSiteRole = 'read'" in QUALIFIER


def test_qualification_does_not_use_azure_or_graph_mutation_commands():
    forbidden_fragments = (
        "az role assignment create",
        "az identity create",
        "New-Mg",
        "Update-Mg",
        "Remove-Mg",
    )
    for fragment in forbidden_fragments:
        assert fragment not in QUALIFIER
