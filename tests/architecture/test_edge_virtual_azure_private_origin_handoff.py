from __future__ import annotations

from pathlib import Path

SCRIPT = Path("scripts/edge_demo/Invoke-EdgeVirtualAzurePrivateOrigin.ps1")
WORKFLOW = Path(".github/workflows/deploy-edge-dark-azure.yml")
DOC = Path("docs/edge/EDGE_VIRTUAL_AZURE_PRIVATE_ORIGIN_HANDOFF.md")


def test_handoff_uses_exact_workflow_dispatch_run_identity() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'return_run_details = $true' in text
    assert "workflow_run_id" in text
    assert "X-GitHub-Api-Version: $ApiVersion" in text
    assert '$ApiVersion = "2026-03-10"' in text
    assert "gh run watch" in text
    assert "headSha" in text
    assert "workflow_dispatch" in text


def test_handoff_requires_protected_environment_variable_names() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    required = (
        "AZURE_CLIENT_ID",
        "AZURE_TENANT_ID",
        "AZURE_SUBSCRIPTION_ID",
        "ETS_EDGE_DEMO_ACR_NAME",
        "ETS_EDGE_DEMO_ACR_RESOURCE_GROUP",
        "ETS_EDGE_DEMO_RESOURCE_GROUP",
        "ETS_EDGE_DEMO_LOCATION",
    )
    for name in required:
        assert f'"{name}"' in text
    assert "environments/$EnvironmentName/variables?per_page=100" in text


def test_handoff_accepts_only_qualified_immutable_image_set() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "ets.edge_virtual_azure.image_set.v1" in text
    assert 'vulnerability_gate -ne "PASS"' in text
    assert "registry_credentials_retained -ne $false" in text
    assert "customer_identifiers_retained -ne $false" in text
    assert "sha256:[0-9a-f]{64}" in text
    for repository in (
        "ets/edge-demo/api",
        "ets/edge-demo/bff",
        "ets/edge-demo/upstream",
        "ets/edge-demo/ui",
    ):
        assert repository in text


def test_handoff_fails_on_source_drift_before_origin() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "$mainBeforeOrigin -ne $sourceSha" in script
    assert "expected_source_sha = $sourceSha" in script
    assert "expected_source_sha:" in workflow
    source_check = 'test "${GITHUB_SHA}" = "${EXPECTED_SOURCE_SHA}"'
    assert source_check in workflow
    assert workflow.index(source_check) < workflow.index("uses: azure/login@v2")


def test_origin_workflow_emits_public_safe_machine_readable_evidence() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "ets.edge_virtual_azure.origin.v1" in text
    assert "edge-virtual-azure-origin-${{ github.run_id }}" in text
    assert "origin-manifest.json" in text
    assert "'synthetic_only': True" in text
    assert "'hardware_attested': False" in text
    assert "'public_activation': False" in text
    assert "'credentials_retained': False" in text
    assert "'customer_identifiers_retained': False" in text
    assert "'runtime_identity_count':" in text
    assert "'public_network_access':" in text
    assert "if: inputs.phase == 'origin' && success()" in text


def test_operator_handoff_cannot_cross_public_activation_boundary() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert 'phase = "origin"' in script
    assert 'phase = "public-edge"' not in script
    assert "private-endpoint-connection approve" not in script
    assert "az network dns" not in script.lower()
    assert "STOP BOUNDARY: public-edge was not dispatched." in script
    assert "Private Link approval remains a" in doc
    assert "specific human review action" in doc


def test_handoff_does_not_introduce_secret_value_transport() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    for text in (script, workflow):
        assert "AZURE_CLIENT_SECRET" not in text
        assert "secrets." not in text
        assert "private-endpoint-connection approve" not in text
