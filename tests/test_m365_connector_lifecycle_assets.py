from __future__ import annotations

from pathlib import Path

OFFBOARDING_SCRIPT = Path("scripts/m365/offboard-echomedia-sharepoint-connector.ps1")
LIFECYCLE_RUNBOOK = Path(
    "docs/connectors/MICROSOFT_CONNECTOR_LIFECYCLE_RUNBOOK_V1.md"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized_text(path: Path) -> str:
    return " ".join(_text(path).split())


def test_offboarding_is_dry_run_by_default_and_delete_calls_are_guarded() -> None:
    script = _text(OFFBOARDING_SCRIPT)

    apply_guard = script.index("if ($Apply) {")
    delete_positions: list[int] = []
    start = 0
    while True:
        position = script.find("-Method DELETE", start)
        if position < 0:
            break
        delete_positions.append(position)
        start = position + 1

    assert "[switch]$Apply" in script
    assert delete_positions
    assert all(position > apply_guard for position in delete_positions)
    assert "mode = if ($Apply) { 'apply' } else { 'dry_run' }" in script


def test_offboarding_fails_closed_on_tenant_or_permission_ambiguity() -> None:
    script = _text(OFFBOARDING_SCRIPT)
    required_guards = (
        "Microsoft Graph tenant does not match the active Azure subscription tenant",
        "Authenticated tenant does not contain required verified domain",
        "Multiple SharePoint site grants were found for the managed identity",
        "Target SharePoint permission also grants another application",
        "Duplicate Sites.Selected app-role assignments",
        "SharePoint site permission remained after offboarding mutation",
    )

    for guard in required_guards:
        assert guard in script


def test_offboarding_does_not_delete_identity_or_ets_history() -> None:
    script = _text(OFFBOARDING_SCRIPT)
    lowered = script.casefold()

    assert "az identity delete" not in lowered
    assert "managedIdentityDeleted = $false" in script
    assert "connectorHistoryDeleted = $false" in script
    assert "reusableCredentialRetained = $false" in script


def test_sites_selected_role_removal_requires_two_explicit_attestations() -> None:
    script = _text(OFFBOARDING_SCRIPT)
    guarded_removal = (
        "if ($RemoveSitesSelectedRole -and $sitesSelectedAssignmentPresentBefore)"
    )

    assert "[switch]$RemoveSitesSelectedRole" in script
    assert "[switch]$ConfirmDedicatedIdentity" in script
    assert "$RemoveSitesSelectedRole -and -not $ConfirmDedicatedIdentity" in script
    assert "script cannot prove that the managed identity" in script
    assert guarded_removal in script
    assert "if ($RemoveSitesSelectedRole)" in script
    assert "dedicatedIdentityConfirmed = [bool]$ConfirmDedicatedIdentity" in script
    assert "Sites.Selected app-role assignment remained" in script


def test_lifecycle_runbook_preserves_evidence_and_runtime_access_proof() -> None:
    runbook = _text(LIFECYCLE_RUNBOOK)
    required_boundaries = (
        "disable the connector with its current expected",
        "does not fabricate a destructive connector-delete operation",
        "offboarding must not erase them",
        "final evidence package",
        "prove that the former SharePoint target can no longer be read",
        "Operator Graph credentials",
        "historical ETS events or proofs",
    )

    for boundary in required_boundaries:
        assert boundary in runbook


def test_lifecycle_runbook_keeps_operations_separate_from_verification() -> None:
    runbook = _normalized_text(LIFECYCLE_RUNBOOK)

    assert "without changing ETS cryptographic verification semantics" in runbook
    assert "source truth" in runbook
    assert "source" in runbook and "completeness" in runbook
    assert "immutable image digest" in runbook
    assert "checkpoint reset without an explicit reconciliation gap" in runbook
    assert "-ConfirmDedicatedIdentity" in runbook
    assert "cannot prove global non-reuse" in runbook
