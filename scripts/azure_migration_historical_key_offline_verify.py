#!/usr/bin/env python3
"""Verify historical ETS tree-head signatures without source Azure access."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError

from ets.core.signing import verify_tree_head_signature
from ets.core.tree_head import SignedTreeHead

_HISTORICAL_SIGNER_VERSION_ID = "9f578feb997d49abb0a42b5e41651996"
_EXPECTED_PEM_SHA256 = "316823e13778e9514e498a9d0ecbb85aa02780aea99f4697d62a7fec54fbff32"
_EXPECTED_DER_SHA256 = "9b23ad8fa446dfd10fe09405dab607da69808c33d82b229ff61b9c050eec98ec"


class OfflineVerificationError(RuntimeError):
    """Fail-closed historical verification error."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise OfflineVerificationError(f"{label} is unavailable") from exc
    if not payload:
        raise OfflineVerificationError(f"{label} is empty")
    return payload


def _load_tree_head(path: Path) -> tuple[SignedTreeHead, bytes]:
    payload = _read_bytes(path, "Historical tree head")
    try:
        tree_head = SignedTreeHead.model_validate_json(payload)
    except (ValidationError, ValueError) as exc:
        raise OfflineVerificationError("Historical tree head is invalid") from exc
    if tree_head.signature_alg != "ps256":
        raise OfflineVerificationError("Historical tree head is not PS256 signed")
    if not tree_head.signature:
        raise OfflineVerificationError("Historical tree head has no signature")
    if not tree_head.public_key_id:
        raise OfflineVerificationError("Historical tree head has no public key ID")
    return tree_head, payload


def _load_rsa_public_pem(
    path: Path,
    *,
    expected_pem_sha256: str | None = None,
    expected_der_sha256: str | None = None,
) -> tuple[rsa.RSAPublicKey, bytes, str, str]:
    pem = _read_bytes(path, "Public key PEM")
    pem_sha = _sha256(pem)
    if expected_pem_sha256 is not None and pem_sha != expected_pem_sha256:
        raise OfflineVerificationError("Public key PEM SHA-256 mismatch")
    try:
        public_key = serialization.load_pem_public_key(pem)
    except (TypeError, ValueError) as exc:
        raise OfflineVerificationError("Public key PEM is invalid") from exc
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise OfflineVerificationError("Historical public key is not RSA")
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    der_sha = _sha256(der)
    if expected_der_sha256 is not None and der_sha != expected_der_sha256:
        raise OfflineVerificationError("Public key DER SHA-256 mismatch")
    return public_key, der, pem_sha, der_sha


def _tampered_root(tree_head: SignedTreeHead) -> SignedTreeHead:
    replacement = ("0" if tree_head.root_hash[0] != "0" else "1") + tree_head.root_hash[1:]
    return tree_head.model_copy(update={"root_hash": replacement})


def _tampered_signature(tree_head: SignedTreeHead) -> SignedTreeHead:
    signature = tree_head.signature or ""
    if len(signature) < 2:
        raise OfflineVerificationError("Historical signature encoding is invalid")
    replacement = ("00" if signature[:2] != "00" else "01") + signature[2:]
    return tree_head.model_copy(update={"signature": replacement})


