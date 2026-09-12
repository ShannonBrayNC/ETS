"""Adapt captive electromagnetic actuation trials into ETS Evidence Object v1.

The complete trial remains authoritative under a namespaced extension. Generic Core
claims are emitted only for KNOWN measurements, preserving epistemic state without
promoting UNKNOWN/CONTRADICTED/NOT_AVAILABLE observations into affirmative claims.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ets.evidence_object.models import (
    Claim,
    EvidenceContext,
    EvidenceIdentity,
    EvidenceObject,
    IntegrityBinding,
    Provenance,
    Relationship,
    RelationshipType,
)
from ets.ranger.electromagnetic_actuation import trial_digest

_SCHEMA = "ranger.electromagnetic-actuation-trial.v0.1"
_EXTENSION = "org.lanternprotocol.ranger.electromagnetic-actuation-trial.v0.1"
_INTEGRITY_PROFILE = "ets.ranger.electromagnetic-actuation-trial.sha256.v0.1"


class ElectromagneticActuationEvidenceAdapterError(ValueError):
    """Raised when a captive actuation trial cannot be projected safely."""


def electromagnetic_actuation_trial_to_evidence_object(
    trial: Mapping[str, Any],
) -> EvidenceObject:
    payload = dict(trial)
    if payload.get("schema_version") != _SCHEMA:
        raise ElectromagneticActuationEvidenceAdapterError(
            f"schema_version must be {_SCHEMA}"
        )

    digest = payload.get("trial_digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise ElectromagneticActuationEvidenceAdapterError("sealed trial_digest is required")
    if trial_digest(payload) != digest:
        raise ElectromagneticActuationEvidenceAdapterError("trial digest mismatch")

    trial_id = _required_string(payload, "trial_id")
    apparatus_id = _required_string(payload, "apparatus_id")
    occurred_at = _required_datetime(payload, "occurred_at")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ElectromagneticActuationEvidenceAdapterError("authority must be an object")
    policy_id = _required_string(authority, "policy_id")

    claims: list[Claim] = []
    relationships: list[Relationship] = []
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise ElectromagneticActuationEvidenceAdapterError("observations must be an array")

    for item in observations:
        if not isinstance(item, Mapping):
            raise ElectromagneticActuationEvidenceAdapterError("observation must be an object")
        observation_id = _required_string(item, "observation_id")
        kind = _required_string(item, "kind")
        source_id = _required_string(item, "source_id")
        measurement = item.get("measurement")
        if not isinstance(measurement, Mapping):
            raise ElectromagneticActuationEvidenceAdapterError("measurement must be an object")
        state = measurement.get("state")
        if state == "KNOWN":
            claims.append(
                Claim(
                    claim_id=observation_id,
                    subject=apparatus_id,
                    predicate=f"actuation.{kind.lower()}",
                    value={
                        "value": measurement.get("value"),
                        "unit": measurement.get("unit"),
                        "uncertainty": measurement.get("uncertainty"),
                    },
                    confidence=None,
                    source_ref=source_id,
                )
            )
        ancestry = item.get("source_ancestry", [])
        if isinstance(ancestry, list):
            for source_ref in ancestry:
                if isinstance(source_ref, str) and source_ref:
                    relationships.append(
                        Relationship(
                            relationship_id=f"rel:{observation_id}:depends_on:{source_ref}",
                            relationship_type=RelationshipType.DEPENDS_ON,
                            target_evidence_ref=source_ref,
                            observed=True,
                            confidence=None,
                        )
                    )

    evidence_refs = payload.get("evidence")
    if not isinstance(evidence_refs, list):
        raise ElectromagneticActuationEvidenceAdapterError("evidence must be an array")
    for item in evidence_refs:
        if not isinstance(item, Mapping):
            raise ElectromagneticActuationEvidenceAdapterError("evidence entry must be an object")
        evidence_id = _required_string(item, "evidence_id")
        relationships.append(
            Relationship(
                relationship_id=f"rel:{trial_id}:raw-evidence:{evidence_id}",
                relationship_type=RelationshipType.DEPENDS_ON,
                target_evidence_ref=evidence_id,
                observed=True,
                confidence=None,
            )
        )

    command = payload.get("command")
    result = payload.get("result")
    if not isinstance(command, Mapping) or not isinstance(result, Mapping):
        raise ElectromagneticActuationEvidenceAdapterError("command/result must be objects")

    contexts = (
        EvidenceContext(
            context_type="ranger-captive-actuation",
            context_ref=trial_id,
            attributes={
                "apparatus_id": apparatus_id,
                "authorization_state": authority.get("authorization_state"),
                "command_state": command.get("command_state"),
                "safe_to_actuate": payload.get("safety_state", {}).get("safe_to_actuate")
                if isinstance(payload.get("safety_state"), Mapping)
                else None,
            },
        ),
        EvidenceContext(
            context_type="ranger-captive-actuation-result",
            context_ref=trial_id,
            attributes={
                "electrical_response": result.get("electrical_response"),
                "mechanical_response": result.get("mechanical_response"),
                "thermal_response": result.get("thermal_response"),
                "final_safe_state": result.get("final_safe_state"),
            },
        ),
    )

    return EvidenceObject(
        identity=EvidenceIdentity(
            evidence_id=trial_id,
            version=1,
            namespace="urn:lantern:ranger:captive-actuation",
            evidence_type="electromagnetic-actuation-trial",
        ),
        created_at=occurred_at,
        claims=tuple(claims),
        provenance=Provenance(
            collected_by=apparatus_id,
            source_system="ets-ranger",
            device_ref=apparatus_id,
            workflow_ref=trial_id,
        ),
        contexts=contexts,
        relationships=tuple(relationships),
        integrity=(
            IntegrityBinding(
                digest=digest.removeprefix("sha256:"),
                scope="electromagnetic-actuation-trial-preimage",
                profile=_INTEGRITY_PROFILE,
            ),
        ),
        policy_refs=(policy_id,),
        extensions={
            _EXTENSION: {
                "included_in_object_hash": True,
                "trial": payload,
            }
        },
    )


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise ElectromagneticActuationEvidenceAdapterError(f"{field} must be non-empty")
    return result


def _required_datetime(value: Mapping[str, Any], field: str) -> datetime:
    raw = _required_string(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ElectromagneticActuationEvidenceAdapterError(
            f"{field} must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ElectromagneticActuationEvidenceAdapterError(
            f"{field} must be timezone-aware"
        )
    return parsed


__all__ = [
    "ElectromagneticActuationEvidenceAdapterError",
    "electromagnetic_actuation_trial_to_evidence_object",
]
