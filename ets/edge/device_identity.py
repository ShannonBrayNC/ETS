"""Persistent local credential and public device-identity helpers for ETS Edge."""

from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import TypedDict, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


class EdgeDeviceIdentity(TypedDict):
    schema_version: str
    device_id: str
    signing_algorithm: str
    signing_public_key_id: str
    signing_public_key_hex: str
    public_key_fingerprint_sha256: str
    key_custody: str
    hardware_attested: bool


def load_or_create_local_api_key(path: Path, explicit_key: str | None = None) -> str:
    """Return a durable local API key, generating at least 256 bits on first boot."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if explicit_key is not None:
        key = _validate_local_api_key(explicit_key)
        _write_private_text(path, key)
        return key

    if path.exists():
        return _validate_local_api_key(path.read_text(encoding="utf-8").strip())

    key = secrets.token_urlsafe(32)
    _write_private_text(path, key)
    return key


def load_local_api_key(path: Path) -> str:
    """Load the persisted Edge local API key without generating a replacement."""

    if not path.exists():
        raise RuntimeError(f"ETS Edge local API key is missing: {path}")
    return _validate_local_api_key(path.read_text(encoding="utf-8").strip())


def build_device_identity(private_key_hex: str, public_key_id: str) -> EdgeDeviceIdentity:
    """Build a non-secret software device identity from an Ed25519 signing key."""

    if not public_key_id:
        raise RuntimeError("ETS Edge signing public key id is required")
    try:
        private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    except ValueError as exc:
        raise RuntimeError("ETS Edge signing private key must be 32 bytes") from exc

    public_key = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    public_key_hex = public_key.hex()
    fingerprint = hashlib.sha256(public_key).hexdigest()
    return EdgeDeviceIdentity(
        schema_version="ets.edge.device_identity.v1",
        device_id=f"ets-edge:{fingerprint[:32]}",
        signing_algorithm="ed25519",
        signing_public_key_id=public_key_id,
        signing_public_key_hex=public_key_hex,
        public_key_fingerprint_sha256=fingerprint,
        key_custody="software_volume",
        hardware_attested=False,
    )


def write_device_identity(path: Path, identity: EdgeDeviceIdentity) -> None:
    """Persist only the bounded public identity manifest."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(identity, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o644)


def load_device_identity(path: Path) -> EdgeDeviceIdentity:
    """Load and minimally validate the public identity manifest."""

    if not path.exists():
        raise RuntimeError(f"ETS Edge device identity is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("ETS Edge device identity must be a JSON object")
    if payload.get("schema_version") != "ets.edge.device_identity.v1":
        raise RuntimeError("unsupported ETS Edge device identity schema")
    invalid_custody = (
        payload.get("key_custody") != "software_volume"
        or payload.get("hardware_attested") is not False
    )
    if invalid_custody:
        raise RuntimeError("ETS Edge pilot device identity custody declaration is invalid")
    return cast(EdgeDeviceIdentity, payload)


def _validate_local_api_key(value: str) -> str:
    key = value.strip()
    if len(key.encode("utf-8")) < 32:
        raise RuntimeError("ETS Edge local API key must contain at least 32 bytes")
    return key


def _write_private_text(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")
    path.chmod(0o600)
