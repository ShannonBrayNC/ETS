from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.qualification.legacy_http import (
    IndependentFlowObservationV1,
    LegacyHttpEndpointKind,
    LegacyHttpCaptureV1,
    build_capture,
    correlate_outgoing_assertion,
    correlate_system_tcp_assertion,
    parse_outgoing_log,
    parse_system_tcp_log,
    preserve_capture,
    verify_capture,
)

NOW = datetime(2026, 9, 18, 18, 5, 18, tzinfo=UTC)

OUTGOING_HTML = b"""\
<html><body><table>
<tr><th>LAN IP</th><th>Destination URL/IP</th><th>Service/Port Number</th></tr>
<tr><td>192.168.1.2</td><td>1.1.1.1</td><td>HTTP</td></tr>
</table></body></html>
"""

SYSTEM_HTML = b"""\
<html><body><pre>
00:00:00 [192.168.1.1]: System is ready
00:00:00 System is warm start
00:00:00 Firmware Version : 1.04.12, Oct 21 2003
00:06:46 WAN(DHCP) IP is 192.168.86.27
00:09:17 TCP from 192.168.1.2:55516 to 1.1.1.1:80
</pre></body></html>
"""


def _capture(raw: bytes = OUTGOING_HTML) -> LegacyHttpCaptureV1:
    return build_capture(
        raw,
        source_label="synthetic-befsr41v3-fw-1.04.12",
        source_url="http://192.0.2.1/outLogTable.htm",
        endpoint_kind=LegacyHttpEndpointKind.OUTGOING_LOG,
        observer_id="synthetic-t430-eno2",
        acquired_at_utc=NOW,
        http_status=200,
        content_type="text/html",
    )


def test_capture_commits_exact_raw_bytes_before_parsing() -> None:
    capture = _capture()

    assert capture.raw_body_sha256 == hashlib.sha256(OUTGOING_HTML).hexdigest()
    assert capture.raw_body_bytes == len(OUTGOING_HTML)
    assert capture.acquired_at_utc == NOW
    assert capture.authenticated_device_identity is False
    assert capture.completeness_proven is False
    assert capture.semantic_truth_proven is False
    assert capture.independent_observation is False


def test_one_byte_mutation_invalidates_retained_capture() -> None:
    capture = _capture()
    mutated = bytearray(OUTGOING_HTML)
    mutated[-2] ^= 0x01

    assert verify_capture(OUTGOING_HTML, capture) is True
    assert verify_capture(bytes(mutated), capture) is False


def test_preserve_capture_round_trips_raw_artifact_and_metadata(tmp_path: Path) -> None:
    capture = _capture()

    raw_path, metadata_path = preserve_capture(OUTGOING_HTML, capture, tmp_path / "capture")

    assert raw_path.read_bytes() == OUTGOING_HTML
    metadata = LegacyHttpCaptureV1.model_validate_json(metadata_path.read_text("utf-8"))
    assert metadata == capture
    assert verify_capture(raw_path.read_bytes(), metadata) is True


def test_capture_refuses_credentials_in_source_url() -> None:
    with pytest.raises(ValidationError, match="must not contain credentials"):
        build_capture(
            OUTGOING_HTML,
            source_label="synthetic-router",
            source_url="http://admin:secret@192.0.2.1/outLogTable.htm",
            endpoint_kind=LegacyHttpEndpointKind.OUTGOING_LOG,
            observer_id="observer",
            acquired_at_utc=NOW,
        )


def test_outgoing_log_parser_projects_only_device_assertion_fields() -> None:
    assertions = parse_outgoing_log(OUTGOING_HTML)

    assert len(assertions) == 1
    assertion = assertions[0]
    assert assertion.source_lan_ip == "192.168.1.2"
    assert assertion.destination == "1.1.1.1"
    assert assertion.service == "HTTP"
    assert assertion.source_time is None
    assert assertion.source_time_quality == "absent"
    serialized = json.dumps(assertion.model_dump(mode="json"), sort_keys=True)
    assert "synthetic-t430-eno2" not in serialized


def test_system_log_parser_keeps_router_time_relative_and_untrusted() -> None:
    assertions = parse_system_tcp_log(SYSTEM_HTML)

    assert len(assertions) == 1
    assertion = assertions[0]
    assert assertion.relative_time == "00:09:17"
    assert assertion.source_ip == "192.168.1.2"
    assert assertion.source_port == 55516
    assert assertion.destination_ip == "1.1.1.1"
    assert assertion.destination_port == 80
    assert assertion.source_time_quality == "device-relative-untrusted"


def test_outgoing_assertion_can_be_correlated_without_identity_or_truth_upgrade() -> None:
    assertion = parse_outgoing_log(OUTGOING_HTML)[0]
    observation = IndependentFlowObservationV1(
        observer_id="tcpdump:synthetic-t430-eno2",
        observed_at_utc=NOW,
        transport="TCP",
        source_ip="192.168.1.2",
        source_port=55516,
        destination_ip="1.1.1.1",
        destination_port=80,
    )

    result = correlate_outgoing_assertion(assertion, observation)

    assert result.matched is True
    assert result.corroborates_device_assertion is True
    assert result.authenticated_device_identity is False
    assert result.completeness_proven is False
    assert result.semantic_truth_proven is False


def test_system_assertion_requires_full_tcp_tuple_for_exact_correlation() -> None:
    assertion = parse_system_tcp_log(SYSTEM_HTML)[0]
    observation = IndependentFlowObservationV1(
        observer_id="tcpdump:synthetic-t430-eno2",
        observed_at_utc=NOW,
        transport="TCP",
        source_ip="192.168.1.2",
        source_port=55517,
        destination_ip="1.1.1.1",
        destination_port=80,
    )

    result = correlate_system_tcp_assertion(assertion, observation)

    assert result.matched is False
    assert "source_port" not in result.matched_fields
    assert result.corroborates_device_assertion is False


def test_non_html_or_unknown_rows_preserve_raw_capture_without_manufacturing_records() -> None:
    raw = b"\xff\xfelegacy\x00payload"
    capture = _capture(raw)

    assert verify_capture(raw, capture) is True
    assert parse_outgoing_log(raw) == ()
    assert parse_system_tcp_log(raw) == ()
