"""Persistent local credential and public device-identity helpers for ETS Edge."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path
from typing import TypedDict

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
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
_SCRYPT_SCHEMA = "scrypt-v1"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_SCRYPT_SALT_BYTES = 16
_ENCRYPTED_API_KEY_SCHEMA = "ets.edge.local_api_key.encrypted.v1"
_ENCRYPTED_API_KEY_AAD = _ENCRYPTED_API_KEY_SCHEMA.encode("ascii")
_STORAGE_KEY_INFO = b"ets.edge.local-api-key.storage.v1"


def resolve_local_api_key_provisioning(
    explicit_key: str | None,
    explicit_key_file: str | None,
) -> str | None:
    """Resolve optional first-boot local API-key provisioning without logging it.

    A direct environment value and a secret-file path are mutually exclusive.
    The returned value is still validated before use. Secret-file provisioning
    is intentionally handled by ``validate_or_record_local_api_key_verifier``
    so the mounted secret is never copied into Edge's persistent data volume.
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


def validate_or_record_local_api_key_verifier(path: Path, explicit_key: str) -> str:
    """Validate a mounted API key against a durable salted scrypt verifier.

    Secret-file provisioning keeps the plaintext credential in the external
    secret mount and process memory only. Edge persists a versioned, salted,
    memory-hard verifier solely to detect unexpected credential changes across
    restarts; it does not persist a recoverable copy of the mounted credential.
    """

    key = _validate_local_api_key(explicit_key)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        salt, expected = _parse_local_api_key_verifier(path.read_text(encoding="utf-8"))
        actual = _derive_local_api_key_verifier(key, salt)
        if not hmac.compare_digest(expected, actual):
            raise RuntimeError(
                "mounted ETS Edge local API key conflicts with persisted verifier; "
                "implicit rotation is not supported"
            )
        return key

    salt = secrets.token_bytes(_SCRYPT_SALT_BYTES)
    verifier = _derive_local_api_key_verifier(key, salt)
    payload = "$".join(
        (
            _SCRYPT_SCHEMA,
            str(_SCRYPT_N),
            str(_SCRYPT_R),
            str(_SCRYPT_P),
            salt.hex(),
            verifier.hex(),
        )
    )
    path.write_text(payload + "\n", encoding="utf-8")
    path.chmod(0o600)
    return key


def load_or_create_local_api_key(
    path: Path,
    explicit_key: str | None = None,
    *,
    storage_key_material: str,
) -> str:
    """Return a durable local API key without storing that credential in clear text.

    Generated or directly injected credentials are AES-256-GCM encrypted at rest
    using a domain-separated storage key derived from the Edge software signing
    key. Existing legacy clear-text files are migrated in place after validation.
    Secret-file provisioning uses the scrypt-verifier path above instead.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        serialized = path.read_text(encoding="utf-8").strip()
        persisted, legacy_cleartext = _decode_local_api_key_storage(
            path,
            serialized,
            storage_key_material,
        )
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
        if legacy_cleartext:
            _write_encrypted_local_api_key(path, persisted, storage_key_material)
        return persisted

    key = _validate_local_api_key(explicit_key) if explicit_key is not None else secrets.token_urlsafe(32)
    _write_encrypted_local_api_key(path, key, storage_key_material)
    return key


def load_local_api_key(path: Path, *, storage_key_material: str | None = None) -> str:
    """Load an Edge API key from encrypted local storage or an external secret file."""

    if not path.exists():
        raise RuntimeError(f"ETS Edge local API key is missing: {path}")
    serialized = path.read_text(encoding="utf-8").strip()
    if serialized.startswith("{"):
        material = storage_key_material or _load_default_storage_key_material(path)
        key, _ = _decode_local_api_key_storage(path, serialized, material)
        return key
    return _validate_local_api_key(serialized)


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


def _derive_local_api_key_verifier(key: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        key.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )


def _parse_local_api_key_verifier(value: str) -> tuple[bytes, bytes]:
    parts = value.strip().split("$")
    if len(parts) != 6:
        raise RuntimeError("persisted ETS Edge local API key verifier is invalid")
    schema, n_value, r_value, p_value, salt_hex, verifier_hex = parts
    if schema != _SCRYPT_SCHEMA:
        raise RuntimeError("persisted ETS Edge local API key verifier is invalid")
    try:
        parameters = (int(n_value), int(r_value), int(p_value))
        salt = bytes.fromhex(salt_hex)
        verifier = bytes.fromhex(verifier_hex)
    except ValueError as exc:
        raise RuntimeError("persisted ETS Edge local API key verifier is invalid") from exc
    if parameters != (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P):
        raise RuntimeError("persisted ETS Edge local API key verifier is invalid")
    if len(salt) != _SCRYPT_SALT_BYTES or len(verifier) != _SCRYPT_DKLEN:
        raise RuntimeError("persisted ETS Edge local API key verifier is invalid")
    return salt, verifier


def _derive_storage_key(storage_key_material: str) -> bytes:
    try:
        source = bytes.fromhex(storage_key_material.strip())
    except ValueError as exc:
        raise RuntimeError("ETS Edge credential storage key material is invalid") from exc
    if len(source) != 32:
        raise RuntimeError("ETS Edge credential storage key material must be 32 bytes")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_STORAGE_KEY_INFO,
    ).derive(source)


def _write_encrypted_local_api_key(path: Path, key: str, storage_key_material: str) -> None:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_derive_storage_key(storage_key_material)).encrypt(
        nonce,
        key.encode("utf-8"),
        _ENCRYPTED_API_KEY_AAD,
    )
    payload = {
        "schema_version": _ENCRYPTED_API_KEY_SCHEMA,
        "nonce_hex": nonce.hex(),
        "ciphertext_hex": ciphertext.hex(),
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _decode_local_api_key_storage(
    path: Path,
    serialized: str,
    storage_key_material: str,
) -> tuple[str, bool]:
    if not serialized.startswith("{"):
        return _validate_local_api_key(serialized), True
    try:
        payload = json.loads(serialized)
    except json.JSONDecodeError as exc:
        raise RuntimeError("persisted ETS Edge local API key storage is invalid") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "nonce_hex",
        "ciphertext_hex",
    }:
        raise RuntimeError("persisted ETS Edge local API key storage is invalid")
    if payload.get("schema_version") != _ENCRYPTED_API_KEY_SCHEMA:
        raise RuntimeError("persisted ETS Edge local API key storage is invalid")
    try:
        nonce = bytes.fromhex(str(payload["nonce_hex"]))
        ciphertext = bytes.fromhex(str(payload["ciphertext_hex"]))
    except ValueError as exc:
        raise RuntimeError("persisted ETS Edge local API key storage is invalid") from exc
    if len(nonce) != 12 or len(ciphertext) < 16:
        raise RuntimeError("persisted ETS Edge local API key storage is invalid")
    try:
        plaintext = AESGCM(_derive_storage_key(storage_key_material)).decrypt(
            nonce,
            ciphertext,
            _ENCRYPTED_API_KEY_AAD,
        )
        key = plaintext.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("persisted ETS Edge local API key storage is invalid") from exc
    return _validate_local_api_key(key), False


def _load_default_storage_key_material(path: Path) -> str:
    key_path = path.parent / "edge-demo-signing-key.hex"
    if not key_path.exists():
        raise RuntimeError("ETS Edge credential storage key material is unavailable")
    return key_path.read_text(encoding="utf-8").strip()
