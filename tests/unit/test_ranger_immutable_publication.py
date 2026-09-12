import base64
import hashlib
import json
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
from ets.ranger.aws_s3_object_lock import (
    AWS_S3_OBJECT_LOCK_PROVIDER_ID,
    RangerAwsIamDeleteCapabilityArtifact,
    RangerAwsS3BucketObjectLockObservation,
    RangerAwsS3BucketVersioningObservation,
    RangerAwsS3DeleteAttemptArtifact,
    RangerAwsS3GetObjectObservation,
    RangerAwsS3GetObjectRetentionObservation,
    RangerAwsS3ObjectLockCaptureContext,
    RangerAwsS3ObjectLockConfigurationArtifact,
    RangerAwsS3ObjectLockRetentionPutArtifact,
    RangerAwsS3ObjectLockVerificationPolicy,
    RangerAwsS3PostDenialRetrievalArtifact,
    RangerAwsS3PutObjectObservation,
    RangerAwsS3ResponseMetadata,
    aws_s3_object_lock_artifact_bytes,
    verify_aws_s3_object_lock_qualification,
)
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
AWS_ACCOUNT_ID = "123456789012"
AWS_REGION = "us-east-1"
AWS_BUCKET = "ets-ranger-qualification-123456789012"
AWS_OBJECT_KEY = "ranger/publication-archive-q1.json"
AWS_OBJECT_VERSION_ID = "s3-version-7f4f9d20"
AWS_DELETE_PRINCIPAL_ARN = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/ranger-delete-probe"
AWS_BACKEND_INSTANCE_ID = f"aws-account:{AWS_ACCOUNT_ID}:{AWS_REGION}"
AWS_BACKEND_NAMESPACE = f"s3://{AWS_BUCKET}"


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


def _aws_metadata(sequence: int, *, status: int = 200, s3: bool = True):
    return RangerAwsS3ResponseMetadata(
        http_status_code=status,
        request_id=f"aws-request-{sequence}",
        extended_request_id=f"aws-host-request-{sequence}" if s3 else None,
    )


def _aws_context(observed_at_utc: datetime) -> RangerAwsS3ObjectLockCaptureContext:
    return RangerAwsS3ObjectLockCaptureContext(
        qualification_id=QUALIFICATION_ID,
        verifier_challenge_nonce_hex=CHALLENGE_NONCE_HEX,
        aws_partition="aws",
        aws_account_id=AWS_ACCOUNT_ID,
        aws_region=AWS_REGION,
        bucket_name=AWS_BUCKET,
        expected_bucket_owner=AWS_ACCOUNT_ID,
        object_key=AWS_OBJECT_KEY,
        object_version_id=AWS_OBJECT_VERSION_ID,
        delete_test_principal_arn=AWS_DELETE_PRINCIPAL_ARN,
        observed_at_utc=observed_at_utc,
    )


