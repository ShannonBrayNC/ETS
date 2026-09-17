"""Close the frozen Agent 365 + M365 + Ranger R0 demo into ETS evidence.

This module packages the already-frozen Microsoft authorization, Gateway dispatch,
Ranger motion directives, and the seven robot-side boundary records into one Ranger
Decision Event and ETS Evidence Object v1.  It verifies the semantic chain before
projection and preserves the distinction between a stop command and independently
observed stopped state.

The P0 boundary intentionally does not invent actuator acknowledgement or actuator
response evidence.  Those stages remain NOT_OBSERVED even when an independent result
sensor supports the final stopped state.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict

from ets.core.canonical_json import canonicalize
from ets.demos.agent365_r0_mission import (
    MissionAuthorizationState,
    MissionStatus,
    SharePointMissionArtifactV1,
)
from ets.evidence_object.canonical import object_hash
from ets.evidence_object.models import EvidenceObject
from ets.gateway.agent365_r0_mission import (
    GatewayR0DispatchBundle,
    MissionCorrelationEnvelopeV1,
    RangerR0GatewayCommandV1,
)
from ets.ranger.agent365_r0_boundary import (
    RangerR0BoundaryRecordV1,
    RangerR0MotionDirectiveV1,
    RangerR0Stage,
    RangerR0StopDirectiveV1,
    RangerR0StopReason,
)
from ets.ranger.consequence_verifier import verify_ranger_consequence
from ets.ranger.decision_event import decision_event_digest, sign_decision_event
from ets.ranger.evidence_object_adapter import ranger_decision_event_to_evidence_object
from ets.ranger.evidence_object_verifier import verify_ranger_evidence_object
from ets.ranger.source_evidence_verifier import verify_ranger_source_evidence


_AUTH_ARTIFACT_ID: Final = "source:sharepoint-authorization"
_GATEWAY_INGRESS_ID: Final = "source:gateway-ingress"
_GATEWAY_DECISION_ID: Final = "source:gateway-decision"
_GATEWAY_EGRESS_ID: Final = "source:gateway-egress"
_GATEWAY_COMMAND_ID: Final = "source:gateway-robot-command"
_MOTION_DIRECTIVE_ID: Final = "source:ranger-motion-directive"
_STOP_DIRECTIVE_ID: Final = "source:ranger-stop-directive"

_EXPECTED_STAGES: Final = (
    RangerR0Stage.RECEIVED,
    RangerR0Stage.AUTHORIZED,
    RangerR0Stage.MOTION_STARTED,
    RangerR0Stage.STOP_CONDITION_OBSERVED,
    RangerR0Stage.STOP_DECIDED,
    RangerR0Stage.STOP_ACTUATED,
    RangerR0Stage.RESULT_OBSERVED,
)
_EXPECTED_STAGE_DOMAINS: Final = {
    RangerR0Stage.RECEIVED: "ranger.r0",
    RangerR0Stage.AUTHORIZED: "ranger.r0",
    RangerR0Stage.MOTION_STARTED: "ranger.sensor",
    RangerR0Stage.STOP_CONDITION_OBSERVED: "ranger.sensor",
    RangerR0Stage.STOP_DECIDED: "ranger.r0",
    RangerR0Stage.STOP_ACTUATED: "ranger.r0",
    RangerR0Stage.RESULT_OBSERVED: "ranger.sensor",
}


class RangerR0ConsequenceClosureError(ValueError):
    """Raised when Step 4 cannot establish the frozen P0 evidence closure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class RangerR0ConsequenceClosureBundle:
    """Evidence Object plus the exact retained source bytes needed to verify it."""

    mission_id: str
    decision_event: dict[str, Any]
    evidence_object: EvidenceObject
    evidence_object_hash: str
    evidence_bundle_ref: str
    source_artifacts: Mapping[str, bytes]


