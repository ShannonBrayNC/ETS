"""Consequence reconstruction for Ranger cyber-physical Decision Events.

This verifier evaluates whether the supplied event evidence supports a causal path from
selected action through issued command, acknowledgement, actuator response, and observed
consequence. It preserves epistemic absence and contradiction rather than collapsing all
stages into a single success boolean.
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict

from ets.evidence_object.models import EvidenceObject

_RANGER_EXTENSION_NAMESPACE = "org.lanternprotocol.ranger.decision-event.v0.1"


class RangerConsequenceVerificationError(ValueError):
    """Raised when cyber-physical consequence evidence cannot be interpreted safely."""


class RangerStageFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    stage: str
    status: str
    epistemic_state: str | None = None
    reason: str | None = None


class RangerConsequenceVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_id: str
    decision_id: str
    selected_action: str
    overall_status: str
    stage_findings: tuple[RangerStageFinding, ...]
    supporting_measurement_refs: tuple[str, ...]
    contradicting_measurement_refs: tuple[str, ...]
    capability_limitations: tuple[str, ...]
    consequence_claim_supported: bool
    truth_claim_supported: bool = False
    claim_boundary: str = (
        "evidentiary_support_for_a_recorded_consequence_does_not_prove_external_physical_truth"
    )


def verify_ranger_consequence(evidence: EvidenceObject) -> RangerConsequenceVerification:
    """Reconstruct one Ranger decision-to-consequence path from embedded evidence."""

    event = _embedded_event(evidence)
    event_id = _required_string(event, "event_id")
    decision = _required_mapping(event, "decision")
    decision_id = _required_string(decision, "decision_id")
    selected_action = _required_string(decision, "selected_action")

    cps = event.get("cyber_physical_state")
    if cps is None:
        return RangerConsequenceVerification(
            event_id=event_id,
            decision_id=decision_id,
            selected_action=selected_action,
            overall_status="NOT_OBSERVED",
            stage_findings=(
                RangerStageFinding(
                    stage="cyber_physical_state",
                    status="NOT_OBSERVED",
                    reason="Decision Event contains no cyber_physical_state evidence.",
                ),
            ),
            supporting_measurement_refs=(),
            contradicting_measurement_refs=(),
            capability_limitations=(),
            consequence_claim_supported=False,
        )
    if not isinstance(cps, Mapping):
        raise RangerConsequenceVerificationError("cyber_physical_state must be an object")

    capabilities = cps.get("capabilities", [])
    if not isinstance(capabilities, list):
        raise RangerConsequenceVerificationError("capabilities must be an array")
    capability_limitations = tuple(
        _capability_limitation(item)
        for item in capabilities
        if isinstance(item, Mapping) and item.get("state") in {"DEGRADED", "NOT_AVAILABLE", "FAILED", "UNKNOWN"}
    )

    actuation = cps.get("actuation")
    stages: list[RangerStageFinding] = []
    if actuation is None:
        stages.append(
            RangerStageFinding(
                stage="actuation",
                status="NOT_OBSERVED",
                reason="No actuation evidence was recorded.",
            )
        )
    elif not isinstance(actuation, Mapping):
        raise RangerConsequenceVerificationError("actuation must be object or null")
    else:
        stages.extend(_verify_actuation(actuation, selected_action))

    consequence = cps.get("consequence")
    supporting_refs: tuple[str, ...] = ()
    contradicting_refs: tuple[str, ...] = ()
    consequence_state: str | None = None
    if consequence is None:
        stages.append(
            RangerStageFinding(
                stage="observed_consequence",
                status="NOT_OBSERVED",
                reason="No consequence observation was recorded.",
            )
        )
    elif not isinstance(consequence, Mapping):
        raise RangerConsequenceVerificationError("consequence must be object or null")
    else:
        consequence_state = _required_string(consequence, "state")
        supporting_refs = _string_tuple(consequence.get("supporting_measurement_refs", []), "supporting_measurement_refs")
        contradicting_refs = _string_tuple(consequence.get("contradicting_measurement_refs", []), "contradicting_measurement_refs")
        if contradicting_refs or consequence_state == "CONTRADICTED":
            stages.append(
                RangerStageFinding(
                    stage="observed_consequence",
                    status="CONTRADICTED",
                    epistemic_state=consequence_state,
                    reason=_optional_string(consequence.get("reason")) or "Contradicting consequence evidence exists.",
                )
            )
        elif consequence_state == "KNOWN" and supporting_refs:
            stages.append(
                RangerStageFinding(
                    stage="observed_consequence",
                    status="SUPPORTED",
                    epistemic_state=consequence_state,
                )
            )
        else:
            stages.append(
                RangerStageFinding(
                    stage="observed_consequence",
                    status=_status_from_epistemic(consequence_state),
                    epistemic_state=consequence_state,
                    reason=_optional_string(consequence.get("reason")),
                )
            )

    statuses = {stage.status for stage in stages}
    if "CONTRADICTED" in statuses:
        overall = "CONTRADICTED"
    elif "INDETERMINATE" in statuses or "UNKNOWN" in statuses:
        overall = "INDETERMINATE"
    elif "NOT_AVAILABLE" in statuses or "NOT_OBSERVED" in statuses:
        overall = "NOT_OBSERVED"
    elif stages and all(stage.status == "SUPPORTED" for stage in stages):
        overall = "SUPPORTED"
    else:
        overall = "INDETERMINATE"

    return RangerConsequenceVerification(
        event_id=event_id,
        decision_id=decision_id,
        selected_action=selected_action,
        overall_status=overall,
        stage_findings=tuple(stages),
        supporting_measurement_refs=supporting_refs,
        contradicting_measurement_refs=contradicting_refs,
        capability_limitations=capability_limitations,
        consequence_claim_supported=overall == "SUPPORTED",
    )


def _verify_actuation(actuation: Mapping[str, Any], selected_action: str) -> list[RangerStageFinding]:
    findings: list[RangerStageFinding] = []
    ordered = (
        ("selected_action", selected_action),
        ("issued_command", None),
        ("command_acknowledgement", None),
        ("actuator_response", None),
    )
    for stage_name, expected in ordered:
        value = actuation.get(stage_name)
        if value is None:
            findings.append(
                RangerStageFinding(
                    stage=stage_name,
                    status="NOT_OBSERVED",
                    reason=f"No {stage_name} evidence was recorded.",
                )
            )
            continue
        if not isinstance(value, Mapping):
            raise RangerConsequenceVerificationError(f"{stage_name} must be an object")
        epistemic = _required_string(value, "state")
        reason = _optional_string(value.get("reason"))
        if epistemic == "KNOWN":
            if expected is not None and value.get("value") != expected:
                findings.append(
                    RangerStageFinding(
                        stage=stage_name,
                        status="CONTRADICTED",
                        epistemic_state=epistemic,
                        reason="Cyber-physical selected_action does not match Decision Event selected_action.",
                    )
                )
            else:
                findings.append(
                    RangerStageFinding(stage=stage_name, status="SUPPORTED", epistemic_state=epistemic)
                )
        else:
            findings.append(
                RangerStageFinding(
                    stage=stage_name,
                    status=_status_from_epistemic(epistemic),
                    epistemic_state=epistemic,
                    reason=reason,
                )
            )
    return findings


def _status_from_epistemic(state: str) -> str:
    if state == "CONTRADICTED":
        return "CONTRADICTED"
    if state in {"UNKNOWN", "INDETERMINATE"}:
        return "INDETERMINATE"
    if state in {"NOT_AVAILABLE", "NOT_OBSERVED"}:
        return state
    if state == "KNOWN":
        return "SUPPORTED"
    return "INDETERMINATE"


def _embedded_event(evidence: EvidenceObject) -> Mapping[str, Any]:
    extension = evidence.extensions.get(_RANGER_EXTENSION_NAMESPACE)
    if not isinstance(extension, Mapping):
        raise RangerConsequenceVerificationError("Ranger decision-event extension is missing")
    event = extension.get("decision_event")
    if not isinstance(event, Mapping):
        raise RangerConsequenceVerificationError("Ranger decision_event extension is invalid")
    return event


def _required_mapping(value: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    result = value.get(field)
    if not isinstance(result, Mapping):
        raise RangerConsequenceVerificationError(f"{field} must be an object")
    return result


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise RangerConsequenceVerificationError(f"{field} must be a non-empty string")
    return result


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise RangerConsequenceVerificationError(f"{field} must be an array of strings")
    return tuple(value)


def _capability_limitation(value: Mapping[str, Any]) -> str:
    capability_id = _required_string(value, "capability_id")
    state = _required_string(value, "state")
    reason = _optional_string(value.get("reason"))
    return f"{capability_id}:{state}" + (f":{reason}" if reason else "")


__all__ = [
    "RangerConsequenceVerification",
    "RangerConsequenceVerificationError",
    "RangerStageFinding",
    "verify_ranger_consequence",
]
