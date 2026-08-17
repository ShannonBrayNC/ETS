from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

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


def test_container_entrypoint_import_defers_hosted_app_composition() -> None:
    env = os.environ.copy()
    env.update(
        {
            "ETS_STORAGE_PROVIDER": "azure_table",
            "ETS_SIGNING_MODE": "azure_key_vault",
            "ETS_AUTH_MODE": "production_jwks",
        }
    )
    for name in (
        "ETS_AZURE_TABLE_ENDPOINT",
        "ETS_AZURE_TABLE_NAME",
        "ETS_AZURE_KEY_VAULT_URL",
        "ETS_AZURE_KEY_NAME",
    ):
        env.pop(name, None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import ets.api.container_entrypoint; "
                "assert 'ets.api.app' not in sys.modules"
            ),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