class RangerR0ConsequenceClosureVerification(BaseModel):
    """Verification result for the frozen P0 physical-consequence closure."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.consequence-closure-verification.v1"] = (
        "ets.demo.agent365-r0.consequence-closure-verification.v1"
    )
    valid: bool
    mission_id: str
    stage_count: int
    evidence_object_hash: str
    event_digest: str
    source_evidence_status: str
    signature_status: str
    legacy_consequence_status: str
    authorization_binding_valid: bool
    gateway_chain_valid: bool
    boundary_chain_valid: bool
    directive_binding_valid: bool
    independent_result_observation_supported: bool
    physical_result_supported: bool
    actuator_acknowledgement_observed: bool = False
    actuator_response_observed: bool = False
    truth_claim_supported: bool = False
    claim_boundary: str = (
        "verified_frozen_r0_authority_dispatch_boundary_and_independent_stopped_result_"
        "do_not_prove_unobserved_actuator_acknowledgement_or_complete_external_truth"
    )


def build_agent365_r0_consequence_closure(
    authorization_artifact: SharePointMissionArtifactV1,
    dispatch: GatewayR0DispatchBundle,
    boundary_records: Iterable[RangerR0BoundaryRecordV1],
    *,
    motion_directive: RangerR0MotionDirectiveV1,
    stop_directive: RangerR0StopDirectiveV1,
    private_key_hex: str | None = None,
    key_id: str | None = None,
) -> RangerR0ConsequenceClosureBundle:
    """Build one verifiable ETS closure object for the seven-stage Ranger R0 boundary.

    The builder rejects any cross-mission splice, changed authorization material,
    Gateway-chain discontinuity, directive mismatch, boundary-record discontinuity,
    or final result that is not the independently observed STOP_CONFIRMED state.
    """

    records = tuple(boundary_records)
    facts = _validate_semantic_chain(
        authorization_artifact=authorization_artifact,
        ingress=dispatch.ingress_event,
        gateway_decision=dispatch.decision_event,
        egress=dispatch.egress_event,
        command=dispatch.robot_command,
        transport_retry=dispatch.transport_retry,
        motion_directive=motion_directive,
        stop_directive=stop_directive,
        records=records,
    )

    source_artifacts: dict[str, bytes] = {}
    references: list[dict[str, Any]] = []

    def retain(
        artifact_id: str,
        *,
        evidence_type: str,
        source_id: str,
        captured_at: datetime,
        value: BaseModel,
        uri_suffix: str,
    ) -> None:
        raw = _model_bytes(value)
        source_artifacts[artifact_id] = raw
        references.append(
            _evidence_reference(
                artifact_id,
                evidence_type=evidence_type,
                source_id=source_id,
                captured_at=captured_at,
                raw=raw,
                mission_id=facts.mission_id,
                uri_suffix=uri_suffix,
            )
        )

    assert authorization_artifact.authorized_at is not None
    retain(
        _AUTH_ARTIFACT_ID,
        evidence_type="microsoft.sharepoint.mission-authorization",
        source_id="microsoft.sharepoint",
        captured_at=authorization_artifact.authorized_at,
        value=authorization_artifact,
        uri_suffix="sharepoint-authorization",
    )
    retain(
        _GATEWAY_INGRESS_ID,
        evidence_type="ets.gateway.mission-ingress",
        source_id="ets.gateway",
        captured_at=dispatch.ingress_event.observed_at,
        value=dispatch.ingress_event,
        uri_suffix="gateway-ingress",
    )
    retain(
        _GATEWAY_DECISION_ID,
        evidence_type="ets.gateway.authorization-decision",
        source_id="ets.gateway",
        captured_at=dispatch.decision_event.observed_at,
        value=dispatch.decision_event,
        uri_suffix="gateway-decision",
    )
    retain(
        _GATEWAY_EGRESS_ID,
        evidence_type="ets.gateway.robot-egress",
        source_id="ets.gateway",
        captured_at=dispatch.egress_event.observed_at,
        value=dispatch.egress_event,
        uri_suffix="gateway-egress",
    )
    retain(
        _GATEWAY_COMMAND_ID,
        evidence_type="ets.gateway.ranger-command",
        source_id="ets.gateway",
        captured_at=dispatch.robot_command.issued_at,
        value=dispatch.robot_command,
        uri_suffix="gateway-command",
    )
    retain(
        _MOTION_DIRECTIVE_ID,
        evidence_type="ranger.motion-directive",
        source_id=motion_directive.controller_id,
        captured_at=motion_directive.issued_at,
        value=motion_directive,
        uri_suffix="motion-directive",
    )
    retain(
        _STOP_DIRECTIVE_ID,
        evidence_type="ranger.stop-directive",
        source_id=stop_directive.controller_id,
        captured_at=stop_directive.issued_at,
        value=stop_directive,
        uri_suffix="stop-directive",
    )
    for record in records:
        artifact_id = _boundary_artifact_id(record.stage)
        retain(
            artifact_id,
            evidence_type=f"ranger.boundary.{record.stage.value.lower()}",
            source_id=record.envelope.source_domain,
            captured_at=record.envelope.observed_at,
            value=record,
            uri_suffix=f"boundary/{record.stage.value.lower()}",
        )

    stage_ids = {record.stage: _boundary_artifact_id(record.stage) for record in records}
    stop_observation = records[3]
    result = records[6]

    claims = [
        _known_claim(
            "claim-mission-authorized",
            "mission.authorization_state",
            "AUTHORIZED",
            mechanism="sharepoint-authorization-material-v1",
            source_refs=[_AUTH_ARTIFACT_ID],
        ),
        _known_claim(
            "claim-gateway-dispatched",
            "mission.gateway_dispatch",
            True,
            mechanism="gateway-r0-guard-v1",
            source_refs=[_GATEWAY_DECISION_ID, _GATEWAY_EGRESS_ID, _GATEWAY_COMMAND_ID],
        ),
        _known_claim(
            "claim-motion-started",
            "ranger.motion_started",
            True,
            mechanism="independent-motion-sensor",
            source_refs=[stage_ids[RangerR0Stage.MOTION_STARTED]],
        ),
        _known_claim(
            "claim-stop-condition",
            "ranger.stop_condition",
            stop_observation.payload.get("trigger_reasons"),
            mechanism="independent-stop-sensor",
            source_refs=[stage_ids[RangerR0Stage.STOP_CONDITION_OBSERVED]],
        ),
        _known_claim(
            "claim-stop-decision",
            "ranger.stop_decision",
            "STOP",
            mechanism="r0-forward-stop-policy.v1",
            source_refs=[stage_ids[RangerR0Stage.STOP_DECIDED]],
        ),
        _known_claim(
            "claim-stop-command",
            "ranger.stop_command",
            {"linear_speed_mps": 0.0, "yaw_rate_rad_s": 0.0},
            mechanism="ranger-controller-stop-directive",
            source_refs=[_STOP_DIRECTIVE_ID, stage_ids[RangerR0Stage.STOP_ACTUATED]],
        ),
        _known_claim(
            "claim-result-stopped",
            "ranger.result_stopped",
            True,
            mechanism="independent-result-sensor",
            source_refs=[stage_ids[RangerR0Stage.RESULT_OBSERVED]],
        ),
    ]

    event: dict[str, Any] = {
        "schema_version": "ranger.decision-event.v0.1",
        "event_id": f"ranger-r0:{facts.mission_id}:consequence-closure",
        "mission_id": facts.mission_id,
        "ranger_id": motion_directive.vehicle_id,
        "occurred_at": _format_utc(result.envelope.observed_at),
        "subject_context": [
            {
                "subject_id": motion_directive.vehicle_id,
                "subject_scope": "MISSION_RESOURCE",
                "claims": claims,
            }
        ],
        "decision": {
            "decision_id": f"decision:{facts.mission_id}:stop",
            "policy_id": authorization_artifact.policy_version,
            "candidate_actions": ["MOVE_FORWARD", "STOP"],
            "selected_action": "STOP",
            "authorization_state": "AUTHORIZED",
            "participating_claim_ids": [
                "claim-mission-authorized",
                "claim-gateway-dispatched",
                "claim-motion-started",
                "claim-stop-condition",
            ],
            "excluded_claim_ids": [],
            "decision_reason": (
                "The frozen R0 stop policy selected STOP after an independently observed "
                "stop condition. The later result sensor independently observed the stopped state."
            ),
        },
        "evidence": references,
        "cyber_physical_state": {
            "capabilities": [
                {
                    "capability_id": "independent-result-sensor",
                    "state": "KNOWN",
                    "reason": (
                        "A result observer distinct from the motion controller produced "
                        "the final record."
                    ),
                }
            ],
            "actuation": {
                "selected_action": {
                    "state": "KNOWN",
                    "value": "STOP",
                    "source_refs": [stage_ids[RangerR0Stage.STOP_DECIDED]],
                },
                "issued_command": {
                    "state": "KNOWN",
                    "value": "STOP",
                    "source_refs": [_STOP_DIRECTIVE_ID, stage_ids[RangerR0Stage.STOP_ACTUATED]],
                },
                "command_acknowledgement": {
                    "state": "NOT_OBSERVED",
                    "reason": (
                        "The frozen seven-stage P0 boundary does not contain a separate actuator "
                        "acknowledgement signal."
                    ),
                },
                "actuator_response": {
                    "state": "NOT_OBSERVED",
                    "reason": (
                        "The frozen seven-stage P0 boundary does not claim a "
                        "controller-independent actuator response measurement."
                    ),
                },
            },
            "consequence": {
                "state": "KNOWN",
                "value": "STOP_CONFIRMED",
                "supporting_measurement_refs": [stage_ids[RangerR0Stage.RESULT_OBSERVED]],
                "contradicting_measurement_refs": [],
                "reason": (
                    "The independent result sensor observed speed at or below the configured "
                    "stopped threshold for the required stationary interval."
                ),
            },
            "agent365_r0_boundary": {
                "stage_sequence": [stage.value for stage in _EXPECTED_STAGES],
                "gateway_anchor_digest": dispatch.egress_event.canonical_digest(),
                "gateway_egress_event_id": dispatch.egress_event.event_id,
                "authorization_artifact_ref": dispatch.robot_command.authorization_artifact_ref,
                "authorization_material_sha256": (
                    authorization_artifact.authorization_material_sha256()
                ),
                "motion_controller_id": motion_directive.controller_id,
                "result_observer_id": facts.result_observer_id,
                "stop_reason": facts.stop_reason.value,
                "boundary_record_refs": [stage_ids[stage] for stage in _EXPECTED_STAGES],
                "claim_boundary": (
                    "stop_command_is_not_physical_result; final stopped state is supported only "
                    "by the independent result observation"
                ),
            },
        },
        "previous_event_digest": None,
        "event_digest": None,
        "signature": None,
    }
    event["event_digest"] = decision_event_digest(event)

    if (private_key_hex is None) != (key_id is None):
        raise RangerR0ConsequenceClosureError(
            "incomplete_signing_configuration",
            "private_key_hex and key_id must be supplied together",
        )
    if private_key_hex is not None and key_id is not None:
        event = sign_decision_event(event, private_key_hex=private_key_hex, key_id=key_id)

    evidence_object = ranger_decision_event_to_evidence_object(event)
    bundle_ref = f"ets://mission/{facts.mission_id}/bundle/agent365-r0-consequence-closure-v1"
    return RangerR0ConsequenceClosureBundle(
        mission_id=facts.mission_id,
        decision_event=event,
        evidence_object=evidence_object,
        evidence_object_hash=object_hash(evidence_object),
        evidence_bundle_ref=bundle_ref,
        source_artifacts=dict(source_artifacts),
    )


def verify_agent365_r0_consequence_closure(
    bundle: RangerR0ConsequenceClosureBundle,
    *,
    ranger_public_key_hex: str | None = None,
) -> RangerR0ConsequenceClosureVerification:
    """Reverse-verify the retained bundle without trusting the builder's in-memory inputs."""

    evidence_verification = verify_ranger_evidence_object(
        bundle.evidence_object,
        ranger_public_key_hex=ranger_public_key_hex,
        expected_object_hash=bundle.evidence_object_hash,
    )
    source_verification = verify_ranger_source_evidence(
        bundle.evidence_object,
        artifacts=bundle.source_artifacts,
    )
    event = _embedded_event(bundle.evidence_object)
    stored_event_digest = event.get("event_digest")
    if (
        not isinstance(stored_event_digest, str)
        or decision_event_digest(event) != stored_event_digest
    ):
        raise RangerR0ConsequenceClosureError(
            "decision_event_digest_mismatch",
            "closure Decision Event digest does not verify",
        )
    if bundle.decision_event != event:
        raise RangerR0ConsequenceClosureError(
            "decision_event_bundle_mismatch",
            "bundle Decision Event differs from the event embedded in the Evidence Object",
        )
    if source_verification.overall_status != "VERIFIED":
        raise RangerR0ConsequenceClosureError(
            "source_evidence_not_verified",
            f"retained source evidence status is {source_verification.overall_status}",
        )
    if evidence_verification.outer_object_hash_valid is not True:
        raise RangerR0ConsequenceClosureError(
            "evidence_object_hash_mismatch",
            "Evidence Object hash does not match the closure bundle commitment",
        )
    if (
        not evidence_verification.ranger_event_digest_valid
        or not evidence_verification.ranger_integrity_binding_valid
    ):
        raise RangerR0ConsequenceClosureError(
            "evidence_object_binding_invalid",
            "Evidence Object does not preserve a valid Ranger Decision Event binding",
        )
    if (
        ranger_public_key_hex is not None
        and evidence_verification.ranger_signature_status != "VALID"
    ):
        raise RangerR0ConsequenceClosureError(
            "signature_invalid",
            "Ranger closure signature did not verify with the supplied trusted key",
        )

    authorization = _artifact_model(
        bundle.source_artifacts,
        _AUTH_ARTIFACT_ID,
        SharePointMissionArtifactV1,
    )
    ingress = _artifact_model(
        bundle.source_artifacts,
        _GATEWAY_INGRESS_ID,
        MissionCorrelationEnvelopeV1,
    )
    gateway_decision = _artifact_model(
        bundle.source_artifacts,
        _GATEWAY_DECISION_ID,
        MissionCorrelationEnvelopeV1,
    )
    egress = _artifact_model(
        bundle.source_artifacts,
        _GATEWAY_EGRESS_ID,
        MissionCorrelationEnvelopeV1,
    )
    command = _artifact_model(
        bundle.source_artifacts,
        _GATEWAY_COMMAND_ID,
        RangerR0GatewayCommandV1,
    )
    motion_directive = _artifact_model(
        bundle.source_artifacts,
        _MOTION_DIRECTIVE_ID,
        RangerR0MotionDirectiveV1,
    )
    stop_directive = _artifact_model(
        bundle.source_artifacts,
        _STOP_DIRECTIVE_ID,
        RangerR0StopDirectiveV1,
    )
    records = tuple(
        _artifact_model(
            bundle.source_artifacts,
            _boundary_artifact_id(stage),
            RangerR0BoundaryRecordV1,
        )
        for stage in _EXPECTED_STAGES
    )

    facts = _validate_semantic_chain(
        authorization_artifact=authorization,
        ingress=ingress,
        gateway_decision=gateway_decision,
        egress=egress,
        command=command,
        transport_retry=False,
        motion_directive=motion_directive,
        stop_directive=stop_directive,
        records=records,
    )
    if (
        bundle.mission_id != facts.mission_id
        or evidence_verification.mission_id != facts.mission_id
    ):
        raise RangerR0ConsequenceClosureError(
            "mission_id_bundle_mismatch",
            "closure bundle, Evidence Object, and retained source artifacts disagree on mission_id",
        )

    cps = event.get("cyber_physical_state")
    if not isinstance(cps, Mapping):
        raise RangerR0ConsequenceClosureError(
            "missing_cyber_physical_state",
            "closure Decision Event has no cyber_physical_state object",
        )
    boundary = cps.get("agent365_r0_boundary")
    if not isinstance(boundary, Mapping):
        raise RangerR0ConsequenceClosureError(
            "missing_boundary_summary",
            "closure Decision Event has no Agent 365 R0 boundary summary",
        )
    if boundary.get("gateway_anchor_digest") != egress.canonical_digest():
        raise RangerR0ConsequenceClosureError(
            "gateway_anchor_summary_mismatch",
            "Decision Event boundary summary does not commit to the retained Gateway egress",
        )
    if boundary.get("motion_controller_id") != motion_directive.controller_id:
        raise RangerR0ConsequenceClosureError(
            "controller_summary_mismatch",
            "Decision Event controller identity differs from the retained motion directive",
        )
    if boundary.get("result_observer_id") != facts.result_observer_id:
        raise RangerR0ConsequenceClosureError(
            "result_observer_summary_mismatch",
            "Decision Event result observer differs from the retained result record",
        )

    consequence = verify_ranger_consequence(bundle.evidence_object)
    observed_result_supported = any(
        finding.stage == "observed_consequence" and finding.status == "SUPPORTED"
        for finding in consequence.stage_findings
    )
    if not observed_result_supported:
        raise RangerR0ConsequenceClosureError(
            "physical_result_not_supported",
            "independent result observation is not supported by the projected Evidence Object",
        )

    return RangerR0ConsequenceClosureVerification(
        valid=True,
        mission_id=facts.mission_id,
        stage_count=len(records),
        evidence_object_hash=bundle.evidence_object_hash,
        event_digest=stored_event_digest,
        source_evidence_status=source_verification.overall_status,
        signature_status=evidence_verification.ranger_signature_status,
        legacy_consequence_status=consequence.overall_status,
        authorization_binding_valid=True,
        gateway_chain_valid=True,
        boundary_chain_valid=True,
        directive_binding_valid=True,
        independent_result_observation_supported=True,
        physical_result_supported=True,
    )


