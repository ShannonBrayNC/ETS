from __future__ import annotations

from pathlib import Path

import pytest

import scripts.lantern_destination_staging_verify as staging

WORKFLOW = Path(".github/workflows/lantern-destination-staging.yml")


def _site(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "index.html").write_text(
        '<html><head><meta name="robots" content="noindex, nofollow"></head>'
        '<body>Evidence you can prove.</body></html>',
        encoding="utf-8",
    )
    (root / "app.js").write_bytes(b"console.log('lantern');\n")


def test_verifier_requires_noindex_nofollow(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<html></html>", encoding="utf-8")

    with pytest.raises(staging.StagingVerificationError, match="noindex"):
        staging._site_manifest(site)


def test_verifier_requires_azure_default_endpoint_hosts() -> None:
    assert (
        staging._normalize_endpoint(
            "https://lanterndstabc.z13.web.core.windows.net/", "storage"
        )
        == "https://lanterndstabc.z13.web.core.windows.net/"
    )
    assert (
        staging._normalize_endpoint("https://lantern-dst-abc.azurefd.net/", "frontdoor")
        == "https://lantern-dst-abc.azurefd.net/"
    )
    with pytest.raises(staging.StagingVerificationError, match="default host"):
        staging._normalize_endpoint("https://lanternprotocol.net/", "frontdoor")


def test_verifier_requires_exact_bytes_on_both_endpoints(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    site = tmp_path / "site"
    _site(site)
    payloads = {
        "index.html": (site / "index.html").read_bytes(),
        "app.js": (site / "app.js").read_bytes(),
    }

    def fetch(url: str, timeout: float = 15.0) -> bytes:
        del timeout
        name = url.rsplit("/", 1)[-1]
        return payloads[name]

    monkeypatch.setattr(staging, "_fetch_bytes", fetch)
    result = staging.verify(
        site_root=site,
        storage_endpoint="https://lanterndstabc.z13.web.core.windows.net/",
        frontdoor_endpoint="https://lantern-dst-abc.azurefd.net/",
        storage_account="lanterndstabc",
        frontdoor_profile="lantern-destination-fd",
        frontdoor_endpoint_name="lantern-dst-abc",
    )

    assert result["storage_byte_equivalence"] is True
    assert result["frontdoor_byte_equivalence"] is True
    assert result["robots_noindex_nofollow"] is True
    assert result["production_dns_changed"] is False
    assert result["tenant_exit_ready"] is False


def test_verifier_rejects_frontdoor_byte_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    site = tmp_path / "site"
    _site(site)

    def fetch(url: str, timeout: float = 15.0) -> bytes:
        del timeout
        name = url.rsplit("/", 1)[-1]
        if "azurefd.net" in url and name == "app.js":
            return b"changed"
        return (site / name).read_bytes()

    monkeypatch.setattr(staging, "_fetch_bytes", fetch)
    with pytest.raises(staging.StagingVerificationError):
        staging.verify(
            site_root=site,
            storage_endpoint="https://lanterndstabc.z13.web.core.windows.net/",
            frontdoor_endpoint="https://lantern-dst-abc.azurefd.net/",
            storage_account="lanterndstabc",
            frontdoor_profile="lantern-destination-fd",
            frontdoor_endpoint_name="lantern-dst-abc",
        )


def test_workflow_is_destination_only_and_has_no_production_domain_cutover() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    lowered = text.casefold()

    assert "workflow_dispatch:" in text
    assert "LANTERN_DESTINATION_STAGING_AUTHORIZED" in text
    assert "environment: ets-azure-migration-destination-restore" in text
    assert "RESOURCE_GROUP: rg-ets-prod-eastus" in text
    assert "scripts.lantern_content_dependency_sweep" in text
    assert "scripts.lantern_destination_staging_verify" in text
    assert "az storage account create" in text
    assert "az afd profile create" in text
    assert "az afd endpoint create" in text
    assert "az afd origin-group create" in text
    assert "az afd origin create" in text
    assert "az afd route create" in text
    assert "tenant_exit_ready: `false`" in text
    assert "rg-ets-live-eastus" not in text
    assert "environment: ets-azure-q1" not in text
    for forbidden in (
        "az afd custom-domain",
        "az network dns",
        "custom-domain create",
        "custom-domain update",
        "lanternprotocol.net",
        "www.lanternprotocol.net",
    ):
        assert forbidden not in lowered
