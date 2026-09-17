"""Map retained ETS OTLP trace observations into bounded Agent 365 R0 propositions.

The generic Gateway OTLP decoder is product-neutral and already preserves bounded span metadata.
This adapter performs only an explicitly configured semantic projection. It never guesses Agent
365 meaning from span names, timestamp proximity, or undocumented attribute conventions.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.capture.otlp import OtlpObservationV1
from ets.demos.agent365_r0_correlation import (
    Agent365RetainedSourceRefV1,
    Agent365RuntimeObservationV1,
    Agent365ToolObservationV1,
    Agent365ToolStatus,
)


class Agent365R0OtlpMappingError(ValueError):
    """Raised when a retained OTLP span cannot enter the bounded Agent 365 mapping contract."""


class Agent365OtlpAttributeProfileV1(BaseModel):
    """Explicit tenant/exporter attribute contract; no Microsoft keys are silently invented."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.otel-attribute-profile.v1"] = (
        "ets.demo.agent365-r0.otel-attribute-profile.v1"
    )
    profile_id: str = Field(min_length=1, max_length=256)
    package_id_key: str | None = Field(default=None, min_length=1, max_length=256)
    agent_identity_id_key: str | None = Field(default=None, min_length=1, max_length=256)
    invocation_id_key: str = Field(min_length=1, max_length=256)
    session_id_key: str | None = Field(default=None, min_length=1, max_length=256)
    mission_id_key: str | None = Field(default=None, min_length=1, max_length=256)
    tool_call_id_key: str = Field(min_length=1, max_length=256)
    tool_name_key: str = Field(min_length=1, max_length=256)
    tool_status_key: str = Field(min_length=1, max_length=256)
    sharepoint_item_id_key: str | None = Field(default=None, min_length=1, max_length=256)
    sharepoint_authorization_material_sha256_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
    )
    runtime_attribute_locations: tuple[Literal["record", "resource"], ...] = (
        "record",
        "resource",
    )
    tool_attribute_locations: tuple[Literal["record", "resource"], ...] = (
        "record",
        "resource",
    )

    @model_validator(mode="after")
    def require_unique_locations(self) -> Agent365OtlpAttributeProfileV1:
        if len(set(self.runtime_attribute_locations)) != len(self.runtime_attribute_locations):
            raise ValueError("runtime_attribute_locations must not contain duplicates")
        if len(set(self.tool_attribute_locations)) != len(self.tool_attribute_locations):
            raise ValueError("tool_attribute_locations must not contain duplicates")
        return self