def complete_sharepoint_mission_from_closure(
    mission: SharePointMissionArtifactV1,
    closure: RangerR0ConsequenceClosureBundle,
) -> SharePointMissionArtifactV1:
    """Return the completed SharePoint-side mission artifact without changing authority material."""

    verification = verify_agent365_r0_consequence_closure(closure)
    if mission.mission_id != verification.mission_id:
        raise RangerR0ConsequenceClosureError(
            "sharepoint_completion_mission_mismatch",
            "SharePoint mission does not match the verified consequence closure",
        )
    if mission.authorization_state != MissionAuthorizationState.AUTHORIZED:
        raise RangerR0ConsequenceClosureError(
            "sharepoint_completion_not_authorized",
            "only an AUTHORIZED SharePoint mission can be completed from R0 evidence",
        )

    before = mission.authorization_material_sha256()
    stop_decision = _artifact_model(
        closure.source_artifacts,
        _boundary_artifact_id(RangerR0Stage.STOP_DECIDED),
        RangerR0BoundaryRecordV1,
    )
    raw_reason = stop_decision.payload.get("primary_reason")
    if not isinstance(raw_reason, str):
        raise RangerR0ConsequenceClosureError(
            "missing_primary_stop_reason",
            "verified stop decision does not contain primary_reason",
        )
    reason = RangerR0StopReason(raw_reason)
    status = _completion_status(reason)

    values = mission.model_dump(mode="python")
    values.update(
        status=status,
        evidence_object_id=closure.evidence_object.identity.evidence_id,
        evidence_bundle_ref=closure.evidence_bundle_ref,
    )
    completed = SharePointMissionArtifactV1.model_validate(values)
    if completed.authorization_material_sha256() != before:
        raise RangerR0ConsequenceClosureError(
            "authorization_material_changed_on_completion",
            "SharePoint completion changed frozen authorization material",
        )
    return completed


