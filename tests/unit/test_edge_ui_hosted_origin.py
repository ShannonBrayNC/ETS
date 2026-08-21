from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from ets.edge import protected_ingress

APPROVED_ORIGIN = "https://edge-demo.lanternprotocol.net"


def _client(monkeypatch: Any) -> TestClient:
    monkeypatch.setenv("ETS_EDGE_UI_BFF_ENABLED", "1")
    monkeypatch.setenv("ETS_EDGE_UI_ALLOWED_ORIGIN", APPROVED_ORIGIN)
    return TestClient(protected_ingress.app)


def test_hosted_bff_rejects_state_change_without_origin(monkeypatch: Any) -> None:
    client = _client(monkeypatch)

    response = client.post(
        "/edge/ui/v1/capture",
        headers={"X-ETS-UI-Request": "1"},
        json={"payload": {"synthetic": True}},
    )

    assert response.status_code == 403


def test_hosted_bff_rejects_unapproved_origin(monkeypatch: Any) -> None:
    client = _client(monkeypatch)

    response = client.post(
        "/edge/ui/v1/capture",
        headers={
            "X-ETS-UI-Request": "1",
            "Origin": "https://attacker.example",
            "Sec-Fetch-Site": "same-origin",
        },
        json={"payload": {"synthetic": True}},
    )

    assert response.status_code == 403


def test_hosted_bff_accepts_exact_approved_origin(monkeypatch: Any) -> None:
    client = _client(monkeypatch)

    async def fake_capture(_request: object) -> JSONResponse:
        return JSONResponse(
            status_code=201,
            content={"event_id": "evt_hosted_demo", "sync_state": "pending"},
        )

    monkeypatch.setattr(protected_ingress, "_ui_capture", fake_capture)

    response = client.post(
        "/edge/ui/v1/capture",
        headers={
            "X-ETS-UI-Request": "1",
            "Origin": APPROVED_ORIGIN,
            "Sec-Fetch-Site": "same-origin",
        },
        json={"payload": {"synthetic": True}},
    )

    assert response.status_code == 201
    assert response.json()["event_id"] == "evt_hosted_demo"


def test_hosted_bff_get_may_omit_origin(monkeypatch: Any) -> None:
    client = _client(monkeypatch)

    async def fake_status() -> dict[str, object]:
        return {
            "schema_version": "ets.edge.ui.status.v1",
            "device_identity": {
                "device_id": "ets-edge:hosted-demo",
                "hardware_attested": False,
                "key_custody": "software_volume",
            },
        }

    monkeypatch.setattr(protected_ingress, "_ui_status", fake_status)

    response = client.get(
        "/edge/ui/v1/status",
        headers={"X-ETS-UI-Request": "1"},
    )

    assert response.status_code == 200
