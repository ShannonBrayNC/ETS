from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "live-sharepoint-relay-recovery.yml"
BICEP = ROOT / "infra" / "azure" / "ets-live-sharepoint-relay-recovery.bicep"


def test_recovery_workflow_is_manual_protected_and_evidence_bounded() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert 'test "$GITHUB_REF" = "refs/heads/main"' in text
    assert 'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"' in text
    assert "environment: ets-azure-q1" in text
    assert "live-sharepoint-relay-recovery-${{ github.run_id }}" in text
    assert 'queue_state_mutated"] is not True' in text
    assert 'connector_runtime_mutated"] is not True' in text
    assert 'core_state_mutated"] is not False' in text


def test_recovery_requires_matching_core_copy_before_queue_mutation() -> None:
    text = BICEP.read_text(encoding="utf-8")

    verify = text.index('counts["core_present_match"] != qualified_count')
    mutate = text.index("UPDATE sync_queue")
    assert verify < mutate
    assert 'not every terminal event has a matching immutable Core copy' in text
    assert "WHERE idempotency_key = ? AND state = 'terminal_failure'" in text
    assert '"status": "already_present"' in text
    assert 'canonical_json(acknowledgement)' in text


def test_recovery_clears_gap_only_after_queue_failures_are_gone() -> None:
    text = BICEP.read_text(encoding="utf-8")

    queue_check = text.index('queue failures remain after bounded terminal reconciliation')
    gap_update = text.index("SET observation_state = 'healthy_observation', gap_open = 0")
    assert queue_check < gap_update
    assert "connector lease is active; refusing concurrent recovery" in text
    assert "connector has no persisted checkpoint for recovery" in text
    assert "connector has no prior successful collection for recovery" in text


def test_recovery_keeps_runtime_identity_separate_from_registry_pull_identity() -> None:
    text = BICEP.read_text(encoding="utf-8")

    assert "identity: runtimeIdentityResourceId\n          lifecycle: 'Main'" in text
    assert "identity: registryPullIdentityResourceId\n          lifecycle: 'None'" in text
    assert '"core_state_mutated": False' in text
    assert '"queue_state_mutated": True' in text
    assert '"connector_runtime_mutated": True' in text
