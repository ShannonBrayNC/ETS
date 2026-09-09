"""Authenticated administration and configured trusted-time evidence for Ranger R0.2.

This module adds cryptographic governance evidence around the existing key-authority request
contract without changing that v1 contract in place. It proves only that a configured
administrator key approved the exact request and that a configured time-authority key attested
the existence of a supplied digest at a bounded UTC interval. It does not prove human identity,
administrative independence, global clock correctness, Fleet authorization, complete capture,
semantic truth, or physical outcome.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.key_authority import RangerKeyBindingRequest, RangerKeyEventKind


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerGovernanceError(RuntimeError):
    """Raised when Ranger governance evidence cannot be built safely."""


class RangerGovernanceSubjectKind(StrEnum):
    ADMINISTRATIVE_APPROVAL = "administrative_approval"
    KEY_AUTHORITY_EVENT = "key_authority_event"
    RETAINED_AUTHORITY_HEAD = "retained_authority_head"
    AUTHORITY_BOUND_CHECKPOINT = "authority_bound_checkpoint"


class RangerAdministrativeApproval(StrictModel):
    """Administrator signature over the exact existing key-binding request."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/administrative-approval/v1"
        },
    )

    schema_version: Literal["ets.ranger.administrative-approval.v1"] = (
        "ets.ranger.administrative-approval.v1"
    )
    approval_id: str = Field(min_length=1, max_length=256)
    request_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_kind: RangerKeyEventKind
    vehicle_id: str = Field(min_length=12, max_length=160)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    administrator_id: str = Field(min_length=1, max_length=160)
    administrator_signing_key_id: str = Field(min_length=1, max_length=256)
    administrator_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    approval_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    administrator_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    authenticated_administration_proven: Literal[True] = True
    human_identity_proven: Literal[False] = False
    administrative_independence_proven: Literal[False] = False
    operational_device_authorization_proven: Literal[False] = False
    claim_boundary: Literal[
        "configured_admin_key_approval_no_human_independence_or_operational_claim"
    ] = "configured_admin_key_approval_no_human_independence_or_operational_claim"

    @field_validator("vehicle_id")
    @classmethod
    def require_ranger_vehicle_id(cls, value: str) -> str:
        if not value.startswith("ets-ranger:"):
            raise ValueError("vehicle_id must use the ets-ranger: namespace")
        return value


class RangerAdministrativeApprovalVerification(StrictModel):
    valid: bool
    request_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    approval_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authenticated_administration_proven: bool = False
    reason: str