def sharepoint_completion_patch_body(mission: SharePointMissionArtifactV1) -> dict[str, object]:
    """Build the minimal Graph listItem field patch after verified physical closure."""

    if mission.evidence_object_id is None or mission.evidence_bundle_ref is None:
        raise RangerR0ConsequenceClosureError(
            "missing_completion_evidence_refs",
            "completed mission must carry EvidenceObjectId and EvidenceBundleRef",
        )
    return {
        "fields": {
            "Status": mission.status.value,
            "EvidenceObjectId": mission.evidence_object_id,
            "EvidenceBundleRef": mission.evidence_bundle_ref,
        }
    }


@dataclass(frozen=True, slots=True)
class _SemanticFacts:
    mission_id: str
    stop_reason: RangerR0StopReason
    result_observer_id: str


def _validate_semantic_chain(
    *,
    authorization_artifact: SharePointMissionArtifactV1,
    ingress: MissionCorrelationEnvelopeV1,
    gateway_decision: MissionCorrelationEnvelopeV1,
    egress: MissionCorrelationEnvelopeV1,
    command: RangerR0GatewayCommandV1,
    transport_retry: bool,
    motion_directive: RangerR0MotionDirectiveV1,
    stop_directive: RangerR0StopDirectiveV1,
    records: tuple[RangerR0BoundaryRecordV1, ...],
) -> _SemanticFacts:
    if transport_retry or command.retry_of_delivery_id is not None:
        raise RangerR0ConsequenceClosureError(
            "retry_cannot_close_physical_execution",
            "P0 consequence closure must be anchored to the first execution-bearing delivery",
        )
    if authorization_artifact.authorization_state != MissionAuthorizationState.AUTHORIZED:
        raise RangerR0ConsequenceClosureError(
            "mission_not_authorized",
            "SharePoint artifact is not AUTHORIZED",
        )
    if authorization_artifact.status not in {
        MissionStatus.AUTHORIZED,
        MissionStatus.DISPATCHED,
        MissionStatus.EXECUTING,
    }:
        raise RangerR0ConsequenceClosureError(
            "mission_status_not_closable",
            "SharePoint mission status is outside the pre-completion R0 boundary",
        )

    mission_id = authorization_artifact.mission_id
    if command.mission_id != mission_id:
        raise RangerR0ConsequenceClosureError(
            "command_mission_mismatch",
            "Gateway robot command mission_id differs from SharePoint authorization",
        )
    if (
        command.authorization_material_sha256
        != authorization_artifact.authorization_material_sha256()
    ):
        raise RangerR0ConsequenceClosureError(
            "authorization_material_mismatch",
            "Gateway command does not commit to the retained SharePoint authorization material",
        )
    if command.policy_version != authorization_artifact.policy_version:
        raise RangerR0ConsequenceClosureError(
            "policy_version_mismatch",
            "Gateway command policy differs from SharePoint authorization",
        )
    if (
        command.command_parameters.model_dump(mode="json")
        != authorization_artifact.command_parameters
    ):
        raise RangerR0ConsequenceClosureError(
            "command_parameters_mismatch",
            "Gateway command parameters differ from the retained SharePoint authorization",
        )

    for name, envelope in (
        ("ingress", ingress),
        ("decision", gateway_decision),
        ("egress", egress),
    ):
        if envelope.mission_id != mission_id or envelope.source_domain != "ets.gateway":
            raise RangerR0ConsequenceClosureError(
                "gateway_envelope_mismatch",
                f"Gateway {name} envelope is outside the authorized mission/domain",
            )
        if envelope.authorization_artifact_ref != command.authorization_artifact_ref:
            raise RangerR0ConsequenceClosureError(
                "authorization_artifact_ref_mismatch",
                f"Gateway {name} envelope does not preserve authorization_artifact_ref",
            )
    if ingress.event_type != "gateway.command.received":
        raise RangerR0ConsequenceClosureError(
            "gateway_ingress_type_mismatch",
            "first execution-bearing dispatch must begin with gateway.command.received",
        )
    if gateway_decision.event_type != "gateway.authorization.accepted":
        raise RangerR0ConsequenceClosureError(
            "gateway_decision_type_mismatch",
            "Gateway decision event must be gateway.authorization.accepted",
        )
    if egress.event_type != "gateway.command.accepted":
        raise RangerR0ConsequenceClosureError(
            "gateway_egress_type_mismatch",
            "first execution-bearing dispatch must end with gateway.command.accepted",
        )
    if gateway_decision.parent_event_id != ingress.event_id:
        raise RangerR0ConsequenceClosureError(
            "gateway_parent_mismatch",
            "Gateway decision does not descend from ingress",
        )
    if gateway_decision.previous_event_digest != ingress.canonical_digest():
        raise RangerR0ConsequenceClosureError(
            "gateway_decision_digest_link_mismatch",
            "Gateway decision does not chain to ingress digest",
        )
    if egress.parent_event_id != gateway_decision.event_id:
        raise RangerR0ConsequenceClosureError(
            "gateway_egress_parent_mismatch",
            "Gateway egress does not descend from authorization decision",
        )
    if egress.previous_event_digest != gateway_decision.canonical_digest():
        raise RangerR0ConsequenceClosureError(
            "gateway_egress_digest_link_mismatch",
            "Gateway egress does not chain to authorization decision digest",
        )
    if command.gateway_decision_event_id != gateway_decision.event_id:
        raise RangerR0ConsequenceClosureError(
            "gateway_command_decision_mismatch",
            "robot command does not identify the retained Gateway authorization decision",
        )
    if egress.payload_sha256 != command.payload_sha256():
        raise RangerR0ConsequenceClosureError(
            "gateway_command_payload_mismatch",
            "Gateway egress payload commitment does not match the retained robot command",
        )

    if len(records) != len(_EXPECTED_STAGES):
        raise RangerR0ConsequenceClosureError(
            "boundary_stage_count_mismatch",
            f"frozen R0 closure requires exactly {len(_EXPECTED_STAGES)} boundary records",
        )
    if tuple(record.stage for record in records) != _EXPECTED_STAGES:
        raise RangerR0ConsequenceClosureError(
            "boundary_stage_sequence_mismatch",
            "Ranger boundary records are missing, duplicated, or out of order",
        )
    for index, record in enumerate(records):
        if record.envelope.mission_id != mission_id:
            raise RangerR0ConsequenceClosureError(
                "boundary_mission_mismatch",
                f"boundary record {record.stage.value} belongs to another mission",
            )
        if record.envelope.source_domain != _EXPECTED_STAGE_DOMAINS[record.stage]:
            raise RangerR0ConsequenceClosureError(
                "boundary_source_domain_mismatch",
                f"boundary record {record.stage.value} has the wrong source domain",
            )
        if record.envelope.authorization_artifact_ref != command.authorization_artifact_ref:
            raise RangerR0ConsequenceClosureError(
                "boundary_authorization_ref_mismatch",
                f"boundary record {record.stage.value} changed authorization_artifact_ref",
            )
        if index == 0:
            if record.envelope.parent_event_id != egress.event_id:
                raise RangerR0ConsequenceClosureError(
                    "receipt_gateway_parent_mismatch",
                    "Ranger receipt does not descend from retained Gateway egress",
                )
            if record.envelope.previous_event_digest != egress.canonical_digest():
                raise RangerR0ConsequenceClosureError(
                    "receipt_gateway_digest_mismatch",
                    "Ranger receipt does not chain to retained Gateway egress digest",
                )
        else:
            previous = records[index - 1]
            if record.envelope.parent_event_id != previous.envelope.event_id:
                raise RangerR0ConsequenceClosureError(
                    "boundary_parent_mismatch",
                    f"boundary record {record.stage.value} has the wrong parent event",
                )
            if record.envelope.previous_event_digest != previous.envelope.canonical_digest():
                raise RangerR0ConsequenceClosureError(
                    "boundary_digest_link_mismatch",
                    (
                        f"boundary record {record.stage.value} does not chain to its "
                        "predecessor digest"
                    ),
                )

    if motion_directive.mission_id != mission_id or stop_directive.mission_id != mission_id:
        raise RangerR0ConsequenceClosureError(
            "directive_mission_mismatch",
            "Ranger motion/stop directive belongs to another mission",
        )
    if motion_directive.delivery_id != command.delivery_id:
        raise RangerR0ConsequenceClosureError(
            "motion_directive_delivery_mismatch",
            "motion directive does not bind to the first execution-bearing delivery",
        )
    if motion_directive.controller_id != stop_directive.controller_id:
        raise RangerR0ConsequenceClosureError(
            "controller_identity_mismatch",
            "motion and stop directives were not issued by the same controller identity",
        )
    if motion_directive.vehicle_id != stop_directive.vehicle_id:
        raise RangerR0ConsequenceClosureError(
            "vehicle_identity_mismatch",
            "motion and stop directives target different Ranger identities",
        )
    if motion_directive.linear_speed_mps != command.command_parameters.max_speed_mps:
        raise RangerR0ConsequenceClosureError(
            "motion_speed_mismatch",
            "motion directive speed differs from the authorized Gateway command",
        )
    if motion_directive.max_distance_m != command.command_parameters.max_distance_m:
        raise RangerR0ConsequenceClosureError(
            "motion_distance_mismatch",
            "motion directive distance bound differs from the authorized Gateway command",
        )
    if motion_directive.max_duration_s != command.command_parameters.max_duration_s:
        raise RangerR0ConsequenceClosureError(
            "motion_duration_mismatch",
            "motion directive duration bound differs from the authorized Gateway command",
        )
    if motion_directive.stop_distance_m != command.command_parameters.stop_distance_m:
        raise RangerR0ConsequenceClosureError(
            "motion_stop_distance_mismatch",
            "motion directive stop distance differs from the authorized Gateway command",
        )
    if stop_directive.linear_speed_mps != 0.0 or stop_directive.yaw_rate_rad_s != 0.0:
        raise RangerR0ConsequenceClosureError(
            "stop_directive_not_zero_motion",
            "stop directive is not a zero-motion command",
        )

    stop_decision = records[4]
    stop_actuation = records[5]
    result = records[6]
    raw_reason = stop_decision.payload.get("primary_reason")
    if not isinstance(raw_reason, str):
        raise RangerR0ConsequenceClosureError(
            "missing_stop_reason",
            "STOP_DECIDED record does not contain primary_reason",
        )
    try:
        stop_reason = RangerR0StopReason(raw_reason)
    except ValueError as exc:
        raise RangerR0ConsequenceClosureError(
            "invalid_stop_reason",
            "STOP_DECIDED record contains an unsupported stop reason",
        ) from exc
    if stop_directive.stop_reason is not stop_reason:
        raise RangerR0ConsequenceClosureError(
            "stop_directive_reason_mismatch",
            "stop directive reason differs from the STOP_DECIDED record",
        )
    if stop_actuation.payload.get("stop_reason") != stop_reason.value:
        raise RangerR0ConsequenceClosureError(
            "stop_actuation_reason_mismatch",
            "STOP_ACTUATED record changed the selected stop reason",
        )
    actuator_command = stop_actuation.payload.get("actuator_command")
    if not isinstance(actuator_command, dict) or actuator_command != {
        "linear_speed_mps": 0.0,
        "yaw_rate_rad_s": 0.0,
    }:
        raise RangerR0ConsequenceClosureError(
            "stop_actuation_command_mismatch",
            "STOP_ACTUATED record is not the frozen zero-motion command",
        )
    if result.payload.get("outcome") != "STOP_CONFIRMED":
        raise RangerR0ConsequenceClosureError(
            "result_not_stop_confirmed",
            "final Ranger boundary record does not independently support STOP_CONFIRMED",
        )
    result_observer_id = result.payload.get("observer_id")
    if not isinstance(result_observer_id, str) or not result_observer_id:
        raise RangerR0ConsequenceClosureError(
            "missing_result_observer",
            "RESULT_OBSERVED record has no independent observer identity",
        )
    if result_observer_id == motion_directive.controller_id:
        raise RangerR0ConsequenceClosureError(
            "result_observer_not_independent",
            "final result observation was asserted by the motion controller identity",
        )
    if result.payload.get("source_kind") != "independent_result_sensor":
        raise RangerR0ConsequenceClosureError(
            "result_source_not_independent_sensor",
            "final result record is not sourced from the frozen independent-result-sensor class",
        )
    if result.payload.get("stop_reason") != stop_reason.value:
        raise RangerR0ConsequenceClosureError(
            "result_stop_reason_mismatch",
            "final result record does not preserve the selected stop reason",
        )

    return _SemanticFacts(
        mission_id=mission_id,
        stop_reason=stop_reason,
        result_observer_id=result_observer_id,
    )


