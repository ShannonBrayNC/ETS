from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/ranger/decision-event.v0.1.schema.json"
DOC_PATH = ROOT / "docs/research/ranger/core-alignment.md"


def _schema() -> dict[str, object]:
    value = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_ranger_core_alignment_document_exists_and_names_core_profiles() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    for profile in (
        "ets.canonical.json.v1",
        "ets.hash.sha256.v1",
        "ets.signature.ed25519.v1",
        "ets.evidence-object.v1",
    ):
        assert profile in text


def test_ranger_event_digest_is_not_self_referential() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "excluding" in text
    assert "`event_digest`" in text
    assert "`signature`" in text
    assert "cannot participate in its own preimage" in text


def test_ranger_core_alignment_preserves_integrity_truth_boundary() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "integrity and truth" in text
    assert "MUST NOT conclude solely from a valid digest/signature" in text
    assert "a biometric match identified the actual human with certainty" in text


def test_ranger_core_alignment_conserves_epistemic_state() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    for state in (
        "UNKNOWN",
        "INDETERMINATE",
        "NOT_AVAILABLE",
        "NOT_OBSERVED",
        "CONTRADICTED",
    ):
        assert state in text
    assert "Verification and transport MUST conserve epistemic state" in text


def test_ranger_schema_has_digest_chain_and_signature_fields() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert "previous_event_digest" in properties
    assert "event_digest" in properties
    assert "signature" in properties
    assert properties["event_digest"]["pattern"] == "^sha256:[0-9a-f]{64}$"


def test_ranger_decision_exposes_participating_and_excluded_claims() -> None:
    schema = _schema()
    defs = schema["$defs"]
    assert isinstance(defs, dict)
    decision = defs["decision"]
    assert isinstance(decision, dict)
    props = decision["properties"]
    assert "participating_claim_ids" in props
    assert "excluded_claim_ids" in props


def test_ranger_core_mapping_uses_namespaced_extension() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert 'extensions["net.lanternprotocol.ranger.decision-event.v0.1"]' in text
    assert 'identity.evidence_type = "ranger-decision-event"' in text
