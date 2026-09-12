import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from pydantic import ValidationError

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.external_publication import RangerExternalPublisher
from ets.ranger.governance import RangerGovernanceSubjectKind
from ets.ranger.immutable_publication import (
    RangerImmutableDeleteOutcome,
    RangerImmutableEvidenceArtifactKind,
    RangerImmutableEvidenceEnvironment,
    RangerImmutablePublicationError,
    RangerImmutablePublicationEvidenceIssuer,
    RangerImmutablePublicationQualification,
    RangerImmutablePublicationVerificationPolicy,
    RangerImmutableRetentionMode,
    RangerImmutableRetrievalOutcome,
    publication_archive_bundle_digest,
    verify_immutable_publication_qualification,
)
from ets.ranger.publication_archive import RangerPublicationRetrievalAudit
from ets.ranger.publication_key_lifecycle import (
    RangerPublicationKeyAuthorityLedger,
    RangerPublicationKeyBindingIntent,
    RangerPublicationKeyEventKind,
    RangerPublicationKeyRevocationReason,
    RangerPublicationKeyRole,
    RangerPublicationKeySourceKind,
    RangerPublicationSigningKeyDescriptor,
    SQLiteRangerPublicationKeyAuthorityStore,
    build_publication_key_binding_request,
    publication_key_binding_intent_bytes,
)

NOW = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)
SCOPE_ID = "ets-ranger-publication:immutable-backend-demo-1"
PUBLISHER_ID = "ets-publisher:ranger-external-1"
CUSTODIAN_ID = "ets-custodian:ranger-archive-1"
AUTHORITY_ID = "ets-authority:ranger-publication-keys-1"
AUTHORITY_KEY_ID = "publication-key-authority-1"
REGISTRY_ID = "ets-verifier:ranger-registry-1"
REGISTRY_KEY_ID = "registry-software-key-1"
EVIDENCE_ISSUER_ID = "ets-edge:ranger-backend-evidence-1"
EVIDENCE_KEY_ID = "backend-evidence-software-key-1"
BACKEND_PROVIDER_ID = "provider:object-lock-reference"
BACKEND_INSTANCE_ID = "backend:ranger-archive-qualification-1"
BACKEND_NAMESPACE = "ranger-qualification/immutable-publication"
QUALIFICATION_ID = "ranger-immutable-publication-q1"
CHALLENGE_NONCE_HEX = "c" * 64


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


def _append_authority_event(
    ledger: RangerPublicationKeyAuthorityLedger,
    *,
    request_id: str,
    role: RangerPublicationKeyRole,
    kind: RangerPublicationKeyEventKind,
    descriptor: RangerPublicationSigningKeyDescriptor,
    signer: Ed25519PrivateKey | None,
    revocation_reason: RangerPublicationKeyRevocationReason | None = None,
) -> None:
    intent = RangerPublicationKeyBindingIntent(
        request_id=request_id,
        key_role=role,
        event_kind=kind,
        publication_scope_id=SCOPE_ID,
        principal_id=PUBLISHER_ID if role is RangerPublicationKeyRole.PUBLISHER else CUSTODIAN_ID,
        subject_key=descriptor,
        revocation_reason=revocation_reason,
        recorded_at_utc=NOW + timedelta(seconds=len(ledger.list_events()) + 1),
    )
    payload = publication_key_binding_intent_bytes(intent)
    request = build_publication_key_binding_request(
        intent,
        subject_key_proof_signature_hex=None if signer is None else signer.sign(payload).hex(),
    )
    ledger.append(request)


def _retrieval_audit(
    custodian: Ed25519PrivateKey,
    *,
    expected_head: str,
    receipt_count: int,
) -> RangerPublicationRetrievalAudit:
    custodian_public_key_hex = _public_key_hex(custodian)
    observed_at = NOW + timedelta(minutes=7)
    payload = {
        "schema_version": "ets.ranger.publication-retrieval-audit.v1",
        "audit_id": "retrieval-audit-q1",
        "expected_publication_head_digest_sha256": expected_head,
        "observed_publication_head_digest_sha256": expected_head,
        "archived_receipt_count": receipt_count,
        "result": "match",
        "observed_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "custodian_id": CUSTODIAN_ID,
        "custodian_signing_key_id": "custodian-key-1",
        "custodian_public_key_fingerprint_sha256": hashlib.sha256(
            bytes.fromhex(custodian_public_key_hex)
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
            "custodian_signature_hex": custodian.sign(canonicalize(payload)).hex(),
        }
    )