class Agent365OtlpProjectionV1(BaseModel):
    """Typed result of mapping one or more retained OTLP spans."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.otel-projection.v1"] = (
        "ets.demo.agent365-r0.otel-projection.v1"
    )
    profile_id: str
    runtime_observations: tuple[Agent365RuntimeObservationV1, ...]
    tool_observations: tuple[Agent365ToolObservationV1, ...]
    source_record_ordinals: tuple[int, ...]
    claim_boundary: Literal["configured_semantic_projection_of_retained_otlp_only"] = (
        "configured_semantic_projection_of_retained_otlp_only"
    )


class _SpanCore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    trace_id: str = Field(min_length=1, max_length=256)
    span_id: str = Field(min_length=1, max_length=256)
    parent_span_id: str | None = Field(default=None, min_length=1, max_length=256)


def runtime_observation_from_otlp(
    observation: OtlpObservationV1,
    source: Agent365RetainedSourceRefV1,
    profile: Agent365OtlpAttributeProfileV1,
) -> Agent365RuntimeObservationV1:
    """Project one already-retained OTLP trace span into an Agent 365 runtime proposition."""

    _require_trace_observation(observation)
    if source.source_family != "agent365.runtime.otel":
        raise Agent365R0OtlpMappingError(
            "runtime projection requires an agent365.runtime.otel retained source reference"
        )
    span = _span_core(observation)
    attributes = _attributes_for_locations(observation, profile.runtime_attribute_locations)
    invocation_id = _required_attribute(attributes, profile.invocation_id_key)
    package_id = _optional_attribute(attributes, profile.package_id_key)
    agent_identity_id = _optional_attribute(attributes, profile.agent_identity_id_key)
    session_id = _optional_attribute(attributes, profile.session_id_key)
    mission_id = _optional_attribute(attributes, profile.mission_id_key)

    return Agent365RuntimeObservationV1(
        observation_id=_observation_id("runtime", source, observation),
        source=source,
        package_id=package_id,
        agent_identity_id=agent_identity_id,
        invocation_id=invocation_id,
        session_id=session_id,
        trace_id=span.trace_id,
        span_id=span.span_id,
        parent_span_id=span.parent_span_id,
        application_mission_id=mission_id,
    )


def tool_observation_from_otlp(
    observation: OtlpObservationV1,
    source: Agent365RetainedSourceRefV1,
    profile: Agent365OtlpAttributeProfileV1,
) -> Agent365ToolObservationV1:
    """Project one already-retained OTLP trace span into an Agent 365 tool proposition."""

    _require_trace_observation(observation)
    if source.source_family != "agent365.tool.otel":
        raise Agent365R0OtlpMappingError(
            "tool projection requires an agent365.tool.otel retained source reference"
        )
    span = _span_core(observation)
    attributes = _attributes_for_locations(observation, profile.tool_attribute_locations)
    status_text = _required_attribute(attributes, profile.tool_status_key).lower()
    try:
        status = Agent365ToolStatus(status_text)
    except ValueError as exc:
        raise Agent365R0OtlpMappingError(
            "configured Agent 365 tool status is outside the bounded status vocabulary"
        ) from exc

    return Agent365ToolObservationV1(
        observation_id=_observation_id("tool", source, observation),
        source=source,
        package_id=_optional_attribute(attributes, profile.package_id_key),
        agent_identity_id=_optional_attribute(attributes, profile.agent_identity_id_key),
        trace_id=span.trace_id,
        span_id=span.span_id,
        parent_span_id=span.parent_span_id,
        tool_call_id=_required_attribute(attributes, profile.tool_call_id_key),
        tool_name=_required_attribute(attributes, profile.tool_name_key),
        status=status,
        application_mission_id=_optional_attribute(attributes, profile.mission_id_key),
        sharepoint_item_id=_optional_attribute(attributes, profile.sharepoint_item_id_key),
        sharepoint_authorization_material_sha256=_optional_attribute(
            attributes,
            profile.sharepoint_authorization_material_sha256_key,
        ),
    )


def project_agent365_otlp(
    *,
    runtime_spans: tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    tool_spans: tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    profile: Agent365OtlpAttributeProfileV1,
) -> Agent365OtlpProjectionV1:
    """Project explicitly classified retained spans; classification is never inferred here."""

    runtime = tuple(
        runtime_observation_from_otlp(observation, source, profile)
        for observation, source in runtime_spans
    )
    tools = tuple(
        tool_observation_from_otlp(observation, source, profile)
        for observation, source in tool_spans
    )
    ordinals = tuple(
        observation.record_ordinal
        for observation, _ in (*runtime_spans, *tool_spans)
    )
    if len(ordinals) != len(set(ordinals)):
        raise Agent365R0OtlpMappingError(
            "one OTLP record ordinal cannot be projected as more than one Agent 365 proposition"
        )
    return Agent365OtlpProjectionV1(
        profile_id=profile.profile_id,
        runtime_observations=runtime,
        tool_observations=tools,
        source_record_ordinals=ordinals,
    )


def _require_trace_observation(observation: OtlpObservationV1) -> None:
    if observation.signal_class != "traces":
        raise Agent365R0OtlpMappingError("Agent 365 runtime/tool projection requires OTLP traces")


def _span_core(observation: OtlpObservationV1) -> _SpanCore:
    record = observation.record_metadata
    trace_id = _bounded_metadata_string(record.get("trace_id"), "trace_id")
    span_id = _bounded_metadata_string(record.get("span_id"), "span_id")
    parent_value = record.get("parent_span_id")
    parent_span_id = (
        None
        if parent_value is None
        else _bounded_metadata_string(parent_value, "parent_span_id")
    )
    return _SpanCore(trace_id=trace_id, span_id=span_id, parent_span_id=parent_span_id)


def _attributes_for_locations(
    observation: OtlpObservationV1,
    locations: tuple[Literal["record", "resource"], ...],
) -> dict[str, str]:
    merged: dict[str, str] = {}
    for location in locations:
        metadata = (
            observation.record_metadata
            if location == "record"
            else observation.resource_metadata
        )
        attributes = _decode_attributes(metadata.get("attributes"), location=location)
        for key, value in attributes.items():
            existing = merged.get(key)
            if existing is not None and existing != value:
                raise Agent365R0OtlpMappingError(
                    f"Agent 365 OTLP attribute {key!r} conflicts across configured locations"
                )
            merged[key] = value
    return merged


def _decode_attributes(value: Any, *, location: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, list):
        raise Agent365R0OtlpMappingError(
            f"OTLP {location} attributes are not a decoded key/value list"
        )
    decoded: dict[str, str] = {}
    for entry in value:
        if not isinstance(entry, Mapping):
            raise Agent365R0OtlpMappingError("OTLP attribute entry is not a mapping")
        key = entry.get("key")
        wrapped = entry.get("value")
        if not isinstance(key, str) or not key:
            raise Agent365R0OtlpMappingError("OTLP attribute key is not a bounded string")
        if not isinstance(wrapped, Mapping):
            raise Agent365R0OtlpMappingError("OTLP attribute value is not an AnyValue mapping")
        if set(wrapped) != {"string_value"}:
            continue
        raw = wrapped.get("string_value")
        if not isinstance(raw, str) or not raw:
            raise Agent365R0OtlpMappingError("Agent 365 OTLP string attribute is empty")
        if len(raw) > 4096:
            raise Agent365R0OtlpMappingError("Agent 365 OTLP string attribute exceeds 4096 chars")
        previous = decoded.get(key)
        if previous is not None and previous != raw:
            raise Agent365R0OtlpMappingError(
                f"OTLP attribute {key!r} appears more than once with conflicting values"
            )
        decoded[key] = raw
    return decoded


def _required_attribute(attributes: Mapping[str, str], key: str) -> str:
    value = attributes.get(key)
    if value is None:
        raise Agent365R0OtlpMappingError(
            f"required configured Agent 365 OTLP attribute {key!r} is absent"
        )
    return value


def _optional_attribute(attributes: Mapping[str, str], key: str | None) -> str | None:
    if key is None:
        return None
    return attributes.get(key)


def _bounded_metadata_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 256:
        raise Agent365R0OtlpMappingError(
            f"OTLP span {field_name} must be a bounded non-empty string"
        )
    return value


def _observation_id(
    kind: Literal["runtime", "tool"],
    source: Agent365RetainedSourceRefV1,
    observation: OtlpObservationV1,
) -> str:
    return (
        f"agent365-otel:{kind}:{source.source_envelope_sha256}:"
        f"{observation.record_ordinal}"
    )


__all__ = [
    "Agent365OtlpAttributeProfileV1",
    "Agent365OtlpProjectionV1",
    "Agent365R0OtlpMappingError",
    "project_agent365_otlp",
    "runtime_observation_from_otlp",
    "tool_observation_from_otlp",
]
