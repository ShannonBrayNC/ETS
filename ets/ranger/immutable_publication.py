"""Bounded immutable-publication qualification evidence for Ranger R0.2.

The profile binds provider/control-plane evidence artifacts to an exact Ranger publication
archive bundle, publication head, retrieval audit, and publication/custodian key history.  A
simulation emits the same source record but cannot pass the live-provider evidence boundary.

Even a successful live-provider profile proves only that the configured evidence issuer signed
a conformant record over the supplied artifacts.  It does not by itself prove physical WORM
media, organizational independence, globally current state, trusted time, continued availability,
semantic truth, actuator response, or physical outcome.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Self

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.external_publication import RangerExternalPublicationReceipt
from ets.ranger.publication_archive import (
    RangerPublicationRetrievalAudit,
    verify_publication_retrieval_audit,
)
from ets.ranger.publication_key_lifecycle import (
    RangerPublicationKeyAuthorityEvent,
    RangerPublicationSourceKeyStanding,
    verify_publication_lifecycle_chain,
    verify_publication_source_key_standing,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerImmutablePublicationError(RuntimeError):
    """Raised when immutable-publication qualification evidence cannot be built safely."""


class RangerImmutableEvidenceEnvironment(StrEnum):
    SIMULATION = "simulation"
    PROVIDER_CONTROL_PLANE = "provider_control_plane"


class RangerImmutableRetentionMode(StrEnum):
    COMPLIANCE = "compliance"
    GOVERNANCE = "governance"
    NONE = "none"


class RangerImmutableDeleteOutcome(StrEnum):
    DENIED_BY_RETENTION = "denied_by_retention"
    DELETED = "deleted"
    NOT_ATTEMPTED = "not_attempted"
    ERROR = "error"


class RangerImmutableRetrievalOutcome(StrEnum):
    CONTENT_MATCH = "content_match"
    CONTENT_MISMATCH = "content_mismatch"
    NOT_FOUND = "not_found"
    ERROR = "error"


class RangerImmutableEvidenceArtifactKind(StrEnum):
    CONFIGURATION = "configuration"
    RETENTION_PUT = "retention_put"
    DELETE_CAPABILITY = "delete_capability"
    DELETE_ATTEMPT = "delete_attempt"
    RETRIEVAL = "retrieval"


_REQUIRED_ARTIFACT_KINDS = frozenset(RangerImmutableEvidenceArtifactKind)


class RangerImmutablePublicationQualification(StrictModel):
    """Evidence-issuer-signed report for one exact object-retention trial."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.org/schemas/ets/ranger/"
                "immutable-publication-qualification/v1"
            )
        },
    )

    schema_version: Literal["ets.ranger.immutable-publication-qualification.v1"] = (
        "ets.ranger.immutable-publication-qualification.v1"
    )
    qualification_id: str = Field(min_length=1, max_length=256)
    verifier_challenge_nonce_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    publication_scope_id: str = Field(min_length=24, max_length=192)
    evidence_environment: RangerImmutableEvidenceEnvironment

    backend_provider_id: str = Field(min_length=1, max_length=160)
    backend_instance_id: str = Field(min_length=1, max_length=256)
    backend_namespace: str = Field(min_length=1, max_length=512)
    object_key: str = Field(min_length=1, max_length=1024)
    object_version_id: str = Field(min_length=1, max_length=512)

    expected_publication_head_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retained_publication_head_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    publication_archive_bundle_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    publication_retrieval_audit_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    configuration_evidence_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retention_put_evidence_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    delete_capability_evidence_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    delete_attempt_evidence_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_evidence_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    versioning_enabled: bool
    retention_mode: RangerImmutableRetentionMode
    retention_bypass_permitted: bool
    configuration_observed_at_utc: datetime
    retained_at_utc: datetime
    retention_until_utc: datetime

    delete_test_principal_id: str = Field(min_length=1, max_length=256)
    delete_attempted_at_utc: datetime
    delete_outcome: RangerImmutableDeleteOutcome
    delete_result_detail: str | None = Field(default=None, min_length=1, max_length=256)

    retrieval_observed_at_utc: datetime
    retrieval_outcome: RangerImmutableRetrievalOutcome
    retrieved_archive_bundle_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )

    evidence_issuer_id: str = Field(min_length=1, max_length=160)
    evidence_signing_key_id: str = Field(min_length=1, max_length=256)
    evidence_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    qualification_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")

    evidence_artifacts_content_addressed: Literal[True] = True
    evidence_issuer_key_lifecycle_proven: Literal[False] = False
    physical_worm_storage_proven: Literal[False] = False
    organizational_independence_proven: Literal[False] = False
    hardware_rollback_resistance_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    globally_current_state_proven: Literal[False] = False
    continued_availability_proven: Literal[False] = False
    operational_authorization_proven: Literal[False] = False
    complete_capture_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    actuator_response_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "configured_immutable_backend_evidence_no_physical_worm_independence_time_or_truth_claim"
    ] = "configured_immutable_backend_evidence_no_physical_worm_independence_time_or_truth_claim"

    @field_validator("publication_scope_id")
    @classmethod
    def require_publication_scope(cls, value: str) -> str:
        if not value.startswith("ets-ranger-publication:"):
            raise ValueError("publication_scope_id must use the ets-ranger-publication: namespace")
        return value

    @field_validator(
        "configuration_observed_at_utc",
        "retained_at_utc",
        "retention_until_utc",
        "delete_attempted_at_utc",
        "retrieval_observed_at_utc",
    )
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("qualification observation times must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_coherent_trial(self) -> Self:
        if not (
            self.configuration_observed_at_utc
            <= self.retained_at_utc
            <= self.delete_attempted_at_utc
            <= self.retrieval_observed_at_utc
            < self.retention_until_utc
        ):
            raise ValueError(
                "configuration, retention, deletion, retrieval, and retention-until times "
                "must be ordered"
            )
        detail_required = self.delete_outcome in {
            RangerImmutableDeleteOutcome.DENIED_BY_RETENTION,
            RangerImmutableDeleteOutcome.ERROR,
        }
        if detail_required != (self.delete_result_detail is not None):
            raise ValueError(
                "delete result detail must be present exactly for denied/error results"
            )
        if self.retrieval_outcome is RangerImmutableRetrievalOutcome.CONTENT_MATCH:
            if (
                self.retrieved_archive_bundle_digest_sha256
                != self.publication_archive_bundle_digest_sha256
            ):
                raise ValueError("content_match requires the exact retained archive bundle digest")
        elif self.retrieval_outcome is RangerImmutableRetrievalOutcome.CONTENT_MISMATCH:
            if self.retrieved_archive_bundle_digest_sha256 in {
                None,
                self.publication_archive_bundle_digest_sha256,
            }:
                raise ValueError("content_mismatch requires a different observed bundle digest")
        elif self.retrieved_archive_bundle_digest_sha256 is not None:
            raise ValueError("not-found/error retrieval cannot report a content digest")
        artifact_digests = {
            self.configuration_evidence_digest_sha256,
            self.retention_put_evidence_digest_sha256,
            self.delete_capability_evidence_digest_sha256,
            self.delete_attempt_evidence_digest_sha256,
            self.retrieval_evidence_digest_sha256,
        }
        if len(artifact_digests) != len(_REQUIRED_ARTIFACT_KINDS):
            raise ValueError("each qualification evidence artifact must have a distinct digest")
        return self


class RangerImmutablePublicationVerificationPolicy(StrictModel):
    """Pinned verifier configuration; no value is discovered from the qualification record."""

    expected_qualification_id: str = Field(min_length=1, max_length=256)
    expected_verifier_challenge_nonce_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_publication_scope_id: str = Field(min_length=24, max_length=192)
    expected_publication_head_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_publisher_id: str = Field(min_length=1, max_length=160)
    expected_custodian_id: str = Field(min_length=1, max_length=160)
    expected_authority_id: str = Field(min_length=1, max_length=160)
    expected_authority_signing_key_id: str = Field(min_length=1, max_length=256)
    authority_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_registry_id: str = Field(min_length=1, max_length=160)
    expected_registry_signing_key_id: str = Field(min_length=1, max_length=256)
    expected_custodian_signing_key_id: str = Field(min_length=1, max_length=256)
    custodian_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")

    expected_backend_provider_id: str = Field(min_length=1, max_length=160)
    expected_backend_instance_id: str = Field(min_length=1, max_length=256)
    expected_backend_namespace: str = Field(min_length=1, max_length=512)
    expected_object_key: str = Field(min_length=1, max_length=1024)
    expected_object_version_id: str = Field(min_length=1, max_length=512)
    expected_delete_test_principal_id: str = Field(min_length=1, max_length=256)
    expected_evidence_environment: RangerImmutableEvidenceEnvironment
    expected_evidence_issuer_id: str = Field(min_length=1, max_length=160)
    expected_evidence_signing_key_id: str = Field(min_length=1, max_length=256)
    evidence_issuer_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    minimum_reported_retention_seconds: int = Field(ge=1, le=10 * 365 * 24 * 60 * 60)

    @field_validator("expected_publication_scope_id")
    @classmethod
    def require_publication_scope(cls, value: str) -> str:
        if not value.startswith("ets-ranger-publication:"):
            raise ValueError(
                "expected_publication_scope_id must use the ets-ranger-publication: namespace"
            )
        return value

    @model_validator(mode="after")
    def require_role_separation(self) -> Self:
        identities = {
            self.expected_publisher_id,
            self.expected_custodian_id,
            self.expected_authority_id,
            self.expected_evidence_issuer_id,
        }
        if len(identities) != 4:
            raise ValueError(
                "publisher, custodian, authority, and evidence issuer must be distinct"
            )
        key_ids = {
            self.expected_custodian_signing_key_id,
            self.expected_authority_signing_key_id,
            self.expected_evidence_signing_key_id,
        }
        if len(key_ids) != 3:
            raise ValueError("custodian, authority, and evidence signing-key IDs must be distinct")
        keys = {
            self.custodian_public_key_hex,
            self.authority_public_key_hex,
            self.evidence_issuer_public_key_hex,
        }
        if len(keys) != 3:
            raise ValueError("custodian, authority, and evidence public keys must be distinct")
        return self


class RangerImmutablePublicationQualificationVerification(StrictModel):
    valid: bool
    qualification_profile_conformant: bool = False
    evidence_issuer_signature_valid: bool = False
    separate_evidence_issuer_key_proven: bool = False
    evidence_issuer_key_lifecycle_proven: Literal[False] = False
    evidence_artifact_integrity_verified: bool = False
    publication_chain_verified: bool = False
    historical_publisher_key_standing_proven: bool = False
    matches_expected_publication_head: bool = False
    archive_bundle_binding_verified: bool = False
    retrieval_audit_verified: bool = False
    historical_custodian_key_standing_proven: bool = False
    custodian_current_relative_to_presented_history: bool = False
    compliant_retention_configuration_reported: bool = False
    deletion_denial_reported: bool = False
    post_denial_retrieval_verified: bool = False
    provider_control_plane_evidence_profile_passed: bool = False
    simulation_profile_only: bool = False
    physical_worm_storage_proven: Literal[False] = False
    organizational_independence_proven: Literal[False] = False
    hardware_rollback_resistance_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    globally_current_state_proven: Literal[False] = False
    continued_availability_proven: Literal[False] = False
    operational_authorization_proven: Literal[False] = False
    complete_capture_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    actuator_response_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


class RangerImmutablePublicationEvidenceIssuer:
    """Sign one provider-neutral qualification record from preserved adapter artifacts."""

    def __init__(
        self,
        *,
        evidence_issuer_id: str,
        evidence_signing_key_id: str,
        evidence_signing_key_hex: str,
    ) -> None:
        if not evidence_issuer_id or len(evidence_issuer_id) > 160:
            raise RangerImmutablePublicationError(
                "evidence_issuer_id must contain 1-160 characters"
            )
        if not evidence_signing_key_id or len(evidence_signing_key_id) > 256:
            raise RangerImmutablePublicationError(
                "evidence_signing_key_id must contain 1-256 characters"
            )
        self.evidence_issuer_id = evidence_issuer_id
        self.evidence_signing_key_id = evidence_signing_key_id
        self._signing_key = _private_key(evidence_signing_key_hex)

    @property
    def evidence_public_key_hex(self) -> str:
        return self._signing_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    def issue(
        self,
        *,
        qualification_id: str,
        verifier_challenge_nonce_hex: str,
        publication_scope_id: str,
        evidence_environment: RangerImmutableEvidenceEnvironment,
        backend_provider_id: str,
        backend_instance_id: str,
        backend_namespace: str,
        object_key: str,
        object_version_id: str,
        expected_publication_head_digest_sha256: str,
        retained_publication_head_digest_sha256: str,
        publication_archive_bundle_digest_sha256: str,
        publication_retrieval_audit_digest_sha256: str,
        evidence_artifacts: Mapping[RangerImmutableEvidenceArtifactKind | str, bytes],
        versioning_enabled: bool,
        retention_mode: RangerImmutableRetentionMode,
        retention_bypass_permitted: bool,
        configuration_observed_at_utc: datetime,
        retained_at_utc: datetime,
        retention_until_utc: datetime,
        delete_test_principal_id: str,
        delete_attempted_at_utc: datetime,
        delete_outcome: RangerImmutableDeleteOutcome,
        delete_result_detail: str | None,
        retrieval_observed_at_utc: datetime,
        retrieval_outcome: RangerImmutableRetrievalOutcome,
        retrieved_archive_bundle_digest_sha256: str | None,
    ) -> RangerImmutablePublicationQualification:
        """Issue a signed record; raw artifacts remain required for independent verification."""

        artifact_digests = _artifact_digests(evidence_artifacts)
        public_bytes = self._signing_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        candidate = RangerImmutablePublicationQualification.model_validate(
            {
                "qualification_id": qualification_id,
                "verifier_challenge_nonce_hex": verifier_challenge_nonce_hex,
                "publication_scope_id": publication_scope_id,
                "evidence_environment": evidence_environment,
                "backend_provider_id": backend_provider_id,
                "backend_instance_id": backend_instance_id,
                "backend_namespace": backend_namespace,
                "object_key": object_key,
                "object_version_id": object_version_id,
                "expected_publication_head_digest_sha256": (
                    expected_publication_head_digest_sha256
                ),
                "retained_publication_head_digest_sha256": (
                    retained_publication_head_digest_sha256
                ),
                "publication_archive_bundle_digest_sha256": (
                    publication_archive_bundle_digest_sha256
                ),
                "publication_retrieval_audit_digest_sha256": (
                    publication_retrieval_audit_digest_sha256
                ),
                "configuration_evidence_digest_sha256": artifact_digests[
                    RangerImmutableEvidenceArtifactKind.CONFIGURATION
                ],
                "retention_put_evidence_digest_sha256": artifact_digests[
                    RangerImmutableEvidenceArtifactKind.RETENTION_PUT
                ],
                "delete_capability_evidence_digest_sha256": artifact_digests[
                    RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY
                ],
                "delete_attempt_evidence_digest_sha256": artifact_digests[
                    RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT
                ],
                "retrieval_evidence_digest_sha256": artifact_digests[
                    RangerImmutableEvidenceArtifactKind.RETRIEVAL
                ],
                "versioning_enabled": versioning_enabled,
                "retention_mode": retention_mode,
                "retention_bypass_permitted": retention_bypass_permitted,
                "configuration_observed_at_utc": configuration_observed_at_utc,
                "retained_at_utc": retained_at_utc,
                "retention_until_utc": retention_until_utc,
                "delete_test_principal_id": delete_test_principal_id,
                "delete_attempted_at_utc": delete_attempted_at_utc,
                "delete_outcome": delete_outcome,
                "delete_result_detail": delete_result_detail,
                "retrieval_observed_at_utc": retrieval_observed_at_utc,
                "retrieval_outcome": retrieval_outcome,
                "retrieved_archive_bundle_digest_sha256": (retrieved_archive_bundle_digest_sha256),
                "evidence_issuer_id": self.evidence_issuer_id,
                "evidence_signing_key_id": self.evidence_signing_key_id,
                "evidence_public_key_fingerprint_sha256": hashlib.sha256(public_bytes).hexdigest(),
                "qualification_digest_sha256": "0" * 64,
                "evidence_signature_hex": "0" * 128,
            }
        )
        payload = _qualification_payload_from_record(candidate)
        complete = candidate.model_copy(
            update={
                "qualification_digest_sha256": canonical_sha256(payload),
                "evidence_signature_hex": self._signing_key.sign(canonicalize(payload)).hex(),
            }
        )
        return RangerImmutablePublicationQualification.model_validate(complete.model_dump())


def publication_archive_bundle_digest(
    receipts: Iterable[RangerExternalPublicationReceipt],
) -> str:
    """Hash the exact ordered publication records retained in one backend object."""

    try:
        validated = [
            RangerExternalPublicationReceipt.model_validate(receipt.model_dump())
            for receipt in receipts
        ]
    except (AttributeError, ValidationError) as exc:
        raise RangerImmutablePublicationError("publication archive bundle is invalid") from exc
    if not validated:
        raise RangerImmutablePublicationError("publication archive bundle is empty")
    return canonical_sha256(
        {
            "schema_version": "ets.ranger.publication-archive-bundle.v1",
            "receipts": [receipt.model_dump(mode="json") for receipt in validated],
        }
    )


def verify_immutable_publication_qualification(
    qualification: RangerImmutablePublicationQualification,
    receipts: Iterable[RangerExternalPublicationReceipt],
    publisher_standings: Iterable[RangerPublicationSourceKeyStanding],
    retrieval_audit: RangerPublicationRetrievalAudit,
    retrieval_audit_standing: RangerPublicationSourceKeyStanding,
    authority_events: Iterable[RangerPublicationKeyAuthorityEvent],
    evidence_artifacts: Mapping[RangerImmutableEvidenceArtifactKind | str, bytes],
    *,
    policy: RangerImmutablePublicationVerificationPolicy,
) -> RangerImmutablePublicationQualificationVerification:
    """Verify exact bindings and bounded retention-trial semantics fail closed."""

    try:
        record = RangerImmutablePublicationQualification.model_validate(qualification.model_dump())
        configured = RangerImmutablePublicationVerificationPolicy.model_validate(
            policy.model_dump()
        )
    except (AttributeError, ValidationError):
        return _qualification_failure(
            "immutable-publication qualification schema validation failed"
        )

    configuration_error = _configuration_error(record, configured)
    if configuration_error is not None:
        return _qualification_failure(configuration_error)

    evidence_key_bytes = _public_key_bytes(configured.evidence_issuer_public_key_hex)
    if evidence_key_bytes is None:
        return _qualification_failure("evidence issuer public key is not 32-byte Ed25519")
    evidence_fingerprint = hashlib.sha256(evidence_key_bytes).hexdigest()
    if record.evidence_public_key_fingerprint_sha256 != evidence_fingerprint:
        return _qualification_failure("qualification evidence issuer key fingerprint mismatch")
    payload = _qualification_payload_from_record(record)
    if canonical_sha256(payload) != record.qualification_digest_sha256:
        return _qualification_failure("immutable-publication qualification digest mismatch")
    try:
        Ed25519PublicKey.from_public_bytes(evidence_key_bytes).verify(
            bytes.fromhex(record.evidence_signature_hex), canonicalize(payload)
        )
    except (InvalidSignature, ValueError):
        return _qualification_failure("immutable-publication qualification signature is invalid")

    try:
        artifact_digests = _artifact_digests(evidence_artifacts)
    except RangerImmutablePublicationError as exc:
        return _qualification_failure(str(exc))
    expected_artifact_digests = {
        RangerImmutableEvidenceArtifactKind.CONFIGURATION: (
            record.configuration_evidence_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.RETENTION_PUT: (
            record.retention_put_evidence_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY: (
            record.delete_capability_evidence_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT: (
            record.delete_attempt_evidence_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.RETRIEVAL: record.retrieval_evidence_digest_sha256,
    }
    if artifact_digests != expected_artifact_digests:
        return _qualification_failure("qualification evidence artifact digest mismatch")

    chain = list(receipts)
    standing_records = list(publisher_standings)
    events = list(authority_events)
    source_key_fingerprints = {
        descriptor.public_key_fingerprint_sha256
        for event in events
        for descriptor in (
            event.request.intent.subject_key,
            *(
                ()
                if event.request.intent.replacement_key is None
                else (event.request.intent.replacement_key,)
            ),
        )
    }
    if evidence_fingerprint in source_key_fingerprints:
        return _qualification_failure(
            "qualification evidence issuer key must be distinct from publication source keys"
        )

    lifecycle = verify_publication_lifecycle_chain(
        chain,
        standing_records,
        events,
        authority_public_key_hex=configured.authority_public_key_hex,
        expected_publication_scope_id=configured.expected_publication_scope_id,
        expected_publisher_id=configured.expected_publisher_id,
        expected_custodian_id=configured.expected_custodian_id,
        expected_authority_id=configured.expected_authority_id,
        expected_authority_signing_key_id=configured.expected_authority_signing_key_id,
        expected_registry_id=configured.expected_registry_id,
        expected_registry_signing_key_id=configured.expected_registry_signing_key_id,
        expected_latest_publication_digest_sha256=(
            configured.expected_publication_head_digest_sha256
        ),
    )
    if not lifecycle.valid:
        return _qualification_failure(f"publication lifecycle chain is invalid: {lifecycle.reason}")
    try:
        bundle_digest = publication_archive_bundle_digest(chain)
    except RangerImmutablePublicationError as exc:
        return _qualification_failure(str(exc))
    if bundle_digest != record.publication_archive_bundle_digest_sha256:
        return _qualification_failure("qualification archive bundle digest mismatch")

    standing = verify_publication_source_key_standing(
        retrieval_audit_standing,
        retrieval_audit,
        events,
        authority_public_key_hex=configured.authority_public_key_hex,
        expected_publication_scope_id=configured.expected_publication_scope_id,
        expected_publisher_id=configured.expected_publisher_id,
        expected_custodian_id=configured.expected_custodian_id,
        expected_authority_id=configured.expected_authority_id,
        expected_authority_signing_key_id=configured.expected_authority_signing_key_id,
    )
    if not standing.valid:
        return _qualification_failure(
            f"retrieval-audit custodian standing is invalid: {standing.reason}"
        )
    if not standing.currently_authorized_relative_to_presented_history:
        return _qualification_failure(
            "retrieval-audit custodian is not current relative to presented authority history"
        )
    audit = verify_publication_retrieval_audit(
        retrieval_audit,
        custodian_public_key_hex=configured.custodian_public_key_hex,
        expected_custodian_id=configured.expected_custodian_id,
        expected_custodian_signing_key_id=configured.expected_custodian_signing_key_id,
        expected_publication_head_digest_sha256=(
            configured.expected_publication_head_digest_sha256
        ),
    )
    if not audit.valid or not audit.matches_expected_publication_head:
        return _qualification_failure(f"publication retrieval audit is invalid: {audit.reason}")
    if retrieval_audit.archived_receipt_count != len(chain):
        return _qualification_failure("retrieval audit receipt count does not match archive bundle")
    if not (
        record.retrieval_observed_at_utc
        <= retrieval_audit.observed_at_utc
        < record.retention_until_utc
    ):
        return _qualification_failure(
            "retrieval audit time is inconsistent with the reported retention trial"
        )
    if retrieval_audit.audit_digest_sha256 != record.publication_retrieval_audit_digest_sha256:
        return _qualification_failure("qualification retrieval-audit digest mismatch")

    reported_retention_seconds = int(
        (record.retention_until_utc - record.retained_at_utc).total_seconds()
    )
    compliant_configuration = (
        record.versioning_enabled
        and record.retention_mode is RangerImmutableRetentionMode.COMPLIANCE
        and not record.retention_bypass_permitted
        and reported_retention_seconds >= configured.minimum_reported_retention_seconds
    )
    if not compliant_configuration:
        return _qualification_failure(
            "qualification does not report the required versioned compliance retention policy"
        )
    if record.delete_outcome is not RangerImmutableDeleteOutcome.DENIED_BY_RETENTION:
        return _qualification_failure("qualification deletion-negative trial did not deny deletion")
    if record.retrieval_outcome is not RangerImmutableRetrievalOutcome.CONTENT_MATCH:
        return _qualification_failure(
            "qualification did not retrieve the exact archive bundle after deletion denial"
        )

    simulation_only = record.evidence_environment is RangerImmutableEvidenceEnvironment.SIMULATION
    provider_profile_passed = not simulation_only
    return RangerImmutablePublicationQualificationVerification(
        valid=True,
        qualification_profile_conformant=True,
        evidence_issuer_signature_valid=True,
        separate_evidence_issuer_key_proven=True,
        evidence_artifact_integrity_verified=True,
        publication_chain_verified=True,
        historical_publisher_key_standing_proven=(
            lifecycle.historical_publisher_key_standing_proven
        ),
        matches_expected_publication_head=True,
        archive_bundle_binding_verified=True,
        retrieval_audit_verified=True,
        historical_custodian_key_standing_proven=(
            standing.historical_authority_relative_key_standing
        ),
        custodian_current_relative_to_presented_history=True,
        compliant_retention_configuration_reported=True,
        deletion_denial_reported=True,
        post_denial_retrieval_verified=True,
        provider_control_plane_evidence_profile_passed=provider_profile_passed,
        simulation_profile_only=simulation_only,
        reason=(
            "the simulation record conforms to the immutable-publication evidence profile; no "
            "live backend, physical WORM, independence, trusted-time, availability, truth, or "
            "outcome claim is established"
            if simulation_only
            else "the configured evidence issuer signed a conformant provider-control-plane "
            "retention, deletion-denial, and post-denial retrieval record over the exact "
            "publication archive; physical WORM, organizational independence, trusted time, "
            "global currentness, continued availability, truth, and outcome remain unproven"
        ),
    )


def _configuration_error(
    record: RangerImmutablePublicationQualification,
    policy: RangerImmutablePublicationVerificationPolicy,
) -> str | None:
    expected = (
        (record.qualification_id, policy.expected_qualification_id, "qualification identity"),
        (
            record.verifier_challenge_nonce_hex,
            policy.expected_verifier_challenge_nonce_hex,
            "verifier challenge nonce",
        ),
        (
            record.publication_scope_id,
            policy.expected_publication_scope_id,
            "publication scope",
        ),
        (
            record.expected_publication_head_digest_sha256,
            policy.expected_publication_head_digest_sha256,
            "expected publication head",
        ),
        (
            record.retained_publication_head_digest_sha256,
            policy.expected_publication_head_digest_sha256,
            "retained publication head",
        ),
        (record.backend_provider_id, policy.expected_backend_provider_id, "backend provider"),
        (record.backend_instance_id, policy.expected_backend_instance_id, "backend instance"),
        (record.backend_namespace, policy.expected_backend_namespace, "backend namespace"),
        (record.object_key, policy.expected_object_key, "object key"),
        (record.object_version_id, policy.expected_object_version_id, "object version"),
        (
            record.delete_test_principal_id,
            policy.expected_delete_test_principal_id,
            "deletion-probe principal",
        ),
        (
            record.evidence_environment,
            policy.expected_evidence_environment,
            "evidence environment",
        ),
        (record.evidence_issuer_id, policy.expected_evidence_issuer_id, "evidence issuer"),
        (
            record.evidence_signing_key_id,
            policy.expected_evidence_signing_key_id,
            "evidence signing key",
        ),
    )
    for observed, configured, label in expected:
        if observed != configured:
            return f"qualification {label} does not match verifier configuration"
    return None


def _qualification_payload_from_record(
    record: RangerImmutablePublicationQualification,
) -> dict[str, Any]:
    payload = record.model_dump(mode="json")
    payload.pop("qualification_digest_sha256")
    payload.pop("evidence_signature_hex")
    return payload


def _artifact_digests(
    evidence_artifacts: Mapping[RangerImmutableEvidenceArtifactKind | str, bytes],
) -> dict[RangerImmutableEvidenceArtifactKind, str]:
    normalized: dict[RangerImmutableEvidenceArtifactKind, bytes] = {}
    for raw_kind, value in evidence_artifacts.items():
        try:
            kind = RangerImmutableEvidenceArtifactKind(raw_kind)
        except ValueError as exc:
            raise RangerImmutablePublicationError(
                f"unexpected immutable-publication evidence artifact: {raw_kind}"
            ) from exc
        if kind in normalized:
            raise RangerImmutablePublicationError(
                f"duplicate immutable-publication evidence artifact: {kind.value}"
            )
        if not isinstance(value, bytes) or not value:
            raise RangerImmutablePublicationError(
                f"immutable-publication evidence artifact {kind.value} must be non-empty bytes"
            )
        normalized[kind] = value
    if set(normalized) != _REQUIRED_ARTIFACT_KINDS:
        missing = sorted(kind.value for kind in _REQUIRED_ARTIFACT_KINDS - set(normalized))
        unexpected = sorted(kind.value for kind in set(normalized) - _REQUIRED_ARTIFACT_KINDS)
        raise RangerImmutablePublicationError(
            "immutable-publication evidence artifacts are incomplete "
            f"(missing={missing}, unexpected={unexpected})"
        )
    digests = {kind: hashlib.sha256(value).hexdigest() for kind, value in normalized.items()}
    if len(set(digests.values())) != len(_REQUIRED_ARTIFACT_KINDS):
        raise RangerImmutablePublicationError(
            "immutable-publication evidence artifacts must be content-distinct"
        )
    return digests


def _private_key(value: str) -> Ed25519PrivateKey:
    try:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value))
    except ValueError as exc:
        raise RangerImmutablePublicationError(
            "evidence signing key must be a 32-byte Ed25519 key"
        ) from exc


def _public_key_bytes(value: str) -> bytes | None:
    try:
        key_bytes = bytes.fromhex(value)
        if len(key_bytes) != 32:
            return None
        Ed25519PublicKey.from_public_bytes(key_bytes)
        return key_bytes
    except ValueError:
        return None


def _qualification_failure(
    reason: str,
) -> RangerImmutablePublicationQualificationVerification:
    return RangerImmutablePublicationQualificationVerification(valid=False, reason=reason)


__all__ = [
    "RangerImmutableDeleteOutcome",
    "RangerImmutableEvidenceArtifactKind",
    "RangerImmutableEvidenceEnvironment",
    "RangerImmutablePublicationError",
    "RangerImmutablePublicationEvidenceIssuer",
    "RangerImmutablePublicationQualification",
    "RangerImmutablePublicationQualificationVerification",
    "RangerImmutablePublicationVerificationPolicy",
    "RangerImmutableRetentionMode",
    "RangerImmutableRetrievalOutcome",
    "publication_archive_bundle_digest",
    "verify_immutable_publication_qualification",
]
