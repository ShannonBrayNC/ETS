from __future__ import annotations

from fastapi import FastAPI

from ets.api import container_entrypoint


def test_container_entrypoint_launches_composed_app(monkeypatch) -> None:
    app = FastAPI()
    calls: list[tuple[object, str, int]] = []

    monkeypatch.setattr(container_entrypoint, "validate_environment", lambda: None)
    monkeypatch.setattr(container_entrypoint, "create_app_from_env", lambda: app)
    monkeypatch.setattr(
        container_entrypoint.uvicorn,
        "run",
        lambda target, *, host, port: calls.append((target, host, port)),
    )

    container_entrypoint.main()

    assert calls == [(app, "0.0.0.0", 8000)]
