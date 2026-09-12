"""End-to-end verifier for VectorRail/VRX consequence custody.

This module composes existing ETS Ranger evidence contracts across the digital-to-physical
boundary. It does not control hardware. It verifies that a sealed captive-actuation trial,
its Evidence Object projection, and a machine-verifiable VRX acceptance record form a
bounded, integrity-preserving chain from authority and command through observed result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from ets.evidence_object.canonical import object_hash
from ets.ranger.electromagnetic_actuation import trial_digest
from ets.ranger.electromagnetic_actuation_evidence_adapter import (
    ElectromagneticActuationEvidenceAdapterError,
    electromagnetic_actuation_trial_to_evidence_object,
)
from ets.ranger.electromagnetic_actuation_verifier import (
    ElectromagneticActuationVerificationError,
    verify_trial_semantics,
)
from ets.ranger.vectorrail_acceptance_evidence import (
    VectorRailAcceptanceEvidenceError,
    vectorrail_acceptance_to_evidence_object,
)
from ets.ranger.vectorrail_acceptance_evidence_verifier import (
    VectorRailAcceptanceEvidenceVerificationError,
    verify_vectorrail_acceptance_evidence_object,
)

_TRIAL_INTEGRITY_SCOPE = "electromagnetic-actuation-trial-preimage"


class VectorRailConsequenceCustodyVerificationError(ValueError):
    """Raised when the end-to-end package is structurally uninterpretable."""


class VectorRailConsequenceCustodyVerification(BaseModel):
    """Independent reconstruction result for one VRX consequence-custody chain."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    conclusion: str
    trial_id: str
    acceptance_id: str
    authority_state: str
    command_state: str
    electrical_response: str
    mechanical_response: str
    thermal_response: str
    final_safe_state: str
    trial_semantics_valid: bool
    trial_digest_valid: bool
    trial_evidence_object_valid: bool
    trial_projection_conservative: bool
    physical_observation_backing_valid: bool
    raw_evidence_refs_bound: bool
    acceptance_links_trial: bool
    acceptance_evidence_object_valid: bool
    acceptance_independent_verifier_valid: bool
    trial_object_hash: str | None
    acceptance_object_hash: str | None
    independent_observation_groups: tuple[str, ...]
    truth_claim_supported: bool = False
    truth_claim_boundary: str = (
        "verified_reconstruction_does_not_prove_sensor_correctness_physical_truth_"
        "or_action_optimality"
    )


