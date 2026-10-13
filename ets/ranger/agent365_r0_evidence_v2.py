"""Evidence Object v2 mission binding for the frozen Agent 365 + Ranger R0 demo.

Step 4 intentionally preserved the existing Ranger Evidence Object v1 projection.
This module performs the additive v2 promotion required by the frozen P0 mission
contract.  It never rewrites the v1 object: the v2 identity binds the historical
v1 object and Ranger Decision Event by SHA-256 commitment while carrying the
canonical mission context binding and query-friendly ``lantern.demo`` extension.

Proof material remains outside the Evidence Object v2 identity preimage.  The
verifier therefore checks both the v2 identity commitments and the attached v1
proof material instead of treating attachment presence as evidence of truth.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict

from ets.evidence_object import (
    ContractBinding,
    DigestRef,
    EvidenceIdentityV2,
    EvidenceObject,
    EvidenceObjectV2,
    PolicyDescriptorV2,
    ProofMaterialV2,
    identity_hash,
    object_hash,
)
from ets.ranger.agent365_r0_evidence import (
    RangerR0ConsequenceClosureBundle,
    verify_agent365_r0_consequence_closure,
)

MISSION_CONTRACT_ID: Final = "lantern.demo.agent365-r0.mission.v1"
SCENARIO_ID: Final = "agent365-r0-forward-stop-v1"
EVIDENCE_OBJECT_V1_CONTRACT_ID: Final = (
    "https://lanternprotocol.org/schemas/ets/evidence-object/v1"
)
RANGER_DECISION_EVENT_CONTRACT_ID: Final = "ranger.decision-event.v0.1"
V1_PROOF_PROFILE: Final = "ets.evidence-object.canonical-json.sha256.v1"


class RangerR0EvidenceV2Error(ValueError):
    """Raised when the P0 v2 mission binding cannot be established safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class RangerR0EvidenceV2Bundle:
    """Additive Evidence Object v2 projection plus its authoritative Step 4 source."""

    mission_id: str
    evidence_object: EvidenceObjectV2
    evidence_object_identity_hash: str
    source_closure: RangerR0ConsequenceClosureBundle


