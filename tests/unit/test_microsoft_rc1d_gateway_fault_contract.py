from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE_BICEP = (ROOT / "infra" / "azure" / "ets-live-sharepoint-state-probe.bicep").read_text(
    encoding="utf-8"
)
STATE_WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-sharepoint-state-boundary-probe.yml"
).read_text(encoding="utf-8")
FAULT_BICEP = (
    ROOT / "infra" / "azure" / "ets-live-sharepoint-relay-fault-stage.bicep"
).read_text(encoding="utf-8")
FAULT_WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-sharepoint-relay-fault-stage.yml"
).read_text(encoding="utf-8")
RECOVERY_WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-sharepoint-relay-recovery.yml"
).read_text(encoding="utf-8")
RC1D = (
    ROOT / ".github" / "workflows" / "live-microsoft-rc1d-pre-soak-reconciliation.yml"
).read_text(encoding="utf-8")
SEQUENCE = (
    ROOT / "docs" / "connectors" / "MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md"
).read_text(encoding="utf-8")


def test_state_probe_correlates_marker_by_immutable_event_id() -> None:
    assert "SELECT event_id, event_json FROM events" in STATE_BICEP
    assert 'marker_event_ids.add(str(row["event_id"]))' in STATE_BICEP
    assert "SELECT event_id, state FROM sync_queue" in STATE_BICEP
    assert 'str(row["event_id"]) in marker_event_ids' in STATE_BICEP
    assert 'marker in str(row["payload_json"])' not in STATE_BICEP


def test_state_probe_accepts_opaque_terminal_delta_but_not_page_cursor() -> None:
    assert 'if "$skiptoken=" in lowered or "%24skiptoken=" in lowered:' in STATE_BICEP
    assert 'return "page"' in STATE_BICEP
    assert 'return "delta"' in STATE_BICEP
    assert 'return "other"' not in STATE_BICEP


def test_green_state_probe_is_directly_rc1d_consumable() -> None:
    assert (
        'payload.get("schema_version") != "ets.live_sharepoint.state_probe.v1"'
        in STATE_WORKFLOW
    )
    assert 'payload.get("checkpoint_kind") != "delta"' in STATE_WORKFLOW
    assert 'payload.get("observation_state") != "healthy_observation"' in STATE_WORKFLOW
    assert 'payload.get("marker_local_event_count", 0) < 1' in STATE_WORKFLOW
    assert 'payload.get("marker_queue_synchronized", 0) < 1' in STATE_WORKFLOW
    for field in (
        "queue_pending",
        "queue_in_flight",
        "queue_retryable_failure",
        "queue_terminal_failure",
        "marker_queue_pending",
        "marker_queue_in_flight",
        "marker_queue_retryable_failure",
        "marker_queue_terminal_failure",
    ):
        assert f'"{field}"' in STATE_WORKFLOW
    assert "not RC1D-consumable" in STATE_WORKFLOW


def test_fault_stage_is_confirmation_gated_exact_candidate_mutation() -> None:
    assert "image_source_sha:" in FAULT_WORKFLOW
    assert "container_image:" in FAULT_WORKFLOW
    assert "baseline_state_workflow_run_id:" in FAULT_WORKFLOW
    assert "mutation_confirmation:" in FAULT_WORKFLOW
    assert "STAGE_BOUNDED_SHAREPOINT_RELAY_FAULT" in FAULT_WORKFLOW
    assert 'test "$IMAGE_SOURCE_SHA" = "$GITHUB_SHA"' in FAULT_WORKFLOW
    assert 'image != os.environ["CONTAINER_IMAGE"]' in FAULT_WORKFLOW
    assert (
        '"path": ".github/workflows/live-sharepoint-state-boundary-probe.yml"'
        in FAULT_WORKFLOW
    )
    assert (
        "live-sharepoint-state-boundary-"
        "${{ inputs.baseline_state_workflow_run_id }}" in FAULT_WORKFLOW
    )
    assert '"schema_version": "ets.live_sharepoint.relay_fault_stage.v1"' in FAULT_BICEP


