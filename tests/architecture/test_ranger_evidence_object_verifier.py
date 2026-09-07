from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from ets.evidence_object.canonical import object_hash
from ets.ranger.decision_event import decision_event_digest, sign_decision_event
from ets.ranger.evidence_object_adapter import ranger_decision_event_to_evidence_object
from ets.ranger.evidence_object_verifier import verify_ranger_evidence_object

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "docs/research/ranger/examples/decision-event-unknown.json"


def _event() -> dict[str, object]:
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    value["event_digest"] = decision_event_digest(value)
    return value


def test_reverse_verifier_separates_integrity_epistemics_and_truth() -> None:
    event = _event()
    evidence = ranger_decision_event_to_evidence_object(event)
    expected_hash = object_hash(evidence)

    result = verify_ranger_evidence_object(
        evidence,
        expected_object_hash=expected_hash,
    )

    assert result.ranger_event_digest_valid is True
    assert result.ranger_integrity_binding_valid is True
    assert result.ranger_signature_status == "ABSENT"
    assert result.outer_object_hash_valid is True
    assert result.policy_id == "policy-r0-maintain-distance-from-unknown-v1"
    assert result.selected_action == "maintain_distance"
    assert result.truth_claim_supported is False
    assert "do_not_prove" in result.truth_claim_boundary

    identity = next(item for item in result.claim_findings if item.claim_id == "claim-identity")
    assert identity.epistemic_state == "UNKNOWN"
    assert identity.participating is True
    assert identity.excluded is False
    assert identity.reason


def test_reverse_verifier_validates_signature_only_with_supplied_trusted_key() -> None:
    private_key = Ed25519PrivateKey.generate()
    private_hex = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()
    public_hex = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    signed = sign_decision_event(_event(), private_key_hex=private_hex, key_id="test-key")
    evidence = ranger_decision_event_to_evidence_object(signed)

    without_key = verify_ranger_evidence_object(evidence)
    with_key = verify_ranger_evidence_object(evidence, ranger_public_key_hex=public_hex)

    assert without_key.ranger_signature_status == "UNVERIFIED_NO_TRUSTED_KEY"
    assert with_key.ranger_signature_status == "VALID"


def test_reverse_verifier_detects_wrong_signature_key_without_upgrading_truth() -> None:
    signer = Ed25519PrivateKey.generate()
    private_hex = signer.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()
    signed = sign_decision_event(_event(), private_key_hex=private_hex, key_id="test-key")
    evidence = ranger_decision_event_to_evidence_object(signed)

    wrong_key = (
        Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    )
    result = verify_ranger_evidence_object(evidence, ranger_public_key_hex=wrong_key)

    assert result.ranger_event_digest_valid is True
    assert result.ranger_integrity_binding_valid is True
    assert result.ranger_signature_status == "INVALID"
    assert result.truth_claim_supported is False


def test_reverse_verifier_detects_wrong_expected_outer_hash() -> None:
    evidence = ranger_decision_event_to_evidence_object(_event())
    result = verify_ranger_evidence_object(evidence, expected_object_hash="0" * 64)
    assert result.outer_object_hash_valid is False


def test_reverse_verifier_detects_tampered_embedded_event_even_if_object_rebuilt() -> None:
    original = ranger_decision_event_to_evidence_object(_event())
    payload = original.model_dump()
    tampered = deepcopy(payload)
    extension = tampered["extensions"]["org.lanternprotocol.ranger.decision-event.v0.1"]
    extension["decision_event"]["decision"]["selected_action"] = "continue"

    rebuilt = type(original).model_validate(tampered)
    result = verify_ranger_evidence_object(rebuilt)

    assert result.ranger_event_digest_valid is False
    assert result.ranger_integrity_binding_valid is False
    assert result.selected_action == "continue"
    assert result.truth_claim_supported is False
