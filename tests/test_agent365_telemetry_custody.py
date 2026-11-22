from __future__ import annotations

import pytest
from pydantic import ValidationError

from ets.demos.agent365_telemetry_custody import (
    Agent365AttributeSchemaV1,
    Agent365CustodyDestinationV1,
    Agent365DeliveryObservationV1,
    Agent365DistroPinV1,
    Agent365IdentifierSetV1,
    Agent365PrivacyProfileV1,
    Agent365TelemetryCustodyProfileV1,
    assess_agent365_delivery,
)


def _attributes() -> Agent365AttributeSchemaV1:
    return Agent365AttributeSchemaV1(
        blueprint_id_key="agent.blueprint.id",
        instance_app_id_key="agent.instance.app.id",
        object_id_key="agent.object.id",
        package_id_key="agent.package.id",
        case_id_key="ets.case.id",
        mission_id_key="ets.mission.id",
        run_id_key="agent.run.id",
        conversation_id_key="agent.conversation.id",
        trace_id_field="trace_id",
        span_id_field="span_id",
    )


def _profile() -> Agent365TelemetryCustodyProfileV1:
    attributes = _attributes()
    return Agent365TelemetryCustodyProfileV1(
        profile_id="controlled-tenant-agent365-v1",
        distro=Agent365DistroPinV1(
            package_name="Microsoft.OpenTelemetry.Distro",
            package_version="1.9.0",
            schema_url="https://schemas.example.test/agent365/1.0.0",
            schema_version="1.0.0",
        ),
        attributes=attributes,
        privacy=Agent365PrivacyProfileV1(
            attribute_allowlist=tuple(attributes.model_dump().values()),
            redaction_profile_id="agent365-minimization-v1",
            data_classification="confidential",
        ),
        custody_destinations=(
            Agent365CustodyDestinationV1(
                kind="microsoft_observability",
                destination_id="tenant-app-insights",
                retention_days=30,
                encryption_profile_id="microsoft-managed-at-rest",
                access_policy_id="observability-readers-v1",
            ),
            Agent365CustodyDestinationV1(
                kind="ets_evidence_store",
                destination_id="ets-immutable-capture",
                retention_days=365,
                encryption_profile_id="ets-evidence-kms-v1",
                access_policy_id="ets-evidence-readers-v1",
            ),
        ),
    )


def _identifiers() -> Agent365IdentifierSetV1:
    return Agent365IdentifierSetV1(
        blueprint_id="blueprint-1",
        instance_app_id="app-1",
        object_id="object-1",
        package_id="package-1",
        case_id="case-1",
        mission_id="mission-1",
        run_id="run-1",
        conversation_id="conversation-1",
        trace_id="trace-1",
        span_id="span-1",
    )


def test_complete_independent_receipts_are_reported_without_overclaim() -> None:
    assessment = assess_agent365_delivery(
        _profile(),
        _identifiers(),
        Agent365DeliveryObservationV1(
            microsoft_ingestion_receipt_ref="azure://query/1",
            microsoft_ingestion_receipt_sha256="a" * 64,
            application_exporter_receipt_ref="ets://exporter/1",
            application_exporter_receipt_sha256="b" * 64,
            ets_custody_record_ref="ets://capture/1",
            ets_custody_record_sha256="c" * 64,
        ),
    )

    assert assessment.microsoft_ingestion_observed is True
    assert assessment.application_exporter_receipt_observed is True
    assert assessment.ets_custody_observed is True
    assert assessment.delivery_complete is True
    assert "not_semantic_correctness" in assessment.claim_boundary


def test_exporter_receipt_does_not_imply_microsoft_ingestion() -> None:
    assessment = assess_agent365_delivery(
        _profile(),
        _identifiers(),
        Agent365DeliveryObservationV1(
            application_exporter_receipt_ref="ets://exporter/1",
            application_exporter_receipt_sha256="b" * 64,
            ets_custody_record_ref="ets://capture/1",
            ets_custody_record_sha256="c" * 64,
        ),
    )

    assert assessment.application_exporter_receipt_observed is True
    assert assessment.microsoft_ingestion_observed is False
    assert assessment.delivery_complete is False


def test_profile_rejects_floating_distro_version() -> None:
    with pytest.raises(ValidationError, match="package_version"):
        Agent365DistroPinV1(
            package_name="Microsoft.OpenTelemetry.Distro",
            package_version="latest",
            schema_url="https://schemas.example.test/agent365/1.0.0",
            schema_version="1.0.0",
        )


def test_identity_and_correlation_keys_must_be_distinct() -> None:
    values = _attributes().model_dump()
    values["object_id_key"] = values["instance_app_id_key"]
    with pytest.raises(ValidationError, match="distinct keys"):
        Agent365AttributeSchemaV1.model_validate(values)


def test_identifier_values_cannot_equate_conversation_and_trace() -> None:
    values = _identifiers().model_dump()
    values["trace_id"] = values["conversation_id"]
    with pytest.raises(ValidationError, match="must not be equated"):
        Agent365IdentifierSetV1.model_validate(values)


def test_profile_requires_both_distinct_custody_destinations() -> None:
    profile = _profile()
    duplicate = profile.custody_destinations[0].model_copy(
        update={"destination_id": "another-microsoft-store"}
    )
    with pytest.raises(ValidationError, match="Microsoft and ETS"):
        Agent365TelemetryCustodyProfileV1.model_validate(
            {
                **profile.model_dump(),
                "custody_destinations": (profile.custody_destinations[0], duplicate),
            }
        )


def test_privacy_profile_requires_all_prohibited_content_classes() -> None:
    with pytest.raises(ValidationError, match="all raw content"):
        Agent365PrivacyProfileV1(
            attribute_allowlist=("trace_id",),
            prohibited_content=("access_token",),
            redaction_profile_id="redaction-v1",
            data_classification="confidential",
        )


def test_partial_receipt_pair_is_rejected() -> None:
    with pytest.raises(ValidationError, match="reference and SHA-256"):
        Agent365DeliveryObservationV1(
            microsoft_ingestion_receipt_ref="azure://query/1",
        )


def test_empty_receipt_reference_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 1 character"):
        Agent365DeliveryObservationV1(
            application_exporter_receipt_ref="",
            application_exporter_receipt_sha256="a" * 64,
        )
