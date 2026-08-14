"""Gateway OTLP observation mapping for the G1F profile."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from ets.capture import (
    CaptureEnvelopeV1,
    CapturePrivacy,
    CaptureSource,
    CaptureTransformation,
    ContentDigest,
    EvidenceReference,
)
from ets.capture.otlp import OtlpObservationV1
from ets.core.api import canonicalize
from ets.gateway.source_registry import SourceRegistration

OTLP_SEMANTIC_MEDIA_TYPE: Final = "application/vnd.ets.otlp-observation+json;version=1"
OTLP_COMMITTED_REPRESENTATION: Final = "ets.gateway.otlp-metadata.v1"
DEFAULT_MAX_OTLP_COMMITTED_BYTES: Final = 12 * 1024


class GatewayOtlpCaptureError(ValueError):
    """Raised when an OTLP observation cannot enter the Gateway capture profile."""


@dataclass(frozen=True, slots=True)
class GatewayOtlpCaptureRequest:
    """One decoded observation supplied by a bounded OTLP transport adapter."""

    observation: OtlpObservationV1
    delivery_id: str
    correlation_id: str | None = None
    received_at_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class GatewayOtlpCapture:
    """Capture envelope plus the minimized representation committed by ETS."""

    envelope: CaptureEnvelopeV1
    committed_representation: bytes


def build_otlp_capture(
    registration: SourceRegistration,
    request: GatewayOtlpCaptureRequest,
    *,
    collector_id: str = "ets-gateway",
    maximum_committed_bytes: int = DEFAULT_MAX_OTLP_COMMITTED_BYTES,
) -> GatewayOtlpCapture:
    """Map one bounded OTLP observation into a server-authorized capture envelope."""

    if not collector_id:
        raise ValueError("collector_id is required")
    if maximum_committed_bytes < 1:
        raise ValueError("maximum_committed_bytes must be positive")
    if not 1 <= len(request.delivery_id) <= 200:
        raise GatewayOtlpCaptureError("delivery_id must be 1-200 characters")
    if request.correlation_id is not None and len(request.correlation_id) > 200:
        raise GatewayOtlpCaptureError("correlation_id exceeds configured limit")

    received_at = request.received_at_utc or datetime.now(UTC)
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise GatewayOtlpCaptureError("received_at_utc must be timezone-aware")
    received_at = received_at.astimezone(UTC)

    observation = request.observation
    resource_metadata, resource_removed = _minimize_mapping(
        observation.resource_metadata,
        registration.redacted_keys,
    )
    scope_metadata, scope_removed = _minimize_mapping(
        observation.scope_metadata,
        registration.redacted_keys,
    )
    record_metadata, record_removed = _minimize_mapping(
        observation.record_metadata,
        registration.redacted_keys,
    )
    redacted_count = resource_removed + scope_removed + record_removed

    representation = {
        "schema": OTLP_COMMITTED_REPRESENTATION,
        "signal_class": observation.signal_class,
        "record_ordinal": observation.record_ordinal,
        "source_timestamp_utc": _format_utc(observation.source_timestamp_utc),
        "decoder_profile": observation.decoder_profile,
        "transformation_profile": observation.transformation_profile,
        "resource_metadata": resource_metadata,
        "scope_metadata": scope_metadata,
        "record_metadata": record_metadata,
    }
    committed = canonicalize(representation)
    if len(committed) > maximum_committed_bytes:
        raise GatewayOtlpCaptureError("OTLP committed representation exceeds configured limit")

    content_hash = hashlib.sha256(committed).hexdigest()
    idempotency_key = f"otlp:{request.delivery_id}:{observation.record_ordinal}"
    capture_identity = hashlib.sha256(
        canonicalize(
            [
                "ets.gateway.otlp.capture-id.v1",
                registration.tenant_id,
                registration.workspace_id,
                registration.source_id,
                idempotency_key,
            ]
        )
    ).hexdigest()

    envelope = CaptureEnvelopeV1(
        schema_version="ets.capture.v1",
        capture_id=f"gateway-otlp-capture:{capture_identity}",
        collector_id=collector_id,
        adapter_id=registration.adapter_id,
        adapter_version=registration.adapter_version,
        source=CaptureSource(
            system=registration.source_system,
            identifier=registration.source_id,
            tenant_id=registration.tenant_id,
            workspace_id=registration.workspace_id,
            sequence=observation.record_ordinal,
            idempotency_key=idempotency_key,
            transport_identity=registration.principal,
            declared_identity=None,
        ),
        observed_at_utc=observation.source_timestamp_utc,
        received_at_utc=received_at,
        clock_quality=registration.clock_quality,
        media_type=OTLP_SEMANTIC_MEDIA_TYPE,
        content_length=len(committed),
        content_digest=ContentDigest(
            algorithm="sha256",
            value=content_hash,
            representation=OTLP_COMMITTED_REPRESENTATION,
            profile="ets.content.sha256.v1",
        ),
        evidence_reference=EvidenceReference(
            uri=None,
            retention_mode="not_retained",
            store_profile=None,
        ),
        transformation=CaptureTransformation(
            profile="ets.gateway.otlp-metadata-minimization.v1",
            input_format="ets.otlp.observation.v1",
            output_event_type=registration.event_type,
            lossless=False,
            notes=(
                "The committed representation contains bounded decoded OTLP metadata only; "
                "transport protobuf bytes are not retained and configured key minimization "
                "may remove source-declared fields before commitment."
            ),
        ),
        correlation_id=request.correlation_id,
        metadata={
            "otlp_signal_class": observation.signal_class,
            "otlp_record_ordinal": observation.record_ordinal,
            "decoder_profile": observation.decoder_profile,
            "decoder_transformation_profile": observation.transformation_profile,
            "source_timestamp_status": (
                "present" if observation.source_timestamp_utc is not None else "absent"
            ),
            "redacted_field_count": redacted_count,
            "committed_representation_length": len(committed),
            "committed_resource_metadata": resource_metadata,
            "committed_scope_metadata": scope_metadata,
            "committed_record_metadata": record_metadata,
            "raw_transport_payload_retained": False,
        },
        privacy=CapturePrivacy(
            classification=registration.classification,
            redaction_profile=registration.redaction_profile,
            minimization_profile=registration.minimization_profile,
            contains_raw_evidence=False,
        ),
        extensions={},
    )
    return GatewayOtlpCapture(envelope=envelope, committed_representation=committed)


def _format_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _minimize_mapping(
    value: dict[str, Any],
    redacted_keys: frozenset[str],
) -> tuple[dict[str, Any], int]:
    minimized, removed = _minimize_json(value, redacted_keys)
    if not isinstance(minimized, dict):
        raise TypeError("OTLP metadata root must remain a mapping")
    return minimized, removed


def _minimize_json(value: Any, redacted_keys: frozenset[str]) -> tuple[Any, int]:
    if isinstance(value, dict):
        minimized: dict[str, Any] = {}
        removed = 0
        for key, item in value.items():
            if key in redacted_keys:
                removed += 1
                continue
            child, child_removed = _minimize_json(item, redacted_keys)
            minimized[key] = child
            removed += child_removed
        return minimized, removed
    if isinstance(value, list):
        minimized_items: list[Any] = []
        removed = 0
        for item in value:
            child, child_removed = _minimize_json(item, redacted_keys)
            minimized_items.append(child)
            removed += child_removed
        return minimized_items, removed
    return value, 0
