from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from ets.edge import protected_ingress
from ets.edge.device_identity import build_device_identity, write_device_identity


def _client(monkeypatch: Any, tmp_path: Path) -> tuple[TestClient, str]:
    api_key = "K" * 32
    api_key_path = tmp_path / "edge-local-api-key"
    api_key_path.write_text(api_key + "\n", encoding="utf-8")

    identity_path = tmp_path / "edge-device-identity.json"
    identity = build_device_identity("11" * 32, "ets-edge-virtual-demo-key")
    write_device_identity(identity_path, identity)

    monkeypatch.setenv("ETS_EDGE_API_KEY_FILE", str(api_key_path))
    monkeypatch.setenv("ETS_EDGE_DEVICE_IDENTITY_FILE", str(identity_path))
    monkeypatch.setenv("ETS_EDGE_UI_BFF_ENABLED", "1")
    monkeypatch.setenv("ETS_EDGE_UI_TENANT", "tenant_server")
    monkeypatch.setenv("ETS_EDGE_UI_WORKSPACE", "workspace_server")
    return TestClient(protected_ingress.app), api_key


def test_ui_bff_is_disabled_by_default(monkeypatch: Any, tmp_path: Path) -> None:
    client, _api_key = _client(monkeypatch, tmp_path)
    monkeypatch.delenv("ETS_EDGE_UI_BFF_ENABLED")

    response = client.get(
        "/edge/ui/v1/status",
        headers={"X-ETS-UI-Request": "1"},
    )

    assert response.status_code == 404


def test_ui_bff_requires_browser_marker(monkeypatch: Any, tmp_path: Path) -> None:
    client, _api_key = _client(monkeypatch, tmp_path)

    response = client.get("/edge/ui/v1/status")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ETS_EDGE_UI_FORBIDDEN"


def test_ui_bff_rejects_cross_site_browser_request(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    client, _api_key = _client(monkeypatch, tmp_path)

    response = client.get(
        "/edge/ui/v1/status",
        headers={
            "X-ETS-UI-Request": "1",
            "Sec-Fetch-Site": "cross-site",
            "Origin": "https://attacker.example",
        },
    )

    assert response.status_code == 403


def test_ui_status_never_returns_local_api_key(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    client, api_key = _client(monkeypatch, tmp_path)

    async def fake_status() -> dict[str, object]:
        return {
            "schema_version": "ets.edge.ui.status.v1",
            "device_identity": {
                "device_id": "ets-edge:demo",
                "hardware_attested": False,
                "key_custody": "software_volume",
            },
            "fleet": {
                "enrollment_state": "not_configured",
                "heartbeat_state": "not_configured",
            },
        }

    monkeypatch.setattr(protected_ingress, "_ui_status", fake_status)

    response = client.get(
        "/edge/ui/v1/status",
        headers={"X-ETS-UI-Request": "1"},
    )

    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert api_key not in serialized
    assert "api_key" not in serialized.lower()
    assert "private_key" not in serialized.lower()


def test_ui_capture_uses_server_scope_without_browser_secret(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    client, api_key = _client(monkeypatch, tmp_path)
    observed: dict[str, object] = {}

    async def fake_ingress_response(
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        include_scope: bool = False,
    ) -> JSONResponse:
        observed.update(
            method=method,
            path=path,
            body=body,
            params=params,
            include_scope=include_scope,
        )
        return JSONResponse(
            status_code=201,
            content={
                "event_id": "evt_demo_dark_pro",
                "sync_state": "pending",
            },
        )

    monkeypatch.setattr(
        protected_ingress,
        "_ingress_json_response",
        fake_ingress_response,
    )

    response = client.post(
        "/edge/ui/v1/capture",
        headers={
            "X-ETS-UI-Request": "1",
            "X-ETS-Tenant": "attacker_tenant",
            "X-ETS-Workspace": "attacker_workspace",
        },
        json={"payload": {"synthetic": True, "message": "demo"}},
    )

    assert response.status_code == 201
    assert observed["method"] == "POST"
    assert observed["path"] == "/edge/v1/capture/webhook/edge-dark-pro-demo"
    assert observed["include_scope"] is True
    serialized = json.dumps(response.json())
    assert api_key not in serialized
    assert "attacker_tenant" not in serialized
    assert "attacker_workspace" not in serialized
