from __future__ import annotations

from copy import deepcopy

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ets.ranger.decision_event import (
    decision_event_canonical_bytes,
    decision_event_digest,
    decision_event_preimage,
    sign_decision_event,
    verify_decision_event,
)

_PRIVATE_KEY_HEX = "11" * 32


def _public_key_hex() -> str:
    private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(_PRIVATE_KEY_HEX))
    return private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _event() -> dict[str, object]:
    return {
        "schema_version": "ranger.decision-event.v0.1",
        "event_id": "evt-0001",
        "mission_id": "mission-alpha",
        "ranger_id": "ets-ranger:r0-001",
        "occurred_at": "2026-09-06T10:00:00Z",
        "subject_context": [
            {
                "subject_id": "SUBJECT-A921",
                "subject_scope": "MISSION_PSEUDONYM",
                "claims": [
                    {
                        "claim_id": "claim-human",
                        "kind": "human-detected",
                        "value": True,
                        "state": "KNOWN",
                        "confidence": 0.998,
                        "threshold": 0.8,
                        "mechanism": "vision-model:v1",
                        "source_refs": ["evidence-camera-1"],
                        "reason": None,
                        "contradicts_claim_ids": [],
                    },
                    {
                        "claim_id": "claim-identity",
                        "kind": "registered-principal-identity",
                        "state": "UNKNOWN",
                        "confidence": None,
                        "threshold": 0.95,
                        "mechanism": "local-face-template:v1",
                        "source_refs": ["evidence-camera-1"],
                        "reason": "no enrolled principal exceeded threshold",
                        "contradicts_claim_ids": [],
                    },
                ],
            }
        ],
        "decision": {
            "decision_id": "decision-0001",
            "policy_id": "ranger.person-contact.v1",
            "candidate_actions": ["maintain_distance", "approach"],
            "selected_action": "maintain_distance",
            "authorization_state": "AUTHORIZED",
            "participating_claim_ids": ["claim-human", "claim-identity"],
            "excluded_claim_ids": [],
            "decision_reason": "unknown identity requires bounded distance",
        },
        "evidence": [
            {
                "evidence_id": "evidence-camera-1",
                "evidence_type": "camera-frame",
                "source_id": "camera-front",
                "captured_at": "2026-09-06T09:59:59.900Z",
                "digest": "sha256:" + ("ab" * 32),
                "uri": None,
            }
        ],
        "previous_event_digest": "sha256:" + ("00" * 32),
        "event_digest": None,
        "signature": None,
    }


def test_preimage_excludes_only_digest_and_signature() -> None:
    event = _event()
    preimage = decision_event_preimage(event)
    assert "event_digest" not in preimage
    assert "signature" not in preimage
    assert preimage["previous_event_digest"] == event["previous_event_digest"]
    assert preimage["subject_context"] == event["subject_context"]
    assert preimage["decision"] == event["decision"]


def test_canonical_bytes_and_digest_are_deterministic() -> None:
    event = _event()
    reordered = dict(reversed(list(event.items())))
    assert decision_event_canonical_bytes(event) == decision_event_canonical_bytes(reordered)
    assert decision_event_digest(event) == decision_event_digest(reordered)


def test_sign_and_verify_decision_event() -> None:
    signed = sign_decision_event(
        _event(), private_key_hex=_PRIVATE_KEY_HEX, key_id="ranger-r0-test-key"
    )
    assert signed["event_digest"] == decision_event_digest(signed)
    assert verify_decision_event(signed, public_key_hex=_public_key_hex()) is True


def test_mutating_epistemic_state_breaks_verification() -> None:
    signed = sign_decision_event(
        _event(), private_key_hex=_PRIVATE_KEY_HEX, key_id="ranger-r0-test-key"
    )
    mutated = deepcopy(signed)
    mutated["subject_context"][0]["claims"][1]["state"] = "KNOWN"  # type: ignore[index]
    assert verify_decision_event(mutated, public_key_hex=_public_key_hex()) is False


def test_mutating_participating_claim_breaks_verification() -> None:
    signed = sign_decision_event(
        _event(), private_key_hex=_PRIVATE_KEY_HEX, key_id="ranger-r0-test-key"
    )
    mutated = deepcopy(signed)
    mutated["decision"]["participating_claim_ids"] = ["claim-human"]  # type: ignore[index]
    assert verify_decision_event(mutated, public_key_hex=_public_key_hex()) is False


def test_mutating_evidence_digest_breaks_verification() -> None:
    signed = sign_decision_event(
        _event(), private_key_hex=_PRIVATE_KEY_HEX, key_id="ranger-r0-test-key"
    )
    mutated = deepcopy(signed)
    mutated["evidence"][0]["digest"] = "sha256:" + ("cd" * 32)  # type: ignore[index]
    assert verify_decision_event(mutated, public_key_hex=_public_key_hex()) is False


def test_mutating_previous_event_digest_breaks_verification() -> None:
    signed = sign_decision_event(
        _event(), private_key_hex=_PRIVATE_KEY_HEX, key_id="ranger-r0-test-key"
    )
    mutated = deepcopy(signed)
    mutated["previous_event_digest"] = "sha256:" + ("ff" * 32)
    assert verify_decision_event(mutated, public_key_hex=_public_key_hex()) is False


def test_mutating_signature_only_does_not_change_event_digest_but_fails_signature() -> None:
    signed = sign_decision_event(
        _event(), private_key_hex=_PRIVATE_KEY_HEX, key_id="ranger-r0-test-key"
    )
    original_digest = signed["event_digest"]
    mutated = deepcopy(signed)
    mutated["signature"]["value"] = "00" * 64  # type: ignore[index]
    assert decision_event_digest(mutated) == original_digest
    assert verify_decision_event(mutated, public_key_hex=_public_key_hex()) is False
