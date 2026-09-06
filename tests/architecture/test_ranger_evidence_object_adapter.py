from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ets.ranger.decision_event import decision_event_digest
from ets.ranger.evidence_object_adapter import (
    RangerEvidenceObjectAdapterError,
    ranger_decision_event_to_evidence_object,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "docs/research/ranger/examples/decision-event-unknown.json"


def _sealed_event() -> dict[str, object]:
    event = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    event["event_digest"] = decision_event_digest(event)
    return event


def test_adapter_projects_ranger_identity_context_and_integrity() -> None:
    event = _sealed_event()
    evidence = ranger_decision_event_to_evidence_object(event)

    assert evidence.identity.evidence_id == event["event_id"]
    assert evidence.identity.evidence_type == "ranger-decision-event"
    assert evidence.identity.namespace.endswith(str(event["mission_id"]))
    assert evidence.provenance is not None
    assert evidence.provenance.device_ref == event["ranger_id"]
    assert evidence.policy_refs == (event["decision"]["policy_id"],)
    assert len(evidence.integrity) == 1
    assert evidence.integrity[0].digest == str(event["event_digest"]).removeprefix("sha256:")
    assert evidence.integrity[0].scope == "ranger-decision-event-preimage"


def test_adapter_preserves_epistemic_unknown_without_upgrading_claim() -> None:
    evidence = ranger_decision_event_to_evidence_object(_sealed_event())

    identity_claim = next(item for item in evidence.claims if item.claim_id == "claim-identity")
    assert identity_claim.value["epistemic_state"] == "UNKNOWN"
    assert identity_claim.value["value"] is None
    assert "No enrolled principal" in identity_claim.value["reason"]


def test_adapter_preserves_participating_and_excluded_claim_context() -> None:
    evidence = ranger_decision_event_to_evidence_object(_sealed_event())

    decision_context = next(
        item for item in evidence.contexts if item.context_type == "ranger-decision"
    )
    assert decision_context.attributes["participating_claim_ids"] == [
        "claim-human-detected",
        "claim-identity",
    ]
    assert decision_context.attributes["excluded_claim_ids"] == []
    assert decision_context.attributes["selected_action"] == "maintain_distance"


def test_adapter_projects_claim_source_dependencies() -> None:
    evidence = ranger_decision_event_to_evidence_object(_sealed_event())

    dependency_targets = {
        relationship.target_evidence_ref for relationship in evidence.relationships
    }
    assert dependency_targets == {
        "evidence-camera-001",
        "evidence-enrollment-set-001",
    }


def test_adapter_preserves_complete_source_event_in_namespaced_extension() -> None:
    event = _sealed_event()
    evidence = ranger_decision_event_to_evidence_object(event)

    extension = evidence.extensions[
        "org.lanternprotocol.ranger.decision-event.v0.1"
    ]
    assert extension["included_in_object_hash"] is True
    assert extension["decision_event"] == event


def test_adapter_rejects_unsealed_event() -> None:
    event = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    with pytest.raises(RangerEvidenceObjectAdapterError, match="event_digest"):
        ranger_decision_event_to_evidence_object(event)


def test_adapter_rejects_tampered_event_even_when_digest_field_is_retained() -> None:
    event = _sealed_event()
    tampered = copy.deepcopy(event)
    tampered["decision"]["selected_action"] = "continue"

    with pytest.raises(RangerEvidenceObjectAdapterError, match="digest mismatch"):
        ranger_decision_event_to_evidence_object(tampered)
