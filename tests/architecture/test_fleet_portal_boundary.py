from __future__ import annotations

import ast
from pathlib import Path

PORTAL = Path("ets/fleet/portal.py")
API = Path("ets/fleet/portal_api.py")
ASSETS = Path("ets/fleet/portal_assets.py")
DOC = Path("docs/fleet/ETS_FLEET_DARK_PRO_C1.md")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


def test_portal_read_model_has_no_azure_sdk_or_product_plane_dependency() -> None:
    imports = _imports(PORTAL) | _imports(API)
    forbidden = ("azure", "ets.core", "ets.edge", "ets.gateway")
    assert not any(
        imported == prefix or imported.startswith(prefix + ".")
        for imported in imports
        for prefix in forbidden
    )


def test_portal_does_not_use_iot_twin_connection_state_as_truth() -> None:
    source = PORTAL.read_text(encoding="utf-8") + API.read_text(encoding="utf-8")
    assert "connectionState" not in source
    assert "connectionStateUpdatedTime" not in source


def test_bff_never_parses_browser_authorization_or_privileged_scope_headers() -> None:
    source = API.read_text(encoding="utf-8")
    forbidden = (
        'headers.get("authorization")',
        "X-ETS-Tenant",
        "X-ETS-Workspace",
        "localStorage",
        "sessionStorage",
    )
    for token in forbidden:
        assert token not in source


def test_dark_pro_assets_use_output_encoding_and_external_script_style_only() -> None:
    source = ASSETS.read_text(encoding="utf-8")
    assert "textContent" in source
    assert "innerHTML" not in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "<script>" not in source
    assert "<style>" not in source


def test_security_headers_are_fail_closed_for_framing_and_storage() -> None:
    source = API.read_text(encoding="utf-8")
    assert '"Cache-Control": "no-store, max-age=0"' in source
    assert '"X-Frame-Options": "DENY"' in source
    assert "frame-ancestors 'none'" in source
    assert '"Referrer-Policy": "no-referrer"' in source
    assert '"Strict-Transport-Security"' in source


def test_c1_is_read_only_and_defers_trust_mutations() -> None:
    source = API.read_text(encoding="utf-8")
    assert "@router.post" not in source
    assert "@router.put" not in source
    assert "@router.patch" not in source
    assert "@router.delete" not in source


def test_documentation_preserves_fleet_truth_and_browser_boundaries() -> None:
    text = DOC.read_text(encoding="utf-8").lower()
    assert "presence is not health" in text
    assert "heartbeat is not evidence verification" in text
    assert "browser never receives" in text
    assert "fleet.viewer" in text
    assert "fleet.operator" in text
    assert "fleet.securityadmin" in text
    assert "c2" in text
