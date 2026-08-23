from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github" / "workflows" / "live-microsoft-rc1b-preflight.yml").read_text(
    encoding="utf-8"
)
BICEP = (ROOT / "infra" / "azure" / "ets-live-microsoft-rc1b-preflight.bicep").read_text(
    encoding="utf-8"
)
DOC = (ROOT / "docs" / "connectors" / "MICROSOFT_P0_RC1B_LIVE_PREFLIGHT_V1.md").read_text(
    encoding="utf-8"
)
BICEP_WORKFLOW = (ROOT / ".github" / "workflows" / "hosted-azure-bicep.yml").read_text(
    encoding="utf-8"
)


def test_rc1b_preflight_is_manual_protected_and_exact_source_pinned() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "schedule:" not in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "issues: write" in WORKFLOW
    assert 'test "$GITHUB_REF" = "refs/heads/main"' in WORKFLOW
    assert 'test "$IMAGE_SOURCE_SHA" = "$GITHUB_SHA"' in WORKFLOW
    assert "registry/repository@sha256:<digest>" in WORKFLOW
    assert "RESULT_ISSUE: '540'" in WORKFLOW


def test_rc1b_preflight_requires_exact_private_runtime_and_identity_set() -> None:
    for term in (
        "expected exactly one deployment-authoritative Microsoft Gateway",
        "live Microsoft Gateway ingress must remain internal",
        "live Microsoft Gateway must remain single replica",
        "live Microsoft Gateway image differs from the approved digest",
        "live Microsoft Gateway must attach exactly four user-assigned identities",
        "live Microsoft runtime identity client IDs are not distinct",
        "live Microsoft identity assignment set contains drift",
    ):
        assert term in WORKFLOW
    assert "ETS_GATEWAY_DIRECTORY_MANAGED_IDENTITY_CLIENT_ID" in WORKFLOW
    assert "ETS_GATEWAY_PURVIEW_MANAGED_IDENTITY_CLIENT_ID" in WORKFLOW
    assert "ETS_GATEWAY_MICROSOFT_APPLICATION_ID" in WORKFLOW


def test_rc1b_job_attaches_only_directory_runtime_and_pull_identities() -> None:
    assert "'${registryPullIdentityResourceId}': {}" in BICEP
    assert "'${directoryIdentityResourceId}': {}" in BICEP
    assert "identity: registryPullIdentityResourceId\n          lifecycle: 'None'" in BICEP
    assert "identity: directoryIdentityResourceId\n          lifecycle: 'Main'" in BICEP
    assert "sharePointIdentityResourceId" not in BICEP
    assert "purviewIdentityResourceId" not in BICEP
    assert "ManagedIdentityCredential(client_id=DIRECTORY_CLIENT_ID)" in BICEP


def test_rc1b_graph_preflight_is_bounded_read_only_and_proves_denial() -> None:
    assert '"/v1.0/users/delta?$select=id&$top=1"' in BICEP
    assert '"/v1.0/groups/delta?$select=id&$top=1"' in BICEP
    assert 'method="GET"' in BICEP
    assert "if drive_status != 403:" in BICEP
    assert "directory identity was not denied access to the SharePoint drive" in BICEP
    assert "MAXIMUM_RESPONSE_BYTES = 2 * 1024 * 1024" in BICEP
    assert "Microsoft Graph delta continuation escaped the qualified boundary" in BICEP


def test_rc1b_preflight_requires_stable_durable_state_and_core_sync() -> None:
    for term in (
        'connect_ro("connector-runtime.db")',
        'connect_ro("gateway-events.db")',
        'connect_ro("gateway-sync.db")',
        'item["checkpoint_kind"] == "delta"',
        'item["retry_count"] == 0',
        'item["observation_state"] == "healthy_observation"',
        'not item["gap_open"]',
        'not item["lease_active"]',
        'event_state["users"]["observed"]',
        'event_state["groups"]["observed"]',
        'item["synchronized"] and item["clean"]',
    ):
        assert term in BICEP


def test_rc1b_evidence_is_sanitized_and_does_not_widen_claims() -> None:
    for term in (
        '"raw_directory_payload_retained": False',
        '"customer_identifiers_retained": False',
        '"reusable_credential_retained": False',
        '"public_evidence_safe": True',
        '"rc1b_live_qualified": False',
        '"soak_clock_started": False',
    ):
        assert term in BICEP
    for key in (
        "raw_directory_payload_retained",
        "customer_identifiers_retained",
        "reusable_credential_retained",
        "rc1b_live_qualified",
        "soak_clock_started",
    ):
        assert f'"{key}"' in WORKFLOW
    assert "tombstone/replay/throttle/recovery gates remain" in WORKFLOW
    assert "No live preflight is performed merely by merging these assets." in DOC
    assert "Passing it is not completion of #540" in DOC
    assert "Microsoft source truth or universal tenant completeness" in DOC


def test_hosted_bicep_gate_compiles_rc1b_preflight_template() -> None:
    command = "az bicep build --file infra/azure/ets-live-microsoft-rc1b-preflight.bicep --stdout"
    assert command in BICEP_WORKFLOW
