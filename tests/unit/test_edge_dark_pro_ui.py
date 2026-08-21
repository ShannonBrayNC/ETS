from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDGE_APP = ROOT / "ets" / "explorer-ui" / "src" / "EdgeDarkApp.jsx"
EDGE_CSS = ROOT / "ets" / "explorer-ui" / "src" / "edge-dark.css"
LEGACY_EDGE_APP = ROOT / "ets" / "explorer-ui" / "src" / "EdgeApp.jsx"
LEGACY_EDGE_CSS = ROOT / "ets" / "explorer-ui" / "src" / "edge-dark-pro.css"
MAIN = ROOT / "ets" / "explorer-ui" / "src" / "main.jsx"
DOCKERFILE = ROOT / "edge-demo" / "Dockerfile.ui"


def test_edge_build_selects_dark_pro_without_replacing_generic_explorer() -> None:
    main = MAIN.read_text(encoding="utf-8")
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "VITE_ETS_SURFACE_PROFILE === 'edge'" in main
    assert "EdgeDarkApp" in main
    assert "ARG VITE_ETS_SURFACE_PROFILE=edge" in dockerfile
    assert "VITE_ETS_SURFACE_PROFILE=${VITE_ETS_SURFACE_PROFILE}" in dockerfile
    assert EDGE_CSS.is_file()


def test_edge_dark_pro_browser_uses_bff_without_reusable_credentials() -> None:
    source = EDGE_APP.read_text(encoding="utf-8")

    assert "/edge/ui/v1" in source
    assert "X-ETS-UI-Request" in source
    assert "credentials: 'same-origin'" in source
    for forbidden in (
        "X-ETS-API-Key",
        "X-ETS-Tenant",
        "X-ETS-Workspace",
        "Authorization",
        "Bearer token",
        "Local API key",
        'type="password"',
        "bearer_token",
        "api_key",
    ):
        assert forbidden not in source


def test_superseded_credential_entry_shell_is_removed() -> None:
    assert not LEGACY_EDGE_APP.exists()
    assert not LEGACY_EDGE_CSS.exists()