def _known_claim(
    claim_id: str,
    kind: str,
    value: Any,
    *,
    mechanism: str,
    source_refs: list[str],
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "kind": kind,
        "value": value,
        "state": "KNOWN",
        "confidence": None,
        "threshold": None,
        "mechanism": mechanism,
        "source_refs": source_refs,
        "reason": None,
        "contradicts_claim_ids": [],
    }


def _model_bytes(value: BaseModel) -> bytes:
    return canonicalize(value.model_dump(mode="json"))


def _evidence_reference(
    artifact_id: str,
    *,
    evidence_type: str,
    source_id: str,
    captured_at: datetime,
    raw: bytes,
    mission_id: str,
    uri_suffix: str,
) -> dict[str, Any]:
    return {
        "evidence_id": artifact_id,
        "evidence_type": evidence_type,
        "source_id": source_id,
        "captured_at": _format_utc(captured_at),
        "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "uri": f"ets://mission/{mission_id}/source/{uri_suffix}",
    }


def _boundary_artifact_id(stage: RangerR0Stage) -> str:
    return f"source:ranger-boundary:{stage.value.lower()}"


def _artifact_model(
    artifacts: Mapping[str, bytes],
    artifact_id: str,
    model_type: type[BaseModel],
) -> Any:
    raw = artifacts.get(artifact_id)
    if raw is None:
        raise RangerR0ConsequenceClosureError(
            "missing_source_artifact",
            f"retained source artifact is missing: {artifact_id}",
        )
    try:
        return model_type.model_validate_json(raw)
    except ValueError as exc:
        raise RangerR0ConsequenceClosureError(
            "invalid_source_artifact",
            f"retained source artifact cannot be parsed: {artifact_id}",
        ) from exc


