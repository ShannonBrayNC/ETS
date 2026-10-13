"""Controlled-tenant qualification boundary for the Agent 365 R0 OTLP profile.

Synthetic tests may prove that the qualification machinery is ready, but they must never
silently promote an unobserved semantic mapping to a qualified Microsoft profile.  This
module therefore keeps profile readiness distinct from an operator-attested controlled-
tenant capture over already-retained Agent 365 source material.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.capture.otlp import OtlpObservationV1
from ets.demos.agent365_r0_correlation import (
    Agent365IdentityObservationV1,
    Agent365RetainedSourceRefV1,
    SharePointMissionCorrelationAnchorV1,
    correlate_agent365_to_r0_mission,
)
from ets.demos.agent365_r0_otel import (
    Agent365OtlpAttributeProfileV1,
    project_agent365_otlp,
)


class Agent365ProfileQualificationError(ValueError):
    """Raised when a profile cannot be qualified without weakening the evidence boundary."""


class StrictQualificationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Agent365ObservedAttributeKeysV1(StrictQualificationModel):
    """Observed OTLP attribute names only; no attribute values leave retained source custody."""

    schema_version: Literal["ets.demo.agent365-r0.observed-attribute-keys.v1"] = (
        "ets.demo.agent365-r0.observed-attribute-keys.v1"
    )
    runtime_record_keys: tuple[str, ...]
    runtime_resource_keys: tuple[str, ...]
    tool_record_keys: tuple[str, ...]
    tool_resource_keys: tuple[str, ...]
    attribute_values_included: Literal[False] = False


class Agent365ControlledTenantAttestationV1(StrictQualificationModel):
    """Operator assertion that the exact retained sources came from a controlled live run."""

    schema_version: Literal["ets.demo.agent365-r0.controlled-tenant-attestation.v1"] = (
        "ets.demo.agent365-r0.controlled-tenant-attestation.v1"
    )
    run_id: str = Field(min_length=1, max_length=256)
    mission_id: str = Field(min_length=36, max_length=36)
    tenant_id: str = Field(min_length=36, max_length=36)
    profile_id: str = Field(min_length=1, max_length=256)
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_envelope_sha256s: tuple[str, ...] = Field(min_length=1)
    operator_subject: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    controlled_tenant: Literal[True] = True
    raw_sources_retained_before_projection: Literal[True] = True

    @field_validator("captured_at")
    @classmethod
    def normalize_captured_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("controlled-tenant attestation time must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_source_commitments(self) -> Agent365ControlledTenantAttestationV1:
        if len(set(self.source_envelope_sha256s)) != len(self.source_envelope_sha256s):
            raise ValueError("source_envelope_sha256s must not contain duplicates")
        for digest in self.source_envelope_sha256s:
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("source envelope commitments must be lowercase SHA-256 hex")
        return self


class Agent365ProfileQualificationPacketV1(StrictQualificationModel):
    """Deterministic sanitized packet proving profile projection/correlation readiness."""

    schema_version: Literal["ets.demo.agent365-r0.profile-qualification-packet.v1"] = (
        "ets.demo.agent365-r0.profile-qualification-packet.v1"
    )
    qualification_state: Literal["ready_for_live_qualification", "qualified"]
    mission_id: str = Field(min_length=36, max_length=36)
    tenant_id: str = Field(min_length=36, max_length=36)
    profile: Agent365OtlpAttributeProfileV1
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_attribute_keys: Agent365ObservedAttributeKeysV1
    source_envelope_sha256s: tuple[str, ...]
    source_record_refs: tuple[str, ...]
    identity_observation_ids: tuple[str, ...]
    runtime_observation_ids: tuple[str, ...]
    tool_observation_ids: tuple[str, ...]
    sharepoint_item_id: str = Field(min_length=1, max_length=500)
    sharepoint_authorization_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sharepoint_source_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    correlation_bases: tuple[
        Literal["application_mission_id", "sharepoint_item_id", "trace_parentage"], ...
    ]
    live_attestation: Agent365ControlledTenantAttestationV1 | None = None
    raw_otlp_payloads_included: Literal[False] = False
    tool_execution_success_proves_sharepoint_state: Literal[False] = False
    agent365_observation_proves_physical_result: Literal[False] = False
    claim_boundary: Literal[
        "qualified_profile_projects_retained_agent365_sources_and_correlates_to_one_"
        "sharepoint_mission_but_does_not_prove_resource_or_physical_consequence"
    ] = (
        "qualified_profile_projects_retained_agent365_sources_and_correlates_to_one_"
        "sharepoint_mission_but_does_not_prove_resource_or_physical_consequence"
    )


class Agent365ProfileQualificationResultV1(StrictQualificationModel):
    schema_version: Literal["ets.demo.agent365-r0.profile-qualification-result.v1"] = (
        "ets.demo.agent365-r0.profile-qualification-result.v1"
    )
    packet: Agent365ProfileQualificationPacketV1
    packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def qualify_agent365_otlp_profile(
    *,
    profile: Agent365OtlpAttributeProfileV1,
    runtime_spans: tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    tool_spans: tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    identities: tuple[Agent365IdentityObservationV1, ...],
    anchor: SharePointMissionCorrelationAnchorV1,
    live_attestation: Agent365ControlledTenantAttestationV1 | None = None,
) -> Agent365ProfileQualificationResultV1:
    """Project, correlate, and freeze one profile qualification packet.

    Without ``live_attestation`` the result is deliberately limited to
    ``ready_for_live_qualification`` even when every synthetic software assertion succeeds.
    """

    if not runtime_spans:
        raise Agent365ProfileQualificationError("qualification requires at least one runtime span")
    if not tool_spans:
        raise Agent365ProfileQualificationError("qualification requires at least one tool span")
    if not identities:
        raise Agent365ProfileQualificationError(
            "qualification requires retained Agent 365 identity context"
        )
    for identity in identities:
        if identity.source.source_family != "agent365.catalog":
            raise Agent365ProfileQualificationError(
                "qualification identity observations must come from agent365.catalog sources"
            )

    projection = project_agent365_otlp(
        runtime_spans=runtime_spans,
        tool_spans=tool_spans,
        profile=profile,
    )
    correlation = correlate_agent365_to_r0_mission(
        anchor,
        identities=identities,
        runtime=projection.runtime_observations,
        tools=projection.tool_observations,
    )
    profile_sha256 = _canonical_sha256(profile.model_dump(mode="json"))
    source_envelopes = _source_envelope_commitments(runtime_spans, tool_spans, identities)

    state: Literal["ready_for_live_qualification", "qualified"] = (
        "ready_for_live_qualification"
    )
    if live_attestation is not None:
        _validate_live_attestation(
            live_attestation,
            profile=profile,
            profile_sha256=profile_sha256,
            mission_id=anchor.mission_id,
            tenant_id=anchor.tenant_id,
            source_envelopes=source_envelopes,
        )
        state = "qualified"

    packet = Agent365ProfileQualificationPacketV1(
        qualification_state=state,
        mission_id=anchor.mission_id,
        tenant_id=anchor.tenant_id,
        profile=profile,
        profile_sha256=profile_sha256,
        observed_attribute_keys=_observed_attribute_keys(runtime_spans, tool_spans),
        source_envelope_sha256s=source_envelopes,
        source_record_refs=tuple(sorted(projection.source_record_refs)),
        identity_observation_ids=tuple(sorted(item.observation_id for item in identities)),
        runtime_observation_ids=tuple(
            sorted(item.observation_id for item in projection.runtime_observations)
        ),
        tool_observation_ids=tuple(
            sorted(item.observation_id for item in projection.tool_observations)
        ),
        sharepoint_item_id=anchor.item_id,
        sharepoint_authorization_material_sha256=anchor.authorization_material_sha256,
        sharepoint_source_payload_sha256=anchor.source_payload_sha256,
        correlation_bases=correlation.correlation_bases,
        live_attestation=live_attestation,
    )
    return Agent365ProfileQualificationResultV1(
        packet=packet,
        packet_sha256=_canonical_sha256(packet.model_dump(mode="json")),
    )


def _source_envelope_commitments(
    runtime_spans: tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    tool_spans: tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    identities: tuple[Agent365IdentityObservationV1, ...],
) -> tuple[str, ...]:
    values = {
        source.source_envelope_sha256
        for _, source in (*runtime_spans, *tool_spans)
    }
    values.update(identity.source.source_envelope_sha256 for identity in identities)
    return tuple(sorted(values))


def _observed_attribute_keys(
    runtime_spans: tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    tool_spans: tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
) -> Agent365ObservedAttributeKeysV1:
    return Agent365ObservedAttributeKeysV1(
        runtime_record_keys=_keys_for(runtime_spans, location="record"),
        runtime_resource_keys=_keys_for(runtime_spans, location="resource"),
        tool_record_keys=_keys_for(tool_spans, location="record"),
        tool_resource_keys=_keys_for(tool_spans, location="resource"),
    )


def _keys_for(
    spans: tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    *,
    location: Literal["record", "resource"],
) -> tuple[str, ...]:
    keys: set[str] = set()
    for observation, _ in spans:
        metadata = (
            observation.record_metadata if location == "record" else observation.resource_metadata
        )
        keys.update(_string_attribute_keys(metadata))
    return tuple(sorted(keys))


def _string_attribute_keys(metadata: Mapping[str, Any]) -> tuple[str, ...]:
    raw_attributes = metadata.get("attributes")
    if raw_attributes is None:
        return ()
    if not isinstance(raw_attributes, list):
        raise Agent365ProfileQualificationError(
            "OTLP attribute inventory requires decoded key/value lists"
        )
    keys: set[str] = set()
    for entry in raw_attributes:
        if not isinstance(entry, Mapping):
            raise Agent365ProfileQualificationError("OTLP attribute entry is not a mapping")
        key = entry.get("key")
        wrapped = entry.get("value")
        if not isinstance(key, str) or not key:
            raise Agent365ProfileQualificationError("OTLP attribute key is not a non-empty string")
        if not isinstance(wrapped, Mapping):
            raise Agent365ProfileQualificationError(
                "OTLP attribute value is not an AnyValue mapping"
            )
        if set(wrapped) != {"string_value"}:
            continue
        value = wrapped.get("string_value")
        if not isinstance(value, str) or not value:
            raise Agent365ProfileQualificationError("OTLP string attribute is empty")
        keys.add(key)
    return tuple(sorted(keys))


def _validate_live_attestation(
    attestation: Agent365ControlledTenantAttestationV1,
    *,
    profile: Agent365OtlpAttributeProfileV1,
    profile_sha256: str,
    mission_id: str,
    tenant_id: str,
    source_envelopes: tuple[str, ...],
) -> None:
    if attestation.mission_id != mission_id:
        raise Agent365ProfileQualificationError(
            "controlled-tenant attestation belongs to another mission_id"
        )
    if attestation.tenant_id != tenant_id:
        raise Agent365ProfileQualificationError(
            "controlled-tenant attestation belongs to another tenant"
        )
    if attestation.profile_id != profile.profile_id:
        raise Agent365ProfileQualificationError(
            "controlled-tenant attestation names a different profile_id"
        )
    if attestation.profile_sha256 != profile_sha256:
        raise Agent365ProfileQualificationError(
            "controlled-tenant attestation profile digest differs from the active mapping"
        )
    if tuple(sorted(attestation.source_envelope_sha256s)) != source_envelopes:
        raise Agent365ProfileQualificationError(
            "controlled-tenant attestation source commitments differ from projected sources"
        )


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "Agent365ControlledTenantAttestationV1",
    "Agent365ObservedAttributeKeysV1",
    "Agent365ProfileQualificationError",
    "Agent365ProfileQualificationPacketV1",
    "Agent365ProfileQualificationResultV1",
    "qualify_agent365_otlp_profile",
]
