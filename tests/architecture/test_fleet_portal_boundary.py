from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTAL = ROOT / "ets" / "fleet" / "portal.py"
API = ROOT / "ets" / "fleet" / "portal_api.py"
ASSETS = ROOT / "ets" / "fleet" / "portal_assets.py"
DOC = ROOT / "docs" / "fleet" / "ETS_FLEET_DARK_PRO_C1.md"


def test_portal_has_no_azure_product_plane_or_device_credential_coupling() -> None:
    source = PORTAL.read_text(encoding="utf-8").lower()
    forbidden = (
        "azure.",
        "iothub",
        "dps",
        "connectionstring",
        "sharedaccesssignature",
        "sas_token",
        "private_key",
        "core credential",
        "gateway credential",
    )
    for token in forbidden:
        assert token not in source


def test_portal_scope_is_server_owned() -> None:
    source = PORTAL.read_text(encoding="utf-8")
    assert "scope_bindings" in source
    assert "principal.authorizes" in source
    assert "X-ETS-Tenant" not in source
    assert "X-ETS-Workspace" not in source


def test_portal_truth_dimensions_remain_separate() -> None:
    source = PORTAL.read_text(encoding="utf-8")
    assert "transport_presence" in source
    assert "heartbeat_posture" in source
    assert "registration_state" in source
    assert "certificate_posture" in source
    assert "evidence_verified: bool = False" in source
    assert "health_asserted: bool = False" in source
    assert "trust_score" not in source.lower()
    assert "health_score" not in source.lower()


def test_assets_use_safe_dom_and_no_browser_token_storage() -> None:
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


def test_c1_default_composition_remains_read_only_under_c2_extension() -> None:
    source = API.read_text(encoding="utf-8")
    assert "admin_service: FleetPortalAdminService | None = None" in source
    assert "security_session_resolver: SecuritySessionResolver | None = None" in source
    assert (
        "if admin_service is not None and security_session_resolver is not None:"
        in source
    )
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
