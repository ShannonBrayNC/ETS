from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ets.core import EvidenceEvent, canonical_sha256


def make_event(**overrides):
    data = {
        "event_id": "evt_001",
        "tenant_id": "tenant_a",
        "workspace_id": "workspace_a",
        "evidence_id": "evidence_001",
        "event_type": "evidence.registered",
        "subject_ref": None,
        "content_hash": "a" * 64,
        "content_hash_alg": "sha256",
        "metadata": {"case": "alpha", "ordinal": 1},
        "created_at_utc": datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
    }
    data.update(overrides)
    return EvidenceEvent(**data)


def test_evidence_event_defaults_schema_version():
    event = make_event()

    assert event.schema_version == "ets.event.v1"


def test_evidence_event_requires_required_fields():
    with pytest.raises(ValidationError):
        make_event(event_id="")


def test_evidence_event_rejects_missing_required_field():
    data = make_event().model_dump()
    data.pop("tenant_id")

    with pytest.raises(ValidationError):
        EvidenceEvent(**data)


def test_evidence_event_requires_timezone_aware_created_at():
    with pytest.raises(ValidationError):
        make_event(created_at_utc=datetime(2026, 5, 18, 12, 30))


def test_hashable_payload_excludes_server_generated_fields():
    event = make_event(source_system="unit-test")
    payload = event.hashable_payload()

    assert "log_index" not in payload
    assert "inclusion_proof" not in payload
    assert payload["source_system"] == "unit-test"


def test_hashable_payload_is_canonical_and_stable():
    left = make_event(metadata={"b": 2, "a": 1})
    right = make_event(metadata={"a": 1, "b": 2})

    assert canonical_sha256(left.hashable_payload()) == canonical_sha256(right.hashable_payload())


def test_optional_fields_do_not_break_round_trip():
    event = make_event(
        actor_id="actor_001",
        correlation_id="corr_001",
        external_refs={"ticket": "T-1"},
        redaction_profile="local",
    )

    canonical_sha256(event.hashable_payload())
    round_tripped = EvidenceEvent.model_validate(event.model_dump())
    assert round_tripped.hashable_payload() == event.hashable_payload()
