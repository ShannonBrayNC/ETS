from __future__ import annotations

from pathlib import Path

BICEP = Path("infra/azure/ets-edge-virtual-demo-frontdoor.bicep")
DEPLOY_WORKFLOW = Path(".github/workflows/deploy-edge-dark-azure.yml")


def _text() -> str:
    return BICEP.read_text(encoding="utf-8")


def _deploy_text() -> str:
    return DEPLOY_WORKFLOW.read_text(encoding="utf-8")


def test_front_door_is_premium_https_only_and_private_linked() -> None:
    text = _text()

    assert "name: 'Premium_AzureFrontDoor'" in text
    assert "groupId: 'managedEnvironments'" in text
    assert "privateLink: {" in text
    assert "id: managedEnvironment.id" in text
    assert "status: 'Pending'" in text
    assert "enforceCertificateNameCheck: true" in text
    assert "forwardingProtocol: 'HttpsOnly'" in text
    assert "supportedProtocols: [\n      'Https'\n    ]" in text
    assert "linkToDefaultDomain: 'Disabled'" in text


def test_front_door_waf_is_prevention_with_current_managed_rules_and_rate_limit() -> None:
    text = _text()

    assert "Microsoft.Cdn/cdnWebApplicationFirewallPolicies@2025-12-01" in text
    assert "mode: 'Prevention'" in text
    assert "ruleSetType: 'Microsoft_DefaultRuleSet'" in text
    assert "ruleSetVersion: '2.2'" in text
    assert "ruleSetType: 'Microsoft_BotManagerRuleSet'" in text
    assert "ruleSetVersion: '1.1'" in text
    assert "rateLimitDurationInMinutes: 1" in text
    assert "rateLimitThreshold: rateLimitThreshold" in text
    assert "action: 'Block'" in text


def test_entra_auth_is_required_and_only_health_probe_is_anonymous() -> None:
    text = _text()

    assert "Microsoft.App/containerApps/authConfigs@2026-01-01" in text
    assert "enabled: true" in text
    assert "unauthenticatedClientAction: 'RedirectToLoginPage'" in text
    assert "redirectToProvider: 'azureactivedirectory'" in text
    assert "excludedPaths: [\n        '/afd-healthz'\n      ]" in text
    assert "requireHttps: true" in text
    assert "groups: operatorGroupObjectIds" in text
    assert "allowedGroups: operatorGroupObjectIds" in text
    assert "tokenStore: {\n        enabled: false" in text


def test_auth_template_accepts_secret_setting_name_but_never_secret_value() -> None:
    text = _text()

    assert "param entraClientSecretSettingName string" in text
    assert "clientSecretSettingName: entraClientSecretSettingName" in text
    forbidden_parameter_tokens = (
        "param clientSecret ",
        "param entraClientSecret ",
        "@secure()",
        "secureString",
        "secureObject",
    )
    for token in forbidden_parameter_tokens:
        assert token not in text


def test_custom_domain_uses_managed_certificate_and_strong_cipher_profile() -> None:
    text = _text()

    assert "customDomainHostName string = 'edge-demo.lanternprotocol.net'" in text
    assert "certificateType: 'ManagedCertificate'" in text
    assert "cipherSuiteSetType: 'TLS12_2023'" in text


def test_waf_is_bound_only_to_custom_demo_domain() -> None:
    text = _text()

    assert "type: 'WebApplicationFirewall'" in text
    assert "id: customDomain.id" in text
    assert "id: wafPolicy.id" in text
    assert "linkToDefaultDomain: 'Disabled'" in text


def test_deployment_uses_oidc_and_never_github_secret_values() -> None:
    text = _deploy_text()

    assert "id-token: write" in text
    assert "uses: azure/login@v2" in text
    assert "client-id: ${{ vars.AZURE_CLIENT_ID }}" in text
    assert "tenant-id: ${{ vars.AZURE_TENANT_ID }}" in text
    assert "subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}" in text
    assert "AZURE_CLIENT_SECRET" not in text
    assert "secrets." not in text


def test_public_edge_requires_exact_origin_names_and_azure_side_secret_presence() -> None:
    text = _deploy_text()

    assert "inputs.container_app_name" in text
    assert "inputs.managed_environment_name" in text
    assert "az containerapp show" in text
    assert "az containerapp env show" in text
    assert "publicNetworkAccess'] == 'Disabled'" in text
    assert "az containerapp secret list" in text
    assert "Secret value was not read" in text
    assert "contains(name" not in text


def test_private_link_approval_is_not_automated_by_deployment_workflow() -> None:
    text = _deploy_text()

    assert "privateLinkApprovalRequired" in text
    assert "Do not approve any unrelated private endpoint connection." in text
    assert "private-endpoint-connection approve" not in text
