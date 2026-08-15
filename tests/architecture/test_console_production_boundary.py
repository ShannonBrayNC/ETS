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


def test_connector_route_matches_split_read_manage_authority() -> None:
    source = _read("ProductionApp.tsx")

    assert 'auth.capabilities.includes("connector.read")' in source
    assert 'auth.capabilities.includes("connector.manage")' in source
    assert "canReadConnectors" in source
    assert "{canReadConnectors && <Nav" in source
    expected_route = (
        'canReadConnectors ? <ConnectorsPage auth={auth} /> '
        ': <Denied capability="connector.read" />'
    )
    assert expected_route in source


def test_connector_mutation_controls_require_management_authority() -> None:
    source = _read("Connectors.tsx")

    assert 'const canManage = auth.capabilities.includes("connector.manage")' in source
    assert "Read-only connector access is active." in source
    assert "Read-only auditor" in source
    assert "Inspection only" in source
    assert "{canManage ? <div className=\"drawer-actions\">" in source
    assert "{canManage && wizard && <ConnectorWizard" in source


def test_console_api_uses_versioned_management_contract() -> None:
    source = _read("api.ts")

    assert '"/api/v2/auth/context"' in source
    assert "/gateway/connectors/v1/catalog" in source
    assert "/gateway/connectors/v1/instances" in source
    assert "VITE_ETS_MANAGEMENT_BASE" in source
    assert "console-user" not in source


def test_connector_diagnostics_use_bounded_codes_not_message_matching() -> None:
    api_source = _read("api.ts")
    diagnostic_source = _read("connectorDiagnostics.ts")

    assert "diagnosticFromResponse(response, detail)" in api_source
    assert "new ConnectorManagementError(diagnostic)" in api_source
    assert "decorateConnectorHealth(health)" in api_source
    assert 'const schemaVersion = "ets.connector.diagnostic.v1"' in diagnostic_source
    assert 'const categoryHeader = "X-ETS-Connector-Diagnostic-Category"' in diagnostic_source
    assert 'const codeHeader = "X-ETS-Connector-Diagnostic-Code"' in diagnostic_source
    assert "healthCategories[health.code]" in diagnostic_source
    assert "Next action:" in diagnostic_source
    assert "source_authentication" in diagnostic_source
    assert "collection_continuity" in diagnostic_source
    assert "upstream_sync" in diagnostic_source
    assert "message.includes" not in diagnostic_source
    assert "message.match" not in diagnostic_source


def test_connector_overlays_install_keyboard_focus_management() -> None:
    entrypoint = _read("main.tsx")
    accessibility = _read("overlayAccessibility.ts")

    assert 'from "./overlayAccessibility"' in entrypoint
    assert "installOverlayAccessibility();" in entrypoint
    assert 'const overlaySelector = ".connector-modal, .connector-drawer"' in accessibility
    assert 'overlay.setAttribute("role", "dialog")' in accessibility
    assert 'overlay.setAttribute("aria-modal", modal ? "true" : "false")' in accessibility
    assert 'event.key === "Escape"' in accessibility
    assert 'event.key !== "Tab"' in accessibility
    assert "state.previous?.isConnected" in accessibility


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
