from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EDGE_APP = ROOT / "ets" / "explorer-ui" / "src" / "EdgeApp.jsx"
EDGE_CSS = ROOT / "ets" / "explorer-ui" / "src" / "edge-dark-pro.css"
MAIN = ROOT / "ets" / "explorer-ui" / "src" / "main.jsx"
DOCKERFILE = ROOT / "edge-demo" / "Dockerfile.ui"


def test_edge_build_selects_dark_pro_without_replacing_generic_explorer() -> None:
    main = MAIN.read_text(encoding="utf-8")
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "VITE_ETS_EDGE_DARK_PRO === 'true'" in main
    assert "const RootApp = edgeDarkProEnabled ? EdgeApp : App" in main
    assert "ARG VITE_ETS_EDGE_DARK_PRO=true" in dockerfile
    assert "ENV VITE_ETS_EDGE_DARK_PRO=${VITE_ETS_EDGE_DARK_PRO}" in dockerfile


def test_edge_ui_does_not_persist_operator_credentials_in_browser_storage() -> None:
    source = EDGE_APP.read_text(encoding="utf-8")

    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "document.cookie" not in source
    assert "X-ETS-API-Key" in source
    assert "type=\"password\"" in source
    assert "autoComplete=\"off\"" in source
    assert "setApiKey('')" in source


def test_edge_ui_keeps_public_identity_separate_from_protected_operator_status() -> None:
    source = EDGE_APP.read_text(encoding="utf-8")

    assert "/ready" in source
    assert "/version" in source
    assert "/edge/v1/device/identity" in source
    assert "/edge/v1/sync/status" in source
    assert "loadPublicStatus" in source
    assert "loadProtectedStatus" in source
    assert "Private signing material is never returned to the browser" in source


def test_edge_dark_pro_uses_non_color_state_text_and_focus_treatment() -> None:
    source = EDGE_APP.read_text(encoding="utf-8")
    css = EDGE_CSS.read_text(encoding="utf-8")

    assert "Hardware attested" in source
    assert "Software demo" in source
    assert "Security boundary:" in source
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
