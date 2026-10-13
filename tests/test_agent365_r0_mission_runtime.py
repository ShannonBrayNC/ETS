from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import ets.ranger.agent365_r0_mission_runtime as mission_runtime
from ets.ranger.agent365_r0_mission_query import RangerR0MissionIndex


class _FakeStore:
    provider_name = "sqlite"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.closed = False

    def build_index(self) -> RangerR0MissionIndex:
        return RangerR0MissionIndex({})

    def mission_ids(self) -> tuple[str, ...]:
        return ("mission-one",)

    def close(self) -> None:
        self.closed = True


def test_runtime_loads_durable_store_before_reporting_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mission_runtime, "SQLiteRangerR0MissionBundleStore", _FakeStore)
    monkeypatch.setenv("ETS_AGENT365_R0_BUNDLE_DB", str(tmp_path / "missions.db"))
    monkeypatch.setenv("ETS_AUTH_MODE", "local_api_key")
    monkeypatch.setenv("ETS_LOCAL_API_KEY", "not-a-secret-value")

    app = mission_runtime.create_app_from_env()
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "agent365-r0-mission-api",
        "storage": "sqlite",
        "auth": "local_api_key",
        "mission_count": 1,
    }


def test_runtime_requires_explicit_durable_store_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ETS_AGENT365_R0_BUNDLE_DB", raising=False)

    with pytest.raises(RuntimeError, match="ETS_AGENT365_R0_BUNDLE_DB"):
        mission_runtime.create_app_from_env()


def test_runtime_rejects_unknown_auth_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mission_runtime, "SQLiteRangerR0MissionBundleStore", _FakeStore)
    monkeypatch.setenv("ETS_AGENT365_R0_BUNDLE_DB", str(tmp_path / "missions.db"))
    monkeypatch.setenv("ETS_AUTH_MODE", "anonymous")

    with pytest.raises(RuntimeError, match="local_api_key or production_jwks"):
        mission_runtime.create_app_from_env()
