"""Bounded RFC 5424 syslog parsing and ETS event construction.

The Edge pilot keeps its historical UDP bounds and exact-byte hashing behavior
while delegating product-neutral RFC 5424 header parsing to ``ets.capture``.
"""


from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from uuid import uuid4

from ets.capture.syslog import (
    SyslogHeader as SyslogHeader,
    SyslogParseError as SyslogParseError,
    parse_rfc5424_header as _parse_shared_rfc5424_header,
)

MAX_SYSLOG_DATAGRAM_BYTES: Final = 65_507
MAX_SYSLOG_SOURCE_ID_LENGTH: Final = 64

@dataclass(frozen=True, slots=True)
class SyslogCapture:
    event: dict[str, object | None]
    event_id: str
    evidence_id: str
    content_hash: str
    byte_size: int


def parse_rfc5424_header(datagram: bytes) -> SyslogHeader:
    """Parse the bounded Edge UDP pilot header without retaining message content."""

    if not datagram:
        raise SyslogParseError("syslog datagram must not be empty")
    if len(datagram) > MAX_SYSLOG_DATAGRAM_BYTES:
        raise SyslogParseError("syslog datagram exceeds UDP pilot limit")
    try:
        return _parse_shared_rfc5424_header(datagram)
    except SyslogParseError as exc:
        if str(exc) == "ETS supports RFC 5424 VERSION 1 only":
            raise SyslogParseError("ETS Edge pilot supports RFC 5424 VERSION 1 only") from exc
        raise


def build_syslog_capture(
    datagram: bytes,
    *,
    tenant_id: str,
    workspace_id: str,
    source_id: str,
    peer_host: str,
    peer_port: int,
    received_at: datetime | None = None,
    event_id: str | None = None,
) -> SyslogCapture:
    """Build an existing ``ets.event.v1`` record from exact syslog bytes."""

    source_id = source_id.strip()
    if not source_id or len(source_id) > MAX_SYSLOG_SOURCE_ID_LENGTH:
        raise ValueError("source_id must be 1-64 characters")
    if not tenant_id or not workspace_id:
        raise ValueError("tenant_id and workspace_id are required")
    if not 0 <= peer_port <= 65_535:
        raise ValueError("peer_port must be between 0 and 65535")

    header = parse_rfc5424_header(datagram)
    digest = hashlib.sha256(datagram).hexdigest()
    resolved_event_id = event_id or f"evt_syslog_{uuid4().hex}"
    evidence_id = f"syslog:{source_id}:{digest[:48]}"
    captured_at = received_at or datetime.now(UTC)
    created_at = captured_at.astimezone(UTC).isoformat().replace("+00:00", "Z")

    metadata: dict[str, object] = {
        "capture_boundary": "edge.syslog.rfc5424.udp.v1",
        "transport": "udp",
        "source_id": source_id,
        "peer_host": peer_host[:255],
        "peer_port": peer_port,
        "byte_size": len(datagram),
        "rfc5424_priority": header.priority,
        "rfc5424_facility": header.facility,
        "rfc5424_severity": header.severity,
        "rfc5424_version": header.version,
        "raw_payload_retained": False,
    }
    if header.timestamp is not None:
        metadata["source_timestamp"] = header.timestamp
    if header.hostname is not None:
        metadata["hostname"] = header.hostname
    if header.app_name is not None:
        metadata["app_name"] = header.app_name
    if header.procid is not None:
        metadata["procid"] = header.procid
    if header.msgid is not None:
        metadata["msgid"] = header.msgid

    event: dict[str, object | None] = {
        "event_id": resolved_event_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "evidence_id": evidence_id,
        "event_type": "evidence.captured.syslog",
        "subject_ref": f"syslog-source:{source_id}",
        "content_hash": digest,
        "content_hash_alg": "sha256",
        "metadata": metadata,
        "created_at_utc": created_at,
        "schema_version": "ets.event.v1",
        "source_system": f"edge-syslog:{source_id}",
        "actor_id": None,
        "correlation_id": None,
        "external_refs": None,
        "redaction_profile": None,
    }
    return SyslogCapture(
        event=event,
        event_id=resolved_event_id,
        evidence_id=evidence_id,
        content_hash=digest,
        byte_size=len(datagram),
    )
