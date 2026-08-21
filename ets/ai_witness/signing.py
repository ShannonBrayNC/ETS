"""Algorithm-agile signer providers for ETS AI Witness records."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ets.ai_witness.models import SigningAlgorithm

_P256_ORDER = int(
    "FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551",
    16,
)


class SignerError(RuntimeError):
    """Raised when a Witness signer cannot safely produce a signature."""


class WitnessSigner(Protocol):
    """Minimal signer boundary used by the algorithm-agile Witness ledger."""

    @property
    def key_id(self) -> str: ...

    @property
    def algorithm(self) -> SigningAlgorithm: ...

    @property
    def public_key_hex(self) -> str: ...

    @property
    def public_key_fingerprint_sha256(self) -> str: ...

    def sign(self, payload: bytes) -> bytes: ...


class TPMCommandRunner(Protocol):
    """Narrow command boundary for invoking a TPM-backed signing operation."""

    def sign_digest(
        self,
        *,
        executable: str,
        key_context: str,
        digest: bytes,
        timeout_seconds: float,
    ) -> bytes: ...


class SoftwareEd25519Signer:
    """Software-only compatibility signer for existing Witness record v1."""

    def __init__(self, *, key_id: str, private_key_hex: str):
        self._key_id = _validate_identifier(key_id, "key_id", 256)
        try:
            key_bytes = bytes.fromhex(private_key_hex)
            self._private_key = Ed25519PrivateKey.from_private_bytes(key_bytes)
        except ValueError as exc:
            raise SignerError("private key must be a 32-byte Ed25519 key") from exc

    @property
    def key_id(self) -> str:
        return self._key_id

    @property
    def algorithm(self) -> SigningAlgorithm:
        return SigningAlgorithm.ED25519

    @property
    def public_key_hex(self) -> str:
        return self._private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    @property
    def public_key_fingerprint_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.public_key_hex)).hexdigest()

    def sign(self, payload: bytes) -> bytes:
        return self._private_key.sign(payload)


class SoftwareECDSAP256Signer:
    """Software ECDSA signer used for deterministic provider/conformance tests."""

    def __init__(self, *, key_id: str, private_scalar_hex: str):
        self._key_id = _validate_identifier(key_id, "key_id", 256)
        try:
            private_scalar = int(private_scalar_hex, 16)
        except ValueError as exc:
            raise SignerError("P-256 private scalar must be hexadecimal") from exc
        if not 1 <= private_scalar < _P256_ORDER:
            raise SignerError("P-256 private scalar is out of range")
        self._private_key = ec.derive_private_key(private_scalar, ec.SECP256R1())

    @property
    def key_id(self) -> str:
        return self._key_id

    @property
    def algorithm(self) -> SigningAlgorithm:
        return SigningAlgorithm.ECDSA_P256_SHA256

    @property
    def public_key_hex(self) -> str:
        return self._private_key.public_key().public_bytes(
            Encoding.X962,
            PublicFormat.UncompressedPoint,
        ).hex()

    @property
    def public_key_fingerprint_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.public_key_hex)).hexdigest()

    def sign(self, payload: bytes) -> bytes:
        signature = self._private_key.sign(payload, ec.ECDSA(hashes.SHA256()))
        return normalize_ecdsa_p256_signature(signature)


class SubprocessTPMCommandRunner:
    """Invoke tpm2_sign without a shell or private-key material in process memory."""

    def sign_digest(
        self,
        *,
        executable: str,
        key_context: str,
        digest: bytes,
        timeout_seconds: float,
    ) -> bytes:
        if len(digest) != 32:
            raise SignerError("TPM ECDSA signing requires a 32-byte SHA-256 digest")
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise SignerError("TPM signing timeout must be in the range (0, 120]")

        with tempfile.TemporaryDirectory(prefix="ets-aiw-tpm-sign-") as directory:
            root = Path(directory)
            digest_path = root / "payload.sha256"
            signature_path = root / "signature.der"
            digest_path.write_bytes(digest)
            command = [
                executable,
                "-Q",
                "-c",
                key_context,
                "-g",
                "sha256",
                "-s",
                "ecdsa",
                "-d",
                "-f",
                "plain",
                "-o",
                str(signature_path),
                str(digest_path),
            ]
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    timeout=timeout_seconds,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise SignerError("TPM signing command could not complete") from exc
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                detail = stderr[-512:] if stderr else "no diagnostic output"
                raise SignerError(f"TPM signing command failed: {detail}")
            try:
                return signature_path.read_bytes()
            except OSError as exc:
                raise SignerError("TPM signing command did not produce a signature") from exc


class TPM2ToolsECDSASigner:
    """TPM-resident ECDSA P-256 signer backed by an existing TPM key context."""

    def __init__(
        self,
        *,
        key_id: str,
        key_context: str,
        public_key_hex: str,
        runner: TPMCommandRunner | None = None,
        executable: str = "tpm2_sign",
        timeout_seconds: float = 10.0,
    ):
        self._key_id = _validate_identifier(key_id, "key_id", 256)
        self._key_context = _validate_identifier(key_context, "key_context", 512)
        self._executable = _validate_identifier(executable, "executable", 512)
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise SignerError("TPM signing timeout must be in the range (0, 120]")
        self._timeout_seconds = timeout_seconds
        self._runner = runner or SubprocessTPMCommandRunner()
        self._public_key_hex = _validate_p256_public_key(public_key_hex)

    @property
    def key_id(self) -> str:
        return self._key_id

    @property
    def algorithm(self) -> SigningAlgorithm:
        return SigningAlgorithm.ECDSA_P256_SHA256

    @property
    def public_key_hex(self) -> str:
        return self._public_key_hex

    @property
    def public_key_fingerprint_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.public_key_hex)).hexdigest()

    def sign(self, payload: bytes) -> bytes:
        digest = hashlib.sha256(payload).digest()
        signature = self._runner.sign_digest(
            executable=self._executable,
            key_context=self._key_context,
            digest=digest,
            timeout_seconds=self._timeout_seconds,
        )
        signature = normalize_ecdsa_p256_signature(signature)
        if not verify_signature(
            SigningAlgorithm.ECDSA_P256_SHA256,
            self.public_key_hex,
            payload,
            signature,
        ):
            raise SignerError("TPM signature failed verification under configured public key")
        return signature


def verify_signature(
    algorithm: SigningAlgorithm,
    public_key_hex: str,
    payload: bytes,
    signature: bytes,
) -> bool:
    """Verify an AI Witness signature using the algorithm-specific public encoding."""

    try:
        public_bytes = bytes.fromhex(public_key_hex)
        if algorithm is SigningAlgorithm.ED25519:
            public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
            public_key.verify(signature, payload)
            return True

        public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(),
            public_bytes,
        )
        public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError):
        return False
    return True


def normalize_ecdsa_p256_signature(signature: bytes) -> bytes:
    """Return canonical low-S DER for an ECDSA P-256 signature."""

    try:
        r, s = decode_dss_signature(signature)
    except ValueError as exc:
        raise SignerError("ECDSA P-256 signature is not valid DER") from exc
    if not 1 <= r < _P256_ORDER or not 1 <= s < _P256_ORDER:
        raise SignerError("ECDSA P-256 signature scalar is out of range")
    if s > _P256_ORDER // 2:
        s = _P256_ORDER - s
    return encode_dss_signature(r, s)


def _validate_p256_public_key(value: str) -> str:
    try:
        raw = bytes.fromhex(value)
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)
    except ValueError as exc:
        raise SignerError("public key must be an encoded P-256 point") from exc
    return value.lower()


def _validate_identifier(value: str, label: str, maximum: int) -> str:
    if not value or len(value) > maximum or "\x00" in value:
        raise SignerError(f"{label} must contain 1-{maximum} characters without NUL")
    return value
