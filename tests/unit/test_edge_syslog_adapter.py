from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

from ets.edge.syslog_adapter import (
    MAX_SYSLOG_DATAGRAM_BYTES,
    SyslogParseError,
    build_syslog_capture,
    parse_rfc5424_header,
)

VALID = (
    b'<34>1 2003-10-11T22:14:15.003Z mymachine su 8710 ID47 '
    b'[exampleSDID@32473 iut="3" eventSource="Application"] ETS_SYSLOG_SECRET_9f31'
)


def test_parse_rfc5424_header_extracts_bounded_fields() -> None:
    header = parse_rfc5424_header(VALID)

    assert header.priority == 34
    assert header.facility == 4
    assert header.severity == 2
    assert header.version == 1
    assert header.timestamp == "2003-10-11T22:14:15.003Z"
    assert header.hostname == "mymachine"
    assert header.app_name == "su"
    assert header.procid == "8710"
    assert header.msgid == "ID47"


def test_parse_rfc5424_nilvalues_are_not_invented() -> None:
    header = parse_rfc5424_header(b"<13>1 - - - - - - test")

    assert header.priority == 13
    assert header.timestamp is None
    assert header.hostname is None
    assert header.app_name is None
    assert header.procid is None
    assert header.msgid is None


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"not-syslog",
        b"<192>1 - host app proc msg - bad-priority",
        b"<34>2 - host app proc msg - unsupported-version",
        b"<34>1 - host app proc",
        b"<34>1 - host \xff proc msg - non-ascii-header",
    ],
)
def test_parse_rfc5424_rejects_malformed_headers(payload: bytes) -> None:
    with pytest.raises(SyslogParseError):
        parse_rfc5424_header(payload)


def test_parse_rfc5424_rejects_oversized_datagram() -> None:
    payload = b"<34>1 - host app proc msg - " + b"x" * MAX_SYSLOG_DATAGRAM_BYTES

    with pytest.raises(SyslogParseError, match="exceeds UDP pilot limit"):
        parse_rfc5424_header(payload)


def test_build_syslog_capture_hashes_exact_bytes_and_excludes_raw_message() -> None:
    captured = build_syslog_capture(
        VALID,
        tenant_id="tenant_demo",
        workspace_id="workspace_alpha",
        source_id="linux-lab",
        peer_host="192.0.2.10",
        peer_port=53014,
        received_at=datetime(2026, 8, 13, 0, 40, tzinfo=UTC),
        event_id="evt_syslog_test_001",
    )

    assert captured.content_hash == hashlib.sha256(VALID).hexdigest()
    assert captured.byte_size == len(VALID)
    assert captured.event["schema_version"] == "ets.event.v1"
    assert captured.event["event_type"] == "evidence.captured.syslog"
    assert captured.event["content_hash"] == captured.content_hash
    assert captured.event["source_system"] == "edge-syslog:linux-lab"

    metadata = captured.event["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["capture_boundary"] == "edge.syslog.rfc5424.udp.v1"
    assert metadata["raw_payload_retained"] is False
    assert metadata["hostname"] == "mymachine"
    assert metadata["peer_host"] == "192.0.2.10"

    serialized = json.dumps(captured.event, sort_keys=True)
    assert "ETS_SYSLOG_SECRET_9f31" not in serialized
    assert "eventSource" not in serialized


def test_modified_datagram_produces_different_digest() -> None:
    changed = VALID.replace(b"ETS_SYSLOG_SECRET_9f31", b"ETS_SYSLOG_SECRET_CHANGED")

    original = build_syslog_capture(
        VALID,
        tenant_id="tenant_demo",
        workspace_id="workspace_alpha",
        source_id="linux-lab",
        peer_host="127.0.0.1",
        peer_port=5514,
    )
    modified = build_syslog_capture(
        changed,
        tenant_id="tenant_demo",
        workspace_id="workspace_alpha",
        source_id="linux-lab",
        peer_host="127.0.0.1",
        peer_port=5514,
    )

    assert original.content_hash != modified.content_hash


def test_source_id_is_bounded() -> None:
    with pytest.raises(ValueError, match="source_id"):
        build_syslog_capture(
            VALID,
            tenant_id="tenant_demo",
            workspace_id="workspace_alpha",
            source_id="x" * 65,
            peer_host="127.0.0.1",
            peer_port=5514,
        )
