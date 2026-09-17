from datetime import UTC, datetime

from ets.evidence_object import (
    ContractBinding,
    EvidenceIdentityV2,
    EvidenceObjectV2,
    identity_hash,
    identity_payload,
)


def test_v2_identity_payload_omits_none_privacy_without_key_error() -> None:
    evidence = EvidenceObjectV2(
        identity=EvidenceIdentityV2(
            object_id="evidence-object-v2:test-optional-privacy",
            namespace="urn:ets:test",
            object_type="test",
            version=1,
        ),
        created_at=datetime(2026, 9, 17, 18, 0, tzinfo=UTC),
        bindings=(
            ContractBinding(
                binding_type="context",
                contract_id="test.contract.v1",
                subject_ref="subject:test",
            ),
        ),
    )

    payload = identity_payload(evidence)

    assert "privacy" not in payload
    assert len(identity_hash(evidence)) == 64
