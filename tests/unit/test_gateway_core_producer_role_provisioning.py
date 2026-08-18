from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROLE_SCRIPT = ROOT / "scripts" / "azure" / "ensure-core-evidence-producer-app-role.ps1"
ASSIGN_SCRIPT = ROOT / "scripts" / "azure" / "provision-gateway-core-evidence-producer.ps1"
RUNBOOK = ROOT / "docs" / "gateway" / "CORE_PRODUCER_ROLE_PROVISIONING_V1.md"
ROLE_ID = "062e20df-6571-4fa3-ab90-e1f30cd360bd"


def test_core_role_bootstrap_is_tenant_bound_and_apply_gated() -> None:
    text = ROLE_SCRIPT.read_text(encoding="utf-8")

    for required in (
        "[switch]$Apply",
        "ExpectedVerifiedDomain = 'echomedia.ai'",
        ROLE_ID,
        "Application.ReadWrite.All",
        "Microsoft Graph tenant does not match the active Azure subscription tenant.",
        "Refusing to modify the Core application.",
        "mutationRequired = $true",
        "applyRequested = $false",
        "reusableCredentialRetained = $false",
    ):
        assert required in text

    assert "AZURE_CLIENT_SECRET" not in text
    assert "client_secret" not in text.lower()


def test_core_role_bootstrap_preserves_roles_and_fails_on_role_id_drift() -> None:
    text = ROLE_SCRIPT.read_text(encoding="utf-8")

    for required in (
        "$appRoles.Add(@{",
        "allowedMemberTypes = @($role.allowedMemberTypes)",
        "value = [string]$role.value",
        "allowedMemberTypes = @('Application')",
        "value = $RoleValue",
        "Refusing implicit role-id migration.",
        "Expected exactly one '$ExpectedRoleValue' app role on the Core application.",
        "Core '$ExpectedRoleValue' app role is disabled.",
    ):
        assert required in text


def test_gateway_assignment_binds_exact_uami_and_core_role() -> None:
    text = ASSIGN_SCRIPT.read_text(encoding="utf-8")

    for required in (
        "[switch]$Apply",
        "ExpectedVerifiedDomain = 'echomedia.ai'",
        ROLE_ID,
        "AppRoleAssignment.ReadWrite.All",
        "az identity show",
        "[string]$gatewaySp.id -ne [string]$identity.principalId",
        "Core service principal does not expose exactly one enabled application role",
        "Gateway managed identity already has unexpected app-role authority",
        "Duplicate Core evidence_producer app-role assignments were found.",
        "assignmentReady = $false",
        "mutationRequired = $true",
        "reusableCredentialRetained = $false",
    ):
        assert required in text

    assert "AZURE_CLIENT_SECRET" not in text
    assert "client_secret" not in text.lower()


def test_gateway_assignment_is_idempotent_and_rechecks_after_apply() -> None:
    text = ASSIGN_SCRIPT.read_text(encoding="utf-8")

    for required in (
        "$existing.Count -eq 0",
        "if ($Apply)",
        "appRoleAssignedTo",
        "$assignments = Invoke-GraphGet -Uri $assignmentsUri",
        "Core evidence_producer assignment did not converge to exactly one grant.",
        "assignmentReady = $true",
        "assignmentCreated = $created",
    ):
        assert required in text


def test_runbook_keeps_scope_permission_and_soak_claims_separate() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for required in (
        "ETS_AUTH_APP_SCOPE_MAP_JSON",
        "evidence_producer",
        "332d7db3a69acd826a2a000264e81a179894e278",
        "GitHub Actions deployment identities are",
        "Do not upload raw operator output to public release evidence.",
        "roles: [\"evidence_producer\"]",
        "without `evidence.create` is denied ingestion",
        "The 72-hour soak clock remains stopped",
    ):
        assert required in text
