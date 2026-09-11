from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = (
    ROOT / "scripts" / "m365" / "qualify_ets_sharepoint_workload_identity.py"
).read_text(encoding="utf-8")
PREVIEW = (
    ROOT / "scripts" / "m365" / "preview-ets-sharepoint-workload-identity-runtime.ps1"
).read_text(encoding="utf-8")
INVOKER = (
    ROOT
    / "scripts"
    / "m365"
    / "invoke-ets-sharepoint-workload-identity-runtime-qualification.ps1"
).read_text(encoding="utf-8")


def test_runtime_harness_is_bound_to_approved_cross_tenant_target() -> None:
    for expected in (
        "38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe",
        "0be62a70-45b5-405d-92b6-ca0ce3af953a",
        "echomediaai.sharepoint.com",
        "/sites/ETS",
        "Sites.Selected",
        "2604ea4c-3b40-4195-b1a8-e3d7327b7c41",
        "9ddf1ece-7f81-4258-af25-91e06afaa682",
    ):
        assert expected in HARNESS


def test_runtime_harness_uses_production_federated_provider() -> None:
    assert "AzureFederatedManagedIdentityCredentialProvider" in HARNESS
    assert "AzureFederatedManagedIdentityCredentialProfile" in HARNESS
    assert "MICROSOFT_GRAPH_CREDENTIAL_REFERENCE" in HARNESS
    assert "MICROSOFT_GRAPH_DEFAULT_SCOPE" in HARNESS
    assert "ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID" in HARNESS
    assert "IDENTITY_ENDPOINT" in HARNESS
    assert "IDENTITY_HEADER" in HARNESS


def test_runtime_harness_is_app_only_and_graph_get_only() -> None:
    normalized = " ".join(HARNESS.split()).casefold()
    assert 'method="get"' in normalized
    for method in ("post", "patch", "put", "delete"):
        assert f'method="{method}"' not in normalized
    assert 'claims.get("scp")' in HARNESS
    assert "set(map(str, roles)) != {APPROVED_GRAPH_ROLE}" in HARNESS


def test_runtime_harness_outputs_only_sanitized_structural_evidence() -> None:
    assert '"sharePointPayloadRetained": False' in HARNESS
    assert '"reusableCredentialRetained": False' in HARNESS
    assert "print(token" not in HARNESS
    assert "print(site" not in HARNESS
    assert "print(root" not in HARNESS
    assert "Authorization" in HARNESS


def test_preview_is_bound_to_exact_gateway_and_never_mutates_azure() -> None:
    for expected in (
        "rg-ets-prod-eastus",
        "ets-oif5r5ydprrou-gw",
        "ets-oif5r5ydprrou-gw-id",
        "0d20cf0f-3498-46c1-a0db-69b09c634cc2",
        "5729a82b-8850-4868-b96c-96c3805cbb9d",
    ):
        assert expected in PREVIEW
    normalized = " ".join(PREVIEW.split()).casefold()
    for forbidden in (
        "az containerapp update",
        "az containerapp revision activate",
        "az containerapp revision deactivate",
        "az identity create",
        "az identity delete",
        "az role assignment create",
    ):
        assert forbidden not in normalized
    assert "mutationPerformed = $false" in PREVIEW


def test_invoker_refuses_to_activate_or_scale_gateway() -> None:
    normalized = " ".join(INVOKER.split()).casefold()
    assert "az containerapp exec" in normalized
    for forbidden in (
        "az containerapp update",
        "az containerapp revision activate",
        "az containerapp revision deactivate",
        "--min-replicas",
        "--max-replicas",
    ):
        assert forbidden not in normalized
    assert "no active replica exists" in INVOKER
    assert "will not activate a revision" in INVOKER
