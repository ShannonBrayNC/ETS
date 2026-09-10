import hashlib
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

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.external_publication import RangerExternalPublicationReceipt
from ets.ranger.governance import RangerGovernanceSubjectKind
from ets.ranger.publication_archive import RangerPublicationRetrievalAudit
from ets.ranger.publication_key_lifecycle import (
    RangerPublicationKeyAuthorityLedger,
    RangerPublicationKeyBindingIntent,
    RangerPublicationKeyEventKind,
    RangerPublicationKeyLifecycleConflict,
    RangerPublicationKeyLifecycleError,
    RangerPublicationKeyLifecycleIntegrityError,
    RangerPublicationKeyRevocationReason,
    RangerPublicationKeyRole,
    RangerPublicationKeySourceKind,
    RangerPublicationSigningKeyDescriptor,
    SQLiteRangerPublicationKeyAuthorityStore,
    build_publication_key_binding_request,
    publication_key_binding_intent_bytes,
    verify_publication_lifecycle_chain,
    verify_publication_source_key_standing,
)

NOW = datetime(2026, 9, 10, 2, 0, tzinfo=UTC)
SCOPE_ID = "ets-ranger-publication:demo-reference-1"
PUBLISHER_ID = "ets-publisher:ranger-external-1"
CUSTODIAN_ID = "ets-custodian:ranger-archive-1"
AUTHORITY_ID = "ets-authority:ranger-publication-keys-1"
AUTHORITY_KEY_ID = "publication-key-authority-1"
REGISTRY_ID = "ets-verifier:ranger-registry-1"
REGISTRY_KEY_ID = "registry-software-key-1"


def _private_key_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()


def _public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def _descriptor(key: Ed25519PrivateKey, key_id: str) -> RangerPublicationSigningKeyDescriptor:
    public_key_hex = _public_key_hex(key)
    return RangerPublicationSigningKeyDescriptor(
        signing_key_id=key_id,
        public_key_hex=public_key_hex,
        public_key_fingerprint_sha256=hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest(),
    )


def _ledger(
    path: Path,
) -> tuple[
    RangerPublicationKeyAuthorityLedger,
    SQLiteRangerPublicationKeyAuthorityStore,
    Ed25519PrivateKey,
]:
    authority_key = Ed25519PrivateKey.generate()
    store = SQLiteRangerPublicationKeyAuthorityStore(path)
    ledger = RangerPublicationKeyAuthorityLedger(
        store,
        publication_scope_id=SCOPE_ID,
        publisher_id=PUBLISHER_ID,
        custodian_id=CUSTODIAN_ID,
        authority_id=AUTHORITY_ID,
        authority_signing_key_id=AUTHORITY_KEY_ID,
        authority_private_key_hex=_private_key_hex(authority_key),
    )
    return ledger, store, authority_key


def _append(
    ledger: RangerPublicationKeyAuthorityLedger,
    *,
    request_id: str,
    role: RangerPublicationKeyRole,
    kind: RangerPublicationKeyEventKind,
    subject: RangerPublicationSigningKeyDescriptor,
    subject_signer: Ed25519PrivateKey | None,
    replacement: RangerPublicationSigningKeyDescriptor | None = None,
    replacement_signer: Ed25519PrivateKey | None = None,
    revocation_reason: RangerPublicationKeyRevocationReason | None = None,
):
    intent = RangerPublicationKeyBindingIntent(
        request_id=request_id,
        key_role=role,
        event_kind=kind,
        publication_scope_id=SCOPE_ID,
        principal_id=PUBLISHER_ID if role is RangerPublicationKeyRole.PUBLISHER else CUSTODIAN_ID,
        subject_key=subject,
        replacement_key=replacement,
        revocation_reason=revocation_reason,
        recorded_at_utc=NOW + timedelta(seconds=len(ledger.list_events()) + 1),
    )
    payload = publication_key_binding_intent_bytes(intent)
    request = build_publication_key_binding_request(
        intent,
        subject_key_proof_signature_hex=(
            None if subject_signer is None else subject_signer.sign(payload).hex()
        ),
        replacement_key_proof_signature_hex=(
            None if replacement_signer is None else replacement_signer.sign(payload).hex()
        ),
    )
    return ledger.append(request)