def _aws_artifacts(archive_digest: str) -> dict[RangerImmutableEvidenceArtifactKind, bytes]:
    checksum = base64.b64encode(bytes.fromhex(archive_digest)).decode("ascii")
    artifacts = {
        RangerImmutableEvidenceArtifactKind.CONFIGURATION: (
            RangerAwsS3ObjectLockConfigurationArtifact(
                context=_aws_context(NOW + timedelta(minutes=3)),
                get_bucket_versioning=RangerAwsS3BucketVersioningObservation(
                    status="Enabled", metadata=_aws_metadata(1)
                ),
                get_object_lock_configuration=RangerAwsS3BucketObjectLockObservation(
                    object_lock_enabled="Enabled", metadata=_aws_metadata(2)
                ),
            )
        ),
        RangerImmutableEvidenceArtifactKind.RETENTION_PUT: (
            RangerAwsS3ObjectLockRetentionPutArtifact(
                context=_aws_context(NOW + timedelta(minutes=4)),
                put_object=RangerAwsS3PutObjectObservation(
                    requested_body_digest_sha256=archive_digest,
                    requested_checksum_algorithm="SHA256",
                    requested_checksum_sha256_base64=checksum,
                    requested_object_lock_mode="COMPLIANCE",
                    requested_retain_until_utc=NOW + timedelta(days=2),
                    result_version_id=AWS_OBJECT_VERSION_ID,
                    result_checksum_sha256_base64=checksum,
                    result_checksum_type="FULL_OBJECT",
                    metadata=_aws_metadata(3),
                ),
                get_object_retention=RangerAwsS3GetObjectRetentionObservation(
                    mode="COMPLIANCE",
                    retain_until_utc=NOW + timedelta(days=2),
                    metadata=_aws_metadata(4),
                ),
            )
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY: (
            RangerAwsIamDeleteCapabilityArtifact(
                context=_aws_context(NOW + timedelta(minutes=4, seconds=30)),
                policy_source_arn=AWS_DELETE_PRINCIPAL_ARN,
                resource_arn=f"arn:aws:s3:::{AWS_BUCKET}/{AWS_OBJECT_KEY}",
                evaluation_decision="allowed",
                response_truncated=False,
                metadata=_aws_metadata(5, s3=False),
            )
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT: (
            RangerAwsS3DeleteAttemptArtifact(
                context=_aws_context(NOW + timedelta(minutes=5)),
                requested_version_id=AWS_OBJECT_VERSION_ID,
                requested_bypass_governance_retention=False,
                error_code="AccessDenied",
                error_message="Access Denied",
                metadata=_aws_metadata(6, status=403),
            )
        ),
        RangerImmutableEvidenceArtifactKind.RETRIEVAL: (
            RangerAwsS3PostDenialRetrievalArtifact(
                context=_aws_context(NOW + timedelta(minutes=6)),
                get_object=RangerAwsS3GetObjectObservation(
                    requested_version_id=AWS_OBJECT_VERSION_ID,
                    requested_checksum_mode="ENABLED",
                    result_version_id=AWS_OBJECT_VERSION_ID,
                    result_checksum_sha256_base64=checksum,
                    result_checksum_type="FULL_OBJECT",
                    body_digest_sha256=archive_digest,
                    content_length_bytes=1024,
                    metadata=_aws_metadata(7),
                ),
            )
        ),
    }
    return {
        kind: aws_s3_object_lock_artifact_bytes(artifact)
        for kind, artifact in artifacts.items()
    }


def _aws_bundle(tmp_path: Path) -> dict[str, Any]:
    bundle = _bundle(tmp_path, RangerImmutableEvidenceEnvironment.PROVIDER_CONTROL_PLANE)
    archive_digest = bundle["issue_kwargs"]["publication_archive_bundle_digest_sha256"]
    artifacts = _aws_artifacts(archive_digest)
    issue_kwargs = {
        **bundle["issue_kwargs"],
        "backend_provider_id": AWS_S3_OBJECT_LOCK_PROVIDER_ID,
        "backend_instance_id": AWS_BACKEND_INSTANCE_ID,
        "backend_namespace": AWS_BACKEND_NAMESPACE,
        "object_key": AWS_OBJECT_KEY,
        "object_version_id": AWS_OBJECT_VERSION_ID,
        "delete_test_principal_id": AWS_DELETE_PRINCIPAL_ARN,
        "delete_result_detail": "aws_s3:AccessDenied:http_403",
        "evidence_artifacts": artifacts,
    }
    bundle["issue_kwargs"] = issue_kwargs
    bundle["artifacts"] = artifacts
    bundle["qualification"] = bundle["issuer"].issue(**issue_kwargs)
    bundle["policy"] = RangerImmutablePublicationVerificationPolicy.model_validate(
        {
            **bundle["policy"].model_dump(),
            "expected_backend_provider_id": AWS_S3_OBJECT_LOCK_PROVIDER_ID,
            "expected_backend_instance_id": AWS_BACKEND_INSTANCE_ID,
            "expected_backend_namespace": AWS_BACKEND_NAMESPACE,
            "expected_object_key": AWS_OBJECT_KEY,
            "expected_object_version_id": AWS_OBJECT_VERSION_ID,
            "expected_delete_test_principal_id": AWS_DELETE_PRINCIPAL_ARN,
        }
    )
    bundle["aws_policy"] = RangerAwsS3ObjectLockVerificationPolicy(
        expected_qualification_id=QUALIFICATION_ID,
        expected_verifier_challenge_nonce_hex=CHALLENGE_NONCE_HEX,
        expected_backend_instance_id=AWS_BACKEND_INSTANCE_ID,
        expected_backend_namespace=AWS_BACKEND_NAMESPACE,
        expected_aws_partition="aws",
        expected_aws_account_id=AWS_ACCOUNT_ID,
        expected_aws_region=AWS_REGION,
        expected_bucket_name=AWS_BUCKET,
        expected_object_key=AWS_OBJECT_KEY,
        expected_object_version_id=AWS_OBJECT_VERSION_ID,
        expected_delete_test_principal_arn=AWS_DELETE_PRINCIPAL_ARN,
        expected_archive_bundle_digest_sha256=archive_digest,
    )
    return bundle


def _verify_aws(bundle: dict[str, Any]):
    return verify_aws_s3_object_lock_qualification(
        bundle["qualification"],
        bundle["receipts"],
        bundle["publisher_standings"],
        bundle["retrieval_audit"],
        bundle["retrieval_standing"],
        bundle["events"],
        bundle["artifacts"],
        qualification_policy=bundle["policy"],
        aws_policy=bundle["aws_policy"],
    )


def _replace_aws_artifact(
    bundle: dict[str, Any],
    kind: RangerImmutableEvidenceArtifactKind,
    mutate: Any,
) -> None:
    payload = json.loads(bundle["artifacts"][kind])
    mutate(payload)
    artifacts = {**bundle["artifacts"], kind: canonicalize(payload)}
    bundle["artifacts"] = artifacts
    bundle["issue_kwargs"] = {**bundle["issue_kwargs"], "evidence_artifacts": artifacts}
    bundle["qualification"] = bundle["issuer"].issue(**bundle["issue_kwargs"])


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


def test_aws_s3_object_lock_artifacts_compose_with_provider_qualification(
    tmp_path: Path,
) -> None:
    bundle = _aws_bundle(tmp_path)

    result = _verify_aws(bundle)

    assert result.valid
    assert result.provider_neutral_qualification_verified
    assert result.provider_artifact_schemas_verified
    assert result.provider_artifact_digest_bindings_verified
    assert result.provider_resource_identity_verified
    assert result.bucket_versioning_enabled
    assert result.bucket_object_lock_enabled
    assert result.full_object_put_checksum_verified
    assert result.object_compliance_retention_verified
    assert result.delete_principal_identity_policy_capability_reported
    assert result.version_specific_delete_access_denied_while_retained
    assert result.post_denial_version_retrieval_verified
    assert result.provider_specific_artifact_profile_passed
    assert not result.provider_generated_artifact_authenticity_proven
    assert not result.complete_effective_authorization_proven
    assert not result.retention_causality_proven
    assert not result.physical_worm_storage_proven
    assert not result.organizational_independence_proven
    assert not result.trusted_time_proven
    assert not result.operational_authorization_proven
    assert not result.semantic_truth_proven
    assert not result.physical_outcome_proven
    bundle["store"].close()


@pytest.mark.parametrize(
    ("model", "schema_id"),
    [
        (
            RangerAwsS3ObjectLockConfigurationArtifact,
            "aws-s3-object-lock/configuration/v1",
        ),
        (
            RangerAwsS3ObjectLockRetentionPutArtifact,
            "aws-s3-object-lock/retention-put/v1",
        ),
        (RangerAwsIamDeleteCapabilityArtifact, "aws-iam/delete-capability/v1"),
        (
            RangerAwsS3DeleteAttemptArtifact,
            "aws-s3-object-lock/delete-attempt/v1",
        ),
        (
            RangerAwsS3PostDenialRetrievalArtifact,
            "aws-s3-object-lock/retrieval/v1",
        ),
    ],
)
def test_aws_s3_object_lock_artifact_schemas_are_stable_and_closed(
    model: type[Any], schema_id: str
) -> None:
    schema = model.model_json_schema()

    assert schema["$id"] == f"https://lanternprotocol.org/schemas/ets/ranger/{schema_id}"
    assert schema["additionalProperties"] is False


def test_aws_s3_object_lock_rejects_simulation_even_with_provider_artifacts(
    tmp_path: Path,
) -> None:
    bundle = _aws_bundle(tmp_path)
    bundle["issue_kwargs"] = {
        **bundle["issue_kwargs"],
        "evidence_environment": RangerImmutableEvidenceEnvironment.SIMULATION,
    }
    bundle["qualification"] = bundle["issuer"].issue(**bundle["issue_kwargs"])
    bundle["policy"] = bundle["policy"].model_copy(
        update={"expected_evidence_environment": RangerImmutableEvidenceEnvironment.SIMULATION}
    )

    result = _verify_aws(bundle)

    assert not result.valid
    assert result.provider_neutral_qualification_verified
    assert result.provider_artifact_digest_bindings_verified
    assert not result.provider_artifact_schemas_verified
    assert "not a provider-control-plane record" in result.reason
    bundle["store"].close()


@pytest.mark.parametrize(
    ("kind", "mutation", "reason"),
    [
        (
            RangerImmutableEvidenceArtifactKind.CONFIGURATION,
            lambda payload: payload["context"].__setitem__("object_version_id", "substituted"),
            "resource identity",
        ),
        (
            RangerImmutableEvidenceArtifactKind.RETENTION_PUT,
            lambda payload: payload["context"].__setitem__(
                "verifier_challenge_nonce_hex", "d" * 64
            ),
            "resource identity",
        ),
        (
            RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY,
            lambda payload: payload.__setitem__(
                "resource_arn", f"arn:aws:s3:::{AWS_BUCKET}/substituted.json"
            ),
            "DeleteObjectVersion decision",
        ),
        (
            RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT,
            lambda payload: payload.__setitem__("requested_version_id", "substituted"),
            "version-specific",
        ),
        (
            RangerImmutableEvidenceArtifactKind.RETRIEVAL,
            lambda payload: payload["get_object"].__setitem__(
                "result_version_id", "substituted"
            ),
            "exact version",
        ),
    ],
)
def test_aws_s3_object_lock_rejects_cross_trial_or_object_substitution(
    tmp_path: Path,
    kind: RangerImmutableEvidenceArtifactKind,
    mutation: Any,
    reason: str,
) -> None:
    bundle = _aws_bundle(tmp_path)
    _replace_aws_artifact(bundle, kind, mutation)

    result = _verify_aws(bundle)

    assert not result.valid
    assert result.provider_neutral_qualification_verified
    assert result.provider_artifact_schemas_verified
    assert result.provider_artifact_digest_bindings_verified
    assert reason in result.reason
    bundle["store"].close()


@pytest.mark.parametrize(
    ("path", "value", "reason"),
    [
        (("put_object", "requested_object_lock_mode"), "GOVERNANCE", "COMPLIANCE"),
        (("put_object", "result_checksum_type"), "COMPOSITE", "full-object SHA-256"),
        (("get_object_retention", "mode"), "GOVERNANCE", "COMPLIANCE"),
        (
            ("get_object_retention", "retain_until_utc"),
            "2026-09-15T08:00:00Z",
            "retention interval",
        ),
    ],
)
def test_aws_s3_object_lock_rejects_weak_or_substituted_retention(
    tmp_path: Path,
    path: tuple[str, str],
    value: str,
    reason: str,
) -> None:
    bundle = _aws_bundle(tmp_path)

    def mutate(payload: dict[str, Any]) -> None:
        payload[path[0]][path[1]] = value

    _replace_aws_artifact(bundle, RangerImmutableEvidenceArtifactKind.RETENTION_PUT, mutate)

    result = _verify_aws(bundle)

    assert not result.valid
    assert reason in result.reason
    bundle["store"].close()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evaluation_decision", "implicitDeny"),
        ("response_truncated", True),
    ],
)
def test_aws_s3_object_lock_rejects_incapable_or_incomplete_delete_preflight(
    tmp_path: Path, field: str, value: str | bool
) -> None:
    bundle = _aws_bundle(tmp_path)
    _replace_aws_artifact(
        bundle,
        RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY,
        lambda payload: payload.__setitem__(field, value),
    )

    result = _verify_aws(bundle)

    assert not result.valid
    assert "complete allowed DeleteObjectVersion decision" in result.reason
    bundle["store"].close()


