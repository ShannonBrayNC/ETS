"""Governed authority-acceptance composition for Ranger R0.2.

This module composes the existing authority-history, administrative-approval, and trusted-time
evidence into a stronger verifier profile without changing legacy v1 authority events in place.
The acceptance manifest is not a new independent signature. Its claims are valid only when the
referenced signed authority event, administrator approval, and time attestations all verify.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.ranger.governance import (
    RangerAdministrativeApproval,
    RangerGovernanceSubjectKind,
    RangerTrustedTimeAttestation,
    key_binding_request_digest,
    verify_governed_key_binding_request,
    verify_trusted_time_attestation,
)
from ets.ranger.key_authority import RangerKeyAuthorityEvent, RangerKeyAuthorityLedger


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerGovernedAuthorityError(RuntimeError):
    """Raised when governed authority evidence cannot be composed safely."""


class RangerGovernedAuthorityAcceptance(StrictModel):
    """Derived manifest binding one accepted authority event to governance/time proofs."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.org/schemas/ets/ranger/"
                "governed-authority-acceptance/v1"
            )
        },
    )

    schema_version: Literal["ets.ranger.governed-authority-acceptance.v1"] = (
        "ets.ranger.governed-authority-acceptance.v1"
    )
    authority_sequence: int = Field(ge=1, le=2**63 - 1)
    authority_event_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval_time_attestation_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_event_time_attestation_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    vehicle_id: str = Field(min_length=12, max_length=160)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    event_kind: str = Field(min_length=1, max_length=32)

    authority_id: str = Field(min_length=1, max_length=160)
    authority_signing_key_id: str = Field(min_length=1, max_length=256)
    administrator_id: str = Field(min_length=1, max_length=160)
    administrator_signing_key_id: str = Field(min_length=1, max_length=256)
    time_source_id: str = Field(min_length=1, max_length=160)
    time_signing_key_id: str = Field(min_length=1, max_length=256)

    approval_interval_start_utc: datetime
    approval_interval_end_utc: datetime
    acceptance_interval_start_utc: datetime
    acceptance_interval_end_utc: datetime

    acceptance_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    authority_history_integrity_proven: Literal[True] = True
    authority_acceptance_proven: Literal[True] = True
    authenticated_administration_proven: Literal[True] = True
    trusted_time_proven: Literal[True] = True
    approval_precedes_acceptance_proven: Literal[True] = True

    human_identity_proven: Literal[False] = False
    administrative_independence_proven: Literal[False] = False
    operational_device_authorization_proven: Literal[False] = False
    globally_current_history_proven: Literal[False] = False
    global_clock_correctness_proven: Literal[False] = False
    time_source_independence_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "governed_authority_acceptance_no_global_operational_independence_truth_or_outcome_claim"
    ] = (
        "governed_authority_acceptance_no_global_operational_independence_truth_or_outcome_claim"
    )

    @field_validator(
        "approval_interval_start_utc",
        "approval_interval_end_utc",
        "acceptance_interval_start_utc",
        "acceptance_interval_end_utc",
    )
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("governed authority interval timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_ordered_intervals(self) -> Self:
        if self.approval_interval_start_utc > self.approval_interval_end_utc:
            raise ValueError("approval interval is inverted")
        if self.acceptance_interval_start_utc > self.acceptance_interval_end_utc:
            raise ValueError("acceptance interval is inverted")
        if self.approval_interval_end_utc > self.acceptance_interval_start_utc:
            raise ValueError("approval interval does not provably precede authority acceptance")
        return self


class RangerGovernedAuthorityVerification(StrictModel):
    valid: bool
    authority_sequence: int | None = Field(default=None, ge=1)
    authority_event_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    acceptance_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    authority_history_integrity_proven: bool = False
    authority_acceptance_proven: bool = False
    authenticated_administration_proven: bool = False
    trusted_time_proven: bool = False
    approval_precedes_acceptance_proven: bool = False
    reason: str


def build_governed_authority_acceptance(
    history: Iterable[RangerKeyAuthorityEvent],
    approval: RangerAdministrativeApproval,
    approval_time_attestation: RangerTrustedTimeAttestation,
    authority_event_time_attestation: RangerTrustedTimeAttestation,
    *,
    authority_public_key_hex: str,
    administrator_public_key_hex: str,
    time_public_key_hex: str,
) -> RangerGovernedAuthorityAcceptance:
    """Build a manifest only after the complete governed acceptance evidence verifies."""

    verified = _verify_inputs(
        history,
        approval,
        approval_time_attestation,
        authority_event_time_attestation,
        authority_public_key_hex=authority_public_key_hex,
        administrator_public_key_hex=administrator_public_key_hex,
        time_public_key_hex=time_public_key_hex,
    )
    if isinstance(verified, RangerGovernedAuthorityVerification):
        raise RangerGovernedAuthorityError(verified.reason)

    event, approval_start, approval_end, acceptance_start, acceptance_end = verified
    intent = event.request.intent
    payload = _acceptance_payload(
        authority_sequence=event.authority_sequence,
        authority_event_digest_sha256=event.event_digest_sha256,
        request_digest_sha256=key_binding_request_digest(event.request),
        approval_digest_sha256=approval.approval_digest_sha256,
        approval_time_attestation_digest_sha256=(
            approval_time_attestation.attestation_digest_sha256
        ),
        authority_event_time_attestation_digest_sha256=(
            authority_event_time_attestation.attestation_digest_sha256
        ),
        vehicle_id=intent.vehicle_id,
        tenant_id=intent.tenant_id,
        workspace_id=intent.workspace_id,
        event_kind=intent.event_kind.value,
        authority_id=event.authority_id,
        authority_signing_key_id=event.authority_signing_key_id,
        administrator_id=approval.administrator_id,
        administrator_signing_key_id=approval.administrator_signing_key_id,
        time_source_id=approval_time_attestation.time_source_id,
        time_signing_key_id=approval_time_attestation.time_signing_key_id,
        approval_interval_start_utc=approval_start,
        approval_interval_end_utc=approval_end,
        acceptance_interval_start_utc=acceptance_start,
        acceptance_interval_end_utc=acceptance_end,
    )
    return RangerGovernedAuthorityAcceptance.model_validate(
        {
            **payload,
            "acceptance_digest_sha256": canonical_sha256(
                _json_native_acceptance_payload(payload)
            ),
        }
    )


def verify_governed_authority_acceptance(
    acceptance: RangerGovernedAuthorityAcceptance,
    history: Iterable[RangerKeyAuthorityEvent],
    approval: RangerAdministrativeApproval,
    approval_time_attestation: RangerTrustedTimeAttestation,
    authority_event_time_attestation: RangerTrustedTimeAttestation,
    *,
    authority_public_key_hex: str,
    administrator_public_key_hex: str,
    time_public_key_hex: str,
) -> RangerGovernedAuthorityVerification:
    """Independently verify one governed authority-acceptance manifest and its signed inputs."""

    try:
        validated = RangerGovernedAuthorityAcceptance.model_validate(acceptance.model_dump())
    except (AttributeError, ValidationError):
        return _failure("governed authority acceptance schema validation failed")

    verified = _verify_inputs(
        history,
        approval,
        approval_time_attestation,
        authority_event_time_attestation,
        authority_public_key_hex=authority_public_key_hex,
        administrator_public_key_hex=administrator_public_key_hex,
        time_public_key_hex=time_public_key_hex,
    )
    if isinstance(verified, RangerGovernedAuthorityVerification):
        return verified

    event, approval_start, approval_end, acceptance_start, acceptance_end = verified
    intent = event.request.intent
    expected_payload = _acceptance_payload(
        authority_sequence=event.authority_sequence,
        authority_event_digest_sha256=event.event_digest_sha256,
        request_digest_sha256=key_binding_request_digest(event.request),
        approval_digest_sha256=approval.approval_digest_sha256,
        approval_time_attestation_digest_sha256=(
            approval_time_attestation.attestation_digest_sha256
        ),
        authority_event_time_attestation_digest_sha256=(
            authority_event_time_attestation.attestation_digest_sha256
        ),
        vehicle_id=intent.vehicle_id,
        tenant_id=intent.tenant_id,
        workspace_id=intent.workspace_id,
        event_kind=intent.event_kind.value,
        authority_id=event.authority_id,
        authority_signing_key_id=event.authority_signing_key_id,
        administrator_id=approval.administrator_id,
        administrator_signing_key_id=approval.administrator_signing_key_id,
        time_source_id=approval_time_attestation.time_source_id,
        time_signing_key_id=approval_time_attestation.time_signing_key_id,
        approval_interval_start_utc=approval_start,
        approval_interval_end_utc=approval_end,
        acceptance_interval_start_utc=acceptance_start,
        acceptance_interval_end_utc=acceptance_end,
    )
    expected_digest = canonical_sha256(_json_native_acceptance_payload(expected_payload))
    if validated.model_dump(exclude={"acceptance_digest_sha256"}) != expected_payload:
        return _failure("governed authority acceptance manifest does not match signed inputs")
    if validated.acceptance_digest_sha256 != expected_digest:
        return _failure("governed authority acceptance digest mismatch")

    return RangerGovernedAuthorityVerification(
        valid=True,
        authority_sequence=event.authority_sequence,
        authority_event_digest_sha256=event.event_digest_sha256,
        acceptance_digest_sha256=expected_digest,
        authority_history_integrity_proven=True,
        authority_acceptance_proven=True,
        authenticated_administration_proven=True,
        trusted_time_proven=True,
        approval_precedes_acceptance_proven=True,
        reason=(
            "complete authority history, configured administrator approval, and configured "
            "time-authority evidence verify; approval interval provably precedes the authority "
            "event interval. Fleet authorization, global currentness, clock correctness, "
            "administrative independence, semantic truth, and physical outcome are not proven"
        ),
    )


def _verify_inputs(
    history: Iterable[RangerKeyAuthorityEvent],
    approval: RangerAdministrativeApproval,
    approval_time_attestation: RangerTrustedTimeAttestation,
    authority_event_time_attestation: RangerTrustedTimeAttestation,
    *,
    authority_public_key_hex: str,
    administrator_public_key_hex: str,
    time_public_key_hex: str,
) -> (
    tuple[RangerKeyAuthorityEvent, datetime, datetime, datetime, datetime]
    | RangerGovernedAuthorityVerification
):
    events = list(history)
    history_verification = RangerKeyAuthorityLedger.verify_history(
        events, authority_public_key_hex
    )
    if not history_verification.valid or not events:
        return _failure(f"authority history invalid: {history_verification.reason}")

    event = events[-1]
    governed = verify_governed_key_binding_request(
        event.request,
        approval,
        approval_time_attestation,
        administrator_public_key_hex=administrator_public_key_hex,
        time_public_key_hex=time_public_key_hex,
    )
    if not governed.valid:
        return _failure(governed.reason)

    event_time = verify_trusted_time_attestation(
        authority_event_time_attestation, time_public_key_hex
    )
    if not event_time.valid:
        return _failure(event_time.reason)
    if (
        authority_event_time_attestation.subject_kind
        != RangerGovernanceSubjectKind.KEY_AUTHORITY_EVENT
    ):
        return _failure("authority-event time attestation has the wrong subject kind")
    if (
        authority_event_time_attestation.subject_digest_sha256
        != event.event_digest_sha256
    ):
        return _failure("authority-event time attestation targets a different event")

    if (
        approval_time_attestation.time_source_id
        != authority_event_time_attestation.time_source_id
        or approval_time_attestation.time_signing_key_id
        != authority_event_time_attestation.time_signing_key_id
        or approval_time_attestation.time_public_key_fingerprint_sha256
        != authority_event_time_attestation.time_public_key_fingerprint_sha256
    ):
        return _failure(
            "approval and authority-event time attestations do not share one configured "
            "time authority"
        )

    approval_start, approval_end = _interval(approval_time_attestation)
    acceptance_start, acceptance_end = _interval(authority_event_time_attestation)
    if approval_end > acceptance_start:
        return _failure(
            "trusted-time intervals overlap or invert; prior administrative approval is not proven"
        )

    return event, approval_start, approval_end, acceptance_start, acceptance_end


def _interval(attestation: RangerTrustedTimeAttestation) -> tuple[datetime, datetime]:
    delta = timedelta(milliseconds=attestation.uncertainty_ms)
    return attestation.observed_at_utc - delta, attestation.observed_at_utc + delta


def _acceptance_payload(
    *,
    authority_sequence: int,
    authority_event_digest_sha256: str,
    request_digest_sha256: str,
    approval_digest_sha256: str,
    approval_time_attestation_digest_sha256: str,
    authority_event_time_attestation_digest_sha256: str,
    vehicle_id: str,
    tenant_id: str,
    workspace_id: str,
    event_kind: str,
    authority_id: str,
    authority_signing_key_id: str,
    administrator_id: str,
    administrator_signing_key_id: str,
    time_source_id: str,
    time_signing_key_id: str,
    approval_interval_start_utc: datetime,
    approval_interval_end_utc: datetime,
    acceptance_interval_start_utc: datetime,
    acceptance_interval_end_utc: datetime,
) -> dict[str, object]:
    return {
        "schema_version": "ets.ranger.governed-authority-acceptance.v1",
        "authority_sequence": authority_sequence,
        "authority_event_digest_sha256": authority_event_digest_sha256,
        "request_digest_sha256": request_digest_sha256,
        "approval_digest_sha256": approval_digest_sha256,
        "approval_time_attestation_digest_sha256": approval_time_attestation_digest_sha256,
        "authority_event_time_attestation_digest_sha256": (
            authority_event_time_attestation_digest_sha256
        ),
        "vehicle_id": vehicle_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "event_kind": event_kind,
        "authority_id": authority_id,
        "authority_signing_key_id": authority_signing_key_id,
        "administrator_id": administrator_id,
        "administrator_signing_key_id": administrator_signing_key_id,
        "time_source_id": time_source_id,
        "time_signing_key_id": time_signing_key_id,
        "approval_interval_start_utc": approval_interval_start_utc,
        "approval_interval_end_utc": approval_interval_end_utc,
        "acceptance_interval_start_utc": acceptance_interval_start_utc,
        "acceptance_interval_end_utc": acceptance_interval_end_utc,
        "authority_history_integrity_proven": True,
        "authority_acceptance_proven": True,
        "authenticated_administration_proven": True,
        "trusted_time_proven": True,
        "approval_precedes_acceptance_proven": True,
        "human_identity_proven": False,
        "administrative_independence_proven": False,
        "operational_device_authorization_proven": False,
        "globally_current_history_proven": False,
        "global_clock_correctness_proven": False,
        "time_source_independence_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "governed_authority_acceptance_no_global_operational_independence_truth_or_"
            "outcome_claim"
        ),
    }


def _json_native_acceptance_payload(payload: dict[str, object]) -> dict[str, object]:
    candidate = RangerGovernedAuthorityAcceptance.model_validate(
        {**payload, "acceptance_digest_sha256": "0" * 64}
    )
    return candidate.model_dump(mode="json", exclude={"acceptance_digest_sha256"})


def _failure(reason: str) -> RangerGovernedAuthorityVerification:
    return RangerGovernedAuthorityVerification(valid=False, reason=reason)