def _receipt(
    key: Ed25519PrivateKey,
    *,
    key_id: str,
    publication_id: str,
    sequence: int,
    previous_digest: str,
    minute: int,
) -> RangerExternalPublicationReceipt:
    public_key_hex = _public_key_hex(key)
    published_at = NOW + timedelta(minutes=minute)
    payload = {
        "schema_version": "ets.ranger.external-publication-receipt.v1",
        "publication_id": publication_id,
        "publication_sequence": sequence,
        "previous_publication_digest_sha256": previous_digest,
        "subject_kind": RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD.value,
        "subject_digest_sha256": f"{sequence:x}" * 64,
        "time_attestation_digest_sha256": f"{sequence + 8:x}" * 64,
        "registry_id": REGISTRY_ID,
        "registry_signing_key_id": REGISTRY_KEY_ID,
        "published_at_utc": published_at.isoformat().replace("+00:00", "Z"),
        "publisher_id": PUBLISHER_ID,
        "publisher_signing_key_id": key_id,
        "publisher_public_key_fingerprint_sha256": hashlib.sha256(
            bytes.fromhex(public_key_hex)
        ).hexdigest(),
        "signing_algorithm": "ed25519",
        "configured_external_publisher_receipt": True,
        "continued_external_custody_proven": False,
        "publisher_organizational_independence_proven": False,
        "publisher_clock_trusted": False,
        "globally_current_state_proven": False,
        "complete_capture_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "configured_external_publisher_receipt_no_continued_custody_independence_or_truth_claim"
        ),
    }
    return RangerExternalPublicationReceipt.model_validate(
        {
            **payload,
            "subject_kind": RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
            "published_at_utc": published_at,
            "publication_digest_sha256": canonical_sha256(payload),
            "publisher_signature_hex": key.sign(canonicalize(payload)).hex(),
        }
    )


def _audit(
    key: Ed25519PrivateKey,
    *,
    key_id: str,
    audit_id: str,
    expected_head: str,
) -> RangerPublicationRetrievalAudit:
    public_key_hex = _public_key_hex(key)
    observed_at = NOW + timedelta(minutes=5)
    payload = {
        "schema_version": "ets.ranger.publication-retrieval-audit.v1",
        "audit_id": audit_id,
        "expected_publication_head_digest_sha256": expected_head,
        "observed_publication_head_digest_sha256": expected_head,
        "archived_receipt_count": 2,
        "result": "match",
        "observed_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "custodian_id": CUSTODIAN_ID,
        "custodian_signing_key_id": key_id,
        "custodian_public_key_fingerprint_sha256": hashlib.sha256(
            bytes.fromhex(public_key_hex)
        ).hexdigest(),
        "signing_algorithm": "ed25519",
        "archive_chain_integrity_verified": True,
        "freshness_relative_to_expected_head": True,
        "logical_append_only_storage_enforced": True,
        "separate_custodian_key_proven": True,
        "physical_worm_storage_proven": False,
        "organizational_independence_proven": False,
        "hardware_rollback_resistance_proven": False,
        "continued_availability_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "expected_head_relative_archive_audit_no_worm_independence_or_truth_claim"
        ),
    }
    return RangerPublicationRetrievalAudit.model_validate(
        {
            **payload,
            "observed_at_utc": observed_at,
            "audit_digest_sha256": canonical_sha256(payload),
            "custodian_signature_hex": key.sign(canonicalize(payload)).hex(),
        }
    )


def _verify_kwargs(ledger: RangerPublicationKeyAuthorityLedger) -> dict[str, str]:
    return {
        "authority_public_key_hex": ledger.authority_public_key_hex,
        "expected_publication_scope_id": SCOPE_ID,
        "expected_publisher_id": PUBLISHER_ID,
        "expected_custodian_id": CUSTODIAN_ID,
        "expected_authority_id": AUTHORITY_ID,
        "expected_authority_signing_key_id": AUTHORITY_KEY_ID,
    }


