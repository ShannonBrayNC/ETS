"""Deterministic mapping from ETS capture envelopes into frozen event v1."""

from __future__ import annotations

from typing import Any

from ets.capture.models import CaptureEnvelopeV1
from ets.core.api import EvidenceEvent


def capture_event_metadata(capture: CaptureEnvelopeV1) -> dict[str, Any]:
    """Return bounded provenance metadata carried into the event commitment."""

    return {
        "capture_schema_version": capture.schema_version,
        "capture_id": capture.capture_id,
        "collector_id": capture.collector_id,
        "adapter_id": capture.adapter_id,
        "adapter_version": capture.adapter_version,
        "source": {
            "identifier": capture.source.identifier,
            "sequence": capture.source.sequence,
            "idempotency_key": capture.source.idempotency_key,
            "transport_identity": capture.source.transport_identity,
            "declared_identity": capture.source.declared_identity,
        },
        "observed_at_utc": (
            capture.observed_at_utc.isoformat().replace("+00:00", "Z")
            if capture.observed_at_utc is not None
            else None
        ),
        "received_at_utc": capture.received_at_utc.isoformat().replace("+00:00", "Z"),
        "clock_quality": capture.clock_quality,
        "media_type": capture.media_type,
        "content_length": capture.content_length,
        "content_digest": {
            "representation": capture.content_digest.representation,
            "profile": capture.content_digest.profile,
        },
        "evidence_reference": capture.evidence_reference.model_dump(mode="json"),
        "transformation": capture.transformation.model_dump(mode="json"),
        "privacy": capture.privacy.model_dump(mode="json"),
        "capture_metadata": capture.metadata,
        "extensions": capture.extensions,
    }


def to_evidence_event(
    capture: CaptureEnvelopeV1,
    *,
    event_id: str,
    evidence_id: str,
    subject_ref: str | None = None,
    actor_id: str | None = None,
) -> EvidenceEvent:
    """Map a validated capture envelope into the existing event v1 contract."""

    return EvidenceEvent(
        event_id=event_id,
        tenant_id=capture.source.tenant_id,
        workspace_id=capture.source.workspace_id,
        evidence_id=evidence_id,
        event_type=capture.transformation.output_event_type,
        subject_ref=subject_ref,
        content_hash=capture.content_digest.value,
        content_hash_alg="sha256",
        metadata=capture_event_metadata(capture),
        created_at_utc=capture.received_at_utc,
        schema_version="ets.event.v1",
        source_system=capture.source.system,
        actor_id=actor_id,
        correlation_id=capture.correlation_id,
        external_refs=None,
        redaction_profile=capture.privacy.redaction_profile,
    )
