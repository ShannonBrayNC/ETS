from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "live-core-gateway-deployment.yml"


def test_live_core_gateway_deployment_is_manual_and_least_privilege() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "workflow_dispatch:",
        "contents: read",
        "id-token: write",
        "issues: write",
        "environment: ets-azure-q1",
        'test "$GITHUB_REF" = "refs/heads/main"',
        'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"',
        "azure/login@v3.0.0",
    ):
        assert required in text

    for prohibited in (
        "contents: write",
        "packages: write",
        "pull-requests: write",
        "AZURE_CLIENT_SECRET",
        "Application.ReadWrite.All",
        "AppRoleAssignment.ReadWrite.All",
        "ETS_Q1_BEARER_TOKEN",
    ):
        assert prohibited not in text


def test_live_core_gateway_deployment_preserves_authoritative_release_identity() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "Q0_SOURCE_SHA: d3a3c9b98d371881a30d8d6e3ea099bb58767a96",
        "Q0_IMAGE_DIGEST: sha256:7f92c14ca4e99af323c3b0e39c89903180296a0264078d281ff925a89c8c226f",
        (
            "CONTAINER_IMAGE: etsq1a352eb89.azurecr.io/ets/hosted-q1@sha256:"
            "3925355f477a6f76bcb467ad4dbd9b302641bd4de322ce62d999ab7d28f6cfde"
        ),
        'test "$CONTAINER_IMAGE" = "${ACR_NAME}.azurecr.io/ets/hosted-q1@${Q0_IMAGE_DIGEST}"',
        'if container.get("image") != os.environ["CONTAINER_IMAGE"]:',
    ):
        assert required in text

    superseded_digest = (
        "sha256:1331cfa59fa78b3d63f8f6458ea3f2a130560b4ff9962eceb4666a79e30c4ce6"
    )
    assert superseded_digest not in text


def test_live_core_gateway_deployment_requires_exact_protected_identity_scope_contract() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "GATEWAY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-id",
        "ETS_LIVE_CORE_SCOPE",
        "ETS_LIVE_AUTH_AUDIENCE",
        "ETS_LIVE_AUTH_ISSUER",
        "ETS_LIVE_AUTH_JWKS_URL",
        "ETS_LIVE_AUTH_TENANT_ID",
        "ETS_LIVE_AUTH_APP_SCOPE_MAP_JSON",
        "ETS_LIVE_TENANT_ID",
        "ETS_LIVE_WORKSPACE_ID",
        "ETS_LIVE_MICROSOFT_TENANT_ID",
        "ETS_LIVE_SHAREPOINT_DRIVE_ID",
        "Core managed-identity scope must equal <audience>/.default",
        "app scope map key does not match the live Gateway client ID",
        "Gateway scope binding tenant does not match protected ETS tenant",
        "Gateway scope binding workspace does not match protected ETS workspace",
        "Gateway deployment did not reuse the pre-qualified live managed identity",
    ):
        assert required in text

    assert "steps.preflight.outputs.gateway_client_id" not in text


def test_live_core_gateway_deployment_uses_existing_bicep_runtime_contract() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "infra/azure/ets-hosted.bicep",
        "infra/azure/ets-gateway.bicep",
        "az containerapp env list",
        "Expected exactly one live Container Apps managed environment after Core deployment.",
        'core_base_url="https://${CORE_FQDN}"',
        "authAppScopeMapJson=\"$AUTH_APP_SCOPE_MAP_JSON\"",
        "sharePointDriveId=\"$SHAREPOINT_DRIVE_ID\"",
        '"ETS_STORAGE_PROVIDER": "azure_table"',
        '"ETS_SIGNING_MODE": "azure_key_vault"',
        '"ETS_AUTH_MODE": "production_jwks"',
        "ingress must remain internal",
        "must remain single replica",
    ):
        assert required in text

    for prohibited in (
        "local_header",
        "local_unsigned",
        "in_memory",
        "registry-password",
        "registry-username",
    ):
        assert prohibited not in text


def test_live_core_gateway_deployment_retains_bounded_nonclaims() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        '"core_scope_map_configured": True',
        '"azure_runtime_resources_deployed": True',
        '"runtime_health_claimed": False',
        '"producer_token_proof_claimed": False',
        '"negative_control_proof_claimed": False',
        '"m365_source_to_proof_claimed": False',
        '"soak_clock_started": False',
        '"customer_identifiers_retained": False',
        '"reusable_credential_retained": False',
        "producer-token proof claimed: **false**",
        "negative-control proof claimed: **false**",
        "72-hour soak clock started: **false**",
    ):
        assert required in text
