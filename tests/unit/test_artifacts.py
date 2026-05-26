from datetime import UTC, datetime

import pytest

from ets.core.artifacts import (
    build_artifact_event_id,
    build_artifact_reference_uri,
    create_artifact_record,
    decode_artifact_base64,
    hash_artifact_bytes,
    normalize_artifact_metadata,
)


def test_decode_artifact_base64_decodes_valid_content() -> None:
    assert decode_artifact_base64("aGVsbG8=") == b"hello"


def test_decode_artifact_base64_rejects_invalid_content() -> None:
    with pytest.raises(ValueError):
        decode_artifact_base64("not valid base64")


def test_hash_artifact_bytes_is_content_based() -> None:
    assert hash_artifact_bytes(b"same") == hash_artifact_bytes(b"same")
    assert hash_artifact_bytes(b"same") != hash_artifact_bytes(b"same.")


def test_normalize_artifact_metadata_rejects_non_json_native_values() -> None:
    with pytest.raises(TypeError):
        normalize_artifact_metadata({"bad": object()})


def test_build_artifact_event_id_and_reference_uri_are_deterministic() -> None:
    assert build_artifact_event_id("artifact-001") == "artifact_registered:artifact-001"
    assert build_artifact_reference_uri("artifact-001") == "ets://artifact/artifact-001"


def test_build_artifact_helpers_reject_empty_artifact_id() -> None:
    with pytest.raises(ValueError):
        build_artifact_event_id("")
    with pytest.raises(ValueError):
        build_artifact_reference_uri("")


def test_create_artifact_record_excludes_raw_bytes() -> None:
    record = create_artifact_record(
        artifact_id="artifact-001",
        artifact_hash="a" * 64,
        reference_uri="ets://artifact/artifact-001",
        content_type="application/json",
        byte_size=42,
        metadata={"case": "synthetic"},
        ingestion_timestamp_utc=datetime(2026, 5, 26, 12, 0, tzinfo=UTC),
        event_id="artifact_registered:artifact-001",
        log_index=0,
    )

    assert record.artifact_hash == "a" * 64
    assert record.byte_size == 42
    assert not hasattr(record, "artifact_bytes")


def test_create_artifact_record_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        create_artifact_record(
            artifact_id="artifact-001",
            artifact_hash="bad",
            reference_uri="ets://artifact/artifact-001",
            content_type="application/json",
            byte_size=42,
            metadata={},
            ingestion_timestamp_utc=datetime(2026, 5, 26, 12, 0, tzinfo=UTC),
            event_id="artifact_registered:artifact-001",
            log_index=0,
        )
    with pytest.raises(ValueError):
        create_artifact_record(
            artifact_id="artifact-001",
            artifact_hash="a" * 64,
            reference_uri="ets://artifact/artifact-001",
            content_type="application/json",
            byte_size=-1,
            metadata={},
            ingestion_timestamp_utc=datetime(2026, 5, 26, 12, 0, tzinfo=UTC),
            event_id="artifact_registered:artifact-001",
            log_index=0,
        )
    with pytest.raises(ValueError):
        create_artifact_record(
            artifact_id="artifact-001",
            artifact_hash="a" * 64,
            reference_uri="ets://artifact/artifact-001",
            content_type="application/json",
            byte_size=42,
            metadata={},
            ingestion_timestamp_utc=datetime(2026, 5, 26, 12, 0),
            event_id="artifact_registered:artifact-001",
            log_index=0,
        )