class RangerR0EvidenceV2Verification(BaseModel):
    """Separated verification findings for the P0 v2 mission projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.evidence-v2-verification.v1"] = (
        "ets.demo.agent365-r0.evidence-v2-verification.v1"
    )
    valid: bool
    mission_id: str
    evidence_object_identity_hash: str
    mission_context_binding_valid: bool
    mission_extension_valid: bool
    v1_provenance_binding_valid: bool
    ranger_event_binding_valid: bool
    attached_v1_proof_valid: bool
    source_closure_valid: bool
    physical_result_supported: bool
    truth_claim_supported: bool = False
    claim_boundary: str = (
        "v2_identity_commits_to_mission_context_v1_evidence_and_ranger_event_but_does_not_"
        "convert_integrity_or_correlation_into_unbounded_physical_truth"
    )


def promote_agent365_r0_closure_to_v2(
    closure: RangerR0ConsequenceClosureBundle,
) -> RangerR0EvidenceV2Bundle:
    """Create the normative P0 Evidence Object v2 mission binding.

    The source v1 Evidence Object remains unchanged and is carried as proof material.
    Its canonical v1 hash and the Ranger Decision Event digest are committed into the
    v2 identity through typed bindings.
    """

    source_verification = verify_agent365_r0_consequence_closure(closure)
    if not source_verification.valid or not source_verification.physical_result_supported:
        raise RangerR0EvidenceV2Error(
            "source_closure_not_verified",
            "Step 4 closure must verify before Evidence Object v2 promotion",
        )

    source_hash = object_hash(closure.evidence_object)
    if closure.evidence_object_hash != source_hash:
        raise RangerR0EvidenceV2Error(
            "source_v1_hash_mismatch",
            "Step 4 bundle hash does not match the retained Evidence Object v1",
        )

    event_id = _required_string(closure.decision_event, "event_id")
    event_digest = _required_sha256_prefixed(
        _required_string(closure.decision_event, "event_digest"),
        code="invalid_ranger_event_digest",
    )
    decision = _required_mapping(closure.decision_event, "decision")
    policy_id = _required_string(decision, "policy_id")

    evidence_v2 = EvidenceObjectV2(
        identity=EvidenceIdentityV2(
            object_id=f"{closure.evidence_object.identity.evidence_id}:v2",
            namespace=closure.evidence_object.identity.namespace,
            object_type="agent365-r0-cyber-physical-consequence-closure",
            version=1,
        ),
        created_at=closure.evidence_object.created_at,
        bindings=(
            ContractBinding(
                binding_type="context",
                contract_id=MISSION_CONTRACT_ID,
                subject_ref=f"mission:{closure.mission_id}",
            ),
            ContractBinding(
                binding_type="provenance",
                contract_id=EVIDENCE_OBJECT_V1_CONTRACT_ID,
                subject_ref=(
                    f"evidence-object-v1:{closure.evidence_object.identity.evidence_id}"
                ),
                commitment=DigestRef(digest=source_hash),
            ),
            ContractBinding(
                binding_type="event",
                contract_id=RANGER_DECISION_EVENT_CONTRACT_ID,
                subject_ref=f"ranger-event:{event_id}",
                commitment=DigestRef(digest=event_digest.removeprefix("sha256:")),
            ),
        ),
        policies=(
            PolicyDescriptorV2(
                policy_ref=policy_id,
                purpose="frozen Agent 365 R0 bounded forward/stop authorization policy",
            ),
        ),
        extensions={
            "lantern.demo": {
                "mission_id": closure.mission_id,
                "scenario_id": SCENARIO_ID,
            },
            "lantern.compatibility": {
                "source_schema_id": closure.evidence_object.schema_id,
                "source_evidence_object_id": closure.evidence_object.identity.evidence_id,
                "source_evidence_object_hash": source_hash,
                "source_evidence_bundle_ref": closure.evidence_bundle_ref,
            },
        },
        proof_material=(
            ProofMaterialV2(
                proof_type="evidence-object-v1",
                profile=V1_PROOF_PROFILE,
                material={
                    "evidence_object": closure.evidence_object.model_dump(
                        mode="json", exclude_none=True
                    )
                },
            ),
        ),
    )

    return RangerR0EvidenceV2Bundle(
        mission_id=closure.mission_id,
        evidence_object=evidence_v2,
        evidence_object_identity_hash=identity_hash(evidence_v2),
        source_closure=closure,
    )


def verify_agent365_r0_evidence_v2(
    bundle: RangerR0EvidenceV2Bundle,
) -> RangerR0EvidenceV2Verification:
    """Verify the v2 mission binding without collapsing integrity into truth."""

    source = bundle.source_closure
    source_verification = verify_agent365_r0_consequence_closure(source)
    if not source_verification.valid:
        raise RangerR0EvidenceV2Error(
            "source_closure_not_verified",
            "retained Step 4 consequence closure no longer verifies",
        )
    if bundle.mission_id != source.mission_id:
        raise RangerR0EvidenceV2Error(
            "bundle_mission_mismatch",
            "v2 bundle mission_id differs from the retained Step 4 closure",
        )

    recomputed_identity_hash = identity_hash(bundle.evidence_object)
    if bundle.evidence_object_identity_hash != recomputed_identity_hash:
        raise RangerR0EvidenceV2Error(
            "v2_identity_hash_mismatch",
            "stored Evidence Object v2 identity hash does not match canonical identity bytes",
        )

    context_bindings = tuple(
        item
        for item in bundle.evidence_object.bindings
        if item.binding_type == "context" and item.contract_id == MISSION_CONTRACT_ID
    )
    if len(context_bindings) != 1:
        raise RangerR0EvidenceV2Error(
            "mission_context_binding_count",
            "Evidence Object v2 must contain exactly one P0 mission context binding",
        )
    if context_bindings[0].subject_ref != f"mission:{bundle.mission_id}":
        raise RangerR0EvidenceV2Error(
            "mission_context_binding_mismatch",
            "Evidence Object v2 context binding does not identify the retained mission",
        )

    demo_extension = bundle.evidence_object.extensions.get("lantern.demo")
    if not isinstance(demo_extension, Mapping):
        raise RangerR0EvidenceV2Error(
            "missing_mission_extension",
            "Evidence Object v2 is missing the lantern.demo query extension",
        )
    if (
        demo_extension.get("mission_id") != bundle.mission_id
        or demo_extension.get("scenario_id") != SCENARIO_ID
    ):
        raise RangerR0EvidenceV2Error(
            "mission_extension_mismatch",
            "lantern.demo extension does not match the frozen P0 mission/scenario",
        )

    source_hash = object_hash(source.evidence_object)
    provenance_bindings = tuple(
        item
        for item in bundle.evidence_object.bindings
        if item.binding_type == "provenance"
        and item.contract_id == EVIDENCE_OBJECT_V1_CONTRACT_ID
    )
    if len(provenance_bindings) != 1:
        raise RangerR0EvidenceV2Error(
            "v1_provenance_binding_count",
            "Evidence Object v2 must contain exactly one v1 provenance binding",
        )
    provenance = provenance_bindings[0]
    if provenance.subject_ref != (
        f"evidence-object-v1:{source.evidence_object.identity.evidence_id}"
    ):
        raise RangerR0EvidenceV2Error(
            "v1_provenance_subject_mismatch",
            "v2 provenance binding points at another Evidence Object v1",
        )
    if provenance.commitment is None or provenance.commitment.digest != source_hash:
        raise RangerR0EvidenceV2Error(
            "v1_provenance_commitment_mismatch",
            "v2 provenance commitment does not match the canonical v1 object hash",
        )

    event_id = _required_string(source.decision_event, "event_id")
    event_digest = _required_sha256_prefixed(
        _required_string(source.decision_event, "event_digest"),
        code="invalid_ranger_event_digest",
    )
    event_bindings = tuple(
        item
        for item in bundle.evidence_object.bindings
        if item.binding_type == "event"
        and item.contract_id == RANGER_DECISION_EVENT_CONTRACT_ID
    )
    if len(event_bindings) != 1:
        raise RangerR0EvidenceV2Error(
            "ranger_event_binding_count",
            "Evidence Object v2 must contain exactly one Ranger Decision Event binding",
        )
    event_binding = event_bindings[0]
    if event_binding.subject_ref != f"ranger-event:{event_id}":
        raise RangerR0EvidenceV2Error(
            "ranger_event_subject_mismatch",
            "v2 event binding identifies another Ranger Decision Event",
        )
    if (
        event_binding.commitment is None
        or event_binding.commitment.digest != event_digest.removeprefix("sha256:")
    ):
        raise RangerR0EvidenceV2Error(
            "ranger_event_commitment_mismatch",
            "v2 event binding does not commit to the retained Ranger Decision Event digest",
        )

    proofs = tuple(
        item
        for item in bundle.evidence_object.proof_material
        if item.proof_type == "evidence-object-v1" and item.profile == V1_PROOF_PROFILE
    )
    if len(proofs) != 1:
        raise RangerR0EvidenceV2Error(
            "v1_proof_material_count",
            "portable P0 v2 object must carry exactly one attached Evidence Object v1 proof",
        )
    raw_attached_v1 = proofs[0].material.get("evidence_object")
    if not isinstance(raw_attached_v1, dict):
        raise RangerR0EvidenceV2Error(
            "invalid_v1_proof_material",
            "attached v1 proof material is not an Evidence Object JSON object",
        )
    try:
        attached_v1 = EvidenceObject.model_validate_json(
            json.dumps(raw_attached_v1, separators=(",", ":"), sort_keys=True)
        )
    except ValueError as exc:
        raise RangerR0EvidenceV2Error(
            "invalid_v1_proof_material",
            "attached v1 proof material does not satisfy the Evidence Object v1 contract",
        ) from exc
    if object_hash(attached_v1) != source_hash:
        raise RangerR0EvidenceV2Error(
            "v1_proof_material_hash_mismatch",
            "attached v1 proof material does not satisfy the v2 provenance commitment",
        )

    compatibility = bundle.evidence_object.extensions.get("lantern.compatibility")
    if not isinstance(compatibility, Mapping):
        raise RangerR0EvidenceV2Error(
            "missing_compatibility_extension",
            "Evidence Object v2 is missing the source-object compatibility extension",
        )
    if (
        compatibility.get("source_schema_id") != source.evidence_object.schema_id
        or compatibility.get("source_evidence_object_id")
        != source.evidence_object.identity.evidence_id
        or compatibility.get("source_evidence_object_hash") != source_hash
        or compatibility.get("source_evidence_bundle_ref") != source.evidence_bundle_ref
    ):
        raise RangerR0EvidenceV2Error(
            "compatibility_extension_mismatch",
            "v2 compatibility extension disagrees with the retained Step 4 source",
        )

    return RangerR0EvidenceV2Verification(
        valid=True,
        mission_id=bundle.mission_id,
        evidence_object_identity_hash=recomputed_identity_hash,
        mission_context_binding_valid=True,
        mission_extension_valid=True,
        v1_provenance_binding_valid=True,
        ranger_event_binding_valid=True,
        attached_v1_proof_valid=True,
        source_closure_valid=True,
        physical_result_supported=source_verification.physical_result_supported,
    )


def _required_mapping(value: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    result = value.get(field)
    if not isinstance(result, Mapping):
        raise RangerR0EvidenceV2Error(
            "missing_required_mapping",
            f"retained Ranger Decision Event field is not an object: {field}",
        )
    return result


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise RangerR0EvidenceV2Error(
            "missing_required_string",
            f"retained Ranger Decision Event field is not a non-empty string: {field}",
        )
    return result


def _required_sha256_prefixed(value: str, *, code: str) -> str:
    if not value.startswith("sha256:") or len(value) != 71:
        raise RangerR0EvidenceV2Error(code, "expected sha256:<64 lowercase hex characters>")
    try:
        bytes.fromhex(value.removeprefix("sha256:"))
    except ValueError as exc:
        raise RangerR0EvidenceV2Error(
            code,
            "expected sha256:<64 lowercase hex characters>",
        ) from exc
    if value != value.lower():
        raise RangerR0EvidenceV2Error(code, "SHA-256 commitment must be lowercase")
    return value


__all__ = [
    "EVIDENCE_OBJECT_V1_CONTRACT_ID",
    "MISSION_CONTRACT_ID",
    "RANGER_DECISION_EVENT_CONTRACT_ID",
    "RangerR0EvidenceV2Bundle",
    "RangerR0EvidenceV2Error",
    "RangerR0EvidenceV2Verification",
    "SCENARIO_ID",
    "promote_agent365_r0_closure_to_v2",
    "verify_agent365_r0_evidence_v2",
]