def verify_offline(
    *,
    tree_head_path: Path,
    source_public_key_pem: Path,
    expected_source_key_id: str,
    alternate_public_key_pem: Path | None = None,
) -> dict[str, Any]:
    if not expected_source_key_id.strip():
        raise OfflineVerificationError("Expected historical public key ID is required")
    if not expected_source_key_id.rstrip("/").endswith(
        "/" + _HISTORICAL_SIGNER_VERSION_ID
    ):
        raise OfflineVerificationError("Expected key ID does not pin the historical key version")

    tree_head, tree_head_bytes = _load_tree_head(tree_head_path)
    if tree_head.public_key_id != expected_source_key_id:
        raise OfflineVerificationError("Historical tree head public key ID mismatch")

    source_key, source_der, pem_sha, der_sha = _load_rsa_public_pem(
        source_public_key_pem,
        expected_pem_sha256=_EXPECTED_PEM_SHA256,
        expected_der_sha256=_EXPECTED_DER_SHA256,
    )
    if source_key.key_size != 3072:
        raise OfflineVerificationError("Historical source RSA key size is unexpected")

    source_der_hex = source_der.hex()
    if not verify_tree_head_signature(tree_head, source_der_hex):
        raise OfflineVerificationError("Historical tree head signature verification failed")
    if verify_tree_head_signature(_tampered_root(tree_head), source_der_hex):
        raise OfflineVerificationError("Tampered historical payload unexpectedly verified")
    if verify_tree_head_signature(_tampered_signature(tree_head), source_der_hex):
        raise OfflineVerificationError("Tampered historical signature unexpectedly verified")

    alternate_checked = False
    if alternate_public_key_pem is not None:
        _alternate_key, alternate_der, _pem_sha, _der_sha = _load_rsa_public_pem(
            alternate_public_key_pem
        )
        alternate_checked = True
        if verify_tree_head_signature(tree_head, alternate_der.hex()):
            raise OfflineVerificationError(
                "Alternate public key unexpectedly verified source evidence"
            )

    return {
        "schema_version": "ets.azure-migration.historical-key-offline-verification.v1",
        "claim": "historical_source_tree_head_verifies_without_source_key_vault",
        "tree_head_sha256": _sha256(tree_head_bytes),
        "tree_size": tree_head.tree_size,
        "log_id": tree_head.log_id,
        "source_key_version": _HISTORICAL_SIGNER_VERSION_ID,
        "source_public_key_id_sha256": _sha256(expected_source_key_id.encode("utf-8")),
        "source_public_pem_sha256": pem_sha,
        "source_public_der_sha256": der_sha,
        "source_rsa_key_bits": source_key.key_size,
        "positive_signature_verification": True,
        "tampered_payload_rejected": True,
        "tampered_signature_rejected": True,
        "alternate_public_key_negative_control": alternate_checked,
        "source_key_vault_contacted": False,
        "azure_login_required": False,
        "private_key_material_used": False,
    }


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True, indent=2)
        stream.write("\n")


def _write_summary(result: dict[str, Any]) -> None:
    lines = [
        "## Historical source signing-key offline verification",
        "",
        "- qualification: `pass`",
        f"- tree size: `{result['tree_size']}`",
        f"- source key version: `{result['source_key_version']}`",
        f"- retained PEM SHA-256: `{result['source_public_pem_sha256']}`",
        f"- retained DER SHA-256: `{result['source_public_der_sha256']}`",
        "- historical PS256 signature: `verified`",
        "- tampered payload negative control: `rejected`",
        "- tampered signature negative control: `rejected`",
        (
            "- alternate-key negative control: `rejected`"
            if result["alternate_public_key_negative_control"]
            else "- alternate-key negative control: `not supplied`"
        ),
        "- source Key Vault contacted: `false`",
        "- Azure login required: `false`",
        "- private key material used: `false`",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-head", required=True)
    parser.add_argument("--source-public-key-pem", required=True)
    parser.add_argument("--expected-source-key-id", required=True)
    parser.add_argument("--alternate-public-key-pem")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        result = verify_offline(
            tree_head_path=Path(args.tree_head),
            source_public_key_pem=Path(args.source_public_key_pem),
            expected_source_key_id=args.expected_source_key_id,
            alternate_public_key_pem=(
                Path(args.alternate_public_key_pem)
                if args.alternate_public_key_pem
                else None
            ),
        )
        _write_private_json(Path(args.output), result)
        _write_summary(result)
    except (OfflineVerificationError, OSError, ValueError) as exc:
        print(f"Historical offline verification blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
