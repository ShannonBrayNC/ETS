from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "apps" / "console" / "web" / "src"


def _read(path: str) -> str:
    return (CONSOLE / path).read_text(encoding="utf-8")


def test_console_entrypoint_uses_authenticated_production_shell() -> None:
    source = _read("main.tsx")

    assert 'from "./ProductionApp"' in source
    assert "<ProductionApp />" in source
    assert 'from "./App"' not in source
    assert "<App />" not in source


def test_production_shell_uses_server_authorization_context_not_editable_scope() -> None:
    source = _read("ProductionApp.tsx")

    assert "getAuthorizationContext" in source
    assert "auth.tenant_id" in source
    assert "auth.workspace_id" in source
    assert "auth.subject" in source
    assert "ScopeEditor" not in source
    assert "defaultScope" not in source
    assert "console-user" not in source


def test_connector_route_matches_current_fail_closed_management_authority() -> None:
    source = _read("ProductionApp.tsx")

    assert 'auth.capabilities.includes("connector.manage")' in source
    assert '<Denied capability="connector.manage" />' in source


def test_console_api_uses_versioned_management_contract() -> None:
    source = _read("api.ts")

    assert '"/api/v2/auth/context"' in source
    assert "/gateway/connectors/v1/catalog" in source
    assert "/gateway/connectors/v1/instances" in source
    assert "VITE_ETS_MANAGEMENT_BASE" in source
    assert "console-user" not in source


def test_connector_wizard_never_falls_back_to_raw_settings_editor() -> None:
    source = _read("Connectors.tsx")

    assert "<textarea" not in source.casefold()
    assert "UX profile pending" in source
    assert "Credential reference" in source
    assert "Reusable credential values are never displayed here." in source


def test_connector_preview_is_explicitly_precommit_and_non_verification() -> None:
    source = _read("Connectors.tsx")

    assert 'representation: "pre-commit evidence candidate"' in source
    assert 'commitment: "not performed in preview"' in source
    assert "Operational health is not ETS cryptographic verification" in source
