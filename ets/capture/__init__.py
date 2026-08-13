"""Shared ETS capture-envelope contract."""

from ets.capture.mapping import capture_event_metadata, to_evidence_event
from ets.capture.models import (
    CaptureEnvelopeV1,
    CapturePrivacy,
    CaptureSource,
    CaptureTransformation,
    ContentDigest,
    EvidenceReference,
)
from ets.capture.syslog import SyslogHeader, SyslogParseError, parse_rfc5424_header
from ets.capture.syslog_framing import OctetCountingFramer, SyslogFramingError

__all__ = [
    "CaptureEnvelopeV1",
    "CapturePrivacy",
    "CaptureSource",
    "CaptureTransformation",
    "ContentDigest",
    "EvidenceReference",
    "OctetCountingFramer",
    "SyslogFramingError",
    "SyslogHeader",
    "SyslogParseError",
    "capture_event_metadata",
    "parse_rfc5424_header",
    "to_evidence_event",
]
