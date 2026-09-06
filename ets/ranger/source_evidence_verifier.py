"""Verify Ranger Decision Event source-evidence references against supplied artifacts.

This module separates reference declaration, artifact availability, and digest validity.
It does not infer semantic truth from a matching digest; it only establishes that the
supplied bytes match the digest recorded by the Ranger Decision Event.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from ets.evidence_object.models import EvidenceObject

_RANGER_EXTENSION_NAMESPACE = "org.lanternprotocol.ranger.decision-event.v0.1"


class RangerSourceEvidenceVerificationError(ValueError):
    """Raised when Ranger source-evidence metadata cannot be interpreted safely."""


class RangerSourceEvidenceFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    evidence_id: str
    evidence_type: str
    source_id: str
    expected_digest: str
    availability_status: str
    digest_status: str
    actual_digest: str | None = None
    uri: str | None = None


class RangerSourceEvidenceVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_id: str
    referenced_count: int
    available_count: int
    verified_count: int
    missing_count: int
    mismatch_count: int
    overall_status: str
    findings: tuple[RangerSourceEvidenceFinding, ...]
    truth_claim_supported: bool = False
    claim_boundary: str = (
        "source_artifact_digest_verification_proves_byte_identity_not_sensor_or_semantic_truth"
    )


def verify_ranger_source_evidence(
    evidence: EvidenceObject,
    *,
    artifacts: Mapping[str, bytes],
) -> RangerSourceEvidenceVerification:
    """Verify referenced Ranger evidence artifacts supplied by ``evidence_id``.

    Each Decision Event evidence reference is checked independently. Missing artifacts
    remain ``MISSING`` rather than being interpreted as nonexistent observations.
    Matching digests establish byte identity only.
    """

    event = _embedded_event(evidence)
    event_id = _required_string(event, "event_id")
    references = event.get("evidence")
    if not isinstance(references, list):
        raise RangerSourceEvidenceVerificationError("embedded evidence must be an array")

    findings: list[RangerSourceEvidenceFinding] = []
    available_count = 0
    verified_count = 0
    missing_count = 0
    mismatch_count = 0

    for item in references:
        if not isinstance(item, Mapping):
            raise RangerSourceEvidenceVerificationError("evidence reference must be an object")
        evidence_id = _required_string(item, "evidence_id")
        evidence_type = _required_string(item, "evidence_type")
        source_id = _required_string(item, "source_id")
        expected = _required_string(item, "digest")
        if not expected.startswith("sha256:") or len(expected) != 71:
            raise RangerSourceEvidenceVerificationError("evidence digest must be sha256:<64 hex>")
        uri = item.get("uri") if isinstance(item.get("uri"), str) else None

        artifact = artifacts.get(evidence_id)
        if artifact is None:
            missing_count += 1
            findings.append(
                RangerSourceEvidenceFinding(
                    evidence_id=evidence_id,
                    evidence_type=evidence_type,
                    source_id=source_id,
                    expected_digest=expected,
                    availability_status="MISSING",
                    digest_status="NOT_VERIFIED",
                    uri=uri,
                )
            )
            continue
        if not isinstance(artifact, bytes):
            raise RangerSourceEvidenceVerificationError(
                f"artifact {evidence_id} must be bytes"
            )

        available_count += 1
        actual = "sha256:" + hashlib.sha256(artifact).hexdigest()
        if actual == expected:
            verified_count += 1
            digest_status = "MATCH"
        else:
            mismatch_count += 1
            digest_status = "MISMATCH"

        findings.append(
            RangerSourceEvidenceFinding(
                evidence_id=evidence_id,
                evidence_type=evidence_type,
                source_id=source_id,
                expected_digest=expected,
                availability_status="AVAILABLE",
                digest_status=digest_status,
                actual_digest=actual,
                uri=uri,
            )
        )

    if mismatch_count:
        overall = "DIGEST_MISMATCH"
    elif missing_count:
        overall = "INCOMPLETE"
    elif findings and verified_count == len(findings):
        overall = "VERIFIED"
    else:
        overall = "INDETERMINATE"

    return RangerSourceEvidenceVerification(
        event_id=event_id,
        referenced_count=len(findings),
        available_count=available_count,
        verified_count=verified_count,
        missing_count=missing_count,
        mismatch_count=mismatch_count,
        overall_status=overall,
        findings=tuple(findings),
    )


def _embedded_event(evidence: EvidenceObject) -> Mapping[str, Any]:
    extension = evidence.extensions.get(_RANGER_EXTENSION_NAMESPACE)
    if not isinstance(extension, Mapping):
        raise RangerSourceEvidenceVerificationError("Ranger decision-event extension is missing")
    event = extension.get("decision_event")
    if not isinstance(event, Mapping):
        raise RangerSourceEvidenceVerificationError("Ranger decision_event extension is invalid")
    return event


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise RangerSourceEvidenceVerificationError(f"{field} must be a non-empty string")
    return result


__all__ = [
    "RangerSourceEvidenceFinding",
    "RangerSourceEvidenceVerification",
    "RangerSourceEvidenceVerificationError",
    "verify_ranger_source_evidence",
]
