"""Deterministic verification outcomes for untrusted ETS material."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class VerificationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    MALFORMED = "malformed"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class VerificationReason(StrEnum):
    OK = "ok"
    CANONICALIZATION_FAILED = "canonicalization_failed"
    SCHEMA_INVALID = "schema_invalid"
    PROFILE_REQUIRED = "profile_required"
    PROFILE_UNKNOWN = "profile_unknown"
    PROFILE_CONFLICT = "profile_conflict"
    PROFILE_GENERATION_FORBIDDEN = "profile_generation_forbidden"
    DIGEST_MALFORMED = "digest_malformed"
    DIGEST_MISMATCH = "digest_mismatch"
    PROOF_MALFORMED = "proof_malformed"
    PROOF_INVALID = "proof_invalid"
    TREE_SIZE_INVALID = "tree_size_invalid"
    ROOT_MISMATCH = "root_mismatch"
    SIGNATURE_MISSING = "signature_missing"
    SIGNATURE_MALFORMED = "signature_malformed"
    SIGNATURE_INVALID = "signature_invalid"
    SIGNATURE_PROFILE_UNSUPPORTED = "signature_profile_unsupported"
    BUNDLE_LINKAGE_INVALID = "bundle_linkage_invalid"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    INTERNAL_ERROR = "internal_error"


class VerifiedComponent(StrEnum):
    CANONICALIZATION = "canonicalization"
    EVENT = "event"
    DIGEST = "digest"
    INCLUSION_PROOF = "inclusion_proof"
    CONSISTENCY_PROOF = "consistency_proof"
    TREE_HEAD = "tree_head"
    SIGNATURE = "signature"
    BUNDLE = "bundle"
    CERTIFICATE = "certificate"


@dataclass(frozen=True, slots=True)
class VerificationResult:
    status: VerificationStatus
    reason: VerificationReason
    component: VerifiedComponent
    profile_id: str | None = None
    protocol_version: str | None = None
    summary: str = ""
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    @property
    def valid(self) -> bool:
        return self.status is VerificationStatus.VALID

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "reason": self.reason.value,
            "component": self.component.value,
            "profile_id": self.profile_id,
            "protocol_version": self.protocol_version,
            "summary": self.summary,
            "details": dict(sorted(self.details.items())),
        }
