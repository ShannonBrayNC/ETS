from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-sharepoint-source-to-proof.yml"
).read_text(encoding="utf-8")
RUNNER = (
    ROOT / "scripts" / "azure" / "run-live-sharepoint-source-to-proof.sh"
).read_text(encoding="utf-8")
CLIENT = (
    ROOT / "infra" / "azure" / "ets-live-sharepoint-source-proof-client.bicep"
).read_text(encoding="utf-8")
OPERATOR = (
    ROOT / "scripts" / "m365" / "create-echomedia-sharepoint-qualification-document.ps1"
).read_text(encoding="utf-8")
PROVISIONER = (
    ROOT / "scripts" / "m365" / "provision-echomedia-sharepoint-connector.ps1"
).read_text(encoding="utf-8")
APPROVED_DIGEST = (
    "sha256:c83a8cb0729d7e00506e4b7b9f0d0e5a7c5bbe3829abad76113ba7fd1ee3424c"
)


def test_workflow_is_manual_protected_and_pins_live_release() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "issues: write" in WORKFLOW
    assert "refs/heads/main" in RUNNER
    assert "GATEWAY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-id" in WORKFLOW
    assert APPROVED_DIGEST in WORKFLOW
    assert "ETS_LIVE_CORE_SCOPE" in WORKFLOW
    assert "ETS_LIVE_SHAREPOINT_DRIVE_ID" in WORKFLOW
    assert "ETS_Q1_BEARER_TOKEN" not in WORKFLOW


def test_verifier_cannot_bypass_gateway_or_download_document_content() -> None:
    assert 'core_base + "/api/v1/events?limit=500&offset="' in CLIENT
    assert 'core_base + "/api/v1/proofs/inclusion/"' in CLIENT
    assert 'request_json("POST", core_base + "/api/v1/events"' not in CLIENT
    assert '"/content"' not in CLIENT
    assert "@microsoft.graph.downloadUrl" in CLIENT
    assert '"raw_document_content_retrieved": False' in CLIENT
    assert '"raw_source_payload_retained": False' in CLIENT


def test_verifier_uses_exact_gateway_uami_and_proves_site_scope_denial() -> None:
    assert "runtimeIdentityResourceId" in CLIENT
    assert "runtimeIdentityClientId" in CLIENT
    assert "registryPullIdentityResourceId" in CLIENT
    assert "lifecycle: 'Main'" in CLIENT
    assert "lifecycle: 'None'" in CLIENT
    assert "ManagedIdentityCredential" in CLIENT
    assert 'GRAPH_SCOPE = "https://graph.microsoft.com/.default"' in CLIENT
    assert '"https://graph.microsoft.com/v1.0/sites/root?$select=id"' in CLIENT
    assert "expected=(403,)" in CLIENT
    assert '"graph_scope_denial_403_verified": True' in CLIENT


def test_verifier_requires_real_sharepoint_gateway_evidence_and_proofs() -> None:
    assert 'SOURCE_SYSTEM = "microsoft.sharepoint.onedrive_delta"' in CLIENT
    assert 'EVENT_TYPE = "microsoft.sharepoint.metadata.observed"' in CLIENT
    assert 'capture.get("raw_source_payload_retained") is not False' in CLIENT
    assert 'privacy.get("contains_raw_evidence") is not False' in CLIENT
    assert 'evidence_reference.get("retention_mode") != "not_retained"' in CLIENT
    assert "InclusionProof.model_validate_json" in CLIENT
    assert "verify_inclusion_proof" in CLIENT
    assert '"delta_recovery_without_notification_verified": True' in CLIENT
    assert '"duplicate_suppression_verified": True' in CLIENT
    assert '"durable_retention_verified": True' in CLIENT
    assert "time.sleep(75)" in CLIENT


def test_revision_evidence_requires_distinct_source_etags() -> None:
    assert "all_etags = {etag for _, etag in observations}" in CLIENT
    assert "len(all_etags) < expected" in CLIENT
    assert (
        '"revision_evidence_verified": expected >= 2 and len(all_etags) >= expected'
        in CLIENT
    )
    assert (
        'expected >= 2 and result.get("revision_evidence_verified") is not True'
        in RUNNER
    )


def test_runner_resolves_existing_private_runtime_and_cleans_ephemeral_job() -> None:
    assert "expected exactly one live Core and one SharePoint Gateway" in RUNNER
    assert "Core and Gateway are not in the same managed environment" in RUNNER
    assert "deployed Gateway SharePoint drive differs from the protected contract" in RUNNER
    assert "Gateway runtime client ID differs from the exact Gateway UAMI" in RUNNER
    assert "Gateway registry identity must remain pull-only and distinct" in RUNNER
    assert 'export MANAGED_ENVIRONMENT_NAME="$MANAGED_ENVIRONMENT_NAME"' in RUNNER
    assert 'os.environ["MANAGED_ENVIRONMENT_NAME"]' in RUNNER
    assert "trap cleanup EXIT" in RUNNER
    assert "az containerapp job delete" in RUNNER
    assert "ets-spq-" in RUNNER


def test_public_evidence_is_sanitized_and_does_not_start_soak() -> None:
    assert '"m365_source_to_proof_claimed": True' in RUNNER
    assert '"full_microsoft_runtime_health_claimed": False' in RUNNER
    assert '"customer_identifiers_retained": False' in RUNNER
    assert '"reusable_credential_retained": False' in RUNNER
    assert '"public_evidence_safe": True' in RUNNER
    assert '"soak_clock_started": False' in RUNNER
    assert "evidence/live-sharepoint-source-to-proof/*.json" in WORKFLOW
    assert "live-sharepoint-source-to-proof.log" not in WORKFLOW


def test_operator_uses_delegated_write_only_for_synthetic_file() -> None:
    assert "Sites.ReadWrite.All" in OPERATOR
    assert "SharePointHostname" in OPERATOR
    assert "'/sites/ETS'" in OPERATOR
    assert '"ets-live-qualification-$Marker.txt"' in OPERATOR
    assert "customer_content=false" in OPERATOR
    assert '"$encodedName`:/content"' in OPERATOR
    assert "InputFilePath" in OPERATOR
    assert "sharePointMetadataVerified = $true" in OPERATOR
    assert "rawCustomerContentUsed = $false" in OPERATOR
    assert "live-sharepoint-source-to-proof.yml" in OPERATOR
    assert '"expected_observations=$Revision"' in OPERATOR


def test_echo_media_delegated_operator_is_pinned_in_both_m365_scripts() -> None:
    expected = "shannon.bray@echomedia.ai"
    for script in (OPERATOR, PROVISIONER):
        assert expected in script
        assert "$context.Account -ine $ExpectedOperatorAccount" in script
        assert "operatorAccountVerified = $true" in script


def test_operator_discovers_exact_documents_drive_when_drive_id_is_omitted() -> None:
    assert "[string]$DriveId = ''" in OPERATOR
    assert "[string]::IsNullOrWhiteSpace($DriveId)" in OPERATOR
    assert "$_.name -eq 'Documents'" in OPERATOR
    assert "The ETS Documents library could not be resolved uniquely." in OPERATOR
    assert "$resolvedDriveId = [string]$approvedDrive[0].id" in OPERATOR
    assert "documentsDriveResolved = $true" in OPERATOR