class RangerTrustedTimeAttestation(StrictModel):
    """Configured time-authority signature over one evidence digest and UTC interval."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/trusted-time-attestation/v1"
        },
    )

    schema_version: Literal["ets.ranger.trusted-time-attestation.v1"] = (
        "ets.ranger.trusted-time-attestation.v1"
    )
    attestation_id: str = Field(min_length=1, max_length=256)
    subject_kind: RangerGovernanceSubjectKind
    subject_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at_utc: datetime
    uncertainty_ms: int = Field(ge=0, le=86_400_000)
    time_source_id: str = Field(min_length=1, max_length=160)
    time_signing_key_id: str = Field(min_length=1, max_length=256)
    time_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    attestation_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    time_authority_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    configured_time_authority_proven: Literal[True] = True
    trusted_time_proven: Literal[True] = True
    global_clock_correctness_proven: Literal[False] = False
    time_source_independence_proven: Literal[False] = False
    claim_boundary: Literal[
        "configured_time_authority_interval_no_global_clock_or_independence_claim"
    ] = "configured_time_authority_interval_no_global_clock_or_independence_claim"

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at_utc must be timezone-aware")
        return value.astimezone(UTC)


class RangerTrustedTimeVerification(StrictModel):
    valid: bool
    subject_kind: RangerGovernanceSubjectKind | None = None
    subject_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    observed_at_utc: datetime | None = None
    uncertainty_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    trusted_time_proven: bool = False
    reason: str


class RangerGovernedRequestVerification(StrictModel):
    valid: bool
    request_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    approval_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    time_attestation_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    authenticated_administration_proven: bool = False
    trusted_time_proven: bool = False
    authority_acceptance_proven: Literal[False] = False
    reason: str


def key_binding_request_digest(request: RangerKeyBindingRequest) -> str:
    """Return the canonical digest used by governance approval evidence."""

    validated = RangerKeyBindingRequest.model_validate(request.model_dump())
    return canonical_sha256(validated.model_dump(mode="json"))


def build_administrative_approval(
    request: RangerKeyBindingRequest,
    *,
    approval_id: str,
    administrator_id: str,
    administrator_signing_key_id: str,
    administrator_private_key_hex: str,
) -> RangerAdministrativeApproval:
    """Sign the exact key-binding request with a configured administrator key."""

    try:
        validated = RangerKeyBindingRequest.model_validate(request.model_dump())
    except (AttributeError, ValidationError) as exc:
        raise RangerGovernanceError("invalid Ranger key-binding request") from exc
    private_key = _private_key(administrator_private_key_hex, "administrator")
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    intent = validated.intent
    payload = _administrative_approval_payload(
        approval_id=approval_id,
        request_digest_sha256=key_binding_request_digest(validated),
        event_kind=intent.event_kind,
        vehicle_id=intent.vehicle_id,
        tenant_id=intent.tenant_id,
        workspace_id=intent.workspace_id,
        administrator_id=administrator_id,
        administrator_signing_key_id=administrator_signing_key_id,
        administrator_public_key_fingerprint_sha256=hashlib.sha256(public_bytes).hexdigest(),
    )
    digest = canonical_sha256(payload)
    try:
        return RangerAdministrativeApproval.model_validate(
            {
                **payload,
                "event_kind": intent.event_kind,
                "approval_digest_sha256": digest,
                "administrator_signature_hex": private_key.sign(canonicalize(payload)).hex(),
            }
        )
    except ValidationError as exc:
        raise RangerGovernanceError("invalid administrative approval fields") from exc


def verify_administrative_approval(
    request: RangerKeyBindingRequest,
    approval: RangerAdministrativeApproval,
    administrator_public_key_hex: str,
) -> RangerAdministrativeApprovalVerification:
    """Verify that one configured administrator approved the exact request and scope."""

    try:
        validated_request = RangerKeyBindingRequest.model_validate(request.model_dump())
        validated_approval = RangerAdministrativeApproval.model_validate(approval.model_dump())
    except (AttributeError, ValidationError):
        return _approval_failure("governance approval schema validation failed")

    intent = validated_request.intent
    expected_request_digest = key_binding_request_digest(validated_request)
    if validated_approval.request_digest_sha256 != expected_request_digest:
        return _approval_failure("administrative approval request digest mismatch")
    if (
        validated_approval.event_kind != intent.event_kind
        or validated_approval.vehicle_id != intent.vehicle_id
        or validated_approval.tenant_id != intent.tenant_id
        or validated_approval.workspace_id != intent.workspace_id
    ):
        return _approval_failure("administrative approval identity or scope mismatch")

    public_key, fingerprint = _public_key(administrator_public_key_hex)
    if public_key is None or fingerprint is None:
        return _approval_failure("administrator public key is not 32-byte Ed25519")
    if validated_approval.administrator_public_key_fingerprint_sha256 != fingerprint:
        return _approval_failure("administrator public key fingerprint mismatch")

    payload = _administrative_approval_payload_from_record(validated_approval)
    if canonical_sha256(payload) != validated_approval.approval_digest_sha256:
        return _approval_failure("administrative approval digest mismatch")
    try:
        public_key.verify(
            bytes.fromhex(validated_approval.administrator_signature_hex),
            canonicalize(payload),
        )
    except (InvalidSignature, ValueError):
        return _approval_failure("administrator signature invalid")

    return RangerAdministrativeApprovalVerification(
        valid=True,
        request_digest_sha256=expected_request_digest,
        approval_digest_sha256=validated_approval.approval_digest_sha256,
        authenticated_administration_proven=True,
        reason=(
            "configured administrator signature matches the exact key-binding request; human "
            "identity, administrative independence, and operational authorization are not proven"
        ),
    )


def build_trusted_time_attestation(
    *,
    attestation_id: str,
    subject_kind: RangerGovernanceSubjectKind,
    subject_digest_sha256: str,
    observed_at_utc: datetime,
    uncertainty_ms: int,
    time_source_id: str,
    time_signing_key_id: str,
    time_private_key_hex: str,
) -> RangerTrustedTimeAttestation:
    """Sign a digest and bounded UTC interval with a configured time-authority key."""

    observed_at = _require_aware_utc(observed_at_utc)
    private_key = _private_key(time_private_key_hex, "time authority")
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    payload = _trusted_time_payload(
        attestation_id=attestation_id,
        subject_kind=subject_kind,
        subject_digest_sha256=subject_digest_sha256,
        observed_at_utc=observed_at,
        uncertainty_ms=uncertainty_ms,
        time_source_id=time_source_id,
        time_signing_key_id=time_signing_key_id,
        time_public_key_fingerprint_sha256=hashlib.sha256(public_bytes).hexdigest(),
    )
    digest = canonical_sha256(payload)
    try:
        return RangerTrustedTimeAttestation.model_validate(
            {
                **payload,
                "subject_kind": subject_kind,
                "observed_at_utc": observed_at,
                "attestation_digest_sha256": digest,
                "time_authority_signature_hex": private_key.sign(canonicalize(payload)).hex(),
            }
        )
    except ValidationError as exc:
        raise RangerGovernanceError("invalid trusted-time attestation fields") from exc


def verify_trusted_time_attestation(
    attestation: RangerTrustedTimeAttestation,
    time_public_key_hex: str,
) -> RangerTrustedTimeVerification:
    """Verify one configured time-authority attestation without claiming global clock truth."""

    try:
        validated = RangerTrustedTimeAttestation.model_validate(attestation.model_dump())
    except (AttributeError, ValidationError):
        return _time_failure("trusted-time attestation schema validation failed")

    public_key, fingerprint = _public_key(time_public_key_hex)
    if public_key is None or fingerprint is None:
        return _time_failure("time authority public key is not 32-byte Ed25519")
    if validated.time_public_key_fingerprint_sha256 != fingerprint:
        return _time_failure("time authority public key fingerprint mismatch")

    payload = _trusted_time_payload_from_record(validated)
    if canonical_sha256(payload) != validated.attestation_digest_sha256:
        return _time_failure("trusted-time attestation digest mismatch")
    try:
        public_key.verify(
            bytes.fromhex(validated.time_authority_signature_hex),
            canonicalize(payload),
        )
    except (InvalidSignature, ValueError):
        return _time_failure("time authority signature invalid")

    return RangerTrustedTimeVerification(
        valid=True,
        subject_kind=validated.subject_kind,
        subject_digest_sha256=validated.subject_digest_sha256,
        observed_at_utc=validated.observed_at_utc,
        uncertainty_ms=validated.uncertainty_ms,
        trusted_time_proven=True,
        reason=(
            "configured time-authority signature verifies a bounded UTC interval for the exact "
            "subject digest; global clock correctness and source independence are not proven"
        ),
    )


def verify_governed_key_binding_request(
    request: RangerKeyBindingRequest,
    approval: RangerAdministrativeApproval,
    time_attestation: RangerTrustedTimeAttestation,
    *,
    administrator_public_key_hex: str,
    time_public_key_hex: str,
) -> RangerGovernedRequestVerification:
    """Compose administrator authentication and time evidence for one authority request."""

    approval_verification = verify_administrative_approval(
        request, approval, administrator_public_key_hex
    )
    if not approval_verification.valid:
        return _governed_failure(approval_verification.reason)
    time_verification = verify_trusted_time_attestation(time_attestation, time_public_key_hex)
    if not time_verification.valid:
        return _governed_failure(time_verification.reason)
    if time_attestation.subject_kind != RangerGovernanceSubjectKind.ADMINISTRATIVE_APPROVAL:
        return _governed_failure("time attestation does not target an administrative approval")
    if time_attestation.subject_digest_sha256 != approval.approval_digest_sha256:
        return _governed_failure("time attestation targets a different administrative approval")

    return RangerGovernedRequestVerification(
        valid=True,
        request_digest_sha256=approval.request_digest_sha256,
        approval_digest_sha256=approval.approval_digest_sha256,
        time_attestation_digest_sha256=time_attestation.attestation_digest_sha256,
        authenticated_administration_proven=True,
        trusted_time_proven=True,
        reason=(
            "the exact key-binding request has a valid configured-admin approval and that approval "
            "has configured-time-authority evidence; authority acceptance remains a separate claim"
        ),
    )


def verify_retained_receipt_time(
    *,
    subject_kind: RangerGovernanceSubjectKind,
    subject_digest_sha256: str,
    time_attestation: RangerTrustedTimeAttestation,
    time_public_key_hex: str,
) -> RangerTrustedTimeVerification:
    """Verify time evidence bound to one retained authority or custody checkpoint digest."""

    if subject_kind not in {
        RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
    }:
        return _time_failure("subject kind is not a retained Ranger receipt")
    verification = verify_trusted_time_attestation(time_attestation, time_public_key_hex)
    if not verification.valid:
        return verification
    if time_attestation.subject_kind != subject_kind:
        return _time_failure("trusted-time attestation retained-receipt kind mismatch")
    if time_attestation.subject_digest_sha256 != subject_digest_sha256:
        return _time_failure("trusted-time attestation retained-receipt digest mismatch")
    return verification


def _administrative_approval_payload(
    *,
    approval_id: str,
    request_digest_sha256: str,
    event_kind: RangerKeyEventKind,
    vehicle_id: str,
    tenant_id: str,
    workspace_id: str,
    administrator_id: str,
    administrator_signing_key_id: str,
    administrator_public_key_fingerprint_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "ets.ranger.administrative-approval.v1",
        "approval_id": approval_id,
        "request_digest_sha256": request_digest_sha256,
        "event_kind": event_kind.value,
        "vehicle_id": vehicle_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "administrator_id": administrator_id,
        "administrator_signing_key_id": administrator_signing_key_id,
        "administrator_public_key_fingerprint_sha256": (
            administrator_public_key_fingerprint_sha256
        ),
        "signing_algorithm": "ed25519",
        "authenticated_administration_proven": True,
        "human_identity_proven": False,
        "administrative_independence_proven": False,
        "operational_device_authorization_proven": False,
        "claim_boundary": (
            "configured_admin_key_approval_no_human_independence_or_operational_claim"
        ),
    }


def _administrative_approval_payload_from_record(
    approval: RangerAdministrativeApproval,
) -> dict[str, Any]:
    return _administrative_approval_payload(
        approval_id=approval.approval_id,
        request_digest_sha256=approval.request_digest_sha256,
        event_kind=approval.event_kind,
        vehicle_id=approval.vehicle_id,
        tenant_id=approval.tenant_id,
        workspace_id=approval.workspace_id,
        administrator_id=approval.administrator_id,
        administrator_signing_key_id=approval.administrator_signing_key_id,
        administrator_public_key_fingerprint_sha256=(
            approval.administrator_public_key_fingerprint_sha256
        ),
    )


def _trusted_time_payload(
    *,
    attestation_id: str,
    subject_kind: RangerGovernanceSubjectKind,
    subject_digest_sha256: str,
    observed_at_utc: datetime,
    uncertainty_ms: int,
    time_source_id: str,
    time_signing_key_id: str,
    time_public_key_fingerprint_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "ets.ranger.trusted-time-attestation.v1",
        "attestation_id": attestation_id,
        "subject_kind": subject_kind.value,
        "subject_digest_sha256": subject_digest_sha256,
        "observed_at_utc": observed_at_utc.isoformat().replace("+00:00", "Z"),
        "uncertainty_ms": uncertainty_ms,
        "time_source_id": time_source_id,
        "time_signing_key_id": time_signing_key_id,
        "time_public_key_fingerprint_sha256": time_public_key_fingerprint_sha256,
        "signing_algorithm": "ed25519",
        "configured_time_authority_proven": True,
        "trusted_time_proven": True,
        "global_clock_correctness_proven": False,
        "time_source_independence_proven": False,
        "claim_boundary": (
            "configured_time_authority_interval_no_global_clock_or_independence_claim"
        ),
    }


def _trusted_time_payload_from_record(
    attestation: RangerTrustedTimeAttestation,
) -> dict[str, Any]:
    return _trusted_time_payload(
        attestation_id=attestation.attestation_id,
        subject_kind=attestation.subject_kind,
        subject_digest_sha256=attestation.subject_digest_sha256,
        observed_at_utc=attestation.observed_at_utc,
        uncertainty_ms=attestation.uncertainty_ms,
        time_source_id=attestation.time_source_id,
        time_signing_key_id=attestation.time_signing_key_id,
        time_public_key_fingerprint_sha256=attestation.time_public_key_fingerprint_sha256,
    )


def _private_key(value: str, label: str) -> Ed25519PrivateKey:
    try:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value))
    except ValueError as exc:
        raise RangerGovernanceError(f"{label} private key must be a 32-byte Ed25519 key") from exc


def _public_key(value: str) -> tuple[Ed25519PublicKey | None, str | None]:
    try:
        key_bytes = bytes.fromhex(value)
        key = Ed25519PublicKey.from_public_bytes(key_bytes)
    except ValueError:
        return None, None
    return key, hashlib.sha256(key_bytes).hexdigest()


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangerGovernanceError("trusted-time observation must be timezone-aware")
    return value.astimezone(UTC)


def _approval_failure(reason: str) -> RangerAdministrativeApprovalVerification:
    return RangerAdministrativeApprovalVerification(valid=False, reason=reason)


def _time_failure(reason: str) -> RangerTrustedTimeVerification:
    return RangerTrustedTimeVerification(valid=False, reason=reason)


def _governed_failure(reason: str) -> RangerGovernedRequestVerification:
    return RangerGovernedRequestVerification(valid=False, reason=reason)
