"""Artifact registration helpers for ETS evidence receipts."""

from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ets.core.canonical_json import canonicalize


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    artifact_hash: str
    reference_uri: str
    content_type: str
    byte_size: int
    metadata: dict[str, Any]
    ingestion_timestamp_utc: datetime
    event_id: str
    log_index: int


def decode_artifact_base64(artifact_base64: str) -> bytes:
    """Decode artifact content using strict base64 validation."""

    try:
        return base64.b64decode(artifact_base64.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise ValueError("artifact_base64 must be valid base64") from exc


def hash_artifact_bytes(content: bytes) -> str:
    """Return the SHA-256 digest of artifact bytes."""

    return hashlib.sha256(content).hexdigest()


def normalize_artifact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Validate JSON-native artifact metadata without affecting content hash."""

    canonicalize(metadata)
    return dict(metadata)


def build_artifact_event_id(artifact_id: str) -> str:
    """Build a deterministic event identifier for artifact registration."""

    if not artifact_id:
        raise ValueError("artifact_id is required")
    return f"artifact_registered:{artifact_id}"


def build_artifact_reference_uri(artifact_id: str) -> str:
    """Build a local reference URI without storing raw artifact bytes."""

    if not artifact_id:
        raise ValueError("artifact_id is required")
    return f"ets://artifact/{artifact_id}"


def create_artifact_record(
    *,
    artifact_id: str,
    artifact_hash: str,
    reference_uri: str,
    content_type: str,
    byte_size: int,
    metadata: dict[str, Any],
    ingestion_timestamp_utc: datetime,
    event_id: str,
    log_index: int,
) -> ArtifactRecord:
    """Create a JSON-safe artifact record that excludes raw artifact bytes."""

    if byte_size < 0:
        raise ValueError("byte_size must be non-negative")
    if ingestion_timestamp_utc.tzinfo is None or ingestion_timestamp_utc.utcoffset() is None:
        raise ValueError("ingestion_timestamp_utc must be timezone-aware")
    bytes.fromhex(artifact_hash)
    if len(artifact_hash) != 64:
        raise ValueError("artifact_hash must be a SHA-256 hex digest")
    return ArtifactRecord(
        artifact_id=artifact_id,
        artifact_hash=artifact_hash,
        reference_uri=reference_uri,
        content_type=content_type,
        byte_size=byte_size,
        metadata=normalize_artifact_metadata(metadata),
        ingestion_timestamp_utc=ingestion_timestamp_utc.astimezone(UTC),
        event_id=event_id,
        log_index=log_index,
    )
