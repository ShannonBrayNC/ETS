from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "ets" / "fleet" / "container_apps_auth.py"
RUNTIME = ROOT / "ets" / "fleet" / "production_runtime.py"
BICEP = ROOT / "infra" / "azure" / "ets-fleet-c3c-frontdoor.bicep"


def test_c3c_bridge_reads_only_platform_principal_not_tokens_or_ets_authority() -> None:
    source = BRIDGE.read_text(encoding="utf-8").lower()
    assert '"x-ms-client-principal"' in source
    assert "x-ms-token-aad-access-token" not in source
    assert "x-ms-token-aad-refresh-token" not in source
    assert "authorization" not in source
    assert "request.cookies" not in source
    assert "x-ets-tenant" not in source
    assert "x-ets-workspace" not in source
    assert "x-ets-role" not in source
    assert "x-ets-step-up" not in source


def test_c3c_bridge_requires_session_time_and_conditional_access_context() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    assert '_unix_claim(claims, "auth_time")' in source
    assert '_one_claim(claims, "sid")' in source
    assert '_expanded_multi_claim(claims, "acrs")' in source
    assert "session_generation=1" in source
    assert "ets-fleet-c3c-csrf-v1" in source


def test_c3c_runtime_requires_explicit_container_apps_easyauth_boundary() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert 'auth_bridge = _required_env("ETS_FLEET_AUTH_BRIDGE")' in source
    assert 'auth_bridge != "container-apps-easyauth"' in source
    assert 'step_up_auth_context_id = _required_env("ETS_FLEET_STEP_UP_ACRS")' in source
    assert "ContainerAppsEasyAuthMiddleware" in source
    assert "portal routes remain" in source
    assert "401 fail-closed" in source


def test_c3c_frontdoor_is_private_link_premium_waf_and_not_hostname_activated() -> None:
    source = BICEP.read_text(encoding="utf-8")
    assert "Premium_AzureFrontDoor" in source
    assert "sharedPrivateLinkResource" in source
    assert "groupId: 'managedEnvironments'" in source
    assert "status: 'Pending'" in source
    assert "linkToDefaultDomain: 'Enabled'" in source
    assert "mode: 'Prevention'" in source
    assert "Microsoft_DefaultRuleSet" in source
    assert "Microsoft_BotManagerRuleSet" in source
    assert "publicHostnameActivated bool = false" in source
    assert "fleet.lanternprotocol.net" not in source
    assert "profiles/customDomains" not in source


def test_c3c_easyauth_is_single_tenant_fail_closed_and_token_store_disabled() -> None:
    source = BICEP.read_text(encoding="utf-8")
    assert "unauthenticatedClientAction: 'RedirectToLoginPage'" in source
    assert "redirectToProvider: 'azureactivedirectory'" in source
    assert "clientSecretSettingName: entraClientSecretSettingName" in source
    assert "operatorGroupObjectIds" in source
    assert "allowedAudiences" in source
    assert "tokenStore:" in source
    assert "enabled: false" in source
    assert "tokenStoreEnabled bool = false" in source
    assert "entraClientSecret string" not in source
