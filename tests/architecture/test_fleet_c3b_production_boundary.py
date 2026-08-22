from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSTGRES = ROOT / "ets" / "fleet" / "postgres.py"
POSTGRES_AUTH = ROOT / "ets" / "fleet" / "postgres_auth.py"
ENTRA = ROOT / "ets" / "fleet" / "entra_session.py"
RUNTIME = ROOT / "ets" / "fleet" / "production_runtime.py"
BICEP = ROOT / "infra" / "azure" / "ets-fleet-c3b.bicep"
DOCKERFILE = ROOT / "Dockerfile.fleet"


def test_shared_postgres_uses_serializable_transactions_and_tls() -> None:
    source = POSTGRES.read_text(encoding="utf-8")
    assert "BEGIN ISOLATION LEVEL SERIALIZABLE" in source
    assert 'sslmode="verify-full"' in source
    assert "https://ossrdbms-aad.database.windows.net/.default" in source
    assert "EnrollmentStoreConflict" in source
    assert "record_version" in source
    assert "pointer_version" in source
    assert "rotation_version" in source
    assert "ETS_FLEET_POSTGRES_PASSWORD" not in source
    assert "connection_string" not in source.lower()


def test_authorization_store_retains_hash_only_session_identifier() -> None:
    source = POSTGRES_AUTH.read_text(encoding="utf-8")
    assert "session_id_sha256" in source
    assert "hashlib.sha256" in source
    assert "refresh_token" not in source
    assert "access_token" not in source
    assert "csrf_token" not in source
    assert "fleet_principal_scopes" in source
    assert "fleet_session_standing" in source


def test_entra_adapter_never_uses_browser_headers_as_authority() -> None:
    source = ENTRA.read_text(encoding="utf-8")
    assert "request.headers" not in source
    assert "request.cookies" not in source
    assert "Fleet.Viewer" in (ROOT / "ets" / "fleet" / "portal.py").read_text(
        encoding="utf-8"
    )
    assert "resolve_scopes" in source
    assert "resolve_standing" in source
    assert "issuer mismatch" in source
    assert "audience mismatch" in source
    assert "tenant mismatch" in source
    assert "generation is stale" in source
    assert "roles changed" in source
    assert "step_up_not_before_utc" in source


def test_production_runtime_fails_closed_until_trusted_auth_bridge_exists() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "ContainerAppsEasyAuthMiddleware" in source
    assert 'auth_bridge = _required_env("ETS_FLEET_AUTH_BRIDGE")' in source
    assert 'auth_bridge != "container-apps-easyauth"' in source
    assert "Missing or malformed trusted context" in source
    assert "401 fail-closed" in source
    assert "Fleet PostgreSQL schema is not ready" in source
    assert "evidence_verified" not in source
    assert "health_asserted" not in source


def test_azure_composition_is_private_entra_only_and_multi_replica() -> None:
    source = BICEP.read_text(encoding="utf-8")
    lines = {line.strip() for line in source.splitlines()}
    assert "passwordAuth: 'Disabled'" in source
    assert "activeDirectoryAuth: 'Enabled'" in source
    assert source.count("publicNetworkAccess: 'Disabled'") >= 2
    assert (
        "var postgresPrivateDnsZoneName = 'privatelink.postgres.database.azure.com'"
        in lines
    )
    assert "'postgresqlServer'" in source
    assert "minReplicas: 2" in source
    assert "maxReplicas: 6" in source
    assert "AZURE_CLIENT_ID" in source
    assert "ETS_FLEET_POSTGRES_PASSWORD" not in source
    assert "administratorLoginPassword" not in source
    assert "Microsoft.Cdn/profiles" not in source
    assert "fleet.lanternprotocol.net" not in source
    assert "publicHostnameActivated bool = false" in source
    assert "corePublicEndpointCreated bool = false" in source
    assert "gatewayPublicEndpointCreated bool = false" in source
    assert "iotPublicManagementEndpointCreated bool = false" in source


def test_fleet_runtime_image_drops_root_privileges() -> None:
    source = DOCKERFILE.read_text(encoding="utf-8")
    assert "adduser --system" in source
    assert "USER ets" in source
    assert '.[fleet]' in source
    assert "ets.fleet.production_entrypoint" in source
