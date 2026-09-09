from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from pydantic import ValidationError

from ets.ranger import external_publication as target
from ets.ranger.governance import (
    RangerGovernanceSubjectKind,
    build_trusted_time_attestation,
)
from ets.ranger.timed_retained_receipts import RangerTimeAttestedReceiptVerification

NOW = datetime(2026, 9, 9, 15, 0, tzinfo=UTC)
REGISTRY_ID = "ets-verifier:ranger-registry-1"
REGISTRY_KEY_ID = "registry-software-key-1"
PUBLISHER_ID = "ets-publisher:ranger-external-1"
PUBLISHER_KEY_ID = "publisher-software-key-1"
TIME_SOURCE_ID = "ets-time:ranger-configured-1"
TIME_KEY_ID = "time-software-key-1"
SUBJECT_DIGEST = "a" * 64
TIME_DIGEST = "b" * 64


def _private_key_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()


def _public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _publisher(private_material: Ed25519PrivateKey | None = None) -> target.RangerExternalPublisher:
    signing_key = private_material or Ed25519PrivateKey.generate()
    return target.RangerExternalPublisher(
        publisher_id=PUBLISHER_ID,
        publisher_signing_key_id=PUBLISHER_KEY_ID,
        publisher_private_key_hex=_private_key_hex(signing_key),
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
    )


def _publish(
    publisher: target.RangerExternalPublisher,
    *,
    sequence: int = 1,
    subject_kind: RangerGovernanceSubjectKind = (
        RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD
    ),
    subject_digest: str = SUBJECT_DIGEST,
    time_digest: str = TIME_DIGEST,
):
    return publisher.publish(
        publication_id=f"publication-{sequence}",
        subject_kind=subject_kind,
        subject_digest_sha256=subject_digest,
        time_attestation_digest_sha256=time_digest,
        registry_id=REGISTRY_ID,
        registry_signing_key_id=REGISTRY_KEY_ID,
        published_at_utc=NOW + timedelta(minutes=sequence),
    )


def _verify_chain(
    publisher: target.RangerExternalPublisher,
    receipts,
    *,
    expected_head: str,
    publisher_public_key_hex: str | None = None,
):
    return target.verify_external_publication_chain(
        receipts,
        publisher_public_key_hex=(publisher_public_key_hex or publisher.publisher_public_key_hex),
        expected_publisher_id=PUBLISHER_ID,
        expected_publisher_signing_key_id=PUBLISHER_KEY_ID,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        expected_latest_publication_digest_sha256=expected_head,
    )


def _time_attestation():
    key = Ed25519PrivateKey.generate()
    return build_trusted_time_attestation(
        attestation_id="time-attestation-1",
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256=SUBJECT_DIGEST,
        observed_at_utc=NOW,
        uncertainty_ms=25,
        time_source_id=TIME_SOURCE_ID,
        time_signing_key_id=TIME_KEY_ID,
        time_private_key_hex=_private_key_hex(key),
    )


def _timed_result(
    *,
    kind: RangerGovernanceSubjectKind = RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
    subject_digest: str = SUBJECT_DIGEST,
    time_digest: str = TIME_DIGEST,
    valid: bool = True,
) -> RangerTimeAttestedReceiptVerification:
    if not valid:
        return RangerTimeAttestedReceiptVerification(valid=False, reason="synthetic failure")
    return RangerTimeAttestedReceiptVerification(
        valid=True,
        receipt_kind=kind,
        receipt_digest_sha256=subject_digest,
        registry_sequence=1,
        time_attestation_digest_sha256=time_digest,
        registry_id=REGISTRY_ID,
        registry_signing_key_id=REGISTRY_KEY_ID,
        time_source_id=TIME_SOURCE_ID,
        time_signing_key_id=TIME_KEY_ID,
        receipt_chain_integrity_proven=True,
        configured_registry_identity_proven=True,
        trusted_time_proven=True,
        configured_time_identity_proven=True,
        reason="synthetic valid result",
    )


