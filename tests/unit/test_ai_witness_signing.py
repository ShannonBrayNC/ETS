import hashlib
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.utils import (
    Prehashed,
    decode_dss_signature,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from ets.ai_witness import (
    AIWitnessEvent,
    AIWitnessLedger,
    DigestRef,
    ModelIdentity,
    SignerError,
    SigningAlgorithm,
    SoftwareECDSAP256Signer,
    TPM2ToolsECDSASigner,
    WitnessEventKind,
    verify_signature,
)

NOW = datetime(2026, 8, 21, 8, 0, tzinfo=UTC)
P256_ORDER = int(
    "FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551",
    16,
)


def event() -> AIWitnessEvent:
    prompt = b"sensitive prompt"
    return AIWitnessEvent(
        witness_id="ets-aiw:signer-test",
        session_id="session-1",
        event_id="event-1",
        sequence=0,
        kind=WitnessEventKind.MODEL_REQUEST,
        workload_ref="svc:test",
        occurred_at=NOW,
        observed_at=NOW,
        model=ModelIdentity(provider="test", model="model"),
        input_digests=(
            DigestRef(
                digest=hashlib.sha256(prompt).hexdigest(),
                byte_length=len(prompt),
            ),
        ),
    )


def ed25519_private_hex() -> str:
    return Ed25519PrivateKey.generate().private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption(),
    ).hex()


def p256_public_hex(private_key: ec.EllipticCurvePrivateKey) -> str:
    return private_key.public_key().public_bytes(
        Encoding.X962,
        PublicFormat.UncompressedPoint,
    ).hex()


class FakeTPMRunner:
    def __init__(self, private_key: ec.EllipticCurvePrivateKey):
        self.private_key = private_key
        self.last_digest: bytes | None = None
        self.last_executable: str | None = None
        self.last_key_context: str | None = None

    def sign_digest(
        self,
        *,
        executable: str,
        key_context: str,
        digest: bytes,
        timeout_seconds: float,
    ) -> bytes:
        assert timeout_seconds > 0
        self.last_digest = digest
        self.last_executable = executable
        self.last_key_context = key_context
        return self.private_key.sign(
            digest,
            ec.ECDSA(Prehashed(hashes.SHA256())),
        )


def test_legacy_constructor_preserves_v1_ed25519_records() -> None:
    ledger = AIWitnessLedger(
        witness_id="ets-aiw:signer-test",
        signing_key_id="software-ed25519",
        private_key_hex=ed25519_private_hex(),
    )
    record = ledger.record(event())

    assert record.schema_version == "ets.ai-witness.record.v1"
    assert record.signing_algorithm is SigningAlgorithm.ED25519
    assert ledger.verify_record(record, ledger.public_key_hex)


def test_ecdsa_provider_emits_algorithm_bound_v2_record() -> None:
    signer = SoftwareECDSAP256Signer(
        key_id="test-p256",
        private_scalar_hex="1".rjust(64, "0"),
    )
    ledger = AIWitnessLedger(
        witness_id="ets-aiw:signer-test",
        signer=signer,
    )
    record = ledger.record(event())

    assert record.schema_version == "ets.ai-witness.record.v2"
    assert record.signing_algorithm is SigningAlgorithm.ECDSA_P256_SHA256
    assert ledger.verify_record(record, signer.public_key_hex)

    evidence = ledger.to_evidence_event(record, tenant_id="t", workspace_id="w")
    assert evidence.metadata["ai_witness"]["signing_algorithm"] == "ecdsa-p256-sha256"


def test_v2_algorithm_substitution_fails_verification() -> None:
    signer = SoftwareECDSAP256Signer(
        key_id="test-p256",
        private_scalar_hex="2".rjust(64, "0"),
    )
    ledger = AIWitnessLedger(witness_id="ets-aiw:signer-test", signer=signer)
    record = ledger.record(event())
    tampered = record.model_copy(update={"signing_algorithm": SigningAlgorithm.ED25519})

    assert not ledger.verify_record(tampered, signer.public_key_hex)


def test_ecdsa_signatures_are_canonical_low_s() -> None:
    signer = SoftwareECDSAP256Signer(
        key_id="test-p256",
        private_scalar_hex="3".rjust(64, "0"),
    )
    ledger = AIWitnessLedger(witness_id="ets-aiw:signer-test", signer=signer)
    record = ledger.record(event())
    _, s = decode_dss_signature(bytes.fromhex(record.signature_hex))

    assert s <= P256_ORDER // 2


def test_wrong_ecdsa_public_key_fails_verification() -> None:
    signer = SoftwareECDSAP256Signer(
        key_id="test-p256",
        private_scalar_hex="4".rjust(64, "0"),
    )
    other = SoftwareECDSAP256Signer(
        key_id="other-p256",
        private_scalar_hex="5".rjust(64, "0"),
    )
    ledger = AIWitnessLedger(witness_id="ets-aiw:signer-test", signer=signer)
    record = ledger.record(event())

    assert not ledger.verify_record(record, other.public_key_hex)


def test_tpm_provider_signs_sha256_digest_without_private_key_bytes() -> None:
    private_key = ec.derive_private_key(6, ec.SECP256R1())
    runner = FakeTPMRunner(private_key)
    signer = TPM2ToolsECDSASigner(
        key_id="tpm:witness-signing-1",
        key_context="0x81010001",
        public_key_hex=p256_public_hex(private_key),
        runner=runner,
        executable="tpm2_sign",
    )
    payload = b"canonical witness record payload"
    signature = signer.sign(payload)

    assert runner.last_digest == hashlib.sha256(payload).digest()
    assert runner.last_executable == "tpm2_sign"
    assert runner.last_key_context == "0x81010001"
    assert verify_signature(
        SigningAlgorithm.ECDSA_P256_SHA256,
        signer.public_key_hex,
        payload,
        signature,
    )


def test_tpm_provider_rejects_signature_from_wrong_key() -> None:
    signing_key = ec.derive_private_key(7, ec.SECP256R1())
    advertised_key = ec.derive_private_key(8, ec.SECP256R1())
    signer = TPM2ToolsECDSASigner(
        key_id="tpm:witness-signing-1",
        key_context="0x81010001",
        public_key_hex=p256_public_hex(advertised_key),
        runner=FakeTPMRunner(signing_key),
    )

    with pytest.raises(SignerError, match="failed verification"):
        signer.sign(b"payload")


def test_signer_provider_and_private_key_hex_are_mutually_exclusive() -> None:
    signer = SoftwareECDSAP256Signer(
        key_id="test-p256",
        private_scalar_hex="9".rjust(64, "0"),
    )
    with pytest.raises(ValueError, match="must not be supplied"):
        AIWitnessLedger(
            witness_id="ets-aiw:signer-test",
            signing_key_id="test-p256",
            private_key_hex=ed25519_private_hex(),
            signer=signer,
        )
