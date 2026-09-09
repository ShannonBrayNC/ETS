"""Trusted-time composition for Ranger retained verification receipts.

This additive R0.2 profile verifies an existing registry-signed retained receipt and then requires
configured trusted-time evidence over that exact receipt digest. It does not change the legacy
retained-head or authority-bound checkpoint schemas, and it deliberately does not upgrade a local
``received_at_utc`` value into trusted time.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ets.ranger.authority_checkpoint import (
    RangerAuthorityBoundCheckpoint,
    RangerAuthorityCheckpointRegistry,
)
from ets.ranger.authority_head import (
    RangerAuthorityHeadRegistry,
    RangerRetainedAuthorityHead,
)
from ets.ranger.governance import (
    RangerGovernanceSubjectKind,
    RangerTrustedTimeAttestation,
    verify_retained_receipt_time,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerTimeAttestedReceiptVerification(StrictModel):
    """Verification result for one retained receipt plus configured trusted-time evidence."""

    valid: bool
    receipt_kind: RangerGovernanceSubjectKind | None = None
    receipt_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    registry_sequence: int | None = Field(default=None, ge=1)
    receipt_received_at_utc: datetime | None = None
    time_attestation_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    attested_interval_start_utc: datetime | None = None
    attested_interval_end_utc: datetime | None = None
    registry_id: str | None = None
    registry_signing_key_id: str | None = None
    time_source_id: str | None = None
    time_signing_key_id: str | None = None

    receipt_chain_integrity_proven: bool = False
    configured_registry_identity_proven: bool = False
    registry_relative_freshness_proven: bool = False
    authority_bindings_verified: bool = False
    trusted_time_proven: bool = False
    configured_time_identity_proven: bool = False

    receipt_local_time_trusted: Literal[False] = False
    independent_external_custody_proven: Literal[False] = False
    globally_current_state_proven: Literal[False] = False
    global_clock_correctness_proven: Literal[False] = False
    time_source_independence_proven: Literal[False] = False
    operational_device_authorization_proven: Literal[False] = False
    complete_capture_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


def verify_time_attested_authority_head(
    checkpoints: Iterable[RangerRetainedAuthorityHead],
    time_attestation: RangerTrustedTimeAttestation,
    *,
    registry_public_key_hex: str,
    expected_registry_id: str,
    expected_registry_signing_key_id: str,
    time_public_key_hex: str,
    expected_time_source_id: str,
    expected_time_signing_key_id: str,
) -> RangerTimeAttestedReceiptVerification:
    """Verify the latest presented retained authority head and trusted-time evidence for it."""

    chain = list(checkpoints)
    if not chain:
        return _failure("retained authority-head chain is empty")

    chain_verification = RangerAuthorityHeadRegistry.verify_checkpoint_chain(
        chain, registry_public_key_hex
    )
    if not chain_verification.valid:
        return _failure(
            f"retained authority-head chain is invalid: {chain_verification.reason}"
        )

    receipt = chain[-1]
    if (
        chain_verification.checkpoint_count != len(chain)
        or chain_verification.latest_checkpoint_digest_sha256
        != receipt.checkpoint_digest_sha256
        or chain_verification.latest_authority_event_count != receipt.authority_event_count
        or chain_verification.latest_authority_history_head_digest_sha256
        != receipt.authority_history_head_digest_sha256
    ):
        return _failure("authority-head chain verification does not terminate at supplied receipt")

    if (
        receipt.registry_id != expected_registry_id
        or receipt.registry_signing_key_id != expected_registry_signing_key_id
    ):
        return _failure("retained authority-head registry identity does not match configuration")

    time_verification = verify_retained_receipt_time(
        subject_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
        time_attestation=time_attestation,
        time_public_key_hex=time_public_key_hex,
    )
    if not time_verification.valid:
        return _failure(time_verification.reason)
    if (
        time_attestation.time_source_id != expected_time_source_id
        or time_attestation.time_signing_key_id != expected_time_signing_key_id
    ):
        return _failure("trusted-time authority identity does not match configuration")

    interval_start, interval_end = _attested_interval(time_attestation)
    return RangerTimeAttestedReceiptVerification(
        valid=True,
        receipt_kind=RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
        receipt_digest_sha256=receipt.checkpoint_digest_sha256,
        registry_sequence=receipt.registry_sequence,
        receipt_received_at_utc=receipt.received_at_utc,
        time_attestation_digest_sha256=time_attestation.attestation_digest_sha256,
        attested_interval_start_utc=interval_start,
        attested_interval_end_utc=interval_end,
        registry_id=receipt.registry_id,
        registry_signing_key_id=receipt.registry_signing_key_id,
        time_source_id=time_attestation.time_source_id,
        time_signing_key_id=time_attestation.time_signing_key_id,
        receipt_chain_integrity_proven=True,
        configured_registry_identity_proven=True,
        registry_relative_freshness_proven=(
            chain_verification.freshness_relative_to_retained_state
        ),
        trusted_time_proven=True,
        configured_time_identity_proven=True,
        reason=(
            "the complete presented retained authority-head chain verifies and the configured "
            "time-authority key attests to the exact registry-signed receipt digest; the receipt's "
            "local received_at_utc value, global currentness, and external custody remain unproven"
        ),
    )


def verify_time_attested_authority_checkpoint(
    checkpoints: Iterable[RangerAuthorityBoundCheckpoint],
    time_attestation: RangerTrustedTimeAttestation,
    *,
    registry_public_key_hex: str,
    expected_registry_id: str,
    expected_registry_signing_key_id: str,
    time_public_key_hex: str,
    expected_time_source_id: str,
    expected_time_signing_key_id: str,
) -> RangerTimeAttestedReceiptVerification:
    """Verify the latest authority-bound custody receipt and trusted-time evidence for it."""

    chain = list(checkpoints)
    if not chain:
        return _failure("authority-bound retained-checkpoint chain is empty")

    chain_verification = RangerAuthorityCheckpointRegistry.verify_checkpoint_chain(
        chain, registry_public_key_hex
    )
    if not chain_verification.valid:
        return _failure(
            "authority-bound retained-checkpoint chain is invalid: "
            f"{chain_verification.reason}"
        )

    receipt = chain[-1]
    if (
        chain_verification.checkpoint_count != len(chain)
        or chain_verification.latest_checkpoint_digest_sha256
        != receipt.checkpoint_digest_sha256
        or chain_verification.latest_boot_sequence != receipt.boot_sequence
        or chain_verification.latest_authority_history_head_digest_sha256
        != receipt.authority_history_head_digest_sha256
        or not chain_verification.authority_bindings_verified
    ):
        return _failure(
            "authority-bound chain verification does not terminate at supplied receipt"
        )

    if (
        receipt.registry_id != expected_registry_id
        or receipt.registry_signing_key_id != expected_registry_signing_key_id
    ):
        return _failure("authority-bound receipt registry identity does not match configuration")

    time_verification = verify_retained_receipt_time(
        subject_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        subject_digest_sha256=receipt.checkpoint_digest_sha256,
        time_attestation=time_attestation,
        time_public_key_hex=time_public_key_hex,
    )
    if not time_verification.valid:
        return _failure(time_verification.reason)
    if (
        time_attestation.time_source_id != expected_time_source_id
        or time_attestation.time_signing_key_id != expected_time_signing_key_id
    ):
        return _failure("trusted-time authority identity does not match configuration")

    interval_start, interval_end = _attested_interval(time_attestation)
    return RangerTimeAttestedReceiptVerification(
        valid=True,
        receipt_kind=RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
        receipt_digest_sha256=receipt.checkpoint_digest_sha256,
        registry_sequence=receipt.registry_sequence,
        receipt_received_at_utc=receipt.received_at_utc,
        time_attestation_digest_sha256=time_attestation.attestation_digest_sha256,
        attested_interval_start_utc=interval_start,
        attested_interval_end_utc=interval_end,
        registry_id=receipt.registry_id,
        registry_signing_key_id=receipt.registry_signing_key_id,
        time_source_id=time_attestation.time_source_id,
        time_signing_key_id=time_attestation.time_signing_key_id,
        receipt_chain_integrity_proven=True,
        configured_registry_identity_proven=True,
        registry_relative_freshness_proven=(
            chain_verification.freshness_relative_to_retained_state
        ),
        authority_bindings_verified=True,
        trusted_time_proven=True,
        configured_time_identity_proven=True,
        reason=(
            "the complete presented authority-bound custody receipt chain verifies, including its "
            "retained authority binding, and the configured time-authority key attests to the exact "
            "registry-signed receipt digest; local receipt time, global currentness, complete "
            "capture, and physical outcome remain unproven"
        ),
    )


def _attested_interval(
    attestation: RangerTrustedTimeAttestation,
) -> tuple[datetime, datetime]:
    uncertainty = timedelta(milliseconds=attestation.uncertainty_ms)
    return (
        attestation.observed_at_utc - uncertainty,
        attestation.observed_at_utc + uncertainty,
    )


def _failure(reason: str) -> RangerTimeAttestedReceiptVerification:
    return RangerTimeAttestedReceiptVerification(valid=False, reason=reason)
