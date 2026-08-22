from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "fleet-c3c-q0-image.yml"


def test_fleet_c3c_q0_publication_is_main_only_and_oidc_only() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert 'test "${GITHUB_REF_NAME}" = "main"' in source
    assert 'test "$(git rev-parse HEAD)" = "${GITHUB_SHA}"' in source
    assert "id-token: write" in source
    assert "azure/login@v3.0.0" in source
    assert "AZURE_CLIENT_SECRET" not in source
    assert "az acr credential" not in source
    assert "adminUserEnabled" in source
    assert "adminUserEnabled'] is False" in source


def test_fleet_c3c_q0_retains_digest_sbom_scan_and_attestations() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "immutable-image.txt" in source
    assert "manifest.json" in source
    assert "sbom.spdx.json" in source
    assert "trivy-high-critical.json" in source
    assert "fixable HIGH/CRITICAL" in source
    assert "subject-digest: ${{ steps.image.outputs.digest }}" in source
    assert "push-to-registry: true" in source
    assert "retention-days: 90" in source