def test_aws_s3_object_lock_rejects_non_versioned_or_successful_delete(
    tmp_path: Path,
) -> None:
    no_version = _aws_bundle(tmp_path / "no-version")
    _replace_aws_artifact(
        no_version,
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT,
        lambda payload: payload.__setitem__("requested_version_id", "null"),
    )
    no_version_result = _verify_aws(no_version)
    assert not no_version_result.valid
    assert "version-specific" in no_version_result.reason

    successful = _aws_bundle(tmp_path / "successful")
    _replace_aws_artifact(
        successful,
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT,
        lambda payload: payload["metadata"].__setitem__("http_status_code", 204),
    )
    successful_result = _verify_aws(successful)
    assert not successful_result.valid
    assert "HTTP 403" in successful_result.reason
    no_version["store"].close()
    successful["store"].close()


def test_aws_s3_object_lock_rejects_post_denial_content_or_checksum_substitution(
    tmp_path: Path,
) -> None:
    bundle = _aws_bundle(tmp_path)
    substituted_checksum = base64.b64encode(bytes.fromhex("f" * 64)).decode("ascii")
    _replace_aws_artifact(
        bundle,
        RangerImmutableEvidenceArtifactKind.RETRIEVAL,
        lambda payload: payload["get_object"].__setitem__(
            "result_checksum_sha256_base64", substituted_checksum
        ),
    )

    result = _verify_aws(bundle)

    assert not result.valid
    assert "archive digest" in result.reason
    bundle["store"].close()


