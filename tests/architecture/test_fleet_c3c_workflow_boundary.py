from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE = ROOT / ".github" / "workflows" / "fleet-c3c-live.yml"
Q0 = ROOT / ".github" / "workflows" / "fleet-c3c-q0-image.yml"
DOC = ROOT / "docs" / "fleet" / "ETS_FLEET_C3C_LIVE_QUALIFICATION.md"


def test_live_workflow_requires_exact_source_immutable_image_and_private_origin() -> None:
    source = LIVE.read_text(encoding="utf-8")
    assert "expected_source_sha" in source
    assert "fleet_image" in source
    assert "@sha256:[0-9a-f]{64}" in source
    assert "GITHUB_SHA" in source
    assert "publicNetworkAccess" in source
    assert "Disabled" in source
    assert "internal" in source
    assert "ETS_FLEET_AUTH_BRIDGE=container-apps-easyauth" in source
    assert "ETS_FLEET_STEP_UP_ACRS" in source


def test_live_workflow_approves_only_exact_reviewed_private_link() -> None:
    source = LIVE.read_text(encoding="utf-8")
    assert "private_link_connection_name" in source
    assert "PRIVATE_LINK_REQUEST_MESSAGE" in source
    assert "state['status'] == 'Pending'" in source
    assert "len(exact) == 1" in source
    assert "private-endpoint-connection approve" in source
    assert "--id \"${connection_id}\"" in source


def test_route_qualification_does_not_overclaim_entra_store_mutation_or_hostname() -> None:
    source = LIVE.read_text(encoding="utf-8")
    assert "'shared_store_qualified': False" in source
    assert "'entra_enforced': False" in source
    assert "'live_fleet_mutation_qualified': False" in source
    assert "'public_hostname_tls_qualified': False" in source
    assert "'public_hostname_activated': False" in source
    assert "fleet.lanternprotocol.net" not in source


def test_fleet_q0_image_gate_is_immutable_scanned_attested_and_non_root() -> None:
    source = Q0.read_text(encoding="utf-8")
    assert "Dockerfile.fleet" in source
    assert "USER ets" in source
    assert "docker/build-push-action@v7.2.0" in source
    assert "provenance: mode=max" in source
    assert "sbom: true" in source
    assert "sha256:[0-9a-f]{64}" in source
    assert "anchore/sbom-action@v0.24.0" in source
    assert "aquasecurity/trivy-action@v0.36.0" in source
    assert "fail_on_fixable_high_critical_v1" in source
    assert source.count("actions/attest@v4.2.1") == 2
    assert "registry_credentials_retained': False" in source


def test_c3c_document_preserves_seven_independent_claim_states() -> None:
    source = DOC.read_text(encoding="utf-8")
    for claim in (
        "software_composed",
        "shared_store_qualified",
        "entra_enforced",
        "azure_private_origin_qualified",
        "frontdoor_route_qualified",
        "public_hostname_tls_qualified",
        "live_fleet_mutation_qualified",
    ):
        assert claim in source
    assert "Do not modify the `lanternprotocol.net` apex or current `www` records" in source
