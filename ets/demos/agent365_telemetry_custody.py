"""Fail-closed Agent 365 telemetry semantics and custody contract.

This module validates a declared, version-pinned observability profile.  It does not treat
exporter activity as proof of Microsoft ingestion and does not qualify a live tenant.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictTelemetryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Agent365DistroPinV1(StrictTelemetryModel):
    """Exact Microsoft OpenTelemetry Distro and semantic-schema pin."""

    package_name: str = Field(min_length=1, max_length=256)
    package_version: str = Field(pattern=r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
    schema_url: str = Field(min_length=1, max_length=1024)
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


class Agent365AttributeSchemaV1(StrictTelemetryModel):
    """Exact identity and correlation keys observed for one pinned profile."""

    blueprint_id_key: str = Field(min_length=1, max_length=256)
    instance_app_id_key: str = Field(min_length=1, max_length=256)
    object_id_key: str = Field(min_length=1, max_length=256)
    package_id_key: str = Field(min_length=1, max_length=256)
    case_id_key: str = Field(min_length=1, max_length=256)
    mission_id_key: str = Field(min_length=1, max_length=256)
    run_id_key: str = Field(min_length=1, max_length=256)
    conversation_id_key: str = Field(min_length=1, max_length=256)
    trace_id_field: str = Field(min_length=1, max_length=256)
    span_id_field: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def require_distinct_semantics(self) -> Agent365AttributeSchemaV1:
        values = tuple(self.model_dump().values())
        if len(values) != len(set(values)):
            raise ValueError("identity and correlation semantics must use distinct keys")
        return self


class Agent365PrivacyProfileV1(StrictTelemetryModel):
    """Minimization controls applied before either destination receives telemetry."""

    attribute_allowlist: tuple[str, ...] = Field(min_length=1)
    prohibited_content: tuple[
        Literal[
            "conversation_body",
            "prompt_body",
            "tool_payload_body",
            "access_token",
            "authorization_header",
        ],
        ...,
    ] = (
        "conversation_body",
        "prompt_body",
        "tool_payload_body",
        "access_token",
        "authorization_header",
    )
    redaction_profile_id: str = Field(min_length=1, max_length=256)
    data_classification: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def require_bounded_allowlist(self) -> Agent365PrivacyProfileV1:
        if len(self.attribute_allowlist) != len(set(self.attribute_allowlist)):
            raise ValueError("attribute_allowlist must not contain duplicates")
        required_prohibitions = {
            "conversation_body",
            "prompt_body",
            "tool_payload_body",
            "access_token",
            "authorization_header",
        }
        if set(self.prohibited_content) != required_prohibitions:
            raise ValueError("privacy profile must prohibit all raw content and credential classes")
        return self


class Agent365CustodyDestinationV1(StrictTelemetryModel):
    """One independently governed telemetry destination."""

    kind: Literal["microsoft_observability", "ets_evidence_store"]
    destination_id: str = Field(min_length=1, max_length=256)
    retention_days: int = Field(ge=1, le=3650)
    encryption_profile_id: str = Field(min_length=1, max_length=256)
    access_policy_id: str = Field(min_length=1, max_length=256)


class Agent365TelemetryCustodyProfileV1(StrictTelemetryModel):
    """Versioned OBS-03 contract for semantics, minimization, and dual custody."""

    schema_version: Literal["ets.agent365.telemetry-custody-profile.v1"] = (
        "ets.agent365.telemetry-custody-profile.v1"
    )
    profile_id: str = Field(min_length=1, max_length=256)
    distro: Agent365DistroPinV1
    attributes: Agent365AttributeSchemaV1
    privacy: Agent365PrivacyProfileV1
    custody_destinations: tuple[Agent365CustodyDestinationV1, ...] = Field(
        min_length=2,
        max_length=2,
    )
    claim_boundary: Literal[
        "declared_profile_not_live_ingestion_or_tenant_qualification"
    ] = "declared_profile_not_live_ingestion_or_tenant_qualification"

    @model_validator(mode="after")
    def require_dual_destination_custody(self) -> Agent365TelemetryCustodyProfileV1:
        kinds = {destination.kind for destination in self.custody_destinations}
        if kinds != {"microsoft_observability", "ets_evidence_store"}:
            raise ValueError("custody must declare Microsoft and ETS destinations separately")
        ids = {destination.destination_id for destination in self.custody_destinations}
        if len(ids) != 2:
            raise ValueError("custody destinations must have distinct identities")
        allowed = set(self.privacy.attribute_allowlist)
        required = set(self.attributes.model_dump().values())
        if not required.issubset(allowed):
            raise ValueError("privacy allowlist must include every declared semantic key")
        return self


class Agent365IdentifierSetV1(StrictTelemetryModel):
    """Observed values whose semantic categories must remain independent."""

    blueprint_id: str = Field(min_length=1, max_length=512)
    instance_app_id: str = Field(min_length=1, max_length=512)
    object_id: str = Field(min_length=1, max_length=512)
    package_id: str = Field(min_length=1, max_length=512)
    case_id: str = Field(min_length=1, max_length=512)
    mission_id: str = Field(min_length=1, max_length=512)
    run_id: str = Field(min_length=1, max_length=512)
    conversation_id: str = Field(min_length=1, max_length=512)
    trace_id: str = Field(min_length=1, max_length=512)
    span_id: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def reject_equated_identifiers(self) -> Agent365IdentifierSetV1:
        values = tuple(self.model_dump().values())
        if len(values) != len(set(values)):
            raise ValueError("identity and correlation identifiers must not be equated")
        return self


class Agent365DeliveryObservationV1(StrictTelemetryModel):
    """Independent delivery evidence; neither receipt implies the other."""

    microsoft_ingestion_receipt_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=4096,
    )
    microsoft_ingestion_receipt_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    application_exporter_receipt_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=4096,
    )
    application_exporter_receipt_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    ets_custody_record_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=4096,
    )
    ets_custody_record_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )

    @model_validator(mode="after")
    def require_complete_receipt_pairs(self) -> Agent365DeliveryObservationV1:
        pairs = (
            (self.microsoft_ingestion_receipt_ref, self.microsoft_ingestion_receipt_sha256),
            (self.application_exporter_receipt_ref, self.application_exporter_receipt_sha256),
            (self.ets_custody_record_ref, self.ets_custody_record_sha256),
        )
        if any((reference is None) != (digest is None) for reference, digest in pairs):
            raise ValueError("each delivery receipt requires both a reference and SHA-256")
        return self


class Agent365TelemetryAssessmentV1(StrictTelemetryModel):
    schema_version: Literal["ets.agent365.telemetry-assessment.v1"] = (
        "ets.agent365.telemetry-assessment.v1"
    )
    profile_id: str = Field(min_length=1, max_length=256)
    microsoft_ingestion_observed: bool
    application_exporter_receipt_observed: bool
    ets_custody_observed: bool
    delivery_complete: bool
    claim_boundary: Literal[
        "receipt_assessment_not_semantic_correctness_completeness_or_live_qualification"
    ] = "receipt_assessment_not_semantic_correctness_completeness_or_live_qualification"


def assess_agent365_delivery(
    profile: Agent365TelemetryCustodyProfileV1,
    identifiers: Agent365IdentifierSetV1,
    observation: Agent365DeliveryObservationV1,
) -> Agent365TelemetryAssessmentV1:
    """Assess three receipts independently after profile and identifier validation."""

    del identifiers  # Pydantic construction is the fail-closed identifier validation step.
    microsoft = observation.microsoft_ingestion_receipt_ref is not None
    exporter = observation.application_exporter_receipt_ref is not None
    custody = observation.ets_custody_record_ref is not None
    return Agent365TelemetryAssessmentV1(
        profile_id=profile.profile_id,
        microsoft_ingestion_observed=microsoft,
        application_exporter_receipt_observed=exporter,
        ets_custody_observed=custody,
        delivery_complete=microsoft and exporter and custody,
    )


__all__ = [
    "Agent365AttributeSchemaV1",
    "Agent365CustodyDestinationV1",
    "Agent365DeliveryObservationV1",
    "Agent365DistroPinV1",
    "Agent365IdentifierSetV1",
    "Agent365PrivacyProfileV1",
    "Agent365TelemetryAssessmentV1",
    "Agent365TelemetryCustodyProfileV1",
    "assess_agent365_delivery",
]