def verify_vectorrail_consequence_custody(
    trial: Mapping[str, Any],
    acceptance_record: Mapping[str, Any],
) -> VectorRailConsequenceCustodyVerification:
    """Verify one trial through VRX acceptance and Evidence Object projection.

    Integrity failure dominates semantic interpretation. A successful result means the
    recorded chain is internally consistent and independently reconstructable within the
    stated observability boundary; it does not elevate recorded observations to objective
    physical truth.
    """

    trial_id = _required_string(trial, "trial_id")
    acceptance_id = _required_string(acceptance_record, "acceptance_id")
    authority = _required_mapping(trial, "authority")
    command = _required_mapping(trial, "command")
    result = _required_mapping(trial, "result")
    observations = _mapping_sequence(trial.get("observations"), "observations")

    authority_state = _required_string(authority, "authorization_state")
    command_state = _required_string(command, "command_state")
    electrical_response = _required_string(result, "electrical_response")
    mechanical_response = _required_string(result, "mechanical_response")
    thermal_response = _required_string(result, "thermal_response")
    final_safe_state = _required_string(result, "final_safe_state")

    stored_digest = trial.get("trial_digest")
    computed_digest = trial_digest(trial)
    trial_digest_valid = isinstance(stored_digest, str) and stored_digest == computed_digest

    try:
        trial_semantics_valid = verify_trial_semantics(trial)
    except ElectromagneticActuationVerificationError:
        trial_semantics_valid = False

    trial_evidence_object_valid = False
    trial_projection_conservative = False
    raw_evidence_refs_bound = False
    trial_object_hash: str | None = None

    if trial_digest_valid:
        try:
            trial_evidence = electromagnetic_actuation_trial_to_evidence_object(trial)
            trial_object_hash = object_hash(trial_evidence)
            integrity = {
                item.scope: item.digest for item in trial_evidence.integrity
            }
            trial_evidence_object_valid = (
                integrity.get(_TRIAL_INTEGRITY_SCOPE)
                == computed_digest.removeprefix("sha256:")
            )
            known_ids = {
                _required_string(item, "observation_id")
                for item in observations
                if _measurement_state(item) == "KNOWN"
            }
            claim_ids = {claim.claim_id for claim in trial_evidence.claims}
            trial_projection_conservative = claim_ids == known_ids

            raw_refs = {
                _required_string(item, "evidence_id")
                for item in _mapping_sequence(trial.get("evidence"), "evidence")
            }
            relationship_targets = {
                relationship.target_evidence_ref
                for relationship in trial_evidence.relationships
            }
            raw_evidence_refs_bound = raw_refs <= relationship_targets
        except ElectromagneticActuationEvidenceAdapterError:
            trial_evidence_object_valid = False

    independent_groups = tuple(
        sorted(
            {
                group
                for item in observations
                if _measurement_state(item) == "KNOWN"
                for group in [_optional_string(item.get("independence_group"))]
                if group is not None
            }
        )
    )
    physical_observation_backing_valid = _physical_observation_backing_valid(
        observations,
        electrical_response=electrical_response,
        mechanical_response=mechanical_response,
        thermal_response=thermal_response,
    )

    acceptance_links_trial = False
    acceptance_evidence_object_valid = False
    acceptance_independent_verifier_valid = False
    acceptance_object_hash: str | None = None

    try:
        acceptance_evidence = vectorrail_acceptance_to_evidence_object(acceptance_record)
        acceptance_object_hash = object_hash(acceptance_evidence)
        relationship_targets = {
            relationship.target_evidence_ref
            for relationship in acceptance_evidence.relationships
        }
        acceptance_links_trial = trial_id in relationship_targets
        acceptance_verification = verify_vectorrail_acceptance_evidence_object(
            acceptance_evidence,
            expected_object_hash=acceptance_object_hash,
        )
        acceptance_evidence_object_valid = all(
            (
                acceptance_verification.acceptance_record_semantically_valid,
                acceptance_verification.acceptance_record_digest_valid,
                acceptance_verification.acceptance_integrity_binding_valid,
                acceptance_verification.configuration_binding_valid,
                acceptance_verification.outer_object_hash_valid is True,
            )
        )
        package_binding = acceptance_verification.evidence_package_binding_valid
        acceptance_independent_verifier_valid = all(
            (
                acceptance_evidence_object_valid,
                package_binding is not False,
                acceptance_verification.qualification == "QUALIFIED",
                acceptance_verification.final_safe_state == "CONFIRMED",
                acceptance_verification.verifier_status == "VERIFIED",
            )
        )
    except (
        VectorRailAcceptanceEvidenceError,
        VectorRailAcceptanceEvidenceVerificationError,
    ):
        acceptance_evidence_object_valid = False

    conclusion = _conclusion(
        trial_digest_valid=trial_digest_valid,
        trial_semantics_valid=trial_semantics_valid,
        trial_evidence_object_valid=trial_evidence_object_valid,
        trial_projection_conservative=trial_projection_conservative,
        raw_evidence_refs_bound=raw_evidence_refs_bound,
        physical_observation_backing_valid=physical_observation_backing_valid,
        acceptance_links_trial=acceptance_links_trial,
        acceptance_evidence_object_valid=acceptance_evidence_object_valid,
        acceptance_independent_verifier_valid=acceptance_independent_verifier_valid,
        observations=observations,
        command_state=command_state,
        electrical_response=electrical_response,
        mechanical_response=mechanical_response,
        thermal_response=thermal_response,
        final_safe_state=final_safe_state,
    )

    return VectorRailConsequenceCustodyVerification(
        conclusion=conclusion,
        trial_id=trial_id,
        acceptance_id=acceptance_id,
        authority_state=authority_state,
        command_state=command_state,
        electrical_response=electrical_response,
        mechanical_response=mechanical_response,
        thermal_response=thermal_response,
        final_safe_state=final_safe_state,
        trial_semantics_valid=trial_semantics_valid,
        trial_digest_valid=trial_digest_valid,
        trial_evidence_object_valid=trial_evidence_object_valid,
        trial_projection_conservative=trial_projection_conservative,
        physical_observation_backing_valid=physical_observation_backing_valid,
        raw_evidence_refs_bound=raw_evidence_refs_bound,
        acceptance_links_trial=acceptance_links_trial,
        acceptance_evidence_object_valid=acceptance_evidence_object_valid,
        acceptance_independent_verifier_valid=acceptance_independent_verifier_valid,
        trial_object_hash=trial_object_hash,
        acceptance_object_hash=acceptance_object_hash,
        independent_observation_groups=independent_groups,
    )


