"""Entrypoint for the controlled ETS Edge Virtual protected pilot profile.

This wrapper configures the existing ETS API as a single-node local virtual edge
appliance with durable SQLite state, a persistent software Ed25519 signing
identity, and a persistent local API key. It is not a production trust-service
or hardware-attested configuration.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import uvicorn

from ets.edge.device_identity import (
    build_device_identity,
    load_or_create_local_api_key,
    resolve_local_api_key_provisioning,
    write_device_identity,
)

DATA_DIR = Path(os.getenv("ETS_EDGE_DATA_DIR", "/var/lib/ets"))
KEY_PATH = DATA_DIR / "edge-demo-signing-key.hex"
API_KEY_PATH = DATA_DIR / "edge-local-api-key"
DEVICE_IDENTITY_PATH = DATA_DIR / "edge-device-identity.json"


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
    public_key_id = os.getenv("ETS_SIGNING_PUBLIC_KEY_ID", "ets-edge-virtual-demo-key")
    explicit_api_key = resolve_local_api_key_provisioning(
        os.getenv("ETS_LOCAL_API_KEY"),
        os.getenv("ETS_LOCAL_API_KEY_FILE"),
    )
    local_api_key = load_or_create_local_api_key(API_KEY_PATH, explicit_api_key)
    identity = build_device_identity(signing_key_hex, public_key_id)
    write_device_identity(DEVICE_IDENTITY_PATH, identity)

    os.environ.setdefault("ETS_STORAGE_PROVIDER", "sqlite")
    os.environ.setdefault("ETS_SQLITE_PATH", str(DATA_DIR / "edge.db"))
    os.environ.setdefault("ETS_LOG_ID", "ets-edge-virtual-demo")
    os.environ.setdefault("ETS_REDACTION_PROFILE", "none")
    os.environ.setdefault("ETS_AUTH_MODE", "local_api_key")
    os.environ.setdefault("ETS_SIGNING_MODE", "ed25519")
    os.environ.setdefault("ETS_SIGNING_PUBLIC_KEY_ID", public_key_id)
    os.environ["ETS_SIGNING_PRIVATE_KEY_HEX"] = signing_key_hex
    os.environ["ETS_LOCAL_API_KEY"] = local_api_key
    os.environ["ETS_EDGE_API_KEY_FILE"] = str(API_KEY_PATH)
    os.environ["ETS_EDGE_DEVICE_IDENTITY_FILE"] = str(DEVICE_IDENTITY_PATH)

    # Import the ETS API package only after the complete protected pilot
    # environment exists. Package initialization constructs the configured app.
    from ets.api.profile_guard import validate_environment

    validate_environment()
    uvicorn.run("ets.api.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
