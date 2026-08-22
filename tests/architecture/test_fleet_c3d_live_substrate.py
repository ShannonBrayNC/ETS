from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BICEP = ROOT / "infra" / "azure" / "ets-fleet-c3d-live.bicep"
READINESS_BICEP = ROOT / "infra" / "azure" / "ets-fleet-c3d-readiness.bicep"
WORKFLOW = ROOT / ".github" / "workflows" / "fleet-c3d-live-deploy.yml"
BOOTSTRAP = ROOT / "ets" / "fleet" / "bootstrap.py"
READINESS = ROOT / "ets" / "fleet" / "private_readiness_probe.py"


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


def test_governed_fleet_entra_registration_is_single_tenant_and_role_exact() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "AzureADMyOrg" in source
    assert "--enable-id-token-issuance true" in source
    assert "Fleet.Viewer" in source
    assert "Fleet.Operator" in source
    assert "Fleet.SecurityAdmin" in source
    assert "allowedMemberTypes" in source
    assert "az ad sp create" in source
    assert "az ad app credential reset" not in source
    assert "--client-secret" not in source
