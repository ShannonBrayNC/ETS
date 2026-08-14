"""Shared ETS capture-envelope contract."""

from ets.capture.filesystem_object import (
    FilesystemBoundaryUnsupportedError,
    FilesystemObjectDigest,
    FilesystemObjectError,
    FilesystemObjectInstabilityError,
    FilesystemObjectMetadata,
    FilesystemPathError,
    FilesystemReadError,
    digest_filesystem_object,
    normalize_relative_object_path,
)
from ets.capture.mapping import capture_event_metadata, to_evidence_event
from ets.capture.models import (
    CaptureEnvelopeV1,
    CapturePrivacy,
    CaptureSource,
    CaptureTransformation,
    ContentDigest,
    EvidenceReference,
)
from ets.capture.object_digest import (
    BinaryStream,
    StreamDigestError,
    StreamDigestLengthError,
    StreamDigestLimitError,
    StreamDigestResult,
    digest_stream_sha256,
)
from ets.capture.syslog import SyslogHeader, SyslogParseError, parse_rfc5424_header
from ets.capture.syslog_framing import OctetCountingFramer, SyslogFramingError

__all__ = [
    "BinaryStream",
    "CaptureEnvelopeV1",
    "CapturePrivacy",
    "CaptureSource",
    "CaptureTransformation",
    "ContentDigest",
    "EvidenceReference",
    "FilesystemBoundaryUnsupportedError",
    "FilesystemObjectDigest",
    "FilesystemObjectError",
    "FilesystemObjectInstabilityError",
    "FilesystemObjectMetadata",
    "FilesystemPathError",
    "FilesystemReadError",
    "OctetCountingFramer",
    "StreamDigestError",
    "StreamDigestLengthError",
    "StreamDigestLimitError",
    "StreamDigestResult",
    "SyslogFramingError",
    "SyslogHeader",
    "SyslogParseError",
    "capture_event_metadata",
    "digest_filesystem_object",
    "digest_stream_sha256",
    "normalize_relative_object_path",
    "parse_rfc5424_header",
    "to_evidence_event",
]
