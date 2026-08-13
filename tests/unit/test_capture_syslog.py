from __future__ import annotations

import pytest

from ets.capture.syslog import SyslogParseError, parse_rfc5424_header


def test_shared_rfc5424_parser_extracts_header_fields() -> None:
    message = b"<34>1 2003-10-11T22:14:15.003Z host app 123 ID47 - payload"

    header = parse_rfc5424_header(message, maximum_bytes=len(message))

    assert header.priority == 34
    assert header.facility == 4
    assert header.severity == 2
    assert header.version == 1
    assert header.timestamp == "2003-10-11T22:14:15.003Z"
    assert header.hostname == "host"
    assert header.app_name == "app"
    assert header.procid == "123"
    assert header.msgid == "ID47"


def test_shared_rfc5424_parser_preserves_nil_values() -> None:
    header = parse_rfc5424_header(b"<13>1 - - - - - - payload")

    assert header.timestamp is None
    assert header.hostname is None
    assert header.app_name is None
    assert header.procid is None
    assert header.msgid is None


def test_shared_rfc5424_parser_enforces_caller_bound() -> None:
    message = b"<13>1 - host app proc msg - payload"

    parse_rfc5424_header(message, maximum_bytes=len(message))
    with pytest.raises(SyslogParseError, match="configured limit"):
        parse_rfc5424_header(message, maximum_bytes=len(message) - 1)


def test_shared_rfc5424_parser_rejects_invalid_bound() -> None:
    with pytest.raises(ValueError, match="maximum_bytes"):
        parse_rfc5424_header(b"<13>1 - - - - - - payload", maximum_bytes=0)


@pytest.mark.parametrize(
    "message",
    [
        b"",
        b"not-syslog",
        b"<192>1 - host app proc msg - payload",
        b"<34>2 - host app proc msg - payload",
        b"<34>1 - host app proc",
        b"<34>1 - host \xff proc msg - payload",
    ],
)
def test_shared_rfc5424_parser_rejects_malformed_messages(message: bytes) -> None:
    with pytest.raises(SyslogParseError):
        parse_rfc5424_header(message)
