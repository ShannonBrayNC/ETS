from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "live-gateway-identity-bootstrap.yml"


def test_live_gateway_identity_bootstrap_is_one_shot_and_least_privilege() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "push:",
        "- main",
        "- .github/workflows/live-gateway-identity-bootstrap.yml",
        "contents: read",
        "id-token: write",
        "issues: write",
        "environment: ets-azure-q1",
        'test "$GITHUB_REF" = "refs/heads/main"',
        'test "$GITHUB_EVENT_NAME" = "push"',
    ):
        assert required in text

    for prohibited in (
        "contents: write",
        "packages: write",
        "pull-requests: write",
        "AZURE_CLIENT_SECRET",
        "Application.ReadWrite.All",
        "AppRoleAssignment.ReadWrite.All",
    ):
        assert prohibited not in text


def test_live_gateway_identity_bootstrap_uses_bounded_non_customer_seeds() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "RESOURCE_GROUP: rg-ets-live-eastus",
        "ENVIRONMENT_NAME: ets-live",
        "CONNECTOR_INSTANCE_ID: m365-sharepoint-primary",
        "etsEnvironment=live",
        "etsOwner=lantern-protocol",
        "etsPurpose=hosted-gateway",
        "existing resource group is missing required ownership tag",
        "infra/azure/ets-gateway-identity.bicep",
    ):
        assert required in text

    assert "echomedia" not in text.lower()
    assert "sharepoint.com" not in text.lower()


def test_live_gateway_identity_bootstrap_preserves_release_identity() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "Q0_SOURCE_SHA: 332d7db3a69acd826a2a000264e81a179894e278",
        "Q0_IMAGE_DIGEST: sha256:c83a8cb0729d7e00506e4b7b9f0d0e5a7c5bbe3829abad76113ba7fd1ee3424c",
        'echo "::add-mask::$identity_resource_id"',
        'echo "::add-mask::$client_id"',
        'echo "::add-mask::$principal_id"',
        '"gateway_client_id_retained": False',
        '"gateway_principal_id_retained": False',
        '"reusable_credential_retained": False',
    ):
        assert required in text


def test_live_gateway_identity_bootstrap_keeps_release_claims_false() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        '"core_producer_role_assigned": False',
        '"core_scope_map_configured": False',
        '"azure_runtime_deployed": False',
        '"m365_source_to_proof_claimed": False',
        '"soak_clock_started": False',
        "Core `evidence_producer` role assigned: **false**",
        "72-hour soak clock started: **false**",
    ):
        assert required in text