def test_rotated_publisher_receipts_keep_historical_but_not_current_standing(
    tmp_path: Path,
) -> None:
    ledger, store, _ = _ledger(tmp_path / "keys.sqlite3")
    old_publisher = Ed25519PrivateKey.generate()
    new_publisher = Ed25519PrivateKey.generate()
    custodian = Ed25519PrivateKey.generate()
    old_descriptor = _descriptor(old_publisher, "publisher-old")
    new_descriptor = _descriptor(new_publisher, "publisher-new")
    custodian_descriptor = _descriptor(custodian, "custodian-1")
    _append(
        ledger,
        request_id="publisher-enroll",
        role=RangerPublicationKeyRole.PUBLISHER,
        kind=RangerPublicationKeyEventKind.ENROLL,
        subject=old_descriptor,
        subject_signer=old_publisher,
    )
    _append(
        ledger,
        request_id="custodian-enroll",
        role=RangerPublicationKeyRole.CUSTODIAN,
        kind=RangerPublicationKeyEventKind.ENROLL,
        subject=custodian_descriptor,
        subject_signer=custodian,
    )
    old_receipt = _receipt(
        old_publisher,
        key_id=old_descriptor.signing_key_id,
        publication_id="publication-1",
        sequence=1,
        previous_digest="0" * 64,
        minute=1,
    )
    old_standing = ledger.attest_source_key_standing(
        standing_id="standing-old",
        source_kind=RangerPublicationKeySourceKind.EXTERNAL_PUBLICATION_RECEIPT,
        source_digest_sha256=old_receipt.publication_digest_sha256,
        principal_id=PUBLISHER_ID,
        signing_key_id=old_descriptor.signing_key_id,
        public_key_fingerprint_sha256=old_descriptor.public_key_fingerprint_sha256,
        authority_event_count=2,
    )
    _append(
        ledger,
        request_id="publisher-rotate",
        role=RangerPublicationKeyRole.PUBLISHER,
        kind=RangerPublicationKeyEventKind.ROTATE,
        subject=old_descriptor,
        subject_signer=old_publisher,
        replacement=new_descriptor,
        replacement_signer=new_publisher,
    )
    new_receipt = _receipt(
        new_publisher,
        key_id=new_descriptor.signing_key_id,
        publication_id="publication-2",
        sequence=2,
        previous_digest=old_receipt.publication_digest_sha256,
        minute=2,
    )
    new_standing = ledger.attest_source_key_standing(
        standing_id="standing-new",
        source_kind=RangerPublicationKeySourceKind.EXTERNAL_PUBLICATION_RECEIPT,
        source_digest_sha256=new_receipt.publication_digest_sha256,
        principal_id=PUBLISHER_ID,
        signing_key_id=new_descriptor.signing_key_id,
        public_key_fingerprint_sha256=new_descriptor.public_key_fingerprint_sha256,
    )

    old_verification = verify_publication_source_key_standing(
        old_standing, old_receipt, ledger.list_events(), **_verify_kwargs(ledger)
    )
    assert old_verification.valid
    assert old_verification.historical_authority_relative_key_standing
    assert old_verification.source_signature_valid
    assert not old_verification.currently_authorized_relative_to_presented_history
    new_verification = verify_publication_source_key_standing(
        new_standing, new_receipt, ledger.list_events(), **_verify_kwargs(ledger)
    )
    assert new_verification.valid
    assert new_verification.currently_authorized_relative_to_presented_history

    chain = verify_publication_lifecycle_chain(
        [old_receipt, new_receipt],
        [old_standing, new_standing],
        ledger.list_events(),
        **_verify_kwargs(ledger),
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        expected_latest_publication_digest_sha256=new_receipt.publication_digest_sha256,
    )
    assert chain.valid
    assert chain.historical_publisher_key_standing_proven
    assert not chain.all_publisher_keys_currently_authorized_relative_to_presented_history
    store.close()


