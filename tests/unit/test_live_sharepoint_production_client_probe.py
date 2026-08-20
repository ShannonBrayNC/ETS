from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (
    ROOT / ".github" / "workflows" / "live-sharepoint-production-client-probe.yml"
).read_text(encoding="utf-8")
BICEP = (
    ROOT / "infra" / "azure" / "ets-live-sharepoint-production-client-probe.bicep"
).read_text(encoding="utf-8")


def test_probe_is_manual_protected_and_uses_exact_gateway_uami() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    assert "environment: ets-azure-q1" in WORKFLOW
    assert "id-token: write" in WORKFLOW
    assert "GATEWAY_IDENTITY_NAME: ets-o23bf2d6oq44s-gw-id" in WORKFLOW
    assert "runtimeIdentityResourceId" in BICEP
    assert "runtimeIdentityClientId" in BICEP
    assert "ManagedIdentityCredential" in BICEP


def test_probe_executes_exact_production_delta_client() -> None:
    assert "MicrosoftSharePointDeltaHttpClient" in BICEP
    assert "MicrosoftSharePointDeltaRequestProfile" in BICEP
    assert "client.fetch()" in BICEP
    assert "MicrosoftSharePointDeltaRedirectError" in BICEP
    assert "MicrosoftSharePointDeltaResponseTooLargeError" in BICEP
    assert "MicrosoftSharePointDeltaRetryableError" in BICEP
    assert "MicrosoftSharePointDeltaTerminalError" in BICEP
    assert 'maximum_response_bytes=1024 * 1024' in BICEP


def test_probe_retains_only_bounded_classification() -> None:
    assert '"production_client_outcome"' in BICEP
    assert '"parser_failure_class"' in BICEP
    assert '"record_count"' in BICEP
    assert '"cycle_complete"' in BICEP
    assert '"checkpoint_shape"' in BICEP
    assert '"customer_identifiers_retained": False' in BICEP
    assert '"graph_payload_retained": False' in BICEP
    assert '"continuation_url_retained": False' in BICEP
    assert '"reusable_credential_retained": False' in BICEP
    assert '"public_evidence_safe": True' in BICEP
    assert '"m365_source_to_proof_claimed": False' in BICEP
    assert '"soak_clock_started": False' in BICEP
    assert '"/content"' not in BICEP
    assert "@microsoft.graph.downloadUrl" not in BICEP


def test_workflow_uploads_only_sanitized_probe_result() -> None:
    assert "ETS_SP_PRODUCTION_CLIENT_PROBE_B64=" in BICEP
    assert '"production_client_outcome",' in WORKFLOW
    assert '"parser_failure_class",' in WORKFLOW
    assert '"record_count",' in WORKFLOW
    assert '"cycle_complete",' in WORKFLOW
    assert '"checkpoint_shape",' in WORKFLOW
    assert "sharepoint-production-client.log" in WORKFLOW
    assert 'rm -f "$raw"' in WORKFLOW
    assert "evidence/live-sharepoint-production-client/*.json" in WORKFLOW
