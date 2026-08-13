"""Bounded RFC 5424 syslog parsing and ETS event construction.

This module deliberately handles only the RFC 5424 header needed by the Edge
pilot. It hashes the exact received datagram bytes before any parsing and never
places the raw syslog message body into ETS metadata.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from uuid import uuid4

MAX_SYSLOG_DATAGRAM_BYTES: Final = 65_507
MAX_SYSLOG_SOURCE_ID_LENGTH: Final = 64


class SyslogParseError(ValueError):
    """Raised when a datagram is not a bounded RFC 5424 message."""


@dataclass(frozen=True, slots=True)
class SyslogHeader:
    priority: int
    facility: int
    severity: int
    version: int
    timestamp: str | None
    hostname: str | None
    app_name: str | None
    procid: str | None
    msgid: str | None


@dataclass(frozen=True, slots=True)
class SyslogCapture:
    event: dict[str, object | None]
    event_id: str
    evidence_id: str
    content_hash: str
    byte_size: int


def parse_rfc5424_header(datagram: bytes) -> SyslogHeader:
    """Parse the bounded RFC 5424 header without retaining STRUCTURED-DATA/MSG."""

    if not datagram:
        raise SyslogParseError("syslog datagram must not be empty")
    if len(datagram) > MAX_SYSLOG_DATAGRAM_BYTES:
        raise SyslogParseError("syslog datagram exceeds UDP pilot limit")
    if datagram[0:1] != b"<":
        raise SyslogParseError("RFC 5424 PRI prefix is required")

    close = datagram.find(b">", 2, 6)
    if close < 0:
        raise SyslogParseError("RFC 5424 PRI terminator is missing")
    priority_bytes = datagram[1:close]
    if not priority_bytes.isdigit():
        raise SyslogParseError("RFC 5424 PRI must be decimal")
    priority = int(priority_bytes)
    if priority > 191:
        raise SyslogParseError("RFC 5424 PRI must be between 0 and 191")

    version_bytes, separator, remainder = datagram[close + 1 :].partition(b" ")
    if not separator or version_bytes != b"1":
        raise SyslogParseError("ETS Edge pilot supports RFC 5424 VERSION 1 only")

    # Split only the fixed header fields. The final element intentionally keeps
    # STRUCTURED-DATA and MSG opaque because those bytes are not retained.
    fields = remainder.split(b" ", 5)
    if len(fields) != 6:
        raise SyslogParseError("RFC 5424 fixed header is incomplete")
    timestamp_raw, hostname_raw, app_raw, procid_raw, msgid_raw, _opaque = fields

    timestamp = _header_token(timestamp_raw, "timestamp", 64, allow_nil=True)
    hostname = _header_token(hostname_raw, "hostname", 255, allow_nil=True)
    app_name = _header_token(app_raw, "app-name", 48, allow_nil=True)
    procid = _header_token(procid_raw, "procid", 128, allow_nil=True)
    msgid = _header_token(msgid_raw, "msgid", 32, allow_nil=True)

    return SyslogHeader(
        priority=priority,
        facility=priority // 8,
        severity=priority % 8,
        version=1,
        timestamp=timestamp,
        hostname=hostname,
        app_name=app_name,
        procid=procid,
        msgid=msgid,
    )


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


def _header_token(
    value: bytes,
    field_name: str,
    max_length: int,
    *,
    allow_nil: bool,
) -> str | None:
    if allow_nil and value == b"-":
        return None
    if not value:
        raise SyslogParseError(f"RFC 5424 {field_name} must not be empty")
    if len(value) > max_length:
        raise SyslogParseError(f"RFC 5424 {field_name} exceeds {max_length} bytes")
    # RFC 5424 header fields are printable US-ASCII without spaces.
    if any(byte < 33 or byte > 126 for byte in value):
        raise SyslogParseError(f"RFC 5424 {field_name} must be printable US-ASCII")
    try:
        return value.decode("ascii")
    except UnicodeDecodeError as exc:  # defensive; range check above should catch this
        raise SyslogParseError(f"RFC 5424 {field_name} must be US-ASCII") from exc
