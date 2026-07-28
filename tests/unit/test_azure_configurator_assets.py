from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "azure" / "Invoke-EtsAzureConfigurator.ps1"
MAIN = ROOT / "infra" / "azure" / "configurator" / "main.bicep"
MODULE = ROOT / "infra" / "azure" / "configurator" / "modules" / "application.bicep"


def test_azure_configurator_assets_exist_and_are_nonempty() -> None:
    for path in (SCRIPT, MAIN, MODULE):
        assert path.is_file(), f"Missing required Azure configurator asset: {path}"
        assert path.stat().st_size > 100, f"Azure configurator asset is unexpectedly empty: {path}"


def test_configurator_supports_safe_plan_and_upgrade_modes() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "'Connect', 'Plan', 'Deploy', 'Upgrade', 'Validate'" in text
    assert "deployment', 'sub', $Command" in text
    assert "what-if" in text
    assert "ShouldProcess" in text
    assert "Upgrade mode requires -Tier standard" in text


def test_configurator_requires_tenant_aware_login_and_subscription_selection() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--tenant" in text
    assert "account', 'list'" in text
    assert "account set --subscription" in text
    assert "tenantId" in text
    assert "subscriptionId" in text


def test_free_tier_is_explicit_and_upgradable() -> None:
    main = MAIN.read_text(encoding="utf-8")
    module = MODULE.read_text(encoding="utf-8")
    assert "'free'" in main
    assert "'standard'" in main
    assert "staticWebAppSku = tier == 'free' ? 'Free' : 'Standard'" in main
    assert "name: 'Y1'" in module
    assert "tier: 'Dynamic'" in module
    assert "upgradeCommand" in main


def test_baseline_security_controls_are_present() -> None:
    module = MODULE.read_text(encoding="utf-8")
    for expected in (
        "allowBlobPublicAccess: false",
        "supportsHttpsTrafficOnly: true",
        "minimumTlsVersion: 'TLS1_2'",
        "ftpsState: 'Disabled'",
        "httpsOnly: true",
        "type: 'SystemAssigned'",
    ):
        assert expected in module
