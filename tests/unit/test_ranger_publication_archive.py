import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from ets.ranger.external_publication import RangerExternalPublisher
from ets.ranger.governance import RangerGovernanceSubjectKind
from ets.ranger.publication_archive import (
    RangerPublicationArchive,
    RangerPublicationArchiveConflict,
    RangerPublicationArchiveError,
    RangerPublicationArchiveIntegrityError,
    SQLiteRangerPublicationArchiveStore,
    verify_publication_retrieval_audit,
)

NOW = datetime(2026, 9, 10, 1, 0, tzinfo=UTC)
REGISTRY_ID = "ets-verifier:ranger-registry-1"
REGISTRY_KEY_ID = "registry-software-key-1"
PUBLISHER_ID = "ets-publisher:ranger-external-1"
PUBLISHER_KEY_ID = "publisher-software-key-1"
CUSTODIAN_ID = "ets-custodian:ranger-archive-1"
CUSTODIAN_KEY_ID = "custodian-software-key-1"
REGISTRY_PUBLIC_KEY_HEX = "22" * 32


def _private_key_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()


def _public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _publisher(key: Ed25519PrivateKey) -> RangerExternalPublisher:
    return RangerExternalPublisher(
        publisher_id=PUBLISHER_ID,
        publisher_signing_key_id=PUBLISHER_KEY_ID,
        publisher_private_key_hex=_private_key_hex(key),
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
    )


def _receipts(publisher: RangerExternalPublisher, count: int = 2):
    values = []
    for sequence in range(1, count + 1):
        values.append(
            publisher.publish(
                publication_id=f"publication-{sequence}",
                subject_kind=(
                    RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD
                    if sequence % 2
                    else RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT
                ),
                subject_digest_sha256=f"{sequence:x}" * 64,
                time_attestation_digest_sha256=f"{sequence + 8:x}" * 64,
                registry_id=REGISTRY_ID,
                registry_signing_key_id=REGISTRY_KEY_ID,
                published_at_utc=NOW + timedelta(minutes=sequence),
            )
        )
    return values


def _archive(
    path: Path,
    *,
    publisher_key: Ed25519PrivateKey,
    custodian_key: Ed25519PrivateKey,
    expected_head: str | None = None,
):
    store = SQLiteRangerPublicationArchiveStore(path)
    archive = RangerPublicationArchive(
        store,
        publisher_public_key_hex=_public_key_hex(publisher_key),
        registry_public_key_hex=REGISTRY_PUBLIC_KEY_HEX,
        expected_publisher_id=PUBLISHER_ID,
        expected_publisher_signing_key_id=PUBLISHER_KEY_ID,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        custodian_id=CUSTODIAN_ID,
        custodian_signing_key_id=CUSTODIAN_KEY_ID,
        custodian_private_key_hex=_private_key_hex(custodian_key),
        expected_retained_publication_head_digest_sha256=expected_head,
    )
    return store, archive


def test_archive_retains_verified_chain_and_recovers_with_expected_head(
    tmp_path: Path,
) -> None:
    publisher_key = Ed25519PrivateKey.generate()
    custodian_key = Ed25519PrivateKey.generate()
    receipts = _receipts(_publisher(publisher_key))
    path = tmp_path / "archive.sqlite3"
    store, archive = _archive(path, publisher_key=publisher_key, custodian_key=custodian_key)

    assert archive.retain(receipts[:1]) == 1
    assert archive.retain(receipts) == 1
    assert archive.retain(receipts) == 0
    store.close()

    reopened_store, reopened = _archive(
        path,
        publisher_key=publisher_key,
        custodian_key=custodian_key,
        expected_head=receipts[-1].publication_digest_sha256,
    )
    assert reopened.latest_publication_digest_sha256 == receipts[-1].publication_digest_sha256
    assert reopened_store.list_receipts() == receipts
    reopened_store.close()


def test_archive_rejects_stale_and_tampered_presentations(tmp_path: Path) -> None:
    publisher_key = Ed25519PrivateKey.generate()
    custodian_key = Ed25519PrivateKey.generate()
    receipts = _receipts(_publisher(publisher_key))
    store, archive = _archive(
        tmp_path / "archive.sqlite3",
        publisher_key=publisher_key,
        custodian_key=custodian_key,
    )
    archive.retain(receipts)

    with pytest.raises(RangerPublicationArchiveConflict, match="stale"):
        archive.retain(receipts[:1])
    tampered = receipts[0].model_copy(update={"publication_digest_sha256": "f" * 64})
    with pytest.raises(RangerPublicationArchiveError, match="invalid"):
        archive.retain([tampered, receipts[1]])
    store.close()


