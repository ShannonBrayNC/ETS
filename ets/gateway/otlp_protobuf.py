"""Bounded binary-Protobuf decode boundary for Gateway OTLP/HTTP."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, TypeAlias, cast

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError, Message
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from pydantic import ValidationError

from ets.capture.otlp import (
    MAX_OTLP_BATCH_RECORDS,
    OtlpDecodedBatchV1,
    OtlpObservationV1,
    OtlpRejectedRecordV1,
    OtlpSignalClass,
)

OTLP_PROTOBUF_DECODER_PROFILE = "ets.gateway.otlp.protobuf.v1"
OTLP_PROTOBUF_TRANSFORMATION_PROFILE = "ets.gateway.otlp.protobuf-to-semantic.v1"
OtlpRecordRow: TypeAlias = tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    int | None,
]


class OtlpProtobufDecodeError(ValueError):
    """Raised when an OTLP protobuf request cannot enter the bounded semantic contract."""


def decode_otlp_protobuf(signal_class: OtlpSignalClass, payload: bytes) -> OtlpDecodedBatchV1:
    """Decode one binary OTLP export request into bounded semantic observations."""

    request = _parse_request(signal_class, payload)
    rows = list(_iter_records(signal_class, request))
    if len(rows) > MAX_OTLP_BATCH_RECORDS:
        raise OtlpProtobufDecodeError("OTLP request exceeds the configured record count")

    accepted: list[OtlpObservationV1] = []
    rejected: list[OtlpRejectedRecordV1] = []
    for ordinal, (resource, scope, record, source_time_ns) in enumerate(rows):
        try:
            accepted.append(
                OtlpObservationV1(
                    schema_version="ets.otlp.observation.v1",
                    signal_class=signal_class,
                    record_ordinal=ordinal,
                    source_timestamp_utc=_timestamp_from_unix_nano(source_time_ns),
                    decoder_profile=OTLP_PROTOBUF_DECODER_PROFILE,
                    transformation_profile=OTLP_PROTOBUF_TRANSFORMATION_PROFILE,
                    resource_metadata=resource,
                    scope_metadata=scope,
                    record_metadata=record,
                )
            )
        except (TypeError, ValueError, ValidationError):
            rejected.append(
                OtlpRejectedRecordV1(
                    record_ordinal=ordinal,
                    code="invalid_record",
                    field="decoded_record",
                )
            )

    return OtlpDecodedBatchV1(
        schema_version="ets.otlp.decoded_batch.v1",
        signal_class=signal_class,
        total_records=len(rows),
        accepted=accepted,
        rejected=rejected,
    )


def _parse_request(signal_class: OtlpSignalClass, payload: bytes) -> Message:
    if signal_class == "logs":
        request: Message = ExportLogsServiceRequest()
    elif signal_class == "metrics":
        request = ExportMetricsServiceRequest()
    else:
        request = ExportTraceServiceRequest()
    try:
        request.ParseFromString(payload)
    except DecodeError as exc:
        raise OtlpProtobufDecodeError("malformed OTLP protobuf request") from exc
    return request


def _iter_records(signal_class: OtlpSignalClass, request: Message) -> Iterator[OtlpRecordRow]:
    if signal_class == "logs":
        logs_request = cast(Any, request)
        for resource_logs in logs_request.resource_logs:
            resource = _message_mapping(resource_logs.resource)
            for scope_logs in resource_logs.scope_logs:
                scope = _message_mapping(scope_logs.scope)
                for record in scope_logs.log_records:
                    source_time = int(record.time_unix_nano) or None
                    yield resource, scope, _message_mapping(record), source_time
        return

    if signal_class == "metrics":
        metrics_request = cast(Any, request)
        for resource_metrics in metrics_request.resource_metrics:
            resource = _message_mapping(resource_metrics.resource)
            for scope_metrics in resource_metrics.scope_metrics:
                scope = _message_mapping(scope_metrics.scope)
                for metric in scope_metrics.metrics:
                    yield from _metric_rows(resource, scope, metric)
        return

    trace_request = cast(Any, request)
    for resource_spans in trace_request.resource_spans:
        resource = _message_mapping(resource_spans.resource)
        for scope_spans in resource_spans.scope_spans:
            scope = _message_mapping(scope_spans.scope)
            for span in scope_spans.spans:
                source_time = int(span.start_time_unix_nano) or None
                yield resource, scope, _message_mapping(span), source_time


def _metric_rows(
    resource: dict[str, Any],
    scope: dict[str, Any],
    metric: Any,
) -> Iterator[OtlpRecordRow]:
    data_name = metric.WhichOneof("data")
    if data_name is None:
        return
    data = getattr(metric, data_name)
    points = getattr(data, "data_points", ())
    if not points:
        return

    aggregation = _message_mapping(data)
    aggregation.pop("data_points", None)
    descriptor = {
        "name": str(metric.name),
        "description": str(metric.description),
        "unit": str(metric.unit),
        "data_kind": str(data_name),
    }
    for point in points:
        record = {
            "metric": descriptor,
            "aggregation": aggregation,
            "data_point": _message_mapping(point),
        }
        value = int(getattr(point, "time_unix_nano", 0))
        yield resource, scope, record, value or None


def _message_mapping(message: Message) -> dict[str, Any]:
    value = MessageToDict(
        message,
        preserving_proto_field_name=True,
        use_integers_for_enums=False,
    )
    if not isinstance(value, dict):
        raise OtlpProtobufDecodeError("decoded OTLP protobuf record is not a mapping")
    return value


def _timestamp_from_unix_nano(value: int | None) -> datetime | None:
    if value is None:
        return None
    if value < 0:
        raise OtlpProtobufDecodeError("OTLP source timestamp must not be negative")
    seconds, nanoseconds = divmod(value, 1_000_000_000)
    try:
        return datetime.fromtimestamp(seconds, UTC) + timedelta(microseconds=nanoseconds // 1_000)
    except (OverflowError, OSError, ValueError) as exc:
        raise OtlpProtobufDecodeError("OTLP source timestamp is outside supported range") from exc
