"""Sanitized hosted validation evidence records for ETS deployments."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApprovalState = Literal["Approval Required", "Approved", "Rejected", "Superseded"]
TrustLabel = Literal["Requires Human Review", "Approved", "Rejected", "Superseded"]


class HostedValidationEvidence(BaseModel):
    """Sanitized evidence summary for hosted Azure validation runs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    created_at_utc: datetime
    trust_label: TrustLabel
    approval_state: ApprovalState
    trace_id: str = Field(min_length=1)
    managed_identity_label: str = Field(min_length=1)
    key_id_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    rbac_roles_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    signer_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_role: str = Field(min_length=1)
    notes: tuple[str, ...] = ()


def build_hosted_validation_evidence(
    *,
    evidence_id: str,
    run_id: str,
    managed_identity_label: str,
    key_id: str,
    rbac_roles: list[str],
    signer_result: str,
    reviewer_role: str,
    trace_id: str,
    approval_state: ApprovalState = "Approval Required",
    trust_label: TrustLabel = "Requires Human Review",
    notes: tuple[str, ...] = (),
) -> HostedValidationEvidence:
    """Create a sanitized hosted validation evidence record without raw secrets."""

    return HostedValidationEvidence(
        evidence_id=evidence_id,
        run_id=run_id,
        created_at_utc=datetime.now(UTC),
        trust_label=trust_label,
        approval_state=approval_state,
        trace_id=trace_id,
        managed_identity_label=managed_identity_label,
        key_id_hash=_sha256_text(key_id),
        rbac_roles_hash=_sha256_text("\n".join(sorted(rbac_roles))),
        signer_result_hash=_sha256_text(signer_result),
        reviewer_role=reviewer_role,
        notes=notes,
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
