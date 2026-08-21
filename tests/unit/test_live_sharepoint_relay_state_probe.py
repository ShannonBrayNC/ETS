from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-sharepoint-relay-state-probe.yml"
).read_text(encoding="utf-8")
BICEP = (
    ROOT / "infra" / "azure" / "ets-live-sharepoint-relay-state-probe.bicep"
).read_text(encoding="utf-8")


def test_relay_probe_is_manual_protected_and_reuses_live_gateway_boundaries() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "GATEWAY_APP: ets-o23bf2d6oq44s-gw" in WORKFLOW
    assert "GATEWAY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-id" in WORKFLOW
    assert "gatewayStateStorageName" in BICEP
    assert "runtimeIdentityResourceId" in BICEP
    assert "registryPullIdentityResourceId" in BICEP
    assert "storageType: 'AzureFile'" in BICEP
    assert "mountPath: '/mnt/gateway-state'" in BICEP


def test_relay_probe_exposes_runtime_identity_to_main_container_only() -> None:
    runtime_identity = "identity: runtimeIdentityResourceId\n          lifecycle: 'Main'"
    pull_identity = "identity: registryPullIdentityResourceId\n          lifecycle: 'None'"
    assert runtime_identity in BICEP
    assert pull_identity in BICEP
    assert "ManagedIdentityCredential(client_id=client_id)" in BICEP


def test_relay_probe_reads_gateway_state_without_mutating_queue_or_core() -> None:
    assert "mode=ro" in BICEP
    assert "PRAGMA query_only = ON" in BICEP
    assert "method=\"GET\"" in BICEP
    assert '"queue_state_mutated": False' in BICEP
    assert '"core_state_mutated": False' in BICEP
    assert "UPDATE sync_queue" not in BICEP
    assert "INSERT INTO sync_queue" not in BICEP
    assert "DELETE FROM sync_queue" not in BICEP
    assert 'method="POST"' not in BICEP


def test_relay_probe_joins_terminal_queue_rows_to_local_immutable_events() -> None:
    for key in (
        "terminal_total",
        "terminal_sharepoint_count",
        "terminal_marker_count",
        "terminal_local_missing",
        "terminal_event_hash_mismatch",
        "terminal_tenant_mismatch",
        "terminal_workspace_mismatch",
        "terminal_local_invariants_ok",
        "core_present_match",
        "core_present_mismatch",
        "core_not_found",
        "core_auth_failure",
        "core_retryable_http",
        "core_other_http",
        "core_transport_error",
    ):
        assert f'"{key}"' in BICEP
        assert f'"{key}",' in WORKFLOW
    assert "SELECT event_id, event_json, event_hash FROM events" in BICEP
    assert "WHERE state = 'terminal_failure'" in BICEP


def test_relay_probe_retains_no_identifiers_payloads_or_credentials() -> None:
    assert '"customer_identifiers_retained": False' in BICEP
    assert '"event_identifiers_retained": False' in BICEP
    assert '"core_payload_retained": False' in BICEP
    assert '"reusable_credential_retained": False' in BICEP
    assert '"public_evidence_safe": True' in BICEP
    assert '"m365_source_to_proof_claimed": False' in BICEP
    assert '"soak_clock_started": False' in BICEP
    assert "ETS_SP_RELAY_STATE_PROBE_B64=" in BICEP
    assert "evidence/live-sharepoint-relay-state/*.json" in WORKFLOW
