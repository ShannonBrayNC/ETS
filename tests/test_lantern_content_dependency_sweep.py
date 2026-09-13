from __future__ import annotations

from pathlib import Path

import scripts.lantern_content_dependency_sweep as sweep


def test_clean_site_reports_external_hosts_and_no_blocker(tmp_path: Path) -> None:
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_text(
        '<meta name="robots" content="noindex, nofollow">'
        '<link rel="canonical" href="https://lanternprotocol.net/">'
        '<script src="https://elevenlabs.io/player/audioNativeHelper.js"></script>',
        encoding="utf-8",
    )

    result = sweep.sweep(root)

    assert result["source_dependency_free"] is True
    assert result["search_index_ready"] is False
    assert result["external_hosts"] == ["elevenlabs.io", "lanternprotocol.net"]


def test_source_resource_reference_is_blocking(tmp_path: Path) -> None:
    root = tmp_path / "site"
    root.mkdir()
    (root / "app.js").write_text(
        "const rg = 'rg-ets-live-eastus';",
        encoding="utf-8",
    )

    result = sweep.sweep(root)

    assert result["source_dependency_free"] is False
    assert result["blockers"][0]["category"] == "source_resource_group"


def test_direct_azure_provider_endpoint_is_blocking(tmp_path: Path) -> None:
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_text(
        '<a href="https://example.z03.azurefd.net/path">old edge</a>',
        encoding="utf-8",
    )

    result = sweep.sweep(root)

    assert result["source_dependency_free"] is False
    assert any(
        item["category"] == "direct_azure_provider_endpoint"
        for item in result["blockers"]
    )


def test_insecure_external_url_is_blocking(tmp_path: Path) -> None:
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_text(
        '<a href="http://example.com/">insecure</a>',
        encoding="utf-8",
    )

    result = sweep.sweep(root)

    assert result["source_dependency_free"] is False
    assert any(
        item["category"] == "insecure_external_url"
        for item in result["blockers"]
    )


def test_current_site_tree_passes_static_source_dependency_gate() -> None:
    result = sweep.sweep(Path("ops/lantern-site-backup/site"))

    assert result["source_dependency_free"] is True
