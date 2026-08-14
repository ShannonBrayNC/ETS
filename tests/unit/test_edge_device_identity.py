from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from ets.edge.device_identity import (
    build_device_identity,
    load_device_identity,
    load_or_create_local_api_key,
    resolve_local_api_key_provisioning,
    write_device_identity,
)


def _private_key_hex() -> str:
    key = Ed25519PrivateKey.generate()
    return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()


def test_local_api_key_is_generated_once_and_persisted(tmp_path: Path) -> None:
    path = tmp_path / "edge-local-api-key"

    first = load_or_create_local_api_key(path)
    second = load_or_create_local_api_key(path)

    assert first == second
    assert len(first.encode("utf-8")) >= 32
    assert path.read_text(encoding="utf-8").strip() == first
    assert path.stat().st_mode & 0o777 == 0o600


def test_explicit_local_api_key_is_first_boot_provisioning_not_implicit_rotation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "edge-local-api-key"
    explicit = "A" * 32

    assert load_or_create_local_api_key(path, explicit) == explicit
    assert load_or_create_local_api_key(path, explicit) == explicit
    assert path.read_text(encoding="utf-8").strip() == explicit

    with pytest.raises(RuntimeError, match="conflicts with persisted credential"):
        load_or_create_local_api_key(path, "B" * 32)

    assert path.read_text(encoding="utf-8").strip() == explicit


def test_short_explicit_local_api_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "edge-local-api-key"

    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        load_or_create_local_api_key(path, "too-short")

    assert not path.exists()


def test_local_api_key_can_be_provisioned_from_secret_file(tmp_path: Path) -> None:
    secret_file = tmp_path / "edge-api-key-secret"
    secret_file.write_text("S" * 32 + "\n", encoding="utf-8")

    resolved = resolve_local_api_key_provisioning(None, str(secret_file))

    assert resolved == "S" * 32


def test_local_api_key_file_and_environment_value_are_mutually_exclusive(
    tmp_path: Path,
) -> None:
    secret_file = tmp_path / "edge-api-key-secret"
    secret_file.write_text("S" * 32, encoding="utf-8")

    with pytest.raises(RuntimeError, match="mutually exclusive"):
        resolve_local_api_key_provisioning("E" * 32, str(secret_file))


def test_local_api_key_file_configuration_fails_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing-secret"
    with pytest.raises(RuntimeError, match="unable to read"):
        resolve_local_api_key_provisioning(None, str(missing))

    empty = tmp_path / "empty-secret"
    empty.write_text("\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="file is empty"):
        resolve_local_api_key_provisioning(None, str(empty))

    short = tmp_path / "short-secret"
    short.write_text("too-short", encoding="utf-8")
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        resolve_local_api_key_provisioning(None, str(short))


def test_secret_file_provisioning_preserves_no_implicit_rotation_rule(tmp_path: Path) -> None:
    persisted = tmp_path / "edge-local-api-key"
    secret_file = tmp_path / "edge-api-key-secret"
    secret_file.write_text("A" * 32, encoding="utf-8")

    first = resolve_local_api_key_provisioning(None, str(secret_file))
    assert load_or_create_local_api_key(persisted, first) == "A" * 32

    secret_file.write_text("B" * 32, encoding="utf-8")
    conflicting = resolve_local_api_key_provisioning(None, str(secret_file))
    with pytest.raises(RuntimeError, match="conflicts with persisted credential"):
        load_or_create_local_api_key(persisted, conflicting)

    assert persisted.read_text(encoding="utf-8").strip() == "A" * 32
    assert persisted.stat().st_mode & 0o777 == 0o600


def test_device_identity_is_stable_public_metadata(tmp_path: Path) -> None:
    private_key_hex = _private_key_hex()
    identity = build_device_identity(private_key_hex, "ets-edge-virtual-demo-key")
    path = tmp_path / "edge-device-identity.json"

    write_device_identity(path, identity)
    loaded = load_device_identity(path)

    public_key_bytes = bytes.fromhex(loaded["signing_public_key_hex"])
    assert loaded == identity
    assert loaded["device_id"].startswith("ets-edge:")
    assert loaded["public_key_fingerprint_sha256"] == hashlib.sha256(public_key_bytes).hexdigest()
    assert loaded["key_custody"] == "software_volume"
    assert loaded["hardware_attested"] is False
    serialized = path.read_text(encoding="utf-8")
    assert private_key_hex not in serialized
    assert "local_api_key" not in serialized


def test_device_identity_rejects_unexpected_fields(tmp_path: Path) -> None:
    path = tmp_path / "edge-device-identity.json"
    identity = build_device_identity(_private_key_hex(), "ets-edge-virtual-demo-key")
    payload = dict(identity)
    payload["unexpected_secret"] = "must-not-be-returned"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="unexpected or missing fields"):
        load_device_identity(path)


def test_device_identity_rejects_fingerprint_drift(tmp_path: Path) -> None:
    path = tmp_path / "edge-device-identity.json"
    identity = build_device_identity(_private_key_hex(), "ets-edge-virtual-demo-key")
    payload = dict(identity)
    payload["public_key_fingerprint_sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="fingerprint does not match public key"):
        load_device_identity(path)