def test_revoked_custodian_audit_keeps_historical_not_current_standing(tmp_path: Path) -> None:
    ledger, store, _ = _ledger(tmp_path / "keys.sqlite3")
    publisher = Ed25519PrivateKey.generate()
    custodian = Ed25519PrivateKey.generate()
    publisher_descriptor = _descriptor(publisher, "publisher-1")
    custodian_descriptor = _descriptor(custodian, "custodian-old")
    _append(
        ledger,
        request_id="publisher-enroll",
        role=RangerPublicationKeyRole.PUBLISHER,
        kind=RangerPublicationKeyEventKind.ENROLL,
        subject=publisher_descriptor,
        subject_signer=publisher,
    )
    _append(
        ledger,
        request_id="custodian-enroll",
        role=RangerPublicationKeyRole.CUSTODIAN,
        kind=RangerPublicationKeyEventKind.ENROLL,
        subject=custodian_descriptor,
        subject_signer=custodian,
    )
    audit = _audit(
        custodian,
        key_id=custodian_descriptor.signing_key_id,
        audit_id="audit-1",
        expected_head="a" * 64,
    )
    standing = ledger.attest_source_key_standing(
        standing_id="audit-standing",
        source_kind=RangerPublicationKeySourceKind.PUBLICATION_RETRIEVAL_AUDIT,
        source_digest_sha256=audit.audit_digest_sha256,
        principal_id=CUSTODIAN_ID,
        signing_key_id=custodian_descriptor.signing_key_id,
        public_key_fingerprint_sha256=custodian_descriptor.public_key_fingerprint_sha256,
        authority_event_count=2,
    )
    _append(
        ledger,
        request_id="custodian-revoke",
        role=RangerPublicationKeyRole.CUSTODIAN,
        kind=RangerPublicationKeyEventKind.REVOKE,
        subject=custodian_descriptor,
        subject_signer=None,
        revocation_reason=RangerPublicationKeyRevocationReason.COMPROMISE_SUSPECTED,
    )

    verification = verify_publication_source_key_standing(
        standing, audit, ledger.list_events(), **_verify_kwargs(ledger)
    )
    assert verification.valid
    assert verification.source_signature_valid
    assert verification.historical_authority_relative_key_standing
    assert not verification.currently_authorized_relative_to_presented_history
    store.close()


def test_rotation_requires_valid_old_and_new_possession_proofs(tmp_path: Path) -> None:
    ledger, store, _ = _ledger(tmp_path / "keys.sqlite3")
    old_key = Ed25519PrivateKey.generate()
    new_key = Ed25519PrivateKey.generate()
    old_descriptor = _descriptor(old_key, "publisher-old")
    new_descriptor = _descriptor(new_key, "publisher-new")
    _append(
        ledger,
        request_id="publisher-enroll",
        role=RangerPublicationKeyRole.PUBLISHER,
        kind=RangerPublicationKeyEventKind.ENROLL,
        subject=old_descriptor,
        subject_signer=old_key,
    )
    intent = RangerPublicationKeyBindingIntent(
        request_id="publisher-rotate",
        key_role=RangerPublicationKeyRole.PUBLISHER,
        event_kind=RangerPublicationKeyEventKind.ROTATE,
        publication_scope_id=SCOPE_ID,
        principal_id=PUBLISHER_ID,
        subject_key=old_descriptor,
        replacement_key=new_descriptor,
        recorded_at_utc=NOW + timedelta(seconds=2),
    )
    payload = publication_key_binding_intent_bytes(intent)
    request = build_publication_key_binding_request(
        intent,
        subject_key_proof_signature_hex=new_key.sign(payload).hex(),
        replacement_key_proof_signature_hex=new_key.sign(payload).hex(),
    )
    with pytest.raises(RangerPublicationKeyLifecycleError, match="subject-key proof is invalid"):
        ledger.append(request)
    assert len(ledger.list_events()) == 1
    store.close()


