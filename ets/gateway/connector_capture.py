"""Map policy-ready connector candidates into server-authorized Gateway capture envelopes."""

from __future__ import annotations

import hashlib
import re
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
from ets.connectors.models import ConnectorEvidenceCandidateV1
from ets.core.api import canonicalize
from ets.gateway.source_registry import SourceRegistration

CONNECTOR_CANDIDATE_MEDIA_TYPE: Final = "application/vnd.ets.connector-candidate+json;version=1"
CONNECTOR_COMMITTED_REPRESENTATION: Final = "ets.gateway.connector-candidate-metadata.v1"
DEFAULT_MAX_CONNECTOR_COMMITTED_BYTES: Final = 16 * 1024
CONNECTOR_INSTANCE_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class GatewayConnectorCaptureError(ValueError):
    """Raised when a connector candidate cannot enter the Gateway capture profile."""


@dataclass(frozen=True, slots=True)
class GatewayConnectorCandidateRequest:
    candidate: ConnectorEvidenceCandidateV1
    connector_instance_id: str | None = None
    correlation_id: str | None = None
    received_at_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class GatewayConnectorCapture:
    envelope: CaptureEnvelopeV1
    committed_representation: bytes


def build_connector_capture(
    registration: SourceRegistration,
    request: GatewayConnectorCandidateRequest,
    *,
    collector_id: str = "ets-gateway",
    maximum_committed_bytes: int = DEFAULT_MAX_CONNECTOR_COMMITTED_BYTES,
) -> GatewayConnectorCapture:
    """Map one policy-ready connector candidate under authoritative source scope."""

    if not collector_id:
        raise ValueError("collector_id is required")
    if maximum_committed_bytes < 1:
        raise ValueError("maximum_committed_bytes must be positive")
    if request.correlation_id is not None and len(request.correlation_id) > 200:
        raise GatewayConnectorCaptureError("correlation_id exceeds configured limit")
    if (
        request.connector_instance_id is not None
        and CONNECTOR_INSTANCE_ID_PATTERN.fullmatch(request.connector_instance_id) is None
    ):
        raise GatewayConnectorCaptureError("connector_instance_id is outside configured bounds")

    candidate = request.candidate
    if candidate.source_system != registration.source_system:
        raise GatewayConnectorCaptureError(
            "connector candidate source_system does not match server-authorized registration"
        )

    received_at = request.received_at_utc or datetime.now(UTC)
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise GatewayConnectorCaptureError("received_at_utc must be timezone-aware")
    received_at = received_at.astimezone(UTC)

    minimized_metadata, redacted_count = _minimize_mapping(
        candidate.metadata,
        registration.redacted_keys,
    )
    representation: dict[str, Any] = {
        "schema": CONNECTOR_COMMITTED_REPRESENTATION,
        "source_system": candidate.source_system,
        "source_record_id": candidate.source_record_id,
        "source_event_type_claim": candidate.event_type,
        "source_observed_at_utc": _format_utc(candidate.observed_at_utc),
        "source_media_type": candidate.media_type,
        "connector_transformation_profile": candidate.transformation_profile,
        "connector_lossless_claim": candidate.lossless,
        "metadata": minimized_metadata,
    }
    committed = canonicalize(representation)
    if len(committed) > maximum_committed_bytes:
        raise GatewayConnectorCaptureError(
            "connector committed representation exceeds configured limit"
        )

    content_hash = hashlib.sha256(committed).hexdigest()
    source_identity = hashlib.sha256(
        canonicalize(
            [
                "ets.gateway.connector.source-record.v1",
                candidate.source_system,
                candidate.source_record_id,
            ]
        )
    ).hexdigest()
    idempotency_key = f"connector:{source_identity}"
    capture_identity = hashlib.sha256(
        canonicalize(
            [
                "ets.gateway.connector.capture-id.v1",
                registration.tenant_id,
                registration.workspace_id,
                registration.source_id,
                idempotency_key,
            ]
        )
    ).hexdigest()

    capture_metadata: dict[str, Any] = {
        "connector_source_system": candidate.source_system,
        "connector_source_record_id": candidate.source_record_id,
        "connector_source_event_type_claim": candidate.event_type,
        "connector_transformation_profile": candidate.transformation_profile,
        "connector_lossless_claim": candidate.lossless,
        "redacted_field_count": redacted_count,
        "committed_representation_length": len(committed),
        "committed_connector_metadata": minimized_metadata,
        "raw_source_payload_retained": False,
    }
    if request.connector_instance_id is not None:
        capture_metadata["connector_instance_id"] = request.connector_instance_id

    envelope = CaptureEnvelopeV1(
        schema_version="ets.capture.v1",
        capture_id=f"gateway-connector-capture:{capture_identity}",
        collector_id=collector_id,
        adapter_id=registration.adapter_id,
        adapter_version=registration.adapter_version,
        source=CaptureSource(
            system=registration.source_system,
            identifier=registration.source_id,
            tenant_id=registration.tenant_id,
            workspace_id=registration.workspace_id,
            sequence=None,
            idempotency_key=idempotency_key,
            transport_identity=registration.principal,
            declared_identity=None,
        ),
        observed_at_utc=candidate.observed_at_utc,
        received_at_utc=received_at,
        clock_quality=registration.clock_quality,
        media_type=CONNECTOR_CANDIDATE_MEDIA_TYPE,
        content_length=len(committed),
        content_digest=ContentDigest(
            algorithm="sha256",
            value=content_hash,
            representation=CONNECTOR_COMMITTED_REPRESENTATION,
            profile="ets.content.sha256.v1",
        ),
        evidence_reference=EvidenceReference(
            uri=None,
            retention_mode="not_retained",
            store_profile=None,
        ),
        transformation=CaptureTransformation(
            profile="ets.gateway.connector-candidate-minimization.v1",
            input_format="ets.connector.candidate.v1",
            output_event_type=registration.event_type,
            lossless=False,
            notes=(
                "The connector candidate has passed the adapter normalization boundary. "
                "Authoritative ETS scope and event type come from server registration; "
                "configured key minimization is applied again before commitment."
            ),
        ),
        correlation_id=request.correlation_id,
        metadata=capture_metadata,
        privacy=CapturePrivacy(
            classification=registration.classification,
            redaction_profile=registration.redaction_profile,
            minimization_profile=registration.minimization_profile,
            contains_raw_evidence=False,
        ),
        extensions={},
    )
    return GatewayConnectorCapture(envelope=envelope, committed_representation=committed)


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
        raise TypeError("connector metadata root must remain a mapping")
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
