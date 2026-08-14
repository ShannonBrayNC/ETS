from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.capture.otlp import (
    MAX_OTLP_MAPPING_ITEMS,
    MAX_OTLP_STRING_CHARS,
    OtlpDecodedBatchV1,
    OtlpObservationV1,
    OtlpRejectedRecordV1,
)


def _observation(
    *,
    signal_class: str = "logs",
    ordinal: int = 0,
    **overrides: object,
) -> OtlpObservationV1:
    values: dict[str, object] = {
        "schema_version": "ets.otlp.observation.v1",
        "signal_class": signal_class,
        "record_ordinal": ordinal,
        "source_timestamp_utc": datetime(2026, 8, 14, 0, 0, tzinfo=UTC),
        "decoder_profile": "otlp-semantic.v1",
        "transformation_profile": "otlp-metadata.v1",
        "resource_metadata": {"service.name": "example"},
        "scope_metadata": {"name": "demo-scope", "version": "1.0"},
        "record_metadata": {"severity": "INFO"},
    }
    values.update(overrides)
    return OtlpObservationV1.model_validate(values)


@pytest.mark.parametrize("signal_class", ["logs", "metrics", "traces"])
def test_otlp_observation_accepts_declared_signal_classes(signal_class: str) -> None:
    observation = _observation(signal_class=signal_class)
    assert observation.signal_class == signal_class


def test_otlp_observation_normalizes_source_time_to_utc() -> None:
    source_time = datetime(2026, 8, 13, 20, 0, tzinfo=timezone_offset())
    observation = _observation(source_timestamp_utc=source_time)
    assert observation.source_timestamp_utc == datetime(2026, 8, 14, 0, 0, tzinfo=UTC)


def timezone_offset() -> object:
    return UTC - timedelta(hours=0)


def test_otlp_observation_rejects_naive_source_time() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _observation(source_timestamp_utc=datetime(2026, 8, 14, 0, 0))


def test_otlp_observation_forbids_server_authorization_and_commitment_fields() -> None:
    with pytest.raises(ValidationError, match="tenant_id"):
        _observation(tenant_id="tenant-untrusted")
    with pytest.raises(ValidationError, match="commitment_state"):
        _observation(commitment_state="committed")


def test_otlp_metadata_repr_does_not_echo_values() -> None:
    marker = "RAW-OTLP-MARKER"
    observation = _observation(record_metadata={"message": marker})
    assert marker not in repr(observation)


def test_otlp_metadata_rejects_non_json_values_and_non_finite_numbers() -> None:
    with pytest.raises(ValidationError, match="JSON-native"):
        _observation(record_metadata={"bytes": b"raw"})
    with pytest.raises(ValidationError, match="finite"):
        _observation(record_metadata={"ratio": float("nan")})


def test_otlp_metadata_rejects_oversize_key_string_and_item_count() -> None:
    with pytest.raises(ValidationError, match="keys"):
        _observation(record_metadata={"k" * 257: "x"})
    with pytest.raises(ValidationError, match="string"):
        _observation(record_metadata={"message": "x" * (MAX_OTLP_STRING_CHARS + 1)})
    too_many = {f"k{index}": index for index in range(MAX_OTLP_MAPPING_ITEMS + 1)}
    with pytest.raises(ValidationError, match="item count"):
        _observation(record_metadata=too_many)


def test_otlp_metadata_rejects_excessive_nesting_and_serialized_size() -> None:
    too_deep = {"a": {"b": {"c": {"d": {"e": "x"}}}}}
    with pytest.raises(ValidationError, match="nesting depth"):
        _observation(record_metadata=too_deep)

    large_mapping = {f"k{index}": "x" * 4096 for index in range(5)}
    with pytest.raises(ValidationError, match="16 KiB"):
        _observation(record_metadata=large_mapping)


def test_otlp_decoded_batch_reports_partial_acceptance_explicitly() -> None:
    accepted = _observation(signal_class="logs", ordinal=0)
    rejected = OtlpRejectedRecordV1(
        record_ordinal=1,
        code="limit_exceeded",
        field="attributes",
    )
    batch = OtlpDecodedBatchV1(
        schema_version="ets.otlp.decoded_batch.v1",
        signal_class="logs",
        total_records=2,
        accepted=[accepted],
        rejected=[rejected],
    )
    assert len(batch.accepted) == 1
    assert len(batch.rejected) == 1


def test_otlp_decoded_batch_requires_complete_unique_accounting() -> None:
    accepted = _observation(ordinal=0)
    with pytest.raises(ValidationError, match="include every decoded record"):
        OtlpDecodedBatchV1(
            schema_version="ets.otlp.decoded_batch.v1",
            signal_class="logs",
            total_records=2,
            accepted=[accepted],
            rejected=[],
        )

    duplicate = OtlpRejectedRecordV1(record_ordinal=0, code="invalid_record")
    with pytest.raises(ValidationError, match="ordinals must be unique"):
        OtlpDecodedBatchV1(
            schema_version="ets.otlp.decoded_batch.v1",
            signal_class="logs",
            total_records=2,
            accepted=[accepted],
            rejected=[duplicate],
        )


def test_otlp_decoded_batch_rejects_cross_signal_observations() -> None:
    metric = _observation(signal_class="metrics", ordinal=0)
    with pytest.raises(ValidationError, match="match the batch signal class"):
        OtlpDecodedBatchV1(
            schema_version="ets.otlp.decoded_batch.v1",
            signal_class="logs",
            total_records=1,
            accepted=[metric],
            rejected=[],
        )


def test_otlp_rejection_contract_cannot_carry_raw_source_value() -> None:
    with pytest.raises(ValidationError, match="raw_value"):
        OtlpRejectedRecordV1.model_validate(
            {
                "record_ordinal": 0,
                "code": "invalid_record",
                "raw_value": "sensitive",
            }
        )