def test_roles_cannot_reuse_a_publisher_key_as_a_custodian_key(tmp_path: Path) -> None:
    ledger, store, _ = _ledger(tmp_path / "keys.sqlite3")
    shared_key = Ed25519PrivateKey.generate()
    shared_descriptor = _descriptor(shared_key, "shared-key")
    _append(
        ledger,
        request_id="publisher-enroll",
        role=RangerPublicationKeyRole.PUBLISHER,
        kind=RangerPublicationKeyEventKind.ENROLL,
        subject=shared_descriptor,
        subject_signer=shared_key,
    )
    with pytest.raises(RangerPublicationKeyLifecycleConflict, match="cannot reuse"):
        _append(
            ledger,
            request_id="custodian-enroll",
            role=RangerPublicationKeyRole.CUSTODIAN,
            kind=RangerPublicationKeyEventKind.ENROLL,
            subject=shared_descriptor,
            subject_signer=shared_key,
        )
    store.close()


def test_standing_and_reordered_history_tampering_fail_closed(tmp_path: Path) -> None:
    ledger, store, _ = _ledger(tmp_path / "keys.sqlite3")
    publisher = Ed25519PrivateKey.generate()
    custodian = Ed25519PrivateKey.generate()
    publisher_descriptor = _descriptor(publisher, "publisher-1")
    custodian_descriptor = _descriptor(custodian, "custodian-1")
    _append(
        ledger,
        request_id="publisher-enroll",
        role=RangerPublicationKeyRole.PUBLISHER,
        kind=RangerPublicationKeyEventKind.ENROLL,
        subject=publisher_descriptor,
        subject_signer=publisher,
    )
    _append(
        ledger,
        request_id="custodian-enroll",
        role=RangerPublicationKeyRole.CUSTODIAN,
        kind=RangerPublicationKeyEventKind.ENROLL,
        subject=custodian_descriptor,
        subject_signer=custodian,
    )
    receipt = _receipt(
        publisher,
        key_id=publisher_descriptor.signing_key_id,
        publication_id="publication-1",
        sequence=1,
        previous_digest="0" * 64,
        minute=1,
    )
    standing = ledger.attest_source_key_standing(
        standing_id="standing-1",
        source_kind=RangerPublicationKeySourceKind.EXTERNAL_PUBLICATION_RECEIPT,
        source_digest_sha256=receipt.publication_digest_sha256,
        principal_id=PUBLISHER_ID,
        signing_key_id=publisher_descriptor.signing_key_id,
        public_key_fingerprint_sha256=publisher_descriptor.public_key_fingerprint_sha256,
    )
    assert not RangerPublicationKeyAuthorityLedger.verify_history(
        list(reversed(ledger.list_events())), ledger.authority_public_key_hex
    ).valid
    tampered = standing.model_copy(update={"source_digest_sha256": "f" * 64})
    verification = verify_publication_source_key_standing(
        tampered, receipt, ledger.list_events(), **_verify_kwargs(ledger)
    )
    assert not verification.valid
    assert "digest mismatch" in verification.reason
    store.close()


def test_sqlite_key_authority_index_tampering_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "keys.sqlite3"
    ledger, store, _ = _ledger(path)
    publisher = Ed25519PrivateKey.generate()
    publisher_descriptor = _descriptor(publisher, "publisher-1")
    _append(
        ledger,
        request_id="publisher-enroll",
        role=RangerPublicationKeyRole.PUBLISHER,
        kind=RangerPublicationKeyEventKind.ENROLL,
        subject=publisher_descriptor,
        subject_signer=publisher,
    )
    store.close()
    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE ranger_publication_key_authority_events SET key_role = ?",
        ("custodian",),
    )
    connection.commit()
    connection.close()
    tampered_store = SQLiteRangerPublicationKeyAuthorityStore(path)
    with pytest.raises(RangerPublicationKeyLifecycleIntegrityError, match="index metadata"):
        tampered_store.list_events()
    tampered_store.close()
