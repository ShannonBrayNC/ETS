from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-gateway-authorization-qualification.yml"
).read_text(encoding="utf-8")
RUNNER = (
    ROOT / "scripts" / "azure" / "run-live-gateway-authorization-qualification.sh"
).read_text(encoding="utf-8")
DIAGNOSTIC = (
    ROOT
    / "scripts"
    / "azure"
    / "run-live-gateway-authorization-qualification-diagnostic.sh"
).read_text(encoding="utf-8")
CLIENT_BICEP = (
    ROOT / "infra" / "azure" / "ets-live-auth-qualification-client.bicep"
).read_text(encoding="utf-8")


def test_workflow_is_manual_and_protected() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "issues: write" in WORKFLOW
    assert "refs/heads/main" in WORKFLOW
    assert "ETS_Q1_BEARER_TOKEN" not in WORKFLOW
    assert "run-live-gateway-authorization-qualification-diagnostic.sh" in WORKFLOW


def test_exact_gateway_identity_is_the_positive_control() -> None:
    assert "GATEWAY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-id" in WORKFLOW
    assert '"producer"' in RUNNER
    assert "GATEWAY_IDENTITY_ID" in RUNNER
    assert "GATEWAY_CLIENT_ID" in RUNNER
    assert "producer_role_present" in RUNNER
    assert "inclusion_proof_verified" in RUNNER


def test_negative_control_is_mapped_without_producer_role() -> None:
    assert "az identity create" in RUNNER
    assert "temporary[control] = {" in RUNNER
    assert '"denied"' in RUNNER
    assert "negative_control_forbidden" in RUNNER
    assert "ETS_AUTH_FORBIDDEN" in CLIENT_BICEP
    assert "negative-control token unexpectedly had evidence_producer" in RUNNER


def test_scope_map_and_ephemeral_identity_are_restored_fail_closed() -> None:
    assert "trap on_exit EXIT" in RUNNER
    assert "SCOPE_MAP_MUTATED=0" in RUNNER
    assert "restore_scope_map" in RUNNER
    assert 'ETS_AUTH_APP_SCOPE_MAP_JSON=$AUTH_APP_SCOPE_MAP_JSON' in RUNNER
    assert "live Core app scope map did not restore exactly" in RUNNER
    assert "restored Core scope map must contain exactly one client" in RUNNER
    assert "az identity delete" in RUNNER
    assert "cleanup_stale_jobs" in RUNNER
    assert "ets-authp-" in RUNNER
    assert "ets-authn-" in RUNNER


def test_failure_diagnostics_are_sanitized_and_bounded() -> None:
    for failure_class in (
        "core_unreachable",
        "core_not_ready",
        "managed_identity_token_acquisition",
        "managed_identity_audience_mismatch",
        "producer_role_mismatch",
        "inclusion_proof_verification_failed",
    ):
        assert failure_class in RUNNER
    assert '"customer_identifiers_retained": False' in RUNNER
    assert '"reusable_credential_retained": False' in RUNNER
    assert '"public_evidence_safe": True' in RUNNER
    assert "evidence/live-gateway-authorization/*.json" in WORKFLOW
    assert "live-auth-producer.log" not in WORKFLOW


def test_diagnostic_wrapper_retries_private_logs_and_never_publishes_them() -> None:
    assert "containerapp job logs show" in DIAGNOSTIC
    assert "for _ in $(seq 1 12)" in DIAGNOSTIC
    assert "ETS_AUTH_DIAGNOSTIC_RAW" in DIAGNOSTIC
    assert "qualification_log_unavailable" in DIAGNOSTIC
    assert "qualification_json_decode_failed" in DIAGNOSTIC
    assert "inclusion_proof_verifier_exception" in DIAGNOSTIC
    assert 'payload["customer_identifiers_retained"] = False' in DIAGNOSTIC
    assert 'payload["reusable_credential_retained"] = False' in DIAGNOSTIC
    assert 'payload["public_evidence_safe"] = True' in DIAGNOSTIC
    assert 'rm -f "$PRIVATE_RAW"' in DIAGNOSTIC
    assert "PRIVATE_RAW" not in WORKFLOW


def test_public_handoff_does_not_claim_sharepoint_or_soak() -> None:
    assert '"runtime_health_claimed": False' in RUNNER
    assert '"m365_source_to_proof_claimed": False' in RUNNER
    assert '"soak_clock_started": False' in RUNNER
    assert '"customer_identifiers_retained": False' in RUNNER
    assert '"reusable_credential_retained": False' in RUNNER


def test_qualification_job_separates_runtime_and_pull_identity() -> None:
    assert "runtimeIdentityResourceId" in CLIENT_BICEP
    assert "registryPullIdentityResourceId" in CLIENT_BICEP
    assert "lifecycle: 'Main'" in CLIENT_BICEP
    assert "lifecycle: 'None'" in CLIENT_BICEP
    assert "ManagedIdentityCredential" in CLIENT_BICEP
    assert "claims.get(\"idtyp\") != \"app\"" in CLIENT_BICEP
    assert "roles != [\"evidence_producer\"]" in CLIENT_BICEP
    assert 'expected=(403,)' in CLIENT_BICEP
    assert "verify_inclusion_proof" in CLIENT_BICEP
