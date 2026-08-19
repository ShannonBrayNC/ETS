from pathlib import Path


WORKFLOW = Path(
    ".github/workflows/live-gateway-authorization-qualification.yml"
).read_text(encoding="utf-8")
CLIENT_BICEP = Path(
    "infra/azure/ets-live-auth-qualification-client.bicep"
).read_text(encoding="utf-8")


def test_workflow_is_manual_and_protected() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "issues: write" in WORKFLOW
    assert "refs/heads/main" in WORKFLOW
    assert "ETS_Q1_BEARER_TOKEN" not in WORKFLOW


def test_exact_gateway_identity_is_the_positive_control() -> None:
    assert "GATEWAY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-id" in WORKFLOW
    assert "GATEWAY_IDENTITY_ID" in WORKFLOW
    assert "GATEWAY_CLIENT_ID" in WORKFLOW
    assert '"mode": {"value": "producer"}' in WORKFLOW
    assert "producer_role_present" in WORKFLOW
    assert "inclusion_proof_verified" in WORKFLOW


def test_negative_control_is_mapped_without_producer_role() -> None:
    assert "az identity create" in WORKFLOW
    assert "temporary[control]" in WORKFLOW
    assert '"mode": {"value": "denied"}' in WORKFLOW
    assert "negative_control_forbidden" in WORKFLOW
    assert "ETS_AUTH_FORBIDDEN" in WORKFLOW
    assert "negative-control token unexpectedly had evidence_producer" in WORKFLOW


def test_scope_map_and_ephemeral_identity_are_restored_fail_closed() -> None:
    assert "if: always()" in WORKFLOW
    assert 'ETS_AUTH_APP_SCOPE_MAP_JSON=$AUTH_APP_SCOPE_MAP_JSON' in WORKFLOW
    assert "live Core app scope map did not restore exactly" in WORKFLOW
    assert "restored Core scope map must contain exactly one client" in WORKFLOW
    assert "az identity delete" in WORKFLOW
    assert "ephemeral_control_identity_removed" in WORKFLOW


def test_public_handoff_does_not_claim_sharepoint_or_soak() -> None:
    assert '"runtime_health_claimed": False' in WORKFLOW
    assert '"m365_source_to_proof_claimed": False' in WORKFLOW
    assert '"soak_clock_started": False' in WORKFLOW
    assert '"customer_identifiers_retained": False' in WORKFLOW
    assert '"reusable_credential_retained": False' in WORKFLOW


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
