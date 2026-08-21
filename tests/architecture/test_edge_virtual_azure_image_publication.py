from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(".github/workflows/edge-virtual-azure-q0-images.yml")


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_publication_is_manual_main_only_and_uses_oidc() -> None:
    text = _text()

    assert "workflow_dispatch:" in text
    assert 'test "${GITHUB_REF_NAME}" = "main"' in text
    assert 'test "$(git rev-parse HEAD)" = "${GITHUB_SHA}"' in text
    assert "id-token: write" in text
    assert "uses: azure/login@v3.0.0" in text
    assert "client-id: ${{ vars.AZURE_CLIENT_ID }}" in text
    assert "AZURE_CLIENT_SECRET" not in text
    assert "secrets." not in text


def test_publication_uses_governed_registry_and_fixed_repositories() -> None:
    text = _text()

    assert "ACR_NAME: ${{ vars.ETS_EDGE_DEMO_ACR_NAME }}" in text
    assert "ACR_RESOURCE_GROUP: ${{ vars.ETS_EDGE_DEMO_ACR_RESOURCE_GROUP }}" in text
    assert "API_REPOSITORY: ets/edge-demo/api" in text
    assert "BFF_REPOSITORY: ets/edge-demo/bff" in text
    assert "UPSTREAM_REPOSITORY: ets/edge-demo/upstream" in text
    assert "UI_REPOSITORY: ets/edge-demo/ui" in text
    assert "adminUserEnabled" in text
    assert "authentication-as-arm show" in text
    assert "acr_oauth_docker_login.py" in text
    assert "docker login -u" not in text
    assert ":latest" not in text


def test_all_four_dockerfiles_are_built_from_one_source() -> None:
    text = _text()

    for dockerfile in (
        "./edge-demo/Dockerfile.api",
        "./edge-demo/Dockerfile.webhook",
        "./edge-demo/Dockerfile.upstream",
        "./edge-demo/Dockerfile.ui.azure",
    ):
        assert f"file: {dockerfile}" in text
    assert text.count("platforms: linux/amd64") == 4
    assert text.count("provenance: mode=max") == 4
    assert text.count("sbom: true") == 4
    assert "edge-demo-${GITHUB_SHA:0:12}-${GITHUB_RUN_ID}" in text


def test_every_image_requires_canonical_digest_and_registry_inspection() -> None:
    text = _text()

    assert "sha256:[0-9a-f]{64}" in text
    assert "for name in ('API_DIGEST', 'BFF_DIGEST', 'UPSTREAM_DIGEST', 'UI_DIGEST')" in text
    assert "docker buildx imagetools inspect" in text
    for key in ("api_ref", "bff_ref", "upstream_ref", "ui_ref"):
        assert key in text


def test_supply_chain_evidence_and_vulnerability_gate_cover_all_images() -> None:
    text = _text()

    for component in ("api", "bff", "upstream", "ui"):
        assert f"{component}-sbom.spdx.json" in text
        assert f"{component}-trivy-high-critical.json" in text
    assert text.count("uses: anchore/sbom-action@v0.24.0") == 4
    assert text.count("uses: aquasecurity/trivy-action@v0.36.0") == 4
    assert text.count("uses: actions/attest@v4.2.1") == 8
    assert "fail_on_fixable_high_critical_v1" in text
    assert "if gate != 'PASS':" in text


def test_aggregate_manifest_maps_directly_to_origin_image_inputs() -> None:
    text = _text()

    assert "ets.edge_virtual_azure.image_set.v1" in text
    assert "'edge_api': os.environ['API_REF']" in text
    assert "'edge_bff': os.environ['BFF_REF']" in text
    assert "'edge_upstream': os.environ['UPSTREAM_REF']" in text
    assert "'edge_ui': os.environ['UI_REF']" in text
    assert "registry_credentials_retained': False" in text
    assert "customer_identifiers_retained': False" in text


def test_published_ui_is_requalified_as_unprivileged_narrow_surface() -> None:
    text = _text()

    assert "Config.User" in text
    assert '= "nginx"' in text
    assert "8080/tcp" in text
    assert "/afd-healthz" in text
    for path in ("/api", "/docs", "/openapi.json", "/edge/v1/device/identity", "/internal", "/ready", "/version"):
        assert path in text
    assert 'grep -R -F "Local API key"' in text
    assert 'grep -R -F "Bearer token"' in text
    assert 'grep -R -F "X-ETS-API-Key"' in text