def _conclusion(
    *,
    trial_digest_valid: bool,
    trial_semantics_valid: bool,
    trial_evidence_object_valid: bool,
    trial_projection_conservative: bool,
    raw_evidence_refs_bound: bool,
    physical_observation_backing_valid: bool,
    acceptance_links_trial: bool,
    acceptance_evidence_object_valid: bool,
    acceptance_independent_verifier_valid: bool,
    observations: Sequence[Mapping[str, Any]],
    command_state: str,
    electrical_response: str,
    mechanical_response: str,
    thermal_response: str,
    final_safe_state: str,
) -> str:
    if not trial_digest_valid:
        return "INTEGRITY_FAILURE"
    if not trial_semantics_valid or not physical_observation_backing_valid:
        return "SEMANTIC_INCONSISTENCY"
    if not trial_evidence_object_valid or not trial_projection_conservative:
        return "EVIDENCE_OBJECT_FAILURE"
    if not raw_evidence_refs_bound:
        return "EVIDENCE_BINDING_FAILURE"
    if (
        not acceptance_links_trial
        or not acceptance_evidence_object_valid
        or not acceptance_independent_verifier_valid
    ):
        return "ACCEPTANCE_CHAIN_FAILURE"

    states = {_measurement_state(item) for item in observations}
    if "CONTRADICTED" in states:
        return "INDETERMINATE_PHYSICAL_CONSEQUENCE"
    if command_state == "REJECTED":
        return "VERIFIED_FAIL_CLOSED"
    if mechanical_response == "BLOCKED":
        return "VERIFIED_BLOCKED_CONSEQUENCE"
    if states & {"NOT_AVAILABLE", "UNKNOWN", "INDETERMINATE"}:
        return "VERIFIED_WITH_OBSERVABILITY_LIMIT"
    if "UNKNOWN" in {
        electrical_response,
        mechanical_response,
        thermal_response,
        final_safe_state,
    }:
        return "VERIFIED_WITH_OBSERVABILITY_LIMIT"
    if (
        command_state == "ISSUED"
        and electrical_response == "OBSERVED"
        and mechanical_response == "OBSERVED"
        and thermal_response == "OBSERVED"
        and final_safe_state == "CONFIRMED"
    ):
        return "VERIFIED_CONSISTENT"
    return "VERIFIED_BOUNDED_RECONSTRUCTION"


def _physical_observation_backing_valid(
    observations: Sequence[Mapping[str, Any]],
    *,
    electrical_response: str,
    mechanical_response: str,
    thermal_response: str,
) -> bool:
    known_kinds = {
        _required_string(item, "kind")
        for item in observations
        if _measurement_state(item) == "KNOWN"
    }
    if electrical_response == "OBSERVED" and "ACTUATION_CURRENT" not in known_kinds:
        return False
    if mechanical_response in {"OBSERVED", "BLOCKED"}:
        if "ARMATURE_POSITION" not in known_kinds:
            return False
    if thermal_response == "OBSERVED" and "TEMPERATURE" not in known_kinds:
        return False
    return True


def _measurement_state(observation: Mapping[str, Any]) -> str:
    measurement = _required_mapping(observation, "measurement")
    return _required_string(measurement, "state")


def _required_mapping(value: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    item = value.get(field)
    if not isinstance(item, Mapping):
        raise VectorRailConsequenceCustodyVerificationError(
            f"{field} must be an object"
        )
    return item


def _mapping_sequence(value: object, field: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise VectorRailConsequenceCustodyVerificationError(f"{field} must be an array")
    items: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise VectorRailConsequenceCustodyVerificationError(
                f"{field} entries must be objects"
            )
        items.append(item)
    return items


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise VectorRailConsequenceCustodyVerificationError(
            f"{field} must be non-empty"
        )
    return result


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = [
    "VectorRailConsequenceCustodyVerification",
    "VectorRailConsequenceCustodyVerificationError",
    "verify_vectorrail_consequence_custody",
]
