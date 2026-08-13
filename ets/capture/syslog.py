"""Product-neutral RFC 5424 syslog header parsing primitives."""

from __future__ import annotations

from dataclasses import dataclass


class SyslogParseError(ValueError):
    """Raised when a bounded RFC 5424 message cannot be parsed."""


@dataclass(frozen=True, slots=True)
class SyslogHeader:
    """RFC 5424 fixed header fields used by ETS capture adapters."""

    priority: int
    facility: int
    severity: int
    version: int
    timestamp: str | None
    hostname: str | None
    app_name: str | None
    procid: str | None
    msgid: str | None


def parse_rfc5424_header(
    message: bytes,
    *,
    maximum_bytes: int | None = None,
) -> SyslogHeader:
    """Parse the RFC 5424 fixed header without retaining STRUCTURED-DATA or MSG."""

    if maximum_bytes is not None and maximum_bytes < 1:
        raise ValueError("maximum_bytes must be positive when provided")
    if not message:
        raise SyslogParseError("syslog message must not be empty")
    if maximum_bytes is not None and len(message) > maximum_bytes:
        raise SyslogParseError("syslog message exceeds configured limit")
    if message[0:1] != b"<":
        raise SyslogParseError("RFC 5424 PRI prefix is required")

    close = message.find(b">", 2, 6)
    if close < 0:
        raise SyslogParseError("RFC 5424 PRI terminator is missing")
    priority_bytes = message[1:close]
    if not priority_bytes.isdigit():
        raise SyslogParseError("RFC 5424 PRI must be decimal")
    priority = int(priority_bytes)
    if priority > 191:
        raise SyslogParseError("RFC 5424 PRI must be between 0 and 191")

    version_bytes, separator, remainder = message[close + 1 :].partition(b" ")
    if not separator or version_bytes != b"1":
        raise SyslogParseError("ETS supports RFC 5424 VERSION 1 only")

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
    if any(byte < 33 or byte > 126 for byte in value):
        raise SyslogParseError(f"RFC 5424 {field_name} must be printable US-ASCII")
    try:
        return value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise SyslogParseError(f"RFC 5424 {field_name} must be US-ASCII") from exc
