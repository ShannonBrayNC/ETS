from __future__ import annotations

from pathlib import Path

ADR = Path("docs/adr/ADR-009-microsoft-graph-drive-subscription-p0.md")
COMPOSITION = Path("docs/connectors/MICROSOFT_P0_GRAPH_LIFECYCLE_COMPOSITION_V1.md")
PRE_SOAK = Path("docs/connectors/MICROSOFT_P0_PRE_SOAK_GATE_V1.md")
ROLE_BOOTSTRAP = Path("scripts/azure/provision-microsoft-p0-connector-app-roles.ps1")
GATEWAY_BICEP = Path("infra/azure/ets-gateway.bicep")
RC1C_WORKFLOW = Path(".github/workflows/live-microsoft-rc1c-preflight.yml")
RC1C_JOB = Path("infra/azure/ets-live-microsoft-rc1c-preflight.bicep")


def test_graph_drive_subscription_decision_is_accepted_and_governance_is_reconciled() -> None:
    decision = ADR.read_text(encoding="utf-8")
    pre_soak = PRE_SOAK.read_text(encoding="utf-8")
    assert "Status: Accepted" in decision
    assert "Accepted through: #552" in decision
    assert "LanternProtocol supplied the" in decision
    assert "independent approval" in decision
    assert "issue contracts were reconciled" in pre_soak
    assert "pre-soak gate" in pre_soak
    assert "remains blocked" in pre_soak


def test_decision_records_current_permissions_and_private_delivery_option() -> None:
    decision = ADR.read_text(encoding="utf-8")
    composition = COMPOSITION.read_text(encoding="utf-8")
    for value in (
        "Files.Read.All",
        "Files.ReadWrite.All",
        "Sites.Selected",
        "Azure Event Hubs",
        "Microsoft Entra RBAC",
        "Microsoft Graph Change Tracking",
    ):
        assert value in decision
    assert "does not reduce the Microsoft Graph resource permission" in decision
    assert "does not reduce the drive subscription permission" in composition
    assert "change-notifications-delivery-event-hubs" in decision
    assert "subscription-post-subscriptions" in decision
    assert "subscription-list" in decision


def test_p0_role_bootstrap_does_not_widen_graph_file_authority() -> None:
    source = ROLE_BOOTSTRAP.read_text(encoding="utf-8")
    assert "$directoryRoleValues = @('User.Read.All', 'Group.Read.All')" in source
    assert "$purviewRoleValues = @('ActivityFeed.Read')" in source
    for forbidden in (
        "Files.Read.All",
        "Files.ReadWrite.All",
        "Sites.Read.All",
        "Subscription.Read.All",
    ):
        assert forbidden not in source


def test_graph_lifecycle_and_public_ingress_remain_disabled_by_default() -> None:
    bicep = GATEWAY_BICEP.read_text(encoding="utf-8")
    workflow = RC1C_WORKFLOW.read_text(encoding="utf-8")
    job = RC1C_JOB.read_text(encoding="utf-8")
    assert "param graphNotificationUrl string = ''" in bicep
    assert "param graphClientState string = ''" in bicep
    assert "external: false" in bicep
    assert (
        "Graph lifecycle configuration is present before permission and ingress approval"
        in workflow
    )
    assert "graph_subscription_permission_decision_pending" not in workflow
    assert '"graph_subscription_scope_decision": "deferred_from_p0"' in workflow
    assert '"graph_subscription_scope_decision_record": "ADR-009"' in workflow
    assert '"graph_subscription_deferred_from_p0": True' in workflow
    assert '"graph_future_delivery_profile": "azure_event_hubs_entra_rbac"' in workflow
    assert '"graph_permission_mutation_performed": False' in workflow
    assert '"graph_subscription_operation_performed": False' in workflow
    assert '"graph_callback_ingress_external": False' in workflow
    assert "durable Graph subscription state exists before callback authorization" in job


def test_future_delivery_candidate_rejects_secret_and_public_callback_fallbacks() -> None:
    decision = ADR.read_text(encoding="utf-8")
    assert "SAS/connection-string delivery is not an acceptable production fallback" in decision
    assert "no SAS, connection string, client secret, or public Gateway ingress" in decision
    assert "must not silently fall back to a public unauthenticated webhook" in decision