def _artifacts() -> dict[RangerImmutableEvidenceArtifactKind, bytes]:
    return {
        RangerImmutableEvidenceArtifactKind.CONFIGURATION: (
            b'{"versioning":true,"retention_mode":"compliance"}'
        ),
        RangerImmutableEvidenceArtifactKind.RETENTION_PUT: (
            b'{"operation":"put","retention":"active","version":"v-1"}'
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY: (
            b'{"principal":"delete-probe","delete_capability":true}'
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT: (
            b'{"operation":"delete","result":"denied_by_retention"}'
        ),
        RangerImmutableEvidenceArtifactKind.RETRIEVAL: (
            b'{"operation":"get","version":"v-1","result":"content_match"}'
        ),
    }


def _bundle(
    tmp_path: Path,
    environment: RangerImmutableEvidenceEnvironment = RangerImmutableEvidenceEnvironment.SIMULATION,
) -> dict[str, Any]:
    publisher = Ed25519PrivateKey.generate()
    custodian = Ed25519PrivateKey.generate()
    authority = Ed25519PrivateKey.generate()
    evidence_signer = Ed25519PrivateKey.generate()
    publisher_descriptor = _descriptor(publisher, "publisher-key-1")
    custodian_descriptor = _descriptor(custodian, "custodian-key-1")

    store = SQLiteRangerPublicationKeyAuthorityStore(tmp_path / "key-authority.sqlite3")
    ledger = RangerPublicationKeyAuthorityLedger(
        store,
        publication_scope_id=SCOPE_ID,
        publisher_id=PUBLISHER_ID,
        custodian_id=CUSTODIAN_ID,
        authority_id=AUTHORITY_ID,
        authority_signing_key_id=AUTHORITY_KEY_ID,
        authority_private_key_hex=_private_key_hex(authority),
    )
    _append_authority_event(
        ledger,
        request_id="publisher-enroll",
        role=RangerPublicationKeyRole.PUBLISHER,
        kind=RangerPublicationKeyEventKind.ENROLL,
        descriptor=publisher_descriptor,
        signer=publisher,
    )
    _append_authority_event(
        ledger,
        request_id="custodian-enroll",
        role=RangerPublicationKeyRole.CUSTODIAN,
        kind=RangerPublicationKeyEventKind.ENROLL,
        descriptor=custodian_descriptor,
        signer=custodian,
    )

    external_publisher = RangerExternalPublisher(
        publisher_id=PUBLISHER_ID,
        publisher_signing_key_id=publisher_descriptor.signing_key_id,
        publisher_private_key_hex=_private_key_hex(publisher),
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
    )
    receipts = [
        external_publisher.publish(
            publication_id="publication-1",
            subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
            subject_digest_sha256="1" * 64,
            time_attestation_digest_sha256="a" * 64,
            registry_id=REGISTRY_ID,
            registry_signing_key_id=REGISTRY_KEY_ID,
            published_at_utc=NOW + timedelta(minutes=1),
        ),
        external_publisher.publish(
            publication_id="publication-2",
            subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
            subject_digest_sha256="2" * 64,
            time_attestation_digest_sha256="b" * 64,
            registry_id=REGISTRY_ID,
            registry_signing_key_id=REGISTRY_KEY_ID,
            published_at_utc=NOW + timedelta(minutes=2),
        ),
    ]
    publisher_standings = [
        ledger.attest_source_key_standing(
            standing_id=f"publisher-standing-{index}",
            source_kind=RangerPublicationKeySourceKind.EXTERNAL_PUBLICATION_RECEIPT,
            source_digest_sha256=receipt.publication_digest_sha256,
            principal_id=PUBLISHER_ID,
            signing_key_id=publisher_descriptor.signing_key_id,
            public_key_fingerprint_sha256=(publisher_descriptor.public_key_fingerprint_sha256),
        )
        for index, receipt in enumerate(receipts, start=1)
    ]
    head = receipts[-1].publication_digest_sha256
    retrieval_audit = _retrieval_audit(custodian, expected_head=head, receipt_count=len(receipts))
    retrieval_standing = ledger.attest_source_key_standing(
        standing_id="custodian-standing-retrieval-q1",
        source_kind=RangerPublicationKeySourceKind.PUBLICATION_RETRIEVAL_AUDIT,
        source_digest_sha256=retrieval_audit.audit_digest_sha256,
        principal_id=CUSTODIAN_ID,
        signing_key_id=custodian_descriptor.signing_key_id,
        public_key_fingerprint_sha256=custodian_descriptor.public_key_fingerprint_sha256,
    )
    artifacts = _artifacts()
    issuer = RangerImmutablePublicationEvidenceIssuer(
        evidence_issuer_id=EVIDENCE_ISSUER_ID,
        evidence_signing_key_id=EVIDENCE_KEY_ID,
        evidence_signing_key_hex=_private_key_hex(evidence_signer),
    )
    issue_kwargs = {
        "qualification_id": QUALIFICATION_ID,
        "verifier_challenge_nonce_hex": CHALLENGE_NONCE_HEX,
        "publication_scope_id": SCOPE_ID,
        "evidence_environment": environment,
        "backend_provider_id": BACKEND_PROVIDER_ID,
        "backend_instance_id": BACKEND_INSTANCE_ID,
        "backend_namespace": BACKEND_NAMESPACE,
        "object_key": "ranger/publication-archive-q1.json",
        "object_version_id": "provider-version-v1",
        "expected_publication_head_digest_sha256": head,
        "retained_publication_head_digest_sha256": head,
        "publication_archive_bundle_digest_sha256": publication_archive_bundle_digest(receipts),
        "publication_retrieval_audit_digest_sha256": retrieval_audit.audit_digest_sha256,
        "evidence_artifacts": artifacts,
        "versioning_enabled": True,
        "retention_mode": RangerImmutableRetentionMode.COMPLIANCE,
        "retention_bypass_permitted": False,
        "configuration_observed_at_utc": NOW + timedelta(minutes=3),
        "retained_at_utc": NOW + timedelta(minutes=4),
        "retention_until_utc": NOW + timedelta(days=2),
        "delete_test_principal_id": "principal:qualified-delete-probe",
        "delete_attempted_at_utc": NOW + timedelta(minutes=5),
        "delete_outcome": RangerImmutableDeleteOutcome.DENIED_BY_RETENTION,
        "delete_result_detail": "RETENTION_POLICY_ACTIVE",
        "retrieval_observed_at_utc": NOW + timedelta(minutes=6),
        "retrieval_outcome": RangerImmutableRetrievalOutcome.CONTENT_MATCH,
        "retrieved_archive_bundle_digest_sha256": publication_archive_bundle_digest(receipts),
    }
    qualification = issuer.issue(**issue_kwargs)
    policy = RangerImmutablePublicationVerificationPolicy(
        expected_qualification_id=QUALIFICATION_ID,
        expected_verifier_challenge_nonce_hex=CHALLENGE_NONCE_HEX,
        expected_publication_scope_id=SCOPE_ID,
        expected_publication_head_digest_sha256=head,
        expected_publisher_id=PUBLISHER_ID,
        expected_custodian_id=CUSTODIAN_ID,
        expected_authority_id=AUTHORITY_ID,
        expected_authority_signing_key_id=AUTHORITY_KEY_ID,
        authority_public_key_hex=ledger.authority_public_key_hex,
        expected_registry_id=REGISTRY_ID,
        expected_registry_signing_key_id=REGISTRY_KEY_ID,
        expected_custodian_signing_key_id=custodian_descriptor.signing_key_id,
        custodian_public_key_hex=_public_key_hex(custodian),
        expected_backend_provider_id=BACKEND_PROVIDER_ID,
        expected_backend_instance_id=BACKEND_INSTANCE_ID,
        expected_backend_namespace=BACKEND_NAMESPACE,
        expected_object_key="ranger/publication-archive-q1.json",
        expected_object_version_id="provider-version-v1",
        expected_delete_test_principal_id="principal:qualified-delete-probe",
        expected_evidence_environment=environment,
        expected_evidence_issuer_id=EVIDENCE_ISSUER_ID,
        expected_evidence_signing_key_id=EVIDENCE_KEY_ID,
        evidence_issuer_public_key_hex=issuer.evidence_public_key_hex,
        minimum_reported_retention_seconds=24 * 60 * 60,
    )
    return {
        "qualification": qualification,
        "receipts": receipts,
        "publisher_standings": publisher_standings,
        "retrieval_audit": retrieval_audit,
        "retrieval_standing": retrieval_standing,
        "events": ledger.list_events(),
        "artifacts": artifacts,
        "policy": policy,
        "issuer": issuer,
        "issue_kwargs": issue_kwargs,
        "ledger": ledger,
        "store": store,
        "custodian_descriptor": custodian_descriptor,
        "publisher": publisher,
    }


def _verify(bundle: dict[str, Any]):
    return verify_immutable_publication_qualification(
        bundle["qualification"],
        bundle["receipts"],
        bundle["publisher_standings"],
        bundle["retrieval_audit"],
        bundle["retrieval_standing"],
        bundle["events"],
        bundle["artifacts"],
        policy=bundle["policy"],
    )


def test_simulation_uses_same_profile_without_live_or_worm_claim(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)

    result = _verify(bundle)

    assert result.valid
    assert result.qualification_profile_conformant
    assert result.evidence_issuer_signature_valid
    assert result.separate_evidence_issuer_key_proven
    assert not result.evidence_issuer_key_lifecycle_proven
    assert result.evidence_artifact_integrity_verified
    assert result.publication_chain_verified
    assert result.historical_publisher_key_standing_proven
    assert result.matches_expected_publication_head
    assert result.archive_bundle_binding_verified
    assert result.retrieval_audit_verified
    assert result.historical_custodian_key_standing_proven
    assert result.custodian_current_relative_to_presented_history
    assert result.compliant_retention_configuration_reported
    assert result.deletion_denial_reported
    assert result.post_denial_retrieval_verified
    assert result.simulation_profile_only
    assert not result.provider_control_plane_evidence_profile_passed
    assert not result.physical_worm_storage_proven
    assert not result.organizational_independence_proven
    assert not result.hardware_rollback_resistance_proven
    assert not result.trusted_time_proven
    assert not result.continued_availability_proven
    assert not result.operational_authorization_proven
    assert not result.semantic_truth_proven
    assert not result.actuator_response_proven
    assert not result.physical_outcome_proven
    bundle["store"].close()


def test_provider_record_passes_only_bounded_control_plane_profile(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, RangerImmutableEvidenceEnvironment.PROVIDER_CONTROL_PLANE)

    result = _verify(bundle)

    assert result.valid
    assert result.provider_control_plane_evidence_profile_passed
    assert not result.simulation_profile_only
    assert not result.physical_worm_storage_proven
    assert "physical WORM" in result.reason
    bundle["store"].close()


def test_qualification_accepts_single_pass_evidence_iterables(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)

    result = verify_immutable_publication_qualification(
        bundle["qualification"],
        iter(bundle["receipts"]),
        iter(bundle["publisher_standings"]),
        bundle["retrieval_audit"],
        bundle["retrieval_standing"],
        iter(bundle["events"]),
        bundle["artifacts"],
        policy=bundle["policy"],
    )

    assert result.valid
    bundle["store"].close()


def test_qualification_rejects_record_or_raw_artifact_tampering(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    bundle["qualification"] = bundle["qualification"].model_copy(
        update={"delete_result_detail": "TAMPERED_AFTER_SIGNING"}
    )
    tampered_record = _verify(bundle)
    assert not tampered_record.valid
    assert "digest mismatch" in tampered_record.reason

    clean = _bundle(tmp_path / "artifact")
    clean["artifacts"] = {
        **clean["artifacts"],
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT: b'{"result":"deleted"}',
    }
    tampered_artifact = _verify(clean)
    assert not tampered_artifact.valid
    assert "artifact digest mismatch" in tampered_artifact.reason
    bundle["store"].close()
    clean["store"].close()


@pytest.mark.parametrize("mutation", ["prefix", "reordered"])
def test_qualification_rejects_stale_or_reordered_publication_chain(
    tmp_path: Path, mutation: str
) -> None:
    bundle = _bundle(tmp_path)
    if mutation == "prefix":
        bundle["receipts"] = bundle["receipts"][:1]
        bundle["publisher_standings"] = bundle["publisher_standings"][:1]
    else:
        bundle["receipts"] = list(reversed(bundle["receipts"]))
        bundle["publisher_standings"] = list(reversed(bundle["publisher_standings"]))

    result = _verify(bundle)

    assert not result.valid
    assert "publication lifecycle chain is invalid" in result.reason
    bundle["store"].close()


def test_qualification_rejects_successful_delete_even_when_signed(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    issue_kwargs = {
        **bundle["issue_kwargs"],
        "delete_outcome": RangerImmutableDeleteOutcome.DELETED,
        "delete_result_detail": None,
        "retrieval_outcome": RangerImmutableRetrievalOutcome.NOT_FOUND,
        "retrieved_archive_bundle_digest_sha256": None,
    }
    bundle["qualification"] = bundle["issuer"].issue(**issue_kwargs)

    result = _verify(bundle)

    assert not result.valid
    assert "did not deny deletion" in result.reason
    bundle["store"].close()


def test_qualification_rejects_revoked_custodian_as_not_current(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    _append_authority_event(
        bundle["ledger"],
        request_id="custodian-revoke",
        role=RangerPublicationKeyRole.CUSTODIAN,
        kind=RangerPublicationKeyEventKind.REVOKE,
        descriptor=bundle["custodian_descriptor"],
        signer=None,
        revocation_reason=RangerPublicationKeyRevocationReason.COMPROMISE_SUSPECTED,
    )
    bundle["events"] = bundle["ledger"].list_events()

    result = _verify(bundle)

    assert not result.valid
    assert "custodian is not current" in result.reason
    bundle["store"].close()


@pytest.mark.parametrize(
    ("policy_field", "substitute", "reason"),
    [
        ("expected_backend_instance_id", "backend:substituted", "backend instance"),
        ("expected_object_key", "ranger/substituted.json", "object key"),
        ("expected_object_version_id", "substituted-version", "object version"),
        (
            "expected_delete_test_principal_id",
            "principal:incapable-probe",
            "deletion-probe principal",
        ),
    ],
)
def test_qualification_rejects_backend_object_or_principal_substitution(
    tmp_path: Path,
    policy_field: str,
    substitute: str,
    reason: str,
) -> None:
    bundle = _bundle(tmp_path)
    bundle["policy"] = bundle["policy"].model_copy(update={policy_field: substitute})

    result = _verify(bundle)

    assert not result.valid
    assert reason in result.reason
    bundle["store"].close()


def test_qualification_rejects_expected_head_substitution(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    bundle["policy"] = bundle["policy"].model_copy(
        update={"expected_publication_head_digest_sha256": "f" * 64}
    )

    result = _verify(bundle)

    assert not result.valid
    assert "expected publication head" in result.reason
    bundle["store"].close()


def test_qualification_rejects_replayed_challenge_or_source_key_reuse(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    bundle["policy"] = bundle["policy"].model_copy(
        update={"expected_verifier_challenge_nonce_hex": "d" * 64}
    )
    replayed = _verify(bundle)
    assert not replayed.valid
    assert "challenge nonce" in replayed.reason

    collision = _bundle(tmp_path / "collision")
    reused_issuer = RangerImmutablePublicationEvidenceIssuer(
        evidence_issuer_id=EVIDENCE_ISSUER_ID,
        evidence_signing_key_id=EVIDENCE_KEY_ID,
        evidence_signing_key_hex=_private_key_hex(collision["publisher"]),
    )
    collision["qualification"] = reused_issuer.issue(**collision["issue_kwargs"])
    collision["policy"] = collision["policy"].model_copy(
        update={"evidence_issuer_public_key_hex": reused_issuer.evidence_public_key_hex}
    )
    reused = _verify(collision)
    assert not reused.valid
    assert "distinct from publication source keys" in reused.reason
    bundle["store"].close()
    collision["store"].close()


def test_artifact_set_and_strict_claim_boundary_fail_closed(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    missing = dict(bundle["artifacts"])
    missing.pop(RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY)
    with pytest.raises(RangerImmutablePublicationError, match="incomplete"):
        bundle["issuer"].issue(**{**bundle["issue_kwargs"], "evidence_artifacts": missing})

    payload = bundle["qualification"].model_dump()
    payload["physical_worm_storage_proven"] = True
    with pytest.raises(ValidationError):
        RangerImmutablePublicationQualification.model_validate(payload)
    bundle["store"].close()


def test_policy_requires_distinct_evidence_authority_and_custody_keys(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    payload = bundle["policy"].model_dump()
    payload["evidence_issuer_public_key_hex"] = payload["custodian_public_key_hex"]
    with pytest.raises(ValidationError, match="public keys must be distinct"):
        RangerImmutablePublicationVerificationPolicy.model_validate(payload)
    bundle["store"].close()
