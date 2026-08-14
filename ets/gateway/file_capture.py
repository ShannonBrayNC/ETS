"""Gateway file/drop observation mapping for the G1E profile."""

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
    FilesystemObjectDigest,
)
from ets.core.api import canonicalize
from ets.gateway.source_registry import SourceRegistration

FILE_OBSERVATION_MEDIA_TYPE: Final = "application/vnd.ets.file-observation+json;version=1"
FILE_COMMITTED_REPRESENTATION: Final = "ets.gateway.file-digest-metadata.v1"
DEFAULT_MAX_FILE_COMMITTED_BYTES: Final = 16 * 1024


class GatewayFileCaptureError(ValueError):
    """Raised when a file observation cannot enter the Gateway capture profile."""


@dataclass(frozen=True, slots=True)
class GatewayFileCaptureRequest:
    """One qualified filesystem observation supplied by the file/drop boundary."""

    observation: FilesystemObjectDigest
    delivery_id: str
    declared_filename: str | None = None
    declared_content_type: str | None = None
    correlation_id: str | None = None
    received_at_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class GatewayFileCapture:
    """Capture envelope plus the bounded representation committed by ETS."""

    envelope: CaptureEnvelopeV1
    committed_representation: bytes


def build_file_capture(
    registration: SourceRegistration,
    request: GatewayFileCaptureRequest,
    *,
    collector_id: str = "ets-gateway",
    maximum_committed_bytes: int = DEFAULT_MAX_FILE_COMMITTED_BYTES,
) -> GatewayFileCapture:
    """Map one stable file observation into a server-authorized capture envelope."""

    if not collector_id:
        raise ValueError("collector_id is required")
    if maximum_committed_bytes < 1:
        raise ValueError("maximum_committed_bytes must be positive")
    if not 1 <= len(request.delivery_id) <= 200:
        raise GatewayFileCaptureError("delivery_id must be 1-200 characters")
    _bounded_optional("declared_filename", request.declared_filename, 500)
    _bounded_optional("declared_content_type", request.declared_content_type, 200)
    _bounded_optional("correlation_id", request.correlation_id, 200)

    observation = request.observation
    if observation.stability != "no_change_detected":
        raise GatewayFileCaptureError("file observation is not qualified as stable")
    if observation.commitment_state != "not_committed":
        raise GatewayFileCaptureError("file observation already carries commitment state")
    if observation.raw_object_retained:
        raise GatewayFileCaptureError("raw object retention is outside the G1E-C profile")
    if observation.digest.algorithm != "sha256":
        raise GatewayFileCaptureError("file observation requires sha256")
    if observation.digest.byte_count != observation.observed_after.size:
        raise GatewayFileCaptureError("file observation byte count does not match observed size")

    received_at = request.received_at_utc or datetime.now(UTC)
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise GatewayFileCaptureError("received_at_utc must be timezone-aware")
    received_at = received_at.astimezone(UTC)

    representation = {
        "schema": FILE_COMMITTED_REPRESENTATION,
        "relative_path": observation.relative_path,
        "object_digest": {
            "algorithm": observation.digest.algorithm,
            "value": observation.digest.value,
            "byte_count": observation.digest.byte_count,
        },
        "collector_observation": {
            "stability": observation.stability,
            "before": _metadata(observation.observed_before),
            "after": _metadata(observation.observed_after),
        },
        "source_claims": {
            "filename": request.declared_filename,
            "content_type": request.declared_content_type,
        },
    }
    committed = canonicalize(representation)
    if len(committed) > maximum_committed_bytes:
        raise GatewayFileCaptureError("file committed representation exceeds configured limit")

    content_hash = hashlib.sha256(committed).hexdigest()
    idempotency_key = f"file:{request.delivery_id}"
    capture_identity = hashlib.sha256(
        canonicalize(
            [
                "ets.gateway.file.capture-id.v1",
                registration.tenant_id,
                registration.workspace_id,
                registration.source_id,
                idempotency_key,
            ]
        )
    ).hexdigest()

    envelope = CaptureEnvelopeV1(
        schema_version="ets.capture.v1",
        capture_id=f"gateway-file-capture:{capture_identity}",
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
        observed_at_utc=None,
        received_at_utc=received_at,
        clock_quality=registration.clock_quality,
        media_type=FILE_OBSERVATION_MEDIA_TYPE,
        content_length=observation.digest.byte_count,
        content_digest=ContentDigest(
            algorithm="sha256",
            value=content_hash,
            representation=FILE_COMMITTED_REPRESENTATION,
            profile="ets.content.sha256.v1",
        ),
        evidence_reference=EvidenceReference(
            uri=None,
            retention_mode="not_retained",
            store_profile=None,
        ),
        transformation=CaptureTransformation(
            profile="ets.gateway.file-digest-metadata.v1",
            input_format="filesystem-object",
            output_event_type=registration.event_type,
            lossless=False,
            notes=(
                "The committed representation contains the qualified object digest and bounded "
                "metadata; raw file bytes are not retained or committed directly by this profile."
            ),
        ),
        correlation_id=request.correlation_id,
        metadata={
            "relative_path": observation.relative_path,
            "object_digest": observation.digest.value,
            "object_digest_algorithm": observation.digest.algorithm,
            "object_byte_count": observation.digest.byte_count,
            "collector_stability": observation.stability,
            "observed_before": _metadata(observation.observed_before),
            "observed_after": _metadata(observation.observed_after),
            "declared_filename_claim": request.declared_filename,
            "declared_content_type_claim": request.declared_content_type,
            "committed_representation_length": len(committed),
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
    return GatewayFileCapture(envelope=envelope, committed_representation=committed)


def _metadata(value: object) -> dict[str, int]:
    return {
        "device": int(getattr(value, "device")),
        "inode": int(getattr(value, "inode")),
        "size": int(getattr(value, "size")),
        "mtime_ns": int(getattr(value, "mtime_ns")),
        "ctime_ns": int(getattr(value, "ctime_ns")),
    }


def _bounded_optional(name: str, value: str | None, maximum: int) -> None:
    if value is not None and not 1 <= len(value) <= maximum:
        raise GatewayFileCaptureError(f"{name} must be 1-{maximum} characters when supplied")
