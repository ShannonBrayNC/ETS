from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-sharepoint-state-boundary-probe.yml"
).read_text(encoding="utf-8")
BICEP = (
    ROOT / "infra" / "azure" / "ets-live-sharepoint-state-probe.bicep"
).read_text(encoding="utf-8")


def test_state_probe_is_manual_protected_and_uses_existing_gateway_state() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "GATEWAY_APP: ets-o23bf2d6oq44s-gw" in WORKFLOW
    assert "CONNECTOR_INSTANCE_ID: m365-sharepoint-primary" in WORKFLOW
    assert "gatewayStateStorageName" in BICEP
    assert "storageType: 'AzureFile'" in BICEP
    assert "mountOptions: 'nobrl'" in BICEP
    assert "mountPath: '/mnt/gateway-state'" in BICEP


def test_state_probe_does_not_attach_gateway_runtime_identity_or_modify_state() -> None:
    assert "runtimeIdentityResourceId" not in BICEP
    assert "ManagedIdentityCredential" not in BICEP
    assert "mode=ro" in BICEP
    assert "PRAGMA query_only = ON" in BICEP
    assert "UPDATE connector_runtime" not in BICEP
    assert "INSERT INTO" not in BICEP
    assert "DELETE FROM" not in BICEP


def test_state_probe_reports_only_bounded_runtime_and_queue_state() -> None:
    for key in (
        "checkpoint_present",
        "checkpoint_revision",
        "checkpoint_kind",
        "retry_count",
        "observation_state",
        "gap_open",
        "local_event_count",
        "sharepoint_local_event_count",
        "marker_local_event_count",
        "queue_pending",
        "queue_retryable_failure",
        "queue_terminal_failure",
        "queue_synchronized",
        "marker_queue_synchronized",
    ):
        assert f'"{key}"' in BICEP
        assert f'"{key}",' in WORKFLOW


def test_state_probe_remains_public_safe_and_makes_no_qualification_claim() -> None:
    assert '"customer_identifiers_retained": False' in BICEP
    assert '"reusable_credential_retained": False' in BICEP
    assert '"public_evidence_safe": True' in BICEP
    assert '"m365_source_to_proof_claimed": False' in BICEP
    assert '"soak_clock_started": False' in BICEP
    assert "ETS_SP_STATE_PROBE_B64=" in BICEP
    assert "evidence/live-sharepoint-state-boundary/*.json" in WORKFLOW
