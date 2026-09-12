"""Project VectorRail/VRX laboratory acceptance records into ETS Evidence Object v1.

The source acceptance record remains authoritative under a namespaced extension.
The adapter first verifies the machine-verifiable acceptance semantics, then binds the
complete acceptance record with a deterministic digest and expresses provenance,
configuration identity, supporting evidence references, dry-run trial references, and
the independent acceptance-verifier result in the broader Evidence Architecture model.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime
from typing import Any

from ets.core.canonical_json import canonicalize
from ets.evidence_object.models import (
    Assertion,
    Claim,
    EvidenceContext,
    EvidenceIdentity,
    EvidenceObject,
    IntegrityBinding,
    Provenance,
    Relationship,
    RelationshipType,
    VerificationRecord,
    VerificationResult,
)
from ets.ranger.vectorrail_acceptance import verify_vectorrail_acceptance

_SCHEMA = "ranger.vectorrail-vrx-acceptance.v0.1"
_EXTENSION = "org.lanternprotocol.ranger.vectorrail-vrx-acceptance.v0.1"
_INTEGRITY_SCOPE = "vectorrail-vrx-acceptance-record"
_INTEGRITY_PROFILE = "ets.vectorrail.acceptance-record.sha256.v0.1"


class VectorRailAcceptanceEvidenceError(ValueError):
    """Raised when a VRX acceptance record cannot be projected safely."""


def vectorrail_acceptance_digest(record: Mapping[str, Any]) -> str:
    """Return the deterministic SHA-256 digest of the complete acceptance record."""

    payload = deepcopy(dict(record))
    if payload.get("schema_version") != _SCHEMA:
        raise VectorRailAcceptanceEvidenceError(f"schema_version must be {_SCHEMA}")
    return f"sha256:{hashlib.sha256(canonicalize(payload)).hexdigest()}"


def vectorrail_acceptance_to_evidence_object(record: Mapping[str, Any]) -> EvidenceObject:
    """Convert one semantically valid VRX acceptance record to Evidence Object v1."""

    payload = deepcopy(dict(record))
    try:
        verify_vectorrail_acceptance(payload)
    except ValueError as exc:
        raise VectorRailAcceptanceEvidenceError(str(exc)) from exc

    acceptance_id = _required_string(payload, "acceptance_id")
    device_id = _required_string(payload, "vrx_device_id")
    reviewer_id = _required_string(payload, "reviewer_id")
    reviewed_at = _required_datetime(payload, "reviewed_at")
    configuration_digest = _required_string(payload, "configuration_digest")
    qualification = _required_string(payload, "qualification")
    final_safe_state = _required_string(payload, "final_safe_state")

    verifier = payload.get("verifier")
    if not isinstance(verifier, Mapping):
        raise VectorRailAcceptanceEvidenceError("verifier must be an object")
    verifier_profile = _required_string(verifier, "profile")
    verifier_status = _required_string(verifier, "status")
    evidence_package_digest = verifier.get("evidence_package_digest")

    source_digest = vectorrail_acceptance_digest(payload)

    claims: list[Claim] = [
        Claim(
            claim_id=f"{acceptance_id}:qualification",
            subject=device_id,
            predicate="vectorrail.qualification",
            value=qualification,
            source_ref=acceptance_id,
        ),
        Claim(
            claim_id=f"{acceptance_id}:final-safe-state",
            subject=device_id,
            predicate="vectorrail.final_safe_state",
            value=final_safe_state,
            source_ref=acceptance_id,
        ),
        Claim(
            claim_id=f"{acceptance_id}:configuration",
            subject=device_id,
            predicate="vectorrail.configuration_digest",
            value=configuration_digest,
            source_ref=acceptance_id,
        ),
    ]

    relationships: list[Relationship] = []
    for gate in _mapping_sequence(payload.get("gates"), "gates"):
        gate_id = _required_string(gate, "gate_id")
        gate_status = _required_string(gate, "status")
        claims.append(
            Claim(
                claim_id=f"{acceptance_id}:gate:{gate_id}",
                subject=device_id,
                predicate=f"vectorrail.acceptance.{gate_id.lower()}",
                value=gate_status,
                source_ref=acceptance_id,
            )
        )
        for check in _mapping_sequence(gate.get("checks"), f"{gate_id}.checks"):
            check_id = _required_string(check, "check_id")
            evidence_ref = check.get("evidence_ref")
            if isinstance(evidence_ref, str) and evidence_ref:
                relationships.append(
                    Relationship(
                        relationship_id=f"rel:{acceptance_id}:{gate_id}:{check_id}:evidence",
                        relationship_type=RelationshipType.DEPENDS_ON,
                        target_evidence_ref=evidence_ref,
                        observed=True,
                    )
                )

    for dry_run in _mapping_sequence(payload.get("dry_runs"), "dry_runs"):
        scenario = _required_string(dry_run, "scenario")
        status = _required_string(dry_run, "status")
        claims.append(
            Claim(
                claim_id=f"{acceptance_id}:dry-run:{scenario}",
                subject=device_id,
                predicate=f"vectorrail.dry_run.{scenario.lower()}",
                value=status,
                source_ref=acceptance_id,
            )
        )
        trial_ref = dry_run.get("trial_ref")
        if isinstance(trial_ref, str) and trial_ref:
            relationships.append(
                Relationship(
                    relationship_id=f"rel:{acceptance_id}:dry-run:{scenario}",
                    relationship_type=RelationshipType.DEPENDS_ON,
                    target_evidence_ref=trial_ref,
                    observed=True,
                )
            )

    verification_result = (
        VerificationResult.PASS
        if verifier_status == "VERIFIED"
        else VerificationResult.FAIL
        if verifier_status == "FAILED"
        else VerificationResult.INDETERMINATE
    )

    integrity: list[IntegrityBinding] = [
        IntegrityBinding(
            digest=source_digest.removeprefix("sha256:"),
            scope=_INTEGRITY_SCOPE,
            profile=_INTEGRITY_PROFILE,
        ),
        IntegrityBinding(
            digest=configuration_digest.removeprefix("sha256:"),
            scope="vectorrail-vrx-configuration",
            profile="ets.vectorrail.configuration.sha256.v0.1",
        ),
    ]
    if isinstance(evidence_package_digest, str) and evidence_package_digest.startswith("sha256:"):
        integrity.append(
            IntegrityBinding(
                digest=evidence_package_digest.removeprefix("sha256:"),
                scope="vectorrail-vrx-acceptance-evidence-package",
                profile=verifier_profile,
            )
        )

    return EvidenceObject(
        identity=EvidenceIdentity(
            evidence_id=acceptance_id,
            version=1,
            namespace="urn:lantern:ranger:vectorrail:acceptance",
            evidence_type="vectorrail-vrx-laboratory-acceptance",
        ),
        created_at=reviewed_at,
        claims=tuple(claims),
        assertions=(
            Assertion(
                assertion_id=f"{acceptance_id}:reviewer-qualification-assertion",
                claim_id=f"{acceptance_id}:qualification",
                actor_ref=reviewer_id,
                asserted_at=reviewed_at,
                policy_ref=verifier_profile,
            ),
        ),
        provenance=Provenance(
            collected_by=reviewer_id,
            source_system="ets-ranger-vectorrail",
            device_ref=device_id,
            workflow_ref=acceptance_id,
            operator_ref=reviewer_id,
        ),
        contexts=(
            EvidenceContext(
                context_type="vectorrail-vrx-qualification",
                context_ref=acceptance_id,
                attributes={
                    "vrx_device_id": device_id,
                    "configuration_digest": configuration_digest,
                    "qualification": qualification,
                    "final_safe_state": final_safe_state,
                },
            ),
            EvidenceContext(
                context_type="vectorrail-vrx-independent-verification",
                context_ref=acceptance_id,
                attributes={
                    "profile": verifier_profile,
                    "status": verifier_status,
                    "evidence_package_digest": evidence_package_digest,
                },
            ),
        ),
        relationships=tuple(relationships),
        integrity=tuple(integrity),
        verifications=(
            VerificationRecord(
                verification_id=f"{acceptance_id}:acceptance-verifier",
                method=verifier_profile,
                verified_at=reviewed_at,
                result=verification_result,
                policy_ref=verifier_profile,
                details={
                    "qualification": qualification,
                    "final_safe_state": final_safe_state,
                    "reason": verifier.get("reason"),
                },
            ),
        ),
        policy_refs=(verifier_profile,),
        extensions={
            _EXTENSION: {
                "included_in_object_hash": True,
                "acceptance_record_digest": source_digest,
                "acceptance_record": payload,
            }
        },
    )


def _mapping_sequence(value: object, field: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise VectorRailAcceptanceEvidenceError(f"{field} must be an array")
    result: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise VectorRailAcceptanceEvidenceError(f"{field} entries must be objects")
        result.append(item)
    return result


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise VectorRailAcceptanceEvidenceError(f"{field} must be non-empty")
    return result


def _required_datetime(value: Mapping[str, Any], field: str) -> datetime:
    raw = _required_string(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VectorRailAcceptanceEvidenceError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise VectorRailAcceptanceEvidenceError(f"{field} must be timezone-aware")
    return parsed


__all__ = [
    "VectorRailAcceptanceEvidenceError",
    "vectorrail_acceptance_digest",
    "vectorrail_acceptance_to_evidence_object",
]