def test_fault_stage_targets_only_a_synchronized_marker_with_core_copy() -> None:
    assert "marker_ids" in FAULT_BICEP
    assert "WHERE state = 'synchronized'" in FAULT_BICEP
    assert 'str(row["event_id"]) in marker_ids' in FAULT_BICEP
    assert 'existing.get("event_hash") == str(target["event_hash"])' in FAULT_BICEP
    assert "ETS_RC1D_SYNTHETIC_RELAY_FAULT" in FAULT_BICEP
    assert "SET state = 'terminal_failure'" in FAULT_BICEP
    assert "SET observation_state = 'collection_gap', gap_open = 1" in FAULT_BICEP
    assert '"terminal_total_after": terminal_after' in FAULT_BICEP
    assert '"marker_terminal_after": marker_terminal_after' in FAULT_BICEP
    assert '"core_state_mutated": False' in FAULT_BICEP
    assert '"event_identifiers_retained": False' in FAULT_BICEP
    assert '"event_hashes_retained": False' in FAULT_BICEP


def test_recovery_is_bound_to_exact_fault_stage_and_candidate() -> None:
    assert "fault_stage_workflow_run_id:" in RECOVERY_WORKFLOW
    assert "image_source_sha:" in RECOVERY_WORKFLOW
    assert "container_image:" in RECOVERY_WORKFLOW
    assert 'test "$IMAGE_SOURCE_SHA" = "$GITHUB_SHA"' in RECOVERY_WORKFLOW
    assert (
        '"path": ".github/workflows/live-sharepoint-relay-fault-stage.yml"'
        in RECOVERY_WORKFLOW
    )
    assert (
        "live-sharepoint-relay-fault-stage-"
        "${{ inputs.fault_stage_workflow_run_id }}" in RECOVERY_WORKFLOW
    )
    assert 'payload.get("terminal_total_after") != 1' in RECOVERY_WORKFLOW
    assert 'payload["terminal_total_before"] != 1' in RECOVERY_WORKFLOW
    assert 'payload["terminal_marker_count"] != 1' in RECOVERY_WORKFLOW
    assert (
        '"fault_stage_workflow_run_id": int(os.environ["FAULT_STAGE_RUN_ID"])'
        in RECOVERY_WORKFLOW
    )


def test_rc1d_requires_ordered_baseline_stage_recovery_post_state_chain() -> None:
    assert "gateway_fault_stage_workflow_run_id:" in RC1D
    assert "gateway_recovery_workflow_run_id:" in RC1D
    assert "gateway_state_workflow_run_id:" in RC1D
    assert "post-recovery hardened Gateway durable-state" in RC1D
    assert (
        'validate_run "$GATEWAY_FAULT_STAGE_RUN_ID" '
        '".github/workflows/live-sharepoint-relay-fault-stage.yml"' in RC1D
    )
    assert (
        "live-sharepoint-relay-fault-stage-"
        "${{ inputs.gateway_fault_stage_workflow_run_id }}" in RC1D
    )
    assert 'recovery.get("fault_stage_workflow_run_id") != fault_stage_run' in RC1D
    assert "baseline_state_run < fault_stage_run < recovery_run < state_run" in RC1D
    assert '"gateway_baseline_state_workflow_run_id": baseline_state_run' in RC1D
    assert '"gateway_fault_stage_workflow_run_id": fault_stage_run' in RC1D
    assert '"gateway_fault_stage_verified": True' in RC1D
    assert 'gateway.get("marker_queue_synchronized", 0) < 1' in RC1D


def test_release_sequence_places_fault_injection_before_freeze_and_soak() -> None:
    baseline = SEQUENCE.index("### 7.1 Healthy baseline state")
    stage = SEQUENCE.index("### 7.2 Bounded synthetic relay fault stage")
    recovery = SEQUENCE.index("### 7.3 Exact-stage relay/gap recovery")
    post_state = SEQUENCE.index("### 7.4 Post-recovery healthy state")
    rc1d = SEQUENCE.index("## 8. Reconcile RC1D")
    soak = SEQUENCE.index("## 9. Freeze and start the new governed 72-hour soak")
    assert baseline < stage < recovery < post_state < rc1d < soak
    assert "STAGE_BOUNDED_SHAREPOINT_RELAY_FAULT" in SEQUENCE
    assert "Fault injection is pre-soak only." in SEQUENCE
    assert (
        "never runs Purview subscription mutation/recovery or Gateway fault "
        "staging/recovery after freeze" in SEQUENCE
    )
