from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "live-core-gateway-deployment.yml"


def test_live_core_gateway_deployment_is_manual_and_least_privilege() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "workflow_dispatch:",
        "actions: read",
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


def test_live_core_gateway_deployment_requires_exact_q0_release_identity() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "image_source_sha:",
        "container_image:",
        "q0_workflow_run_id:",
        "Q0_SOURCE_SHA: ${{ inputs.image_source_sha }}",
        "CONTAINER_IMAGE: ${{ inputs.container_image }}",
        "Q0_WORKFLOW_RUN_ID: ${{ inputs.q0_workflow_run_id }}",
        "ref: ${{ github.sha }}",
        'test "$Q0_SOURCE_SHA" = "$GITHUB_SHA"',
        'pattern = rf"{re.escape(registry)}/ets/hosted-q1@sha256:[0-9a-f]{{64}}"',
        'echo "Q0_IMAGE_DIGEST=${CONTAINER_IMAGE##*@}" >> "$GITHUB_ENV"',
        '"path": ".github/workflows/hosted-azure-q0-image.yml"',
        '"conclusion": "success"',
        '"vulnerability_gate": "PASS"',
        '"registry_credentials_retained": False',
        '"customer_identifiers_retained": False',
        'if container.get("image") != os.environ["CONTAINER_IMAGE"]:',
    ):
        assert required in text

    assert "ref: ${{ inputs.image_source_sha }}" not in text


def test_live_core_gateway_deployment_requires_exact_protected_identity_scope_contract() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "GATEWAY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-id",
        "DIRECTORY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-dir-id",
        "PURVIEW_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-pur-id",
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
        "Gateway deployment did not reuse the pre-qualified SharePoint/Core identity.",
        "Gateway deployment did not reuse the pre-qualified directory identity.",
        "Gateway deployment did not reuse the pre-qualified Purview identity.",
        "Microsoft runtime identity client IDs are not distinct",
    ):
        assert required in text

    assert "steps.preflight.outputs.gateway_client_id" not in text


def test_live_core_gateway_deployment_uses_existing_bicep_runtime_contract() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "infra/azure/ets-hosted.bicep",
        "infra/azure/ets-gateway.bicep",
        "properties.outputs.managedEnvironmentName.value",
        "properties.outputs.managedEnvironmentResourceId.value",
        "az containerapp env show",
        "Core managed environment name changed after deployment",
        "Core managed environment resource ID changed after deployment",
        "Core managed environment provisioning did not succeed",
        "does not use the exact Core managed environment",
        'core_base_url="https://${CORE_FQDN}"',
        "authAppScopeMapJson=\"$AUTH_APP_SCOPE_MAP_JSON\"",
        "sharePointDriveId=\"$SHAREPOINT_DRIVE_ID\"",
        '"ETS_STORAGE_PROVIDER": "azure_table"',
        '"ETS_SIGNING_MODE": "azure_key_vault"',
        '"ETS_AUTH_MODE": "production_jwks"',
        "ingress must remain internal",
        "must remain single replica",
        "Gateway must attach exactly four user-assigned identities",
        "Gateway runtime identity lifecycle must remain Main",
        "Gateway ACR pull identity lifecycle must remain None",
        "Graph lifecycle configuration is present in the P0 deployment",
        "Graph lifecycle secret state is present in the P0 deployment",
    ):
        assert required in text

    for prohibited in (
        "az containerapp env list",
        "Expected exactly one live Container Apps managed environment after Core deployment.",
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
        '"managed_environment_name": os.environ["MANAGED_ENVIRONMENT_NAME"]',
        '"schema_version": "ets.live_core_gateway.deployment.v2"',
        '"q0_publication_evidence_verified": True',
        '"separated_microsoft_identities_verified": True',
        '"graph_lifecycle_configuration_present": False',
        '"graph_callback_ingress_external": False',
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
