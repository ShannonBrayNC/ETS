import hashlib
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from pydantic import ValidationError

from ets.ai_witness import (
    AIWitnessEvent,
    AIWitnessLedger,
    DigestRef,
    ModelIdentity,
    WitnessEventKind,
    WitnessValidationError,
)

NOW = datetime(2026, 8, 21, 6, 0, tzinfo=UTC)


def digest(text: str) -> DigestRef:
    return DigestRef(digest=hashlib.sha256(text.encode()).hexdigest(), byte_length=len(text))


def key_hex() -> str:
    return Ed25519PrivateKey.generate().private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption(),
    ).hex()


def request(seq: int = 0, event_id: str = "e0") -> AIWitnessEvent:
    return AIWitnessEvent(
        witness_id="ets-aiw:test",
        session_id="s1",
        event_id=event_id,
        sequence=seq,
        kind=WitnessEventKind.MODEL_REQUEST,
        workload_ref="svc:demo",
        occurred_at=NOW,
        observed_at=NOW,
        model=ModelIdentity(provider="openai", model="gpt-test"),
        input_digests=(digest("secret prompt"),),
    )


def test_digest_only_contract_rejects_raw_fields() -> None:
    with pytest.raises(ValidationError):
        AIWitnessEvent(**{**request().model_dump(), "prompt": "secret"})


def test_model_request_requires_input_digest() -> None:
    payload = request().model_copy(update={"input_digests": ()}).model_dump()
    with pytest.raises(ValidationError):
        AIWitnessEvent.model_validate(payload)


def test_record_is_signed_and_projects_without_raw_prompt() -> None:
    ledger = AIWitnessLedger(
        witness_id="ets-aiw:test",
        signing_key_id="k1",
        private_key_hex=key_hex(),
    )
    record = ledger.record(request())
    assert ledger.verify_record(record, ledger.public_key_hex)

    evidence = ledger.to_evidence_event(record, tenant_id="t", workspace_id="w")
    assert evidence.content_hash == record.record_digest
    assert evidence.redaction_profile == "ets.ai-witness.digest-only.v1"
    assert "secret prompt" not in str(evidence.model_dump(mode="json"))


def test_session_chain_is_contiguous_and_detects_tampering() -> None:
    ledger = AIWitnessLedger(
        witness_id="ets-aiw:test",
        signing_key_id="k1",
        private_key_hex=key_hex(),
    )
    first = ledger.record(request())
    second_event = request(1, "e1").model_copy(
        update={
            "kind": WitnessEventKind.SESSION_END,
            "model": None,
            "input_digests": (),
        }
    )
    second = ledger.record(second_event)
    assert ledger.verify_chain([first, second], ledger.public_key_hex)

    tampered = second.model_copy(update={"previous_record_digest": "0" * 64})
    assert not ledger.verify_chain([first, tampered], ledger.public_key_hex)


def test_noncontiguous_and_duplicate_events_fail_closed() -> None:
    ledger = AIWitnessLedger(
        witness_id="ets-aiw:test",
        signing_key_id="k1",
        private_key_hex=key_hex(),
    )
    ledger.record(request())
    with pytest.raises(WitnessValidationError):
        ledger.record(request(2, "e2"))
    with pytest.raises(WitnessValidationError):
        ledger.record(request(1, "e0"))


def test_wrong_key_does_not_verify() -> None:
    ledger = AIWitnessLedger(
        witness_id="ets-aiw:test",
        signing_key_id="k1",
        private_key_hex=key_hex(),
    )
    record = ledger.record(request())
    other = AIWitnessLedger(
        witness_id="ets-aiw:test",
        signing_key_id="k2",
        private_key_hex=key_hex(),
    )
    assert not ledger.verify_record(record, other.public_key_hex)


def test_signing_key_id_is_cryptographically_bound() -> None:
    ledger = AIWitnessLedger(
        witness_id="ets-aiw:test",
        signing_key_id="k1",
        private_key_hex=key_hex(),
    )
    record = ledger.record(request())
    tampered = record.model_copy(update={"signing_key_id": "attacker-key"})
    assert not ledger.verify_record(tampered, ledger.public_key_hex)


def test_ledger_revalidates_copied_models() -> None:
    ledger = AIWitnessLedger(
        witness_id="ets-aiw:test",
        signing_key_id="k1",
        private_key_hex=key_hex(),
    )
    invalid = request().model_copy(update={"input_digests": ()})
    with pytest.raises(ValidationError):
        ledger.record(invalid)
