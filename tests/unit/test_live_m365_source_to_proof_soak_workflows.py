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
APPROVED_SOURCE = "9a4c3a8aefc50a960bdd3ce34b28f86fd69f1535"
APPROVED_DIGEST = (
    "sha256:e37f78a32dd995bcd73b1dfb4f3ae590bcc0694d8170f0a0a748d937be35fd63"
)


def test_silent_observation_is_manual_protected_and_release_pinned() -> None:
    assert "workflow_dispatch:" in OBSERVATION
    assert "schedule:" not in OBSERVATION
    assert "environment: ets-azure-q1" in OBSERVATION
    assert "id-token: write" in OBSERVATION
    assert "issues: write" not in OBSERVATION
    assert APPROVED_SOURCE in OBSERVATION
    assert APPROVED_DIGEST in OBSERVATION
    assert "post458-release-sync-20260820" in OBSERVATION
    assert "EXPECTED_OBSERVATIONS: '2'" in OBSERVATION
    assert "run-live-sharepoint-source-to-proof-diagnostic.sh" in OBSERVATION


def test_silent_observation_suppresses_only_issue_comment_publication() -> None:
    assert 'if [ "${1:-}" = "issue" ] && [ "${2:-}" = "comment" ]' in OBSERVATION
    assert 'exec "${ETS_REAL_GH:?}" "$@"' in OBSERVATION
    assert "HANDOFF_ISSUE: '479'" in OBSERVATION
    assert "SOURCE_TO_PROOF_ISSUE: '479'" in OBSERVATION
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
    assert "core_observation_count" in OBSERVATION
    assert "< 2" in OBSERVATION
    assert '"soak_clock_started": False' in OBSERVATION
    assert '"customer_identifiers_retained": False' in OBSERVATION
    assert '"reusable_credential_retained": False' in OBSERVATION


def test_soak_is_hourly_issue_backed_and_fail_closed() -> None:
    assert "workflow_dispatch:" in SOAK
    assert "schedule:" in SOAK
    assert "cron: '23 * * * *'" in SOAK
    assert "actions: write" in SOAK
    assert "issues: write" in SOAK
    assert "SOAK_ISSUE: '479'" in SOAK
    assert "ETS_M365_SOAK_STATE_B64=" in SOAK
    assert "prior_observation_run_failed" in SOAK
    assert "monitoring_gap_exceeded" in SOAK
    assert "governed_observation_failed" in SOAK
    assert "manual_restart" in SOAK
    assert "cancel-in-progress: false" in SOAK


def test_soak_preserves_frozen_runtime_and_qualified_revision_boundary() -> None:
    assert APPROVED_SOURCE in SOAK
    assert APPROVED_DIGEST in SOAK
    assert "post458-release-sync-20260820" in SOAK
    assert "EXPECTED_OBSERVATIONS: '2'" in SOAK
    assert "live-m365-soak-source-to-proof-observation.yml" in SOAK
    assert "live-sharepoint-state-boundary-probe.yml" in SOAK
    assert 'payload.get("release_source_sha") != expected_source' in SOAK
    assert 'payload.get("release_image_digest") != expected_digest' in SOAK
    assert 'payload.get("expected_observations") != expected_observations' in SOAK


def test_soak_exit_gate_requires_time_count_and_monitoring_continuity() -> None:
    assert "MIN_SOAK_HOURS: '72'" in SOAK
    assert "MIN_SUCCESSFUL_OBSERVATIONS: '72'" in SOAK
    assert "MAX_GAP_MINUTES: '110'" in SOAK
    assert "elapsed_hours >= min_hours and success_count >= min_observations" in SOAK
    assert "gap_minutes > max_gap_minutes" in SOAK
    assert '"soak_clock_started": True' in SOAK
    assert '"state": "closed", "state_reason": "completed"' in SOAK


def test_soak_requires_healthy_durable_gateway_state() -> None:
    assert 'payload.get("checkpoint_present") is not True' in SOAK
    assert 'payload.get("last_success_present") is not True' in SOAK
    assert 'payload.get("observation_state") != "healthy_observation"' in SOAK
    assert 'payload.get("gap_open") is not False' in SOAK
    for queue_state in (
        "queue_pending",
        "queue_in_flight",
        "queue_retryable_failure",
        "queue_terminal_failure",
    ):
        assert queue_state in SOAK
    assert "queue_synchronized" in SOAK
    assert "sharepoint_local_event_count" in SOAK
    assert "< 4" in SOAK
    assert 'payload.get("customer_identifiers_retained") is not False' in SOAK
    assert 'payload.get("reusable_credential_retained") is not False' in SOAK
    assert 'payload.get("public_evidence_safe") is not True' in SOAK
