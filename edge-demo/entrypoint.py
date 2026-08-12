"""Entrypoint for the controlled ETS Edge Virtual demo profile.

This wrapper intentionally configures the existing ETS API as a single-node,
local-only virtual edge appliance. It uses durable SQLite storage and a
persistent software Ed25519 identity stored in the appliance data volume.

It is a demo/lab profile, not a production trust-service configuration.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import uvicorn

DATA_DIR = Path(os.getenv("ETS_EDGE_DATA_DIR", "/var/lib/ets"))
KEY_PATH = DATA_DIR / "edge-demo-signing-key.hex"


def _load_or_create_signing_key() -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        key_hex = KEY_PATH.read_text(encoding="utf-8").strip()
        if len(key_hex) != 64:
            raise RuntimeError(f"invalid persisted ETS Edge demo signing key: {KEY_PATH}")
        return key_hex

    key_hex = secrets.token_hex(32)
    KEY_PATH.write_text(key_hex + "\n", encoding="utf-8")
    KEY_PATH.chmod(0o600)
    return key_hex


def main() -> None:
    signing_key_hex = _load_or_create_signing_key()

    os.environ.setdefault("ETS_STORAGE_PROVIDER", "sqlite")
    os.environ.setdefault("ETS_SQLITE_PATH", str(DATA_DIR / "edge.db"))
    os.environ.setdefault("ETS_LOG_ID", "ets-edge-virtual-demo")
    os.environ.setdefault("ETS_REDACTION_PROFILE", "none")
    os.environ.setdefault("ETS_AUTH_MODE", "local_header")
    os.environ.setdefault("ETS_SIGNING_MODE", "ed25519")
    os.environ.setdefault("ETS_SIGNING_PUBLIC_KEY_ID", "ets-edge-virtual-demo-key")
    os.environ.setdefault("ETS_ALLOW_INSECURE_LOCAL", "1")
    os.environ["ETS_SIGNING_PRIVATE_KEY_HEX"] = signing_key_hex

    # Import the ETS API package only after the complete demo environment exists.
    # ets.api package initialization constructs the environment-configured app.
    from ets.api.profile_guard import validate_environment

    validate_environment()
    uvicorn.run("ets.api.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
