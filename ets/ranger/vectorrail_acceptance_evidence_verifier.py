"""Reverse verification for VectorRail/VRX acceptance Evidence Objects."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

from ets.evidence_object.canonical import object_hash
from ets.evidence_object.models import EvidenceObject
from ets.ranger.vectorrail_acceptance import verify_vectorrail_acceptance
from ets.ranger.vectorrail_acceptance_evidence import vectorrail_acceptance_digest

_EXTENSION = "org.lanternprotocol.ranger.vectorrail-vrx-acceptance.v0.1"
_INTEGRITY_SCOPE = "vectorrail-vrx-acceptance-record"
_INTEGRITY_PROFILE = "ets.vectorrail.acceptance-record.sha256.v0.1"


class VectorRailAcceptanceEvidenceVerificationError(ValueError):
    """Raised when an Evidence Object cannot be interpreted as VRX acceptance evidence."""


class VectorRailAcceptanceEvidenceVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    acceptance_record_present: bool
    acceptance_record_semantically_valid: bool
    acceptance_record_digest_valid: bool
    acceptance_integrity_binding_valid: bool
    configuration_binding_valid: bool
    evidence_package_binding_valid: bool | None
    qualification: str
    final_safe_state: str
    verifier_status: str
    acceptance_id: str
    vrx_device_id: str
    reviewer_id: str
    supporting_relationship_count: int
    outer_object_hash: str
    outer_object_hash_valid: bool | None
    truth_claim_supported: bool = False
    truth_claim_boundary: str = (
        "qualification_integrity_and_semantic_consistency_do_not_prove_physical_truth_"
        "beyond_the_recorded_observability_boundary"
    )


def verify_vectorrail_acceptance_evidence_object(
    evidence: EvidenceObject,
    *,
    expected_object_hash: str | None = None,
) -> VectorRailAcceptanceEvidenceVerification:
    """Verify the embedded acceptance record and the outer Evidence Object envelope."""

    extension = evidence.extensions.get(_EXTENSION)
    if not isinstance(extension, Mapping):
        raise VectorRailAcceptanceEvidenceVerificationError("VRX acceptance extension is missing")
    record = extension.get("acceptance_record")
    if not isinstance(record, Mapping):
        raise VectorRailAcceptanceEvidenceVerificationError(
            "acceptance_record extension is invalid"
        )

    try:
        semantic_valid = verify_vectorrail_acceptance(record)
    except ValueError:
        semantic_valid = False

    computed_digest = vectorrail_acceptance_digest(record)
    stored_digest = extension.get("acceptance_record_digest")
    digest_valid = isinstance(stored_digest, str) and stored_digest == computed_digest

    acceptance_binding = next(
        (
            item
            for item in evidence.integrity
            if item.scope == _INTEGRITY_SCOPE and item.profile == _INTEGRITY_PROFILE
        ),
        None,
    )
    acceptance_binding_valid = bool(
        acceptance_binding is not None
        and digest_valid
        and acceptance_binding.digest == computed_digest.removeprefix("sha256:")
    )

    configuration_digest = record.get("configuration_digest")
    configuration_binding = next(
        (item for item in evidence.integrity if item.scope == "vectorrail-vrx-configuration"),
        None,
    )
    configuration_binding_valid = bool(
        configuration_binding is not None
        and isinstance(configuration_digest, str)
        and configuration_digest.startswith("sha256:")
        and configuration_binding.digest == configuration_digest.removeprefix("sha256:")
    )

    verifier = record.get("verifier")
    if not isinstance(verifier, Mapping):
        raise VectorRailAcceptanceEvidenceVerificationError("embedded verifier is invalid")
    evidence_package_digest = verifier.get("evidence_package_digest")
    if evidence_package_digest is None:
        evidence_package_binding_valid = None
    else:
        package_binding = next(
            (
                item
                for item in evidence.integrity
                if item.scope == "vectorrail-vrx-acceptance-evidence-package"
            ),
            None,
        )
        evidence_package_binding_valid = bool(
            package_binding is not None
            and isinstance(evidence_package_digest, str)
            and evidence_package_digest.startswith("sha256:")
            and package_binding.digest == evidence_package_digest.removeprefix("sha256:")
        )

    outer_hash = object_hash(evidence)
    outer_hash_valid = None if expected_object_hash is None else outer_hash == expected_object_hash

    acceptance_id = _required_string(record, "acceptance_id")
    device_id = _required_string(record, "vrx_device_id")
    reviewer_id = _required_string(record, "reviewer_id")
    qualification = _required_string(record, "qualification")
    final_safe_state = _required_string(record, "final_safe_state")
    verifier_status = _required_string(verifier, "status")

    supporting_relationship_count = sum(
        1 for item in evidence.relationships if item.relationship_type.value == "depends_on"
    )

    return VectorRailAcceptanceEvidenceVerification(
        acceptance_record_present=True,
        acceptance_record_semantically_valid=semantic_valid,
        acceptance_record_digest_valid=digest_valid,
        acceptance_integrity_binding_valid=acceptance_binding_valid,
        configuration_binding_valid=configuration_binding_valid,
        evidence_package_binding_valid=evidence_package_binding_valid,
        qualification=qualification,
        final_safe_state=final_safe_state,
        verifier_status=verifier_status,
        acceptance_id=acceptance_id,
        vrx_device_id=device_id,
        reviewer_id=reviewer_id,
        supporting_relationship_count=supporting_relationship_count,
        outer_object_hash=outer_hash,
        outer_object_hash_valid=outer_hash_valid,
    )


def _required_string(value: Mapping[str, object], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise VectorRailAcceptanceEvidenceVerificationError(f"{field} must be non-empty")
    return result


__all__ = [
    "VectorRailAcceptanceEvidenceVerification",
    "VectorRailAcceptanceEvidenceVerificationError",
    "verify_vectorrail_acceptance_evidence_object",
]
