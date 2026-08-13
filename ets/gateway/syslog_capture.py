"""Gateway RFC 5424 capture mapping for the G1D syslog profile."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from ets.capture import (
    CaptureEnvelopeV1,
    CapturePrivacy,
    CaptureSource,
    CaptureTransformation,
    ContentDigest,
    EvidenceReference,
)
from ets.capture.syslog import SyslogHeader, parse_rfc5424_header
from ets.core.api import canonicalize
from ets.gateway.source_registry import SourceRegistration

DEFAULT_MAX_SYSLOG_MESSAGE_BYTES: Final = 8192
SYSLOG_MEDIA_TYPE: Final = "application/syslog;profile=rfc5424"
SYSLOG_COMMITTED_REPRESENTATION: Final = "ets.gateway.syslog-fixed-header.v1"


class GatewaySyslogCaptureError(ValueError):
    """Raised when a syslog message cannot enter the declared Gateway capture profile."""


@dataclass(frozen=True, slots=True)
class GatewaySyslogCaptureRequest:
    """One fully framed syslog message supplied by an authenticated transport boundary."""

    message: bytes
    delivery_id: str
    sequence: int | str | None = None
    correlation_id: str | None = None
    received_at_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class GatewaySyslogCapture:
    """Capture envelope plus the committed minimized representation bytes."""

    envelope: CaptureEnvelopeV1
    committed_representation: bytes
    header: SyslogHeader


def build_syslog_capture(
    registration: SourceRegistration,
    request: GatewaySyslogCaptureRequest,
    *,
    collector_id: str = "ets-gateway",
    maximum_message_bytes: int = DEFAULT_MAX_SYSLOG_MESSAGE_BYTES,
) -> GatewaySyslogCapture:
    """Map one RFC 5424 message into the declared header-only Gateway representation."""

    if not collector_id:
        raise ValueError("collector_id is required")
    if maximum_message_bytes < 1:
        raise ValueError("maximum_message_bytes must be positive")
    if not 1 <= len(request.delivery_id) <= 200:
        raise GatewaySyslogCaptureError("delivery_id must be 1-200 characters")
    if request.correlation_id is not None and len(request.correlation_id) > 200:
        raise GatewaySyslogCaptureError("correlation_id exceeds configured limit")
    if len(request.message) > maximum_message_bytes:
        raise GatewaySyslogCaptureError("syslog message exceeds configured limit")

    header = parse_rfc5424_header(request.message, maximum_bytes=maximum_message_bytes)
    committed = canonicalize(
        {
            "schema": SYSLOG_COMMITTED_REPRESENTATION,
            "priority": header.priority,
            "facility": header.facility,
            "severity": header.severity,
            "version": header.version,
            "timestamp": header.timestamp,
            "hostname": header.hostname,
            "app_name": header.app_name,
            "procid": header.procid,
            "msgid": header.msgid,
        }
    )
    content_hash = hashlib.sha256(committed).hexdigest()
    idempotency_key = f"syslog:{request.delivery_id}"
    capture_identity = hashlib.sha256(
        canonicalize(
            [
                "ets.gateway.syslog.capture-id.v1",
                registration.tenant_id,
                registration.workspace_id,
                registration.source_id,
                idempotency_key,
            ]
        )
    ).hexdigest()
    received_at = request.received_at_utc or datetime.now(UTC)
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise GatewaySyslogCaptureError("received_at_utc must be timezone-aware")
    observed_at, timestamp_status = _parse_source_timestamp(header.timestamp)

    envelope = CaptureEnvelopeV1(
        schema_version="ets.capture.v1",
        capture_id=f"gateway-syslog-capture:{capture_identity}",
        collector_id=collector_id,
        adapter_id=registration.adapter_id,
        adapter_version=registration.adapter_version,
        source=CaptureSource(
            system=registration.source_system,
            identifier=registration.source_id,
            tenant_id=registration.tenant_id,
            workspace_id=registration.workspace_id,
            sequence=request.sequence,
            idempotency_key=idempotency_key,
            transport_identity=registration.principal,
            declared_identity=header.hostname,
        ),
        observed_at_utc=observed_at,
        received_at_utc=received_at,
        clock_quality=registration.clock_quality,
        media_type=SYSLOG_MEDIA_TYPE,
        content_length=len(request.message),
        content_digest=ContentDigest(
            algorithm="sha256",
            value=content_hash,
            representation=SYSLOG_COMMITTED_REPRESENTATION,
            profile="ets.content.sha256.v1",
        ),
        evidence_reference=EvidenceReference(
            uri=None,
            retention_mode="not_retained",
            store_profile=None,
        ),
        transformation=CaptureTransformation(
            profile="ets.gateway.syslog-fixed-header-minimization.v1",
            input_format=SYSLOG_MEDIA_TYPE,
            output_event_type=registration.event_type,
            lossless=False,
            notes=(
                "Only the RFC 5424 fixed header is committed in this initial profile; "
                "STRUCTURED-DATA and MSG are excluded and original-byte hashing is not implied."
            ),
        ),
        correlation_id=request.correlation_id,
        metadata={
            "input_content_length": len(request.message),
            "committed_representation_length": len(committed),
            "rfc5424_priority": header.priority,
            "rfc5424_facility": header.facility,
            "rfc5424_severity": header.severity,
            "rfc5424_version": header.version,
            "source_timestamp_claim": header.timestamp,
            "source_timestamp_status": timestamp_status,
            "hostname_claim": header.hostname,
            "app_name_claim": header.app_name,
            "procid_claim": header.procid,
            "msgid_claim": header.msgid,
            "raw_payload_retained": False,
        },
        privacy=CapturePrivacy(
            classification=registration.classification,
            redaction_profile=registration.redaction_profile,
            minimization_profile=registration.minimization_profile,
            contains_raw_evidence=False,
        ),
        extensions={},
    )
    return GatewaySyslogCapture(
        envelope=envelope,
        committed_representation=committed,
        header=header,
    )


def _parse_source_timestamp(value: str | None) -> tuple[datetime | None, str]:
    if value is None:
        return None, "absent"
    if "T" not in value:
        return None, "invalid"
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None, "invalid"
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, "invalid"
    return parsed.astimezone(UTC), "parsed"
