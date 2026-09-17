"""Bound Agent 365 identity/runtime/tool observations to the frozen Ranger R0 mission.

This layer does not treat Agent 365 telemetry as proof of SharePoint state or physical outcome.
It joins retained Microsoft-attributable observations to the SharePoint mission read-back from
#848 using the immutable ``mission_id`` plus explicit source-native relationships.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.demos.agent365_r0_sharepoint_live import SharePointMissionLiveObservationV1


class Agent365R0CorrelationError(ValueError):
    """Raised when Microsoft observations cannot be safely correlated to one R0 mission."""


class Agent365ApiMaturity(StrEnum):
    STABLE = "stable"
    DOCUMENTED_PREVIEW = "documented_preview"
    BETA = "beta"
    UNKNOWN = "unknown"


class Agent365ToolStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class StrictCorrelationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _ObservationWithId(Protocol):
    observation_id: str


class Agent365RetainedSourceRefV1(StrictCorrelationModel):
    """Commitment to already-retained Microsoft source material.

    Raw payloads remain in the source custody store. This object is safe to carry in the mission
    graph because it contains only identifiers, hashes, timestamps, and retention references.
    """

    schema_version: Literal["ets.demo.agent365-r0.retained-source-ref.v1"] = (
        "ets.demo.agent365-r0.retained-source-ref.v1"
    )
    source: Literal["microsoft.agent365"] = "microsoft.agent365"
    tenant_id: str = Field(min_length=36, max_length=36)
    source_family: Literal[
        "agent365.catalog",
        "agent365.runtime.otel",
        "agent365.tool.otel",
    ]
    api_maturity: Agent365ApiMaturity
    acquisition_time: datetime
    microsoft_event_time: datetime | None = None
    payload_ref: str = Field(min_length=1, max_length=4096)
    raw_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_envelope_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    collector_identity: str = Field(min_length=1, max_length=256)
    collector_version: str = Field(min_length=1, max_length=128)

    @field_validator("acquisition_time", "microsoft_event_time")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Agent 365 source timestamps must be timezone-aware")
        return value.astimezone(UTC)


class Agent365IdentityObservationV1(StrictCorrelationModel):
    """Identity/configuration proposition, intentionally separate from runtime execution."""

    schema_version: Literal["ets.demo.agent365-r0.identity-observation.v1"] = (
        "ets.demo.agent365-r0.identity-observation.v1"
    )
    observation_id: str = Field(min_length=1, max_length=512)
    source: Agent365RetainedSourceRefV1
    package_id: str | None = Field(default=None, min_length=1, max_length=512)
    agent_identity_id: str | None = Field(default=None, min_length=1, max_length=512)
    blueprint_id: str | None = Field(default=None, min_length=1, max_length=512)
    claim_boundary: Literal["agent_identity_context_not_runtime_or_physical_result"] = (
        "agent_identity_context_not_runtime_or_physical_result"
    )

    @model_validator(mode="after")
    def require_identity(self) -> Agent365IdentityObservationV1:
        if self.package_id is None and self.agent_identity_id is None:
            raise ValueError("identity observation requires package_id or agent_identity_id")
        return self


class Agent365RuntimeObservationV1(StrictCorrelationModel):
    """Invocation/session/span proposition from retained Agent 365 runtime telemetry."""

    schema_version: Literal["ets.demo.agent365-r0.runtime-observation.v1"] = (
        "ets.demo.agent365-r0.runtime-observation.v1"
    )
    observation_id: str = Field(min_length=1, max_length=512)
    source: Agent365RetainedSourceRefV1
    package_id: str | None = Field(default=None, min_length=1, max_length=512)
    agent_identity_id: str | None = Field(default=None, min_length=1, max_length=512)
    invocation_id: str = Field(min_length=1, max_length=512)
    session_id: str | None = Field(default=None, min_length=1, max_length=512)
    trace_id: str = Field(min_length=1, max_length=256)
    span_id: str = Field(min_length=1, max_length=256)
    parent_span_id: str | None = Field(default=None, min_length=1, max_length=256)
    application_mission_id: str | None = Field(default=None, min_length=36, max_length=36)
    claim_boundary: Literal["agent_runtime_observation_not_resource_or_physical_result"] = (
        "agent_runtime_observation_not_resource_or_physical_result"
    )


class Agent365ToolObservationV1(StrictCorrelationModel):
    """Tool-execution proposition distinct from the SharePoint resource read-back."""

    schema_version: Literal["ets.demo.agent365-r0.tool-observation.v1"] = (
        "ets.demo.agent365-r0.tool-observation.v1"
    )
    observation_id: str = Field(min_length=1, max_length=512)
    source: Agent365RetainedSourceRefV1
    package_id: str | None = Field(default=None, min_length=1, max_length=512)
    agent_identity_id: str | None = Field(default=None, min_length=1, max_length=512)
    trace_id: str = Field(min_length=1, max_length=256)
    span_id: str = Field(min_length=1, max_length=256)
    parent_span_id: str | None = Field(default=None, min_length=1, max_length=256)
    tool_call_id: str = Field(min_length=1, max_length=512)
    tool_name: str = Field(min_length=1, max_length=512)
    status: Agent365ToolStatus
    application_mission_id: str | None = Field(default=None, min_length=36, max_length=36)
    sharepoint_item_id: str | None = Field(default=None, min_length=1, max_length=500)
    sharepoint_authorization_material_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    claim_boundary: Literal["tool_execution_status_not_sharepoint_state_or_physical_result"] = (
        "tool_execution_status_not_sharepoint_state_or_physical_result"
    )


class SharePointMissionCorrelationAnchorV1(StrictCorrelationModel):
    """Minimal source-attributable SharePoint state required for Agent 365 correlation."""

    schema_version: Literal["ets.demo.agent365-r0.sharepoint-correlation-anchor.v1"] = (
        "ets.demo.agent365-r0.sharepoint-correlation-anchor.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    tenant_id: str = Field(min_length=36, max_length=36)
    item_id: str = Field(min_length=1, max_length=500)
    authorization_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_payload_ref: str = Field(min_length=1, max_length=4096)
    acquired_at: datetime

    @field_validator("acquired_at")
    @classmethod
    def normalize_acquired_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("SharePoint correlation anchor time must be timezone-aware")
        return value.astimezone(UTC)


class Agent365R0CorrelationBundleV1(StrictCorrelationModel):
    """Mission-scoped Microsoft evidence references without raw sensitive payload material."""

    schema_version: Literal["ets.demo.agent365-r0.correlation-bundle.v1"] = (
        "ets.demo.agent365-r0.correlation-bundle.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    tenant_id: str = Field(min_length=36, max_length=36)
    sharepoint_item_id: str = Field(min_length=1, max_length=500)
    sharepoint_authorization_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sharepoint_source_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_observations: tuple[Agent365IdentityObservationV1, ...]
    runtime_observations: tuple[Agent365RuntimeObservationV1, ...]
    tool_observations: tuple[Agent365ToolObservationV1, ...]
    correlation_bases: tuple[
        Literal["application_mission_id", "sharepoint_item_id", "trace_parentage"], ...
    ]
    tool_execution_success_proves_sharepoint_state: Literal[False] = False
    agent365_observation_proves_physical_result: Literal[False] = False
    claim_boundary: Literal[
        "agent365_identity_runtime_tool_observations_correlated_to_sharepoint_mission_only"
    ] = "agent365_identity_runtime_tool_observations_correlated_to_sharepoint_mission_only"


def sharepoint_correlation_anchor(
    observation: SharePointMissionLiveObservationV1,
) -> SharePointMissionCorrelationAnchorV1:
    """Derive the correlation anchor from the retained live SharePoint observation."""

    return SharePointMissionCorrelationAnchorV1(
        mission_id=observation.mission.mission_id,
        tenant_id=observation.source.tenant_id,
        item_id=observation.source_item_id,
        authorization_material_sha256=observation.authorization_material_sha256,
        source_payload_sha256=observation.source.raw_payload_sha256,
        source_payload_ref=observation.source.payload_ref,
        acquired_at=observation.source.acquired_at,
    )


def correlate_agent365_to_r0_mission(
    anchor: SharePointMissionCorrelationAnchorV1,
    *,
    identities: tuple[Agent365IdentityObservationV1, ...],
    runtime: tuple[Agent365RuntimeObservationV1, ...],
    tools: tuple[Agent365ToolObservationV1, ...],
) -> Agent365R0CorrelationBundleV1:
    """Fail closed unless one bounded Microsoft observation graph resolves to ``mission_id``.

    Direct ``application_mission_id`` correlation is preferred. A tool observation may instead
    bind deterministically to the exact SharePoint item observed by #848. Runtime observations
    without a mission attribute may then join through the same trace and explicit parent span.
    Identity observations are context only and join by package/agent identity referenced by the
    bound runtime or tool observations.
    """

    identities = _dedupe_observations(identities)
    runtime = _dedupe_observations(runtime)
    tools = _dedupe_observations(tools)
    _require_tenant(anchor.tenant_id, identities, runtime, tools)

    direct_basis = False
    item_basis = False
    bound_tools: list[Agent365ToolObservationV1] = []
    for tool in tools:
        if tool.application_mission_id is not None:
            if tool.application_mission_id != anchor.mission_id:
                raise Agent365R0CorrelationError(
                    "Agent 365 tool observation carries a different application mission_id"
                )
            direct_basis = True
        elif tool.sharepoint_item_id == anchor.item_id:
            item_basis = True
        else:
            continue

        if tool.sharepoint_item_id is not None and tool.sharepoint_item_id != anchor.item_id:
            raise Agent365R0CorrelationError(
                "mission-bound Agent 365 tool observation targets another SharePoint item"
            )
        if (
            tool.sharepoint_authorization_material_sha256 is not None
            and tool.sharepoint_authorization_material_sha256
            != anchor.authorization_material_sha256
        ):
            raise Agent365R0CorrelationError(
                "Agent 365 tool observation disagrees with live SharePoint authorization state"
            )
        bound_tools.append(tool)

    if not bound_tools:
        raise Agent365R0CorrelationError(
            "no Agent 365 tool observation correlates to the SharePoint mission"
        )

    bound_trace_ids = {tool.trace_id for tool in bound_tools}
    bound_runtime: list[Agent365RuntimeObservationV1] = []
    trace_basis = False
    for item in runtime:
        if item.application_mission_id is not None:
            if item.application_mission_id != anchor.mission_id:
                if item.trace_id in bound_trace_ids:
                    raise Agent365R0CorrelationError(
                        "cross-mission Agent 365 runtime observation contaminates a bound trace"
                    )
                continue
            direct_basis = True
            bound_runtime.append(item)
            bound_trace_ids.add(item.trace_id)
            continue
        if item.trace_id in bound_trace_ids:
            bound_runtime.append(item)
            trace_basis = True

    if not bound_runtime:
        raise Agent365R0CorrelationError(
            "no Agent 365 runtime observation correlates to the mission tool execution"
        )

    runtime_span_ids = {item.span_id for item in bound_runtime}
    for tool in bound_tools:
        if tool.parent_span_id is not None and tool.parent_span_id not in runtime_span_ids:
            raise Agent365R0CorrelationError(
                "mission tool observation parent_span_id is absent from bound runtime evidence"
            )

    referenced_packages = {
        value
        for value in [
            *(item.package_id for item in bound_runtime),
            *(item.package_id for item in bound_tools),
        ]
        if value is not None
    }
    referenced_agents = {
        value
        for value in [
            *(item.agent_identity_id for item in bound_runtime),
            *(item.agent_identity_id for item in bound_tools),
        ]
        if value is not None
    }
    bound_identities = tuple(
        item
        for item in identities
        if item.package_id in referenced_packages or item.agent_identity_id in referenced_agents
    )
    if not bound_identities:
        raise Agent365R0CorrelationError(
            "no Agent 365 identity observation matches the mission runtime/tool participants"
        )

    bases: list[
        Literal["application_mission_id", "sharepoint_item_id", "trace_parentage"]
    ] = []
    if direct_basis:
        bases.append("application_mission_id")
    if item_basis:
        bases.append("sharepoint_item_id")
    if trace_basis:
        bases.append("trace_parentage")

    return Agent365R0CorrelationBundleV1(
        mission_id=anchor.mission_id,
        tenant_id=anchor.tenant_id,
        sharepoint_item_id=anchor.item_id,
        sharepoint_authorization_material_sha256=anchor.authorization_material_sha256,
        sharepoint_source_payload_sha256=anchor.source_payload_sha256,
        identity_observations=tuple(sorted(bound_identities, key=lambda item: item.observation_id)),
        runtime_observations=tuple(sorted(bound_runtime, key=lambda item: item.observation_id)),
        tool_observations=tuple(sorted(bound_tools, key=lambda item: item.observation_id)),
        correlation_bases=tuple(bases),
    )


def _require_tenant(
    tenant_id: str,
    identities: tuple[Agent365IdentityObservationV1, ...],
    runtime: tuple[Agent365RuntimeObservationV1, ...],
    tools: tuple[Agent365ToolObservationV1, ...],
) -> None:
    for observation in identities:
        if observation.source.tenant_id != tenant_id:
            raise Agent365R0CorrelationError(
                "Agent 365 identity observation tenant differs from the SharePoint mission tenant"
            )
    for observation in runtime:
        if observation.source.tenant_id != tenant_id:
            raise Agent365R0CorrelationError(
                "Agent 365 runtime observation tenant differs from the SharePoint mission tenant"
            )
    for observation in tools:
        if observation.source.tenant_id != tenant_id:
            raise Agent365R0CorrelationError(
                "Agent 365 tool observation tenant differs from the SharePoint mission tenant"
            )


def _dedupe_observations[T: _ObservationWithId](items: tuple[T, ...]) -> tuple[T, ...]:
    retained: dict[str, T] = {}
    for item in items:
        observation_id = item.observation_id
        previous = retained.get(observation_id)
        if previous is not None and previous != item:
            raise Agent365R0CorrelationError(
                "duplicate Agent 365 observation_id contains conflicting evidence"
            )
        retained[observation_id] = item
    return tuple(retained.values())


__all__ = [
    "Agent365ApiMaturity",
    "Agent365IdentityObservationV1",
    "Agent365R0CorrelationBundleV1",
    "Agent365R0CorrelationError",
    "Agent365RetainedSourceRefV1",
    "Agent365RuntimeObservationV1",
    "Agent365ToolObservationV1",
    "Agent365ToolStatus",
    "SharePointMissionCorrelationAnchorV1",
    "correlate_agent365_to_r0_mission",
    "sharepoint_correlation_anchor",
]