def test_aws_s3_object_lock_rejects_replayed_provider_request_id(tmp_path: Path) -> None:
    bundle = _aws_bundle(tmp_path)
    _replace_aws_artifact(
        bundle,
        RangerImmutableEvidenceArtifactKind.RETRIEVAL,
        lambda payload: payload["get_object"]["metadata"].__setitem__(
            "request_id", "aws-request-6"
        ),
    )

    result = _verify_aws(bundle)

    assert not result.valid
    assert "reuse a provider request ID" in result.reason
    bundle["store"].close()


@pytest.mark.parametrize("encoding", ["duplicate", "pretty", "extra"])
def test_aws_s3_object_lock_rejects_ambiguous_or_noncanonical_json(
    tmp_path: Path, encoding: str
) -> None:
    bundle = _aws_bundle(tmp_path)
    kind = RangerImmutableEvidenceArtifactKind.CONFIGURATION
    raw = bundle["artifacts"][kind]
    if encoding == "duplicate":
        replacement = b'{"artifact_kind":"configuration",' + raw[1:]
    else:
        payload = json.loads(raw)
        if encoding == "extra":
            payload["unrecognized"] = True
            replacement = canonicalize(payload)
        else:
            replacement = json.dumps(payload, indent=2).encode("utf-8")
    artifacts = {**bundle["artifacts"], kind: replacement}
    bundle["artifacts"] = artifacts
    bundle["issue_kwargs"] = {**bundle["issue_kwargs"], "evidence_artifacts": artifacts}
    bundle["qualification"] = bundle["issuer"].issue(**bundle["issue_kwargs"])

    result = _verify_aws(bundle)

    assert not result.valid
    assert result.provider_neutral_qualification_verified
    assert not result.provider_artifact_schemas_verified
    assert result.provider_artifact_digest_bindings_verified
    assert "schema validation failed" in result.reason
    bundle["store"].close()
