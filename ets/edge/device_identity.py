"""Persistent local credential and public device-identity helpers for ETS Edge."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path
from typing import TypedDict

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


_IDENTITY_FIELDS = frozenset(EdgeDeviceIdentity.__annotations__)


def resolve_local_api_key_provisioning(
    explicit_key: str | None,
    explicit_key_file: str | None,
) -> str | None:
    """Resolve optional first-boot local API-key provisioning without logging it.

    A direct environment value and a secret-file path are mutually exclusive.
    The returned value is still validated and persisted by
    ``load_or_create_local_api_key`` so the existing no-implicit-rotation rule
    remains authoritative across restarts.
    """

    if explicit_key is not None and explicit_key_file is not None:
        raise RuntimeError(
            "ETS_LOCAL_API_KEY and ETS_LOCAL_API_KEY_FILE are mutually exclusive"
        )

    if explicit_key_file is None:
        return explicit_key

    file_value = explicit_key_file.strip()
    if not file_value:
        raise RuntimeError("ETS_LOCAL_API_KEY_FILE must not be empty")

    path = Path(file_value)
    try:
        raw_value = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"unable to read ETS local API key file: {path}") from exc

    key = raw_value.strip()
    if not key:
        raise RuntimeError("ETS local API key file is empty")
    return _validate_local_api_key(key)


def load_or_create_local_api_key(path: Path, explicit_key: str | None = None) -> str:
    """Return a durable local API key, generating at least 256 bits on first boot.

    Explicit injection is a first-boot provisioning mechanism, not an implicit
    rotation mechanism. Once a durable key exists, a conflicting injected key
    fails closed so a restart cannot silently replace the appliance credential.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        persisted = _validate_local_api_key(path.read_text(encoding="utf-8").strip())
        if explicit_key is not None:
            injected = _validate_local_api_key(explicit_key)
            if not hmac.compare_digest(
                injected.encode("utf-8"),
                persisted.encode("utf-8"),
            ):
                raise RuntimeError(
                    "injected ETS Edge local API key conflicts with persisted credential; "
                    "implicit rotation is not supported"
                )
        return persisted

    if explicit_key is not None:
        key = _validate_local_api_key(explicit_key)
    else:
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
    """Load and strictly validate the bounded public identity manifest."""

    if not path.exists():
        raise RuntimeError(f"ETS Edge device identity is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("ETS Edge device identity must be a JSON object")
    if set(payload) != _IDENTITY_FIELDS:
        raise RuntimeError("ETS Edge device identity contains unexpected or missing fields")

    string_fields = (
        "schema_version",
        "device_id",
        "signing_algorithm",
        "signing_public_key_id",
        "signing_public_key_hex",
        "public_key_fingerprint_sha256",
        "key_custody",
    )
    if any(not isinstance(payload.get(name), str) for name in string_fields):
        raise RuntimeError("ETS Edge device identity field types are invalid")

    schema_version = payload["schema_version"]
    device_id = payload["device_id"]
    signing_algorithm = payload["signing_algorithm"]
    signing_public_key_id = payload["signing_public_key_id"]
    signing_public_key_hex = payload["signing_public_key_hex"]
    fingerprint = payload["public_key_fingerprint_sha256"]
    key_custody = payload["key_custody"]
    hardware_attested = payload["hardware_attested"]

    if schema_version != "ets.edge.device_identity.v1":
        raise RuntimeError("unsupported ETS Edge device identity schema")
    if signing_algorithm != "ed25519" or not signing_public_key_id:
        raise RuntimeError("ETS Edge device identity signing declaration is invalid")
    if key_custody != "software_volume" or hardware_attested is not False:
        raise RuntimeError("ETS Edge pilot device identity custody declaration is invalid")

    try:
        public_key = bytes.fromhex(signing_public_key_hex)
    except ValueError as exc:
        raise RuntimeError("ETS Edge device identity public key is invalid") from exc
    if len(public_key) != 32:
        raise RuntimeError("ETS Edge device identity Ed25519 public key must be 32 bytes")

    expected_fingerprint = hashlib.sha256(public_key).hexdigest()
    expected_device_id = f"ets-edge:{expected_fingerprint[:32]}"
    if not hmac.compare_digest(fingerprint, expected_fingerprint):
        raise RuntimeError("ETS Edge device identity fingerprint does not match public key")
    if not hmac.compare_digest(device_id, expected_device_id):
        raise RuntimeError("ETS Edge device id does not match public key fingerprint")

    return EdgeDeviceIdentity(
        schema_version=schema_version,
        device_id=device_id,
        signing_algorithm=signing_algorithm,
        signing_public_key_id=signing_public_key_id,
        signing_public_key_hex=signing_public_key_hex,
        public_key_fingerprint_sha256=fingerprint,
        key_custody=key_custody,
        hardware_attested=False,
    )


def _validate_local_api_key(value: str) -> str:
    key = value.strip()
    if len(key.encode("utf-8")) < 32:
        raise RuntimeError("ETS Edge local API key must contain at least 32 bytes")
    return key


def _write_private_text(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")
    path.chmod(0o600)
