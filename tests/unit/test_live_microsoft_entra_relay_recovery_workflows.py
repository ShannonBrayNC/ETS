from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPLAY_WORKFLOW = (
    ROOT
    / ".github"
    / "workflows"
    / "live-microsoft-entra-relay-replay-qualification.yml"
).read_text(encoding="utf-8")
RECOVERY_WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-microsoft-entra-relay-recovery.yml"
).read_text(encoding="utf-8")
REPLAY_BICEP = (
    ROOT
    / "infra"
    / "azure"
    / "ets-live-microsoft-entra-relay-replay-qualification.bicep"
).read_text(encoding="utf-8")
RECOVERY_BICEP = (
    ROOT / "infra" / "azure" / "ets-live-microsoft-entra-relay-recovery.bicep"
).read_text(encoding="utf-8")


def test_both_phases_are_manual_protected_and_exact_source_bound() -> None:
    for workflow in (REPLAY_WORKFLOW, RECOVERY_WORKFLOW):
        assert "workflow_dispatch:" in workflow
        assert "environment: ets-azure-q1" in workflow
        assert "id-token: write" in workflow
        assert "image_source_sha:" in workflow
        assert "container_image:" in workflow
        assert 'test "$GITHUB_REF" = "refs/heads/main"' in workflow
        assert 'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"' in workflow
        assert 'test "$GITHUB_SHA" = "$IMAGE_SOURCE_SHA"' in workflow
        assert 'test "$IMAGE" = "$CONTAINER_IMAGE"' in workflow
        assert 'containerImage="$CONTAINER_IMAGE"' in workflow


def test_replay_validates_exact_entra_events_before_core_mutation() -> None:
    assert "mode=ro" in REPLAY_BICEP
    assert "PRAGMA query_only = ON" in REPLAY_BICEP
    assert "WHERE state = 'terminal_failure'" in REPLAY_BICEP
    assert '"microsoft.entra.directory_delta"' in REPLAY_BICEP
    assert '"microsoft_entra_directory_metadata_v1"' in REPLAY_BICEP
    assert "EvidenceEvent.model_validate(event)" in REPLAY_BICEP
    assert "canonical_sha256(validated.hashable_payload())" in REPLAY_BICEP
    assert 'request_json(opener, token, "POST", "/api/v1/events", body)' in REPLAY_BICEP
    assert '"/api/v1/events/" + quote(event_id, safe="")' in REPLAY_BICEP
    assert "inclusion_proof_url" in REPLAY_BICEP
    assert 'counts["duplicate_reconciled"]' in REPLAY_BICEP
    assert 'counts["proof_endpoint_ok"] == counts["replay_accepted"]' in REPLAY_BICEP
    assert "UPDATE sync_queue" not in REPLAY_BICEP
    assert '"queue_state_mutated": False' in REPLAY_BICEP
    assert '"core_state_mutated": True' in REPLAY_BICEP


def test_recovery_only_mutates_queue_after_exact_core_reconciliation() -> None:
    verify = RECOVERY_BICEP.index('counts["core_present_match"] != qualified_count')
    mutate = RECOVERY_BICEP.index("UPDATE sync_queue")
    assert verify < mutate
    assert '"microsoft.entra.directory_delta"' in RECOVERY_BICEP
    assert '"microsoft_entra_directory_metadata_v1"' in RECOVERY_BICEP
    assert "EvidenceEvent.model_validate(event)" in RECOVERY_BICEP
    assert "canonical_sha256(validated.hashable_payload())" in RECOVERY_BICEP
    assert '"/api/v1/events/" + quote(event_id, safe="")' in RECOVERY_BICEP
    assert 'method="GET"' in RECOVERY_BICEP
    assert 'method="POST"' not in RECOVERY_BICEP
    assert 'connection.execute("BEGIN IMMEDIATE")' in RECOVERY_BICEP
    assert "WHERE idempotency_key = ? AND state = 'terminal_failure'" in RECOVERY_BICEP
    assert '"status": "already_present"' in RECOVERY_BICEP
    assert '"queue_state_mutated": True' in RECOVERY_BICEP
    assert '"connector_runtime_mutated": False' in RECOVERY_BICEP
    assert '"core_state_mutated": False' in RECOVERY_BICEP
    assert "connector-runtime.db" not in RECOVERY_BICEP
    assert "UPDATE connector_runtime" not in RECOVERY_BICEP


def test_public_evidence_shape_is_bounded_and_non_identifying() -> None:
    replay_counts = {
        "terminal_total",
        "terminal_entra_count",
        "terminal_profile_count",
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
    }
    recovery_counts = {
        "terminal_total_before",
        "terminal_entra_count",
        "terminal_profile_count",
        "terminal_local_invariants_ok",
        "terminal_local_invariant_failure",
        "core_present_match",
        "core_present_mismatch",
        "core_not_found",
        "core_auth_failure",
        "core_transport_error",
        "queue_reconciled",
        "queue_terminal_after",
        "queue_retryable_after",
        "queue_synchronized_after",
    }
    for key in replay_counts:
        assert f'"{key}"' in REPLAY_BICEP
        assert f'"{key}",' in REPLAY_WORKFLOW
    for key in recovery_counts:
        assert f'"{key}"' in RECOVERY_BICEP
        assert f'"{key}",' in RECOVERY_WORKFLOW

    for bicep in (REPLAY_BICEP, RECOVERY_BICEP):
        assert '"customer_identifiers_retained": False' in bicep
        assert '"event_identifiers_retained": False' in bicep
        assert '"event_hashes_retained": False' in bicep
        assert '"core_payload_retained": False' in bicep
        assert '"reusable_credential_retained": False' in bicep
        assert '"public_evidence_safe": True' in bicep
        assert '"m365_source_to_proof_claimed": False' in bicep
        assert '"soak_clock_started": False' in bicep

    assert "evidence/live-microsoft-entra-relay-replay/*.json" in REPLAY_WORKFLOW
    assert "evidence/live-microsoft-entra-relay-recovery/*.json" in RECOVERY_WORKFLOW
