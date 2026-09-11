from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github/workflows/azure-migration-destination-image-publish.yml").read_text(
    encoding="utf-8"
)
BOOTSTRAP = (ROOT / "scripts/azure/bootstrap-destination-image-publisher.ps1").read_text(
    encoding="utf-8"
)


def test_destination_publication_is_hard_bound() -> None:
    for expected in (
        "ets-azure-migration-destination-image-publish",
        "0d20cf0f-3498-46c1-a0db-69b09c634cc2",
        "5729a82b-8850-4868-b96c-96c3805cbb9d",
        "rg-ets-shared-eastus",
        "etsprod7c8ab70380",
    ):
        assert expected in WORKFLOW
        assert expected in BOOTSTRAP

    assert "ets/hosted-q1" in WORKFLOW
    assert (
        "repo:ShannonBrayNC/ETS:environment:"
        "ets-azure-migration-destination-image-publish"
        in BOOTSTRAP
    )


def test_publication_uses_oidc_and_no_reusable_registry_secret() -> None:
    assert "id-token: write" in WORKFLOW
    assert "azure/login@v3.0.0" in WORKFLOW
    assert "https://containerregistry.azure.net/.default" in WORKFLOW
    assert "python scripts/acr_oauth_docker_login.py" in WORKFLOW
    assert "adminUserEnabled" in WORKFLOW
    assert "AZURE_CLIENT_SECRET" not in WORKFLOW
    assert "registry-password" not in WORKFLOW
    assert "listCredentials" not in WORKFLOW
    assert "clientSecretCreated = $false" in BOOTSTRAP


def test_publication_proves_gate2_image_capability() -> None:
    assert "AzureFederatedManagedIdentityCredentialProfile" in WORKFLOW
    assert "AzureFederatedManagedIdentityCredentialProvider" in WORKFLOW
    assert "ClientAssertionCredential" in WORKFLOW
    assert "docker run --rm \"$IMMUTABLE_REF\"" in WORKFLOW
    assert "gate2_federated_provider_import_verified" in WORKFLOW


def test_publication_preserves_supply_chain_evidence() -> None:
    for expected in (
        "docker/build-push-action@v7.2.0",
        "provenance: mode=max",
        "sbom: true",
        "anchore/sbom-action@v0.24.0",
        "aquasecurity/trivy-action@v0.36.0",
        "actions/attest@v4.2.1",
        "push-to-registry: true",
        "actions/upload-artifact@v7.0.1",
        "sha256:[0-9a-f]{64}",
    ):
        assert expected in WORKFLOW


def test_publication_cannot_mutate_production_gateway() -> None:
    forbidden = (
        "az containerapp update",
        "az containerapp revision",
        "az containerapp ingress",
        "az containerapp job",
        "runtimeMinReplicas",
        "minReplicas",
        "ets-oif5r5ydprrou-gw",
    )
    for token in forbidden:
        assert token not in WORKFLOW
    assert "production_gateway_mutated': False" in WORKFLOW


def test_publisher_bootstrap_is_acr_scoped_and_separate() -> None:
    assert "ets-gh-dst-image-publisher" in BOOTSTRAP
    assert "github-ets-destination-image-publish" in BOOTSTRAP
    assert "LegacyRegistryPermissions" in BOOTSTRAP
    assert (
        "Container Registry Configuration Reader and Data Access Configuration Reader"
        in BOOTSTRAP
    )
    assert "AcrPush" in BOOTSTRAP
    assert (
        "$count = az role assignment list `\n"
        "        --all `\n"
        "        --scope $Scope `"
        in BOOTSTRAP
    )
    assert "scope=='$Scope' && roleDefinitionName=='$RoleName'" in BOOTSTRAP
    broad_admin_roles = (
        "Owner','Contributor','User Access Administrator',"
        "'Role Based Access Control Administrator"
    )
    assert broad_admin_roles in BOOTSTRAP
    assert "ets-gh-migration-dst-restore" not in BOOTSTRAP
