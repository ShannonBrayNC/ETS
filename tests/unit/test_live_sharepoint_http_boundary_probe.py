from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-sharepoint-http-boundary-probe.yml"
).read_text(encoding="utf-8")
BICEP = (
    ROOT / "infra" / "azure" / "ets-live-sharepoint-http-probe.bicep"
).read_text(encoding="utf-8")


def test_probe_is_manual_protected_and_uses_live_gateway_identity() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "GATEWAY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-id" in WORKFLOW
    assert "ETS_LIVE_CORE_SCOPE" in WORKFLOW
    assert "ETS_LIVE_SHAREPOINT_DRIVE_ID" in WORKFLOW
    assert "runtimeIdentityResourceId" in BICEP
    assert "runtimeIdentityClientId" in BICEP
    assert "ManagedIdentityCredential" in BICEP


def test_probe_uses_deployed_gateway_bindings_instead_of_guessed_app_names() -> None:
    assert "CORE_APP:" not in WORKFLOW
    assert "ets-o23bf2d6oq44s-core" not in WORKFLOW
    assert "ETS_GATEWAY_CORE_BASE_URL" in WORKFLOW
    assert 'coreBaseUrl="$core_base_url"' in WORKFLOW
    assert 'gatewayBaseUrl="$gateway_base_url"' in WORKFLOW
    assert "properties.configuration.ingress.fqdn" in WORKFLOW
    assert 'case "$core_base_url" in' in WORKFLOW
    assert 'case "$gateway_base_url" in' in WORKFLOW
    assert "https://*" in WORKFLOW


def test_probe_is_metadata_only_and_public_safe() -> None:
    assert '"/content"' not in BICEP
    assert "@microsoft.graph.downloadUrl" not in BICEP
    assert '"gateway_health_status"' in BICEP
    assert '"gateway_ready_status"' in BICEP
    assert '"graph_item_status"' in BICEP
    assert '"graph_root_scope_status"' in BICEP
    assert '"core_events_status"' in BICEP
    assert '"customer_identifiers_retained": False' in BICEP
    assert '"reusable_credential_retained": False' in BICEP
    assert '"public_evidence_safe": True' in BICEP
    assert '"m365_source_to_proof_claimed": False' in BICEP
    assert '"soak_clock_started": False' in BICEP


def test_workflow_publishes_only_bounded_status_shape() -> None:
    assert "ETS_SP_HTTP_PROBE_B64=" in BICEP
    assert '"gateway_health_status",' in WORKFLOW
    assert '"gateway_ready_status",' in WORKFLOW
    assert '"graph_item_status",' in WORKFLOW
    assert '"graph_root_scope_status",' in WORKFLOW
    assert '"core_events_status",' in WORKFLOW
    assert "sharepoint-http-boundary.log" in WORKFLOW
    assert 'rm -f "$raw"' in WORKFLOW
    assert "evidence/live-sharepoint-http-boundary/*.json" in WORKFLOW
