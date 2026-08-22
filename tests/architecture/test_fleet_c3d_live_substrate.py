from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BICEP = ROOT / "infra" / "azure" / "ets-fleet-c3d-live.bicep"
READINESS_BICEP = ROOT / "infra" / "azure" / "ets-fleet-c3d-readiness.bicep"
WORKFLOW = ROOT / ".github" / "workflows" / "fleet-c3d-live-deploy.yml"
BOOTSTRAP = ROOT / "ets" / "fleet" / "bootstrap.py"
READINESS = ROOT / "ets" / "fleet" / "private_readiness_probe.py"
ENTRA_BOOTSTRAP = ROOT / "scripts" / "azure" / "ensure-fleet-entra-application.ps1"


def test_c3d_uses_separate_migration_and_runtime_managed_identities() -> None:
    source = BICEP.read_text(encoding="utf-8")
    assert "migrationIdentity" in source
    assert "runtimeIdentityResourceId" in source
    assert "postgresEntraAdministratorObjectId: migrationIdentity.properties.principalId" in source
    assert "postgresEntraAdministratorType: 'ServicePrincipal'" in source
    assert "ETS_FLEET_RUNTIME_PRINCIPAL_ID" in source
    assert "ETS_FLEET_RUNTIME_CLIENT_ID" in source
    assert "python" in source and "ets.fleet.bootstrap" in source
    assert "Microsoft.App/jobs@2025-01-01" in source
    assert "output resolvedPostgresServerVersion string = fleetC3b.outputs.resolvedPostgresServerVersion" in source
    assert "output resolvedPostgresSkuName string = fleetC3b.outputs.resolvedPostgresSkuName" in source
    assert "output deploymentLocation string = fleetC3b.outputs.deploymentLocation" in source
    assert "password" not in source.lower()
    assert "connectionstring" not in source.lower()
    assert "Microsoft.Cdn" not in source
    assert "fleet.lanternprotocol.net" not in source
    assert "publicHostnameActivated bool = false" in source


def test_c3d_bootstrap_binds_entra_oid_and_rejects_database_admin() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "pgaadauth_create_principal_with_oid" in source
    assert "pgaadauth_list_principals" in source
    assert "pg_has_role" in source
    assert "azure_pg_admin" in source
    assert "rolcreaterole" in source
    assert "rolcreatedb" in source
    assert "rolsuper" in source
    assert "GRANT SELECT, INSERT, UPDATE, DELETE" in source
    assert "AzureManagedIdentityPostgresFactory" in source
    assert "ETS_FLEET_POSTGRES_PASSWORD" not in source
    assert "connection_string" not in source.lower()


def test_c3d_readiness_is_private_and_does_not_claim_trust_or_health() -> None:
    bicep = READINESS_BICEP.read_text(encoding="utf-8")
    probe = READINESS.read_text(encoding="utf-8")
    assert "managedEnvironmentName" in bicep
    assert "runtimeIdentityResourceId" in bicep
    assert "ETS_FLEET_INTERNAL_BASE_URL" in bicep
    assert "ets.fleet.private_readiness_probe" in bicep
    assert 'payload.get("evidence_verified") is not False' in probe
    assert 'payload.get("health_asserted") is not False' in probe
    assert '"evidence_verified": False' in probe
    assert '"health_asserted": False' in probe


def test_live_workflow_requires_exact_q0_and_never_activates_public_hostname() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "expected_source_sha" in source
    assert "q0_workflow_run_id" in source
    assert "fleet_image" in source
    assert "entra_client_id" in source
    assert "deployment_location" in source
    assert "default: eastus2" in source
    assert "default: rg-ets-live-eastus2" in source
    assert "postgres_server_version" in source
    assert 'default: "17"' in source
    assert "postgres_sku_name" in source
    assert "Standard_D2ds_v5" in source
    assert "zoneRedundantHaSupported" in source
    assert "postgres-capability.json" in source
    assert "capabilities?api-version=2025-08-01" in source
    assert "actions: read" in source
    assert "gh run view" in source
    assert "gh run download" in source
    assert "fleet-c3c-q0-image-${Q0_RUN_ID}" in source
    assert "manifest.get('source_sha') == os.environ['EXPECTED_SOURCE_SHA']" in source
    assert "manifest.get('immutable_image') == os.environ['FLEET_IMAGE']" in source
    assert "manifest.get('vulnerability_gate') == 'PASS'" in source
    assert "ets/fleet/control-plane" in source
    assert "@sha256:" in source
    assert "azure/login@v3.0.0" in source
    assert "adminUserEnabled" in source
    assert "authentication-as-arm" in source
    assert "az deployment group create" in source
    assert "ets-fleet-c3d-live.bicep" in source
    assert "'resolvedPostgresServerVersion'" in source
    assert "'resolvedPostgresSkuName'" in source
    assert "'resolvedPostgresHighAvailabilityMode'" in source
    assert "'deploymentLocation'" in source
    assert "az containerapp job start" in source
    assert "ETS_FLEET_AUTH_BRIDGE=container-apps-easyauth" in source
    assert "ets-fleet-c3d-readiness.bicep" in source
    assert "passwordAuth" in source
    assert "publicNetworkAccess" in source
    assert "public_hostname_activated': False" in source
    assert "easyauth_platform_activated': False" in source
    assert "fleet.lanternprotocol.net" not in source
    assert "az afd" not in source
    assert "custom-domain" not in source


def test_c3d_github_identity_has_no_graph_application_mutation_path() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "entra_client_id" in source
    assert "github_graph_write_required=false" in source
    assert "az ad app" not in lowered
    assert "az ad sp" not in lowered
    assert "graph.microsoft.com" not in lowered
    assert "application.readwrite" not in lowered
    assert "connect-mggraph" not in lowered
    assert "provision_entra_application" not in source
    assert "entra_application_display_name" not in source


def test_delegated_entra_bootstrap_is_separate_from_c3d_workflow() -> None:
    source = ENTRA_BOOTSTRAP.read_text(encoding="utf-8")
    assert "Connect-MgGraph" in source
    assert "-ContextScope Process" in source
    assert "Application.ReadWrite.All" in source
    assert "AzureADMyOrg" in source
    assert "Fleet.Viewer" in source
    assert "Fleet.Operator" in source
    assert "Fleet.SecurityAdmin" in source
    assert "19292461-7726-5197-acd4-6da5cf9d5440" in source
    assert "b1c406fc-6d94-5397-a37d-7b23192f052f" in source
    assert "cd7b83d7-7fbe-5b30-811d-5b6b8fa79fb4" in source
    assert "enableIdTokenIssuance = $true" in source
    assert "enableAccessTokenIssuance = $false" in source
    assert "oauth2PermissionScopes" in source
    assert "preAuthorizedApplications" in source
    assert "knownClientApplications" in source
    assert "passwordCredentials" in source
    assert "keyCredentials" in source
    assert "githubGraphWriteRequired = $false" in source
