from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "hosted-azure-q0-image-harness.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")


def test_local_image_probe_requires_gate2_federated_runtime_symbols() -> None:
    for marker in (
        "docker run --rm -i --entrypoint python",
        "ClientAssertionCredential",
        "AzureFederatedManagedIdentityCredentialProfile",
        "AzureFederatedManagedIdentityCredentialProvider",
        '"gate2_federated_provider_importable": True',
        '"client_assertion_credential_importable": True',
    ):
        assert marker in TEXT


def test_capability_probe_remains_local_and_registry_free() -> None:
    build_step = TEXT.split("- name: Build Q1 image locally without registry credentials", 1)[1]
    assert "docker build --pull" in build_step
    assert "docker push" not in build_step
    assert "az acr" not in build_step
