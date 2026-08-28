from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OBSERVATION = (
    ROOT
    / ".github"
    / "workflows"
    / "live-m365-soak-source-to-proof-observation.yml"
).read_text(encoding="utf-8")
SOAK = (
    ROOT / ".github" / "workflows" / "live-m365-source-to-proof-soak.yml"
).read_text(encoding="utf-8")
RUNNER = (
    ROOT / "scripts" / "azure" / "run-live-sharepoint-source-to-proof.sh"
).read_text(encoding="utf-8")
INVALIDATED_SOURCE = "9a4c3a8aefc50a960bdd3ce34b28f86fd69f1535"
INVALIDATED_DIGEST = (
    "sha256:e37f78a32dd995bcd73b1dfb4f3ae590bcc0694d8170f0a0a748d937be35fd63"
)


def test_silent_observation_is_manual_protected_and_rc1d_parameterized() -> None:
    assert "workflow_dispatch:" in OBSERVATION
    assert "schedule:" not in OBSERVATION
    assert "environment: ets-azure-q1" in OBSERVATION
    assert "id-token: write" in OBSERVATION
    assert "issues: write" not in OBSERVATION
    assert "image_source_sha:" in OBSERVATION
    assert "container_image:" in OBSERVATION
    assert "marker:" in OBSERVATION
    assert "IMAGE_SOURCE_SHA: ${{ inputs.image_source_sha }}" in OBSERVATION
    assert "CONTAINER_IMAGE: ${{ inputs.container_image }}" in OBSERVATION
    assert 'test "$IMAGE_SOURCE_SHA" = "$GITHUB_SHA"' in OBSERVATION
    assert "run-live-sharepoint-source-to-proof-diagnostic.sh" in OBSERVATION
    assert INVALIDATED_SOURCE not in OBSERVATION
    assert INVALIDATED_DIGEST not in OBSERVATION


def test_silent_observation_suppresses_only_issue_comment_publication() -> None:
    assert 'if [ "${1:-}" = "issue" ] && [ "${2:-}" = "comment" ]' in OBSERVATION
    assert 'exec "${ETS_REAL_GH:?}" "$@"' in OBSERVATION
    assert "HANDOFF_ISSUE: '541'" in OBSERVATION
    assert "SOURCE_TO_PROOF_ISSUE: '541'" in OBSERVATION
    assert "publish_handoff" in RUNNER
    assert "gh issue comment" in RUNNER


def test_silent_observation_reproves_full_revision_and_proof_contract() -> None:
    for predicate in (
        "gateway_health_verified",
        "gateway_readiness_verified",
        "graph_item_metadata_verified",
        "graph_scope_denial_403_verified",
        "delta_recovery_without_notification_verified",
        "exact_version_event_verified",
        "inclusion_proof_verified",
        "duplicate_suppression_verified",
        "durable_retention_verified",
        "revision_evidence_verified",
        "public_evidence_safe",
        "m365_source_to_proof_claimed",
    ):
        assert predicate in OBSERVATION
    assert '"ets.live_m365_soak.source_to_proof_observation.v2"' in OBSERVATION
    assert "core_observation_count" in OBSERVATION
    assert '"soak_clock_started": False' in OBSERVATION
    assert '"customer_identifiers_retained": False' in OBSERVATION
    assert '"reusable_credential_retained": False' in OBSERVATION


def test_soak_is_hourly_issue_backed_and_rc1d_gated() -> None:
    assert "workflow_dispatch:" in SOAK
    assert "schedule:" in SOAK
    assert "cron: '23 * * * *'" in SOAK
    assert "actions: write" in SOAK
    assert "issues: write" in SOAK
    assert "SOAK_ISSUE: '541'" in SOAK
    assert "ETS_MICROSOFT_P0_SOAK_STATE_B64=" in SOAK
    assert "rc1d_workflow_run_id:" in SOAK
    assert "START_72_HOUR_MICROSOFT_P0_SOAK" in SOAK
    assert "ets.live_microsoft.rc1d_pre_soak_candidate.v1" in SOAK
    assert '"pre_soak_reconciliation_passed"' in SOAK
    assert '"freeze_ready"' in SOAK
    assert '"candidate_frozen"' in SOAK
    assert '"soak_clock_started"' in SOAK
    assert "source_drift_after_freeze" in SOAK
    assert "prior_observation_run_failed" in SOAK
    assert "monitoring_gap_exceeded" in SOAK
    assert "governed_observation_failed" in SOAK
    assert "cancel-in-progress: false" in SOAK
    assert INVALIDATED_SOURCE not in SOAK
    assert INVALIDATED_DIGEST not in SOAK


def test_soak_observes_complete_bounded_microsoft_family() -> None:
    assert "live-m365-soak-source-to-proof-observation.yml" in SOAK
    assert "live-microsoft-rc1b-preflight.yml" in SOAK
    assert "live-microsoft-rc1c-preflight.yml" in SOAK
    assert "live-sharepoint-state-boundary-probe.yml" in SOAK
    assert "live-microsoft-rc1c-subscription-recovery.yml" not in SOAK
    assert '"rc1b_live_qualified"' in SOAK
    assert 'payload.get("purview_subscription_status") != "enabled"' in SOAK
    assert '"graph_subscription_operation_performed"' in SOAK
    assert '"public_gateway_callback_configured"' in SOAK
    assert '"graph_drive_subscriptions_deferred": True' in SOAK


def test_soak_preserves_exact_frozen_runtime_boundary() -> None:
    assert 'payload.get("candidate_source_sha")' in SOAK
    assert 'payload.get("candidate_image")' in SOAK
    assert 'payload.get("candidate_image_digest")' in SOAK
    assert 'current_sha != candidate["release_source_sha"]' in SOAK
    assert '"image_source_sha": source' in SOAK
    assert '"container_image": image' in SOAK
    assert 'payload.get("release_source_sha") != source' in SOAK
    assert 'payload.get("release_image_digest") != digest' in SOAK
    assert '"candidate_frozen": True' in SOAK


def test_soak_exit_gate_requires_time_count_and_monitoring_continuity() -> None:
    assert "MIN_SOAK_HOURS: '72'" in SOAK
    assert "MIN_SUCCESSFUL_OBSERVATIONS: '72'" in SOAK
    assert "MAX_GAP_MINUTES: '110'" in SOAK
    assert "elapsed_hours >= min_hours and success_count >= min_observations" in SOAK
    assert "gap_minutes > max_gap_minutes" in SOAK
    assert '"soak_clock_started": True' in SOAK
    assert '{"state": "closed", "state_reason": "completed"}' in SOAK


def test_soak_requires_healthy_durable_gateway_state() -> None:
    assert '"checkpoint_present"' in SOAK
    assert '"last_success_present"' in SOAK
    assert 'payload.get("observation_state") != "healthy_observation"' in SOAK
    assert '"gap_open"' in SOAK
    for queue_state in (
        "queue_pending",
        "queue_in_flight",
        "queue_retryable_failure",
        "queue_terminal_failure",
    ):
        assert queue_state in SOAK
    assert 'payload.get("customer_identifiers_retained")' in SOAK
    assert 'payload.get("reusable_credential_retained")' in SOAK
    assert 'payload.get("public_evidence_safe")' in SOAK