def _compose_authority_head(
    monkeypatch,
    publisher: target.RangerExternalPublisher,
    receipts,
    *,
    timed: RangerTimeAttestedReceiptVerification | None = None,
    publisher_public_key_hex: str | None = None,
    registry_public_key_hex: str | None = None,
):
    result = timed or _timed_result()
    monkeypatch.setattr(
        target,
        "verify_time_attested_authority_head",
        lambda *args, **kwargs: result,
    )
    registry_key = registry_public_key_hex or _public_key_hex(Ed25519PrivateKey.generate())
    return target.verify_externally_published_authority_head(
        [],
        _time_attestation(),
        receipts,
        registry_public_key_hex=registry_key,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex="11" * 32,
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
        publisher_public_key_hex=(publisher_public_key_hex or publisher.publisher_public_key_hex),
        expected_publisher_id=PUBLISHER_ID,
        expected_publisher_signing_key_id=PUBLISHER_KEY_ID,
        expected_latest_publication_digest_sha256=receipts[-1].publication_digest_sha256,
    )


def test_external_publication_chain_verifies_against_expected_head() -> None:
    publisher = _publisher()
    first = _publish(publisher)
    second = _publish(
        publisher,
        sequence=2,
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest="c" * 64,
        time_digest="d" * 64,
    )

    result = _verify_chain(
        publisher,
        [first, second],
        expected_head=second.publication_digest_sha256,
    )

    assert result.valid
    assert result.receipt_count == 2
    assert result.latest_publication_sequence == 2
    assert result.configured_external_publisher_receipts_proven
    assert result.matches_expected_publication_head
    assert result.freshness_relative_to_expected_head


def test_stale_publication_prefix_does_not_match_expected_head() -> None:
    publisher = _publisher()
    first = _publish(publisher)
    second = _publish(
        publisher,
        sequence=2,
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest="c" * 64,
        time_digest="d" * 64,
    )

    result = _verify_chain(
        publisher,
        [first],
        expected_head=second.publication_digest_sha256,
    )

    assert not result.valid
    assert "expected head" in result.reason
    assert result.freshness_relative_to_expected_head is False


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("publisher_signature_hex", "00" * 64, "signature"),
        ("publication_digest_sha256", "f" * 64, "digest"),
    ],
)
def test_publication_chain_rejects_tampering(field: str, value: str, reason: str) -> None:
    publisher = _publisher()
    receipt = _publish(publisher)
    tampered = receipt.model_copy(update={field: value})

    result = _verify_chain(
        publisher,
        [tampered],
        expected_head=tampered.publication_digest_sha256,
    )

    assert not result.valid
    assert reason in result.reason


def test_publication_chain_rejects_tampered_predecessor() -> None:
    publisher = _publisher()
    first = _publish(publisher)
    second = _publish(
        publisher,
        sequence=2,
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest="c" * 64,
        time_digest="d" * 64,
    )
    tampered = second.model_copy(update={"previous_publication_digest_sha256": "e" * 64})

    result = _verify_chain(
        publisher,
        [first, tampered],
        expected_head=tampered.publication_digest_sha256,
    )

    assert not result.valid
    assert "predecessor" in result.reason


def test_publication_chain_rejects_missing_genesis_and_reordering() -> None:
    publisher = _publisher()
    first = _publish(publisher)
    second = _publish(
        publisher,
        sequence=2,
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest="c" * 64,
        time_digest="d" * 64,
    )

    missing = _verify_chain(
        publisher,
        [second],
        expected_head=second.publication_digest_sha256,
    )
    reordered = _verify_chain(
        publisher,
        [second, first],
        expected_head=first.publication_digest_sha256,
    )

    assert not missing.valid
    assert "sequence" in missing.reason
    assert not reordered.valid
    assert "sequence" in reordered.reason


def test_publication_chain_rejects_substituted_key() -> None:
    publisher = _publisher()
    receipt = _publish(publisher)

    result = _verify_chain(
        publisher,
        [receipt],
        expected_head=receipt.publication_digest_sha256,
        publisher_public_key_hex=_public_key_hex(Ed25519PrivateKey.generate()),
    )

    assert not result.valid
    assert "fingerprint" in result.reason


def test_publisher_rejects_duplicate_binding_and_time_regression() -> None:
    publisher = _publisher()
    _publish(publisher)

    with pytest.raises(target.RangerExternalPublicationError, match="already been published"):
        _publish(publisher, sequence=2)
    with pytest.raises(target.RangerExternalPublicationError, match="time must advance"):
        publisher.publish(
            publication_id="publication-2",
            subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
            subject_digest_sha256="c" * 64,
            time_attestation_digest_sha256="d" * 64,
            registry_id=REGISTRY_ID,
            registry_signing_key_id=REGISTRY_KEY_ID,
            published_at_utc=NOW,
        )


