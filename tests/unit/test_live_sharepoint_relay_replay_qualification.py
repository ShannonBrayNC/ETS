from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT
    / ".github"
    / "workflows"
    / "live-sharepoint-relay-replay-qualification.yml"
).read_text(encoding="utf-8")
BICEP = (
    ROOT
    / "infra"
    / "azure"
    / "ets-live-sharepoint-relay-replay-qualification.bicep"
).read_text(encoding="utf-8")


def test_replay_qualification_is_manual_and_protected() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "GATEWAY_APP: ets-o23bf2d6oq44s-gw" in WORKFLOW
    assert "GATEWAY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-id" in WORKFLOW
    assert "live-sharepoint-relay-replay-qualification.bicep" in WORKFLOW


def test_replay_qualification_reads_gateway_state_without_mutating_queue() -> None:
    assert "mode=ro" in BICEP
    assert "PRAGMA query_only = ON" in BICEP
    assert "WHERE state = 'terminal_failure'" in BICEP
    assert '"queue_state_mutated": False' in BICEP
    assert "UPDATE sync_queue" not in BICEP
    assert "INSERT INTO sync_queue" not in BICEP
    assert "DELETE FROM sync_queue" not in BICEP


def test_replay_qualification_uses_runtime_identity_only_in_main_container() -> None:
    runtime = """{
          identity: runtimeIdentityResourceId
          lifecycle: 'Main'
        }"""
    pull = """{
          identity: registryPullIdentityResourceId
          lifecycle: 'None'
        }"""
    assert runtime in BICEP
    assert pull in BICEP


def test_replay_qualification_proves_append_readback_duplicate_and_proof() -> None:
    assert 'request_json(opener, token, "POST", "/api/v1/events", body)' in BICEP
    assert '"/api/v1/events/" + quote(event_id, safe="")' in BICEP
    assert "inclusion_proof_url" in BICEP
    assert 'counts["duplicate_reconciled"]' in BICEP
    assert 'counts["core_readback_match"]' in BICEP
    assert 'counts["proof_endpoint_ok"]' in BICEP
    assert '"core_state_mutated": True' in BICEP


def test_replay_qualification_retains_only_bounded_public_counts() -> None:
    for key in (
        "terminal_total",
        "terminal_sharepoint_count",
        "terminal_marker_count",
        "terminal_local_invariants_ok",
        "terminal_local_invariant_failure",
        "replay_accepted",
        "replay_already_present",
        "replay_auth_failure",
        "replay_validation_failure",
        "replay_retryable_http",
        "replay_other_http",
        "replay_transport_error",
        "replay_ack_mismatch",
        "core_readback_match",
        "core_readback_mismatch",
        "duplicate_reconciled",
        "duplicate_unexpected",
        "proof_endpoint_ok",
        "proof_endpoint_failure",
        "marker_replayed",
    ):
        assert f'"{key}"' in BICEP
        assert f'"{key}",' in WORKFLOW

    assert '"customer_identifiers_retained": False' in BICEP
    assert '"event_identifiers_retained": False' in BICEP
    assert '"event_hashes_retained": False' in BICEP
    assert '"core_payload_retained": False' in BICEP
    assert '"reusable_credential_retained": False' in BICEP
    assert '"public_evidence_safe": True' in BICEP
    assert '"m365_source_to_proof_claimed": False' in BICEP
    assert '"soak_clock_started": False' in BICEP
    assert "ETS_SP_RELAY_REPLAY_B64=" in BICEP
    assert "evidence/live-sharepoint-relay-replay/*.json" in WORKFLOW