def _embedded_event(evidence: EvidenceObject) -> dict[str, Any]:
    extension = evidence.extensions.get("org.lanternprotocol.ranger.decision-event.v0.1")
    if not isinstance(extension, dict):
        raise RangerR0ConsequenceClosureError(
            "missing_ranger_extension",
            "Evidence Object is missing the Ranger Decision Event extension",
        )
    event = extension.get("decision_event")
    if not isinstance(event, dict):
        raise RangerR0ConsequenceClosureError(
            "invalid_ranger_extension",
            "Evidence Object Ranger extension does not contain a Decision Event object",
        )
    return event


def _completion_status(reason: RangerR0StopReason) -> MissionStatus:
    if reason is RangerR0StopReason.OBSTACLE_WITHIN_STOP_DISTANCE:
        return MissionStatus.COMPLETED_OBSTACLE_STOP
    if reason in {
        RangerR0StopReason.MAX_DISTANCE_REACHED,
        RangerR0StopReason.MAX_DURATION_REACHED,
    }:
        return MissionStatus.COMPLETED_STOP_POINT
    if reason is RangerR0StopReason.HARDWARE_ESTOP:
        return MissionStatus.ABORTED_ESTOP
    if reason is RangerR0StopReason.POLICY_ABORT:
        return MissionStatus.ABORTED_POLICY
    raise AssertionError(f"unhandled stop reason: {reason}")


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangerR0ConsequenceClosureError(
            "naive_timestamp",
            "evidence closure timestamps must be timezone-aware",
        )
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


__all__ = [
    "RangerR0ConsequenceClosureBundle",
    "RangerR0ConsequenceClosureError",
    "RangerR0ConsequenceClosureVerification",
    "build_agent365_r0_consequence_closure",
    "complete_sharepoint_mission_from_closure",
    "sharepoint_completion_patch_body",
    "verify_agent365_r0_consequence_closure",
]
