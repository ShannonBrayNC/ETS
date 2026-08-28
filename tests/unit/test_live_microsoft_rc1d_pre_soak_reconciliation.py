from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-microsoft-rc1d-pre-soak-reconciliation.yml"
).read_text(encoding="utf-8")
DOC = (
    ROOT / "docs" / "connectors" / "MICROSOFT_P0_RC1D_PRE_SOAK_RECONCILIATION_V1.md"
).read_text(encoding="utf-8")


def test_rc1d_reconciliation_is_manual_protected_and_exact_source_bound() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "schedule:" not in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "actions: read" in WORKFLOW
    assert "contents: read" in WORKFLOW
    assert "issues: write" in WORKFLOW
    assert 'test "$GITHUB_REF" = "refs/heads/main"' in WORKFLOW
    assert 'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"' in WORKFLOW
    assert 'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"' in WORKFLOW
    assert '"head_sha": os.environ["GITHUB_SHA"]' in WORKFLOW
    assert '"head_branch": "main"' in WORKFLOW
    assert '"conclusion": "success"' in WORKFLOW
    assert "cancel-in-progress: false" in WORKFLOW


def test_rc1d_requires_all_six_release_evidence_families() -> None:
    for name in (
        "q0_workflow_run_id:",
        "rc1b_workflow_run_id:",
        "rc1c_workflow_run_id:",
        "gateway_fault_stage_workflow_run_id:",
        "gateway_recovery_workflow_run_id:",
        "gateway_state_workflow_run_id:",
    ):
        assert name in WORKFLOW
    for workflow in (
        ".github/workflows/hosted-azure-q0-image.yml",
        ".github/workflows/live-microsoft-rc1b-preflight.yml",
        ".github/workflows/live-microsoft-rc1c-subscription-recovery.yml",
        ".github/workflows/live-sharepoint-relay-fault-stage.yml",
        ".github/workflows/live-sharepoint-relay-recovery.yml",
        ".github/workflows/live-sharepoint-state-boundary-probe.yml",
    ):
        assert workflow in WORKFLOW
    for artifact in (
        "host-az-q0-image-",
        "live-microsoft-rc1b-preflight-",
        "live-microsoft-rc1c-subscription-recovery-",
        "live-sharepoint-relay-fault-stage-",
        "live-sharepoint-relay-recovery-",
        "live-sharepoint-state-boundary-",
    ):
        assert artifact in WORKFLOW
    assert WORKFLOW.count("actions/download-artifact@v8.0.1") == 6


def test_rc1d_reconciliation_requires_supply_chain_and_live_qualification_predicates() -> None:
    for term in (
        '"ets.host_az.q0_image.v1"',
        '"vulnerability_gate") != "PASS"',
        '"sbom") != "sbom.spdx.json"',
        '"ets.live_microsoft.rc1b_preflight_handoff.v2"',
        '"rc1b_live_qualified"',
        '"entra_users_tombstone_verified"',
        '"onedrive_replay_idempotent"',
        '"evidence_loss_checkpoint_withheld"',
        '"ets.live_microsoft.rc1c_subscription_recovery_handoff.v2"',
        '"rc1c_live_qualified"',
        '"restart_state_recovered"',
        '"subscription_final_state") != "enabled"',
        '"ets.live_sharepoint.relay_fault_stage.v1"',
        '"stage_pass"',
        '"terminal_total_after") != 1',
        '"marker_terminal_after") != 1',
        '"ets.live_sharepoint.relay_recovery.v1"',
        '"recovery_pass"',
        '"queue_terminal_after") != 0',
        'recovery.get("marker_reconciled") != 1',
        '"ets.live_sharepoint.state_probe.v1"',
        '"checkpoint_kind") != "delta"',
        '"observation_state") != "healthy_observation"',
        'gateway.get("marker_queue_synchronized", 0) < 1',
        "baseline_state_run < fault_stage_run < recovery_run < state_run",
    ):
        assert term in WORKFLOW


def test_rc1d_preserves_graph_deferral_nonretention_and_no_soak_boundary() -> None:
    for term in (
        '"graph_permission_mutation_performed"',
        '"graph_subscription_operation_performed"',
        '"purview_webhook_configured"',
        '"customer_identifiers_retained"',
        '"reusable_credential_retained"',
        '"graph_drive_subscriptions_deferred": True',
        '"graph_subscription_configuration_absent": True',
        '"public_gateway_callback_configured": False',
        '"broader_graph_file_permission_claimed": False',
        '"candidate_frozen": False',
        '"soak_clock_started": False',
    ):
        assert term in WORKFLOW
    assert "Graph drive subscriptions" in DOC
    assert "freeze_ready=true" in DOC
    assert "candidate_frozen=false" in DOC
    assert "soak_clock_started=false" in DOC


def test_rc1d_success_manifest_is_freeze_ready_not_frozen() -> None:
    assert '"schema_version": "ets.live_microsoft.rc1d_pre_soak_candidate.v1"' in WORKFLOW
    assert '"gateway_fault_stage_verified": True' in WORKFLOW
    assert '"gateway_recovery_verified": True' in WORKFLOW
    assert '"gateway_durable_state_healthy": True' in WORKFLOW
    assert '"pre_soak_reconciliation_passed": True' in WORKFLOW
    assert '"freeze_ready": True' in WORKFLOW
    assert '"candidate_frozen": False' in WORKFLOW
    assert '"soak_clock_started": False' in WORKFLOW
    assert "Next protected action: freeze this exact source/image pair" in WORKFLOW