def test_publisher_rejects_registry_identity_substitution() -> None:
    publisher = _publisher()

    with pytest.raises(target.RangerExternalPublicationError, match="registry identity"):
        publisher.publish(
            publication_id="publication-1",
            subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
            subject_digest_sha256=SUBJECT_DIGEST,
            time_attestation_digest_sha256=TIME_DIGEST,
            registry_id="ets-verifier:substituted",
            registry_signing_key_id=REGISTRY_KEY_ID,
            published_at_utc=NOW,
        )


def test_publisher_rejects_non_retained_subject() -> None:
    publisher = _publisher()

    with pytest.raises(target.RangerExternalPublicationError, match="retained Ranger receipt"):
        publisher.publish(
            publication_id="publication-1",
            subject_kind=RangerGovernanceSubjectKind.ADMINISTRATIVE_APPROVAL,
            subject_digest_sha256=SUBJECT_DIGEST,
            time_attestation_digest_sha256=TIME_DIGEST,
            registry_id=REGISTRY_ID,
            registry_signing_key_id=REGISTRY_KEY_ID,
            published_at_utc=NOW,
        )


def test_composed_authority_head_publication_verifies(monkeypatch) -> None:
    publisher = _publisher()
    receipt = _publish(publisher)

    result = _compose_authority_head(monkeypatch, publisher, [receipt])

    assert result.valid
    assert result.time_attested_retained_receipt_proven
    assert result.configured_external_publisher_receipt_proven
    assert result.publisher_key_distinct_from_registry_proven
    assert result.matches_expected_publication_head
    assert result.continued_external_custody_proven is False
    assert result.publisher_organizational_independence_proven is False
    assert result.globally_current_state_proven is False
    assert result.semantic_truth_proven is False
    assert result.physical_outcome_proven is False


def test_composed_publication_rejects_registry_publisher_key_reuse(monkeypatch) -> None:
    publisher = _publisher()
    receipt = _publish(publisher)

    result = _compose_authority_head(
        monkeypatch,
        publisher,
        [receipt],
        registry_public_key_hex=publisher.publisher_public_key_hex,
    )

    assert not result.valid
    assert "distinct" in result.reason


def test_composed_publication_rejects_wrong_retained_binding(monkeypatch) -> None:
    publisher = _publisher()
    receipt = _publish(publisher, subject_digest="c" * 64)

    result = _compose_authority_head(monkeypatch, publisher, [receipt])

    assert not result.valid
    assert "does not bind" in result.reason


def test_composed_publication_rejects_invalid_time_attested_receipt(monkeypatch) -> None:
    publisher = _publisher()
    receipt = _publish(publisher)

    result = _compose_authority_head(
        monkeypatch,
        publisher,
        [receipt],
        timed=_timed_result(valid=False),
    )

    assert not result.valid
    assert "time-attested retained receipt is invalid" in result.reason


def test_composed_authority_checkpoint_uses_checkpoint_verifier(monkeypatch) -> None:
    publisher = _publisher()
    receipt = _publish(
        publisher,
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
    )
    timed = _timed_result(kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT)
    monkeypatch.setattr(
        target,
        "verify_time_attested_authority_checkpoint",
        lambda *args, **kwargs: timed,
    )
    registry_public_key = _public_key_hex(Ed25519PrivateKey.generate())

    result = target.verify_externally_published_authority_checkpoint(
        [],
        _time_attestation(),
        [receipt],
        registry_public_key_hex=registry_public_key,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        time_public_key_hex="11" * 32,
        expected_time_source_id=TIME_SOURCE_ID,
        expected_time_signing_key_id=TIME_KEY_ID,
        publisher_public_key_hex=publisher.publisher_public_key_hex,
        expected_publisher_id=PUBLISHER_ID,
        expected_publisher_signing_key_id=PUBLISHER_KEY_ID,
        expected_latest_publication_digest_sha256=receipt.publication_digest_sha256,
    )

    assert result.valid
    assert result.subject_kind is RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT


def test_publication_contract_is_strict_and_versioned() -> None:
    publisher = _publisher()
    receipt = _publish(publisher)
    payload = receipt.model_dump(mode="json")
    payload["invented_custody_claim"] = True

    with pytest.raises(ValidationError):
        target.RangerExternalPublicationReceipt.model_validate(payload)
    schema = target.RangerExternalPublicationReceipt.model_json_schema()
    assert schema["$id"].endswith("/external-publication-receipt/v1")
    assert schema["additionalProperties"] is False