def test_archive_rejects_valid_alternate_publisher_fork(tmp_path: Path) -> None:
    publisher_key = Ed25519PrivateKey.generate()
    custodian_key = Ed25519PrivateKey.generate()
    retained = _receipts(_publisher(publisher_key), count=1)
    alternate_publisher = _publisher(publisher_key)
    alternate = alternate_publisher.publish(
        publication_id="alternate-publication-1",
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256="e" * 64,
        time_attestation_digest_sha256="d" * 64,
        registry_id=REGISTRY_ID,
        registry_signing_key_id=REGISTRY_KEY_ID,
        published_at_utc=NOW + timedelta(minutes=1),
    )
    store, archive = _archive(
        tmp_path / "archive.sqlite3",
        publisher_key=publisher_key,
        custodian_key=custodian_key,
    )
    archive.retain(retained)

    with pytest.raises(RangerPublicationArchiveConflict, match="forks"):
        archive.retain([alternate])
    store.close()


def test_restored_stale_archive_fails_expected_head_guard(tmp_path: Path) -> None:
    publisher_key = Ed25519PrivateKey.generate()
    custodian_key = Ed25519PrivateKey.generate()
    receipts = _receipts(_publisher(publisher_key))
    path = tmp_path / "archive.sqlite3"
    backup = tmp_path / "archive-stale.sqlite3"
    store, archive = _archive(path, publisher_key=publisher_key, custodian_key=custodian_key)
    archive.retain(receipts[:1])
    store.close()
    shutil.copy2(path, backup)

    store, archive = _archive(path, publisher_key=publisher_key, custodian_key=custodian_key)
    archive.retain(receipts)
    store.close()

    with pytest.raises(RangerPublicationArchiveIntegrityError, match="expected retained"):
        _archive(
            backup,
            publisher_key=publisher_key,
            custodian_key=custodian_key,
            expected_head=receipts[-1].publication_digest_sha256,
        )


def test_archive_detects_tampered_index(tmp_path: Path) -> None:
    publisher_key = Ed25519PrivateKey.generate()
    custodian_key = Ed25519PrivateKey.generate()
    path = tmp_path / "archive.sqlite3"
    receipts = _receipts(_publisher(publisher_key), count=1)
    store, archive = _archive(path, publisher_key=publisher_key, custodian_key=custodian_key)
    archive.retain(receipts)
    store.close()

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE ranger_publication_archive SET publication_id = ?",
        ("substituted-publication",),
    )
    connection.commit()
    connection.close()

    tampered_store = SQLiteRangerPublicationArchiveStore(path)
    with pytest.raises(RangerPublicationArchiveIntegrityError, match="index metadata"):
        tampered_store.list_receipts()
    tampered_store.close()


def test_archive_requires_distinct_custodian_identity_and_key(tmp_path: Path) -> None:
    publisher_key = Ed25519PrivateKey.generate()
    store = SQLiteRangerPublicationArchiveStore(tmp_path / "archive.sqlite3")
    with pytest.raises(RangerPublicationArchiveError, match="distinct"):
        RangerPublicationArchive(
            store,
            publisher_public_key_hex=_public_key_hex(publisher_key),
            registry_public_key_hex=REGISTRY_PUBLIC_KEY_HEX,
            expected_publisher_id=PUBLISHER_ID,
            expected_publisher_signing_key_id=PUBLISHER_KEY_ID,
            expected_registry_id=REGISTRY_ID,
            expected_registry_signing_key_id=REGISTRY_KEY_ID,
            custodian_id=PUBLISHER_ID,
            custodian_signing_key_id=CUSTODIAN_KEY_ID,
            custodian_private_key_hex=_private_key_hex(publisher_key),
        )
    store.close()


