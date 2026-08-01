from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ets.evidence_object import (
    Assertion,
    Claim,
    EvidenceIdentity,
    EvidenceObject,
    Relationship,
    RelationshipType,
    canonical_bytes,
    object_hash,
)


def sample_object() -> EvidenceObject:
    return EvidenceObject(
        identity=EvidenceIdentity(
            evidence_id="release:ets:v0.1.0-alpha",
            version=1,
            namespace="lantern-protocol",
            evidence_type="software-release",
        ),
        created_at=datetime(2026, 8, 1, 19, 0, tzinfo=UTC),
        claims=(
            Claim(
                claim_id="claim:build",
                subject="release:ets:v0.1.0-alpha",
                predicate="build.status",
                value="passed",
                confidence=1.0,
                source_ref="workflow:ci:234",
            ),
        ),
        assertions=(
            Assertion(
                assertion_id="assertion:build",
                claim_id="claim:build",
                actor_ref="system:github-actions",
                asserted_at=datetime(2026, 8, 1, 19, 1, tzinfo=UTC),
            ),
        ),
        relationships=(
            Relationship(
                relationship_id="relationship:source",
                relationship_type=RelationshipType.DERIVED,
                target_evidence_ref="evidence:commit:ed5f363",
            ),
        ),
        policy_refs=("policy:software-release:v1",),
        extensions={"lantern": {"repository": "ShannonBrayNC/ETS"}},
    )


def test_evidence_object_is_deterministic() -> None:
    evidence = sample_object()

    assert canonical_bytes(evidence) == canonical_bytes(evidence)
    assert object_hash(evidence) == object_hash(evidence)
    assert len(object_hash(evidence)) == 64


def test_evidence_object_normalizes_timestamps_to_utc() -> None:
    evidence = sample_object()

    assert evidence.created_at.tzinfo is UTC
    assert evidence.assertions[0].asserted_at.tzinfo is UTC


def test_assertion_must_reference_existing_claim() -> None:
    with pytest.raises(ValidationError, match="unknown claim_id"):
        EvidenceObject(
            identity=EvidenceIdentity(
                evidence_id="evidence:1",
                version=1,
                namespace="test",
                evidence_type="test",
            ),
            created_at=datetime(2026, 8, 1, tzinfo=UTC),
            assertions=(
                Assertion(
                    assertion_id="assertion:1",
                    claim_id="claim:missing",
                    actor_ref="actor:test",
                    asserted_at=datetime(2026, 8, 1, tzinfo=UTC),
                ),
            ),
        )


def test_unknown_normative_fields_are_rejected() -> None:
    payload = sample_object().model_dump(mode="json")
    payload["trust_score"] = 99

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        EvidenceObject.model_validate(payload)


def test_claim_requires_object_or_value() -> None:
    with pytest.raises(ValidationError, match="claim requires object or value"):
        Claim(
            claim_id="claim:empty",
            subject="subject:test",
            predicate="test.predicate",
        )
