"""Mission-indexed reconstruction for the frozen Agent 365 + Ranger R0 demo.

Step 5 binds one verified cyber-physical consequence closure into Evidence Object v2.
This module adds the query boundary needed by the demonstration: a caller supplies a
``mission_id`` and receives the exact retained authorization -> Gateway -> Ranger ->
physical-result -> Evidence Object v1 -> Evidence Object v2 chain.

The index never invents event IDs or derives object identifiers from naming patterns.
Identifiers in the returned manifest are read from retained, verified artifacts.  The
fixed source-artifact IDs below are part of the frozen demonstration contract and are
used only to require that every expected boundary is present.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict

from ets.ranger.agent365_r0_evidence_v2 import (
    SCENARIO_ID,
    RangerR0EvidenceV2Bundle,
    verify_agent365_r0_evidence_v2,
)

AUTHORIZATION_ARTIFACT_ID: Final = "source:sharepoint-authorization"
GATEWAY_ARTIFACT_IDS: Final = (
    "source:gateway-ingress",
    "source:gateway-decision",
    "source:gateway-egress",
    "source:gateway-robot-command",
)
RANGER_ARTIFACT_IDS: Final = (
    "source:ranger-motion-directive",
    "source:ranger-stop-directive",
    "source:ranger-boundary:received",
    "source:ranger-boundary:authorized",
    "source:ranger-boundary:motion_started",
    "source:ranger-boundary:stop_condition_observed",
    "source:ranger-boundary:stop_decided",
    "source:ranger-boundary:stop_actuated",
    "source:ranger-boundary:result_observed",
)
REQUIRED_SOURCE_ARTIFACT_IDS: Final = (
    AUTHORIZATION_ARTIFACT_ID,
    *GATEWAY_ARTIFACT_IDS,
    *RANGER_ARTIFACT_IDS,
)


class RangerR0MissionQueryError(ValueError):
    """Raised when a mission cannot be indexed or reconstructed without ambiguity."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class RangerR0MissionChainManifest(BaseModel):
    """Query-friendly identifiers for one fully retained P0 mission chain."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.mission-chain-manifest.v1"] = (
        "ets.demo.agent365-r0.mission-chain-manifest.v1"
    )
    mission_id: str
    scenario_id: str
    authorization_artifact_id: str
    gateway_artifact_ids: tuple[str, ...]
    ranger_artifact_ids: tuple[str, ...]
    retained_source_artifact_ids: tuple[str, ...]
    decision_event_id: str
    decision_event_digest: str
    evidence_object_v1_id: str
    evidence_object_v1_hash: str
    evidence_object_v2_id: str
    evidence_object_v2_identity_hash: str
    physical_result_supported: bool
    truth_claim_supported: bool = False
    claim_boundary: str = (
        "mission_query_reconstructs_a_verified_retained_chain_but_does_not_convert_"
        "correlation_or_integrity_into_unbounded_physical_truth"
    )


@dataclass(frozen=True, slots=True)
class RangerR0MissionReconstruction:
    """One verified mission chain plus the exact source bytes retained by Step 4."""

    manifest: RangerR0MissionChainManifest
    bundle: RangerR0EvidenceV2Bundle
    source_artifacts: Mapping[str, bytes]


class RangerR0MissionIndex:
    """Fail-closed, in-memory index of verified P0 Evidence Object v2 bundles."""

    def __init__(self, entries: Mapping[str, RangerR0EvidenceV2Bundle]) -> None:
        self._entries = MappingProxyType(dict(entries))

    @classmethod
    def build(cls, bundles: Iterable[RangerR0EvidenceV2Bundle]) -> RangerR0MissionIndex:
        entries: dict[str, RangerR0EvidenceV2Bundle] = {}
        for bundle in bundles:
            verification = verify_agent365_r0_evidence_v2(bundle)
            if not verification.valid:
                raise RangerR0MissionQueryError(
                    "unverified_bundle",
                    "mission index accepts only verified Evidence Object v2 bundles",
                )
            if verification.mission_id != bundle.mission_id:
                raise RangerR0MissionQueryError(
                    "verification_mission_mismatch",
                    "Evidence Object v2 verification returned a different mission_id",
                )
            if bundle.mission_id in entries:
                raise RangerR0MissionQueryError(
                    "duplicate_mission_id",
                    "mission index requires exactly one authoritative chain per mission_id",
                )
            entries[bundle.mission_id] = bundle
        return cls(entries)

    @property
    def mission_ids(self) -> tuple[str, ...]:
        """Return indexed mission identifiers in deterministic order."""

        return tuple(sorted(self._entries))

    def reconstruct(self, mission_id: str) -> RangerR0MissionReconstruction:
        """Return the exact retained chain for ``mission_id`` or fail closed."""

        if not mission_id:
            raise RangerR0MissionQueryError(
                "empty_mission_id",
                "mission_id must be a non-empty string",
            )
        bundle = self._entries.get(mission_id)
        if bundle is None:
            raise RangerR0MissionQueryError(
                "mission_not_found",
                "no verified Agent 365 R0 evidence chain exists for mission_id",
            )

        verification = verify_agent365_r0_evidence_v2(bundle)
        if not verification.valid or verification.mission_id != mission_id:
            raise RangerR0MissionQueryError(
                "mission_reverification_failed",
                "indexed Evidence Object v2 bundle no longer verifies for mission_id",
            )

        closure = bundle.source_closure
        if closure.mission_id != mission_id:
            raise RangerR0MissionQueryError(
                "closure_mission_mismatch",
                "retained Step 4 closure belongs to another mission_id",
            )

        source_artifacts = dict(closure.source_artifacts)
        missing = tuple(
            artifact_id
            for artifact_id in REQUIRED_SOURCE_ARTIFACT_IDS
            if artifact_id not in source_artifacts
        )
        if missing:
            raise RangerR0MissionQueryError(
                "incomplete_source_chain",
                f"retained mission chain is missing required source artifacts: {missing!r}",
            )

        event = closure.decision_event
        if _required_string(event, "mission_id", "decision_event_mission_missing") != mission_id:
            raise RangerR0MissionQueryError(
                "decision_event_mission_mismatch",
                "retained Ranger Decision Event belongs to another mission_id",
            )
        decision_event_id = _required_string(
            event,
            "event_id",
            "decision_event_id_missing",
        )
        decision_event_digest = _required_string(
            event,
            "event_digest",
            "decision_event_digest_missing",
        )

        demo_extension = bundle.evidence_object.extensions.get("lantern.demo")
        if not isinstance(demo_extension, Mapping):
            raise RangerR0MissionQueryError(
                "mission_extension_missing",
                "Evidence Object v2 is missing the lantern.demo extension",
            )
        if demo_extension.get("mission_id") != mission_id:
            raise RangerR0MissionQueryError(
                "mission_extension_mismatch",
                "Evidence Object v2 mission extension identifies another mission",
            )
        scenario_id = demo_extension.get("scenario_id")
        if scenario_id != SCENARIO_ID:
            raise RangerR0MissionQueryError(
                "scenario_extension_mismatch",
                "Evidence Object v2 does not identify the frozen R0 scenario",
            )

        v1_identity = closure.evidence_object.identity
        v2_identity = bundle.evidence_object.identity
        manifest = RangerR0MissionChainManifest(
            mission_id=mission_id,
            scenario_id=SCENARIO_ID,
            authorization_artifact_id=AUTHORIZATION_ARTIFACT_ID,
            gateway_artifact_ids=GATEWAY_ARTIFACT_IDS,
            ranger_artifact_ids=RANGER_ARTIFACT_IDS,
            retained_source_artifact_ids=tuple(sorted(source_artifacts)),
            decision_event_id=decision_event_id,
            decision_event_digest=decision_event_digest,
            evidence_object_v1_id=v1_identity.evidence_id,
            evidence_object_v1_hash=closure.evidence_object_hash,
            evidence_object_v2_id=v2_identity.object_id,
            evidence_object_v2_identity_hash=bundle.evidence_object_identity_hash,
            physical_result_supported=verification.physical_result_supported,
        )
        return RangerR0MissionReconstruction(
            manifest=manifest,
            bundle=bundle,
            source_artifacts=MappingProxyType(source_artifacts),
        )


def build_agent365_r0_mission_index(
    bundles: Iterable[RangerR0EvidenceV2Bundle],
) -> RangerR0MissionIndex:
    """Build a mission-indexed view over already retained P0 Evidence Object v2 bundles."""

    return RangerR0MissionIndex.build(bundles)


def reconstruct_agent365_r0_mission(
    mission_id: str,
    bundles: Iterable[RangerR0EvidenceV2Bundle],
) -> RangerR0MissionReconstruction:
    """Convenience API for one-shot reconstruction by explicit ``mission_id``."""

    return build_agent365_r0_mission_index(bundles).reconstruct(mission_id)


def _required_string(value: Mapping[str, Any], field: str, code: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise RangerR0MissionQueryError(
            code,
            f"retained artifact field is not a non-empty string: {field}",
        )
    return result


__all__ = [
    "AUTHORIZATION_ARTIFACT_ID",
    "GATEWAY_ARTIFACT_IDS",
    "RANGER_ARTIFACT_IDS",
    "REQUIRED_SOURCE_ARTIFACT_IDS",
    "RangerR0MissionChainManifest",
    "RangerR0MissionIndex",
    "RangerR0MissionQueryError",
    "RangerR0MissionReconstruction",
    "build_agent365_r0_mission_index",
    "reconstruct_agent365_r0_mission",
]