def test_signed_retrieval_audit_verifies_bounded_match(tmp_path: Path) -> None:
    publisher_key = Ed25519PrivateKey.generate()
    custodian_key = Ed25519PrivateKey.generate()
    receipts = _receipts(_publisher(publisher_key))
    store, archive = _archive(
        tmp_path / "archive.sqlite3",
        publisher_key=publisher_key,
        custodian_key=custodian_key,
    )
    archive.retain(receipts)
    audit = archive.audit_retrieval(
        audit_id="audit-1",
        expected_publication_head_digest_sha256=receipts[-1].publication_digest_sha256,
        observed_at_utc=NOW + timedelta(hours=1),
    )

    result = verify_publication_retrieval_audit(
        audit,
        custodian_public_key_hex=archive.custodian_public_key_hex,
        expected_custodian_id=CUSTODIAN_ID,
        expected_custodian_signing_key_id=CUSTODIAN_KEY_ID,
        expected_publication_head_digest_sha256=receipts[-1].publication_digest_sha256,
    )

    assert result.valid
    assert result.matches_expected_publication_head
    assert result.freshness_relative_to_expected_head
    assert result.physical_worm_storage_proven is False
    assert result.organizational_independence_proven is False
    assert result.hardware_rollback_resistance_proven is False
    assert result.continued_availability_proven is False
    assert result.semantic_truth_proven is False
    assert result.physical_outcome_proven is False
    assert store.list_audits() == [audit]
    store.close()


def test_retrieval_audit_records_head_mismatch_and_empty_archive(tmp_path: Path) -> None:
    publisher_key = Ed25519PrivateKey.generate()
    custodian_key = Ed25519PrivateKey.generate()
    receipts = _receipts(_publisher(publisher_key), count=1)
    store, archive = _archive(
        tmp_path / "archive.sqlite3",
        publisher_key=publisher_key,
        custodian_key=custodian_key,
    )

    empty = archive.audit_retrieval(
        audit_id="audit-empty",
        expected_publication_head_digest_sha256=receipts[0].publication_digest_sha256,
        observed_at_utc=NOW,
    )
    assert empty.result == "archive_empty"
    assert empty.archive_chain_integrity_verified is False

    archive.retain(receipts)
    mismatch = archive.audit_retrieval(
        audit_id="audit-mismatch",
        expected_publication_head_digest_sha256="f" * 64,
        observed_at_utc=NOW + timedelta(hours=1),
    )
    assert mismatch.result == "head_mismatch"
    assert mismatch.archive_chain_integrity_verified
    assert mismatch.freshness_relative_to_expected_head is False
    store.close()


def test_retrieval_audit_rejects_tampering_wrong_key_and_duplicate_id(
    tmp_path: Path,
) -> None:
    publisher_key = Ed25519PrivateKey.generate()
    custodian_key = Ed25519PrivateKey.generate()
    receipts = _receipts(_publisher(publisher_key), count=1)
    store, archive = _archive(
        tmp_path / "archive.sqlite3",
        publisher_key=publisher_key,
        custodian_key=custodian_key,
    )
    archive.retain(receipts)
    audit = archive.audit_retrieval(
        audit_id="audit-1",
        expected_publication_head_digest_sha256=receipts[0].publication_digest_sha256,
        observed_at_utc=NOW,
    )

    tampered = audit.model_copy(update={"archived_receipt_count": 99})
    tampered_result = verify_publication_retrieval_audit(
        tampered,
        custodian_public_key_hex=archive.custodian_public_key_hex,
        expected_custodian_id=CUSTODIAN_ID,
        expected_custodian_signing_key_id=CUSTODIAN_KEY_ID,
        expected_publication_head_digest_sha256=receipts[0].publication_digest_sha256,
    )
    wrong_key_result = verify_publication_retrieval_audit(
        audit,
        custodian_public_key_hex=_public_key_hex(Ed25519PrivateKey.generate()),
        expected_custodian_id=CUSTODIAN_ID,
        expected_custodian_signing_key_id=CUSTODIAN_KEY_ID,
        expected_publication_head_digest_sha256=receipts[0].publication_digest_sha256,
    )

    assert not tampered_result.valid
    assert "digest" in tampered_result.reason
    assert not wrong_key_result.valid
    assert "identity or key" in wrong_key_result.reason
    with pytest.raises(RangerPublicationArchiveConflict, match="duplicate"):
        archive.audit_retrieval(
            audit_id="audit-1",
            expected_publication_head_digest_sha256=receipts[0].publication_digest_sha256,
            observed_at_utc=NOW + timedelta(hours=1),
        )
    store.close()
