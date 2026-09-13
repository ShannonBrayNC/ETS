from __future__ import annotations

import hashlib
import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

import scripts.azure_migration_historical_key_offline_verify as offline
from ets.core.signing import tree_head_signature_payload
from ets.core.tree_head import SignedTreeHead


def _fixture(tmp_path: Path) -> tuple[Path, Path, str, rsa.RSAPrivateKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    public_key = private_key.public_key()
    pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_path = tmp_path / "source-public.pem"
    key_path.write_bytes(pem)

    key_id = (
        "https://source.example.vault.azure.net/keys/ets-tree-head/"
        + offline._HISTORICAL_SIGNER_VERSION_ID
    )
    unsigned = SignedTreeHead(
        tree_size=37,
        root_hash="a" * 64,
        created_at_utc=datetime(2026, 9, 7, 4, 16, tzinfo=UTC),
        log_id="ets-live-primary",
        signature_alg="ps256",
        signature=None,
        public_key_id=key_id,
    )
    digest = hashlib.sha256(tree_head_signature_payload(unsigned)).digest()
    signature = private_key.sign(
        digest,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=hashes.SHA256().digest_size,
        ),
        Prehashed(hashes.SHA256()),
    )
    signed = unsigned.model_copy(update={"signature": signature.hex()})
    tree_path = tmp_path / "tree-head.json"
    tree_path.write_text(signed.model_dump_json(), encoding="utf-8")
    return tree_path, key_path, key_id, private_key


def _set_expected_hashes(monkeypatch: pytest.MonkeyPatch, key_path: Path) -> None:
    pem = key_path.read_bytes()
    public_key = serialization.load_pem_public_key(pem)
    assert isinstance(public_key, rsa.RSAPublicKey)
    der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    monkeypatch.setattr(
        offline,
        "_EXPECTED_PEM_SHA256",
        hashlib.sha256(pem).hexdigest(),
    )
    monkeypatch.setattr(
        offline,
        "_EXPECTED_DER_SHA256",
        hashlib.sha256(der).hexdigest(),
    )


def test_verify_offline_accepts_historical_ps256_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tree_path, key_path, key_id, _private = _fixture(tmp_path)
    _set_expected_hashes(monkeypatch, key_path)

    result = offline.verify_offline(
        tree_head_path=tree_path,
        source_public_key_pem=key_path,
        expected_source_key_id=key_id,
    )

    assert result["positive_signature_verification"] is True
    assert result["tampered_payload_rejected"] is True
    assert result["tampered_signature_rejected"] is True
    assert result["source_key_vault_contacted"] is False
    assert result["azure_login_required"] is False
    assert result["private_key_material_used"] is False


def test_verify_offline_rejects_wrong_key_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tree_path, key_path, _key_id, _private = _fixture(tmp_path)
    _set_expected_hashes(monkeypatch, key_path)
    wrong = (
        "https://source.example/keys/ets-tree-head/"
        + offline._HISTORICAL_SIGNER_VERSION_ID
    )

    with pytest.raises(offline.OfflineVerificationError, match="public key ID mismatch"):
        offline.verify_offline(
            tree_head_path=tree_path,
            source_public_key_pem=key_path,
            expected_source_key_id=wrong,
        )


def test_verify_offline_rejects_public_key_hash_mismatch(tmp_path: Path) -> None:
    tree_path, key_path, key_id, _private = _fixture(tmp_path)

    with pytest.raises(offline.OfflineVerificationError, match="PEM SHA-256 mismatch"):
        offline.verify_offline(
            tree_head_path=tree_path,
            source_public_key_pem=key_path,
            expected_source_key_id=key_id,
        )


def test_verify_offline_rejects_alternate_key_as_negative_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tree_path, key_path, key_id, _private = _fixture(tmp_path)
    _set_expected_hashes(monkeypatch, key_path)
    alternate = rsa.generate_private_key(public_exponent=65537, key_size=3072).public_key()
    alternate_path = tmp_path / "destination-public.pem"
    alternate_path.write_bytes(
        alternate.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    result = offline.verify_offline(
        tree_head_path=tree_path,
        source_public_key_pem=key_path,
        expected_source_key_id=key_id,
        alternate_public_key_pem=alternate_path,
    )

    assert result["alternate_public_key_negative_control"] is True


def test_module_has_no_azure_or_network_dependency() -> None:
    source = inspect.getsource(offline)
    for forbidden in (
        "azure.identity",
        "azure.keyvault",
        "azure.mgmt",
        "requests.",
        "urllib.request",
        "httpx.",
        "subprocess",
        "az login",
        "CryptographyClient",
    ):
        assert forbidden not in source
