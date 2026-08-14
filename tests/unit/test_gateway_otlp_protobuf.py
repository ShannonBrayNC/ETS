from __future__ import annotations

import json

import pytest
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

from ets.gateway.otlp_protobuf import OtlpProtobufDecodeError, decode_otlp_protobuf

SOURCE_TIME_NS = 1_786_660_800_123_456_000


def _add_attribute(container: object, key: str, value: str) -> None:
    attribute = container.attributes.add()  # type: ignore[attr-defined]
    attribute.key = key
    attribute.value.string_value = value


def _logs_request(*, body: str = "log body") -> ExportLogsServiceRequest:
    request = ExportLogsServiceRequest()
    resource_logs = request.resource_logs.add()
    _add_attribute(resource_logs.resource, "service.name", "orders")
    scope_logs = resource_logs.scope_logs.add()
    scope_logs.scope.name = "orders.instrumentation"
    record = scope_logs.log_records.add()
    record.time_unix_nano = SOURCE_TIME_NS
    record.severity_text = "INFO"
    record.body.string_value = body
    _add_attribute(record, "region", "us-east")
    return request


def test_otlp_log_decoder_omits_raw_body_and_preserves_body_digest() -> None:
    marker = "RAW-OTLP-LOG-BODY-MARKER"
    decoded = decode_otlp_protobuf("logs", _logs_request(body=marker).SerializeToString())

    assert decoded.total_records == 1
    assert len(decoded.accepted) == 1
    observation = decoded.accepted[0]
    serialized = json.dumps(observation.record_metadata, sort_keys=True)
    assert marker not in serialized
    assert observation.record_metadata["body_present"] is True
    digest = observation.record_metadata["body_digest"]
    assert isinstance(digest, dict)
    assert digest["algorithm"] == "sha256"
    assert len(str(digest["value"])) == 64
    assert observation.resource_metadata["attributes"][0]["key"] == "service.name"


def test_otlp_decoder_partially_rejects_overbound_log_metadata() -> None:
    request = _logs_request()
    scope_logs = request.resource_logs[0].scope_logs[0]
    rejected = scope_logs.log_records.add()
    rejected.time_unix_nano = SOURCE_TIME_NS + 1
    _add_attribute(rejected, "oversized", "x" * 5000)

    decoded = decode_otlp_protobuf("logs", request.SerializeToString())

    assert decoded.total_records == 2
    assert len(decoded.accepted) == 1
    assert len(decoded.rejected) == 1
    assert decoded.rejected[0].record_ordinal == 1
    assert decoded.rejected[0].code == "invalid_record"


def test_otlp_metric_decoder_counts_data_points_not_metric_envelopes() -> None:
    request = ExportMetricsServiceRequest()
    resource_metrics = request.resource_metrics.add()
    scope_metrics = resource_metrics.scope_metrics.add()
    metric = scope_metrics.metrics.add()
    metric.name = "request.duration"
    metric.unit = "ms"
    first = metric.gauge.data_points.add()
    first.time_unix_nano = SOURCE_TIME_NS
    first.as_double = 12.5
    second = metric.gauge.data_points.add()
    second.time_unix_nano = SOURCE_TIME_NS + 1000
    second.as_double = 15.0

    decoded = decode_otlp_protobuf("metrics", request.SerializeToString())

    assert decoded.total_records == 2
    assert len(decoded.accepted) == 2
    assert decoded.accepted[0].record_metadata["metric"]["name"] == "request.duration"
    assert decoded.accepted[1].record_ordinal == 1


def test_otlp_trace_decoder_preserves_source_time_as_non_authoritative_metadata() -> None:
    request = ExportTraceServiceRequest()
    resource_spans = request.resource_spans.add()
    scope_spans = resource_spans.scope_spans.add()
    span = scope_spans.spans.add()
    span.name = "checkout"
    span.start_time_unix_nano = SOURCE_TIME_NS
    span.end_time_unix_nano = SOURCE_TIME_NS + 10_000

    decoded = decode_otlp_protobuf("traces", request.SerializeToString())

    assert decoded.total_records == 1
    assert decoded.accepted[0].source_timestamp_utc is not None
    assert decoded.accepted[0].record_metadata["name"] == "checkout"


def test_otlp_decoder_rejects_malformed_protobuf() -> None:
    with pytest.raises(OtlpProtobufDecodeError, match="malformed"):
        decode_otlp_protobuf("logs", b"\xff\xff\xff")


def test_otlp_decoder_rejects_batch_over_record_limit() -> None:
    request = ExportLogsServiceRequest()
    resource_logs = request.resource_logs.add()
    scope_logs = resource_logs.scope_logs.add()
    for index in range(1001):
        record = scope_logs.log_records.add()
        record.time_unix_nano = SOURCE_TIME_NS + index

    with pytest.raises(OtlpProtobufDecodeError, match="record count"):
        decode_otlp_protobuf("logs", request.SerializeToString())
