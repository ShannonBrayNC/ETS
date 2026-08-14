from __future__ import annotations

import hashlib
from io import BytesIO

import pytest

from ets.capture.object_digest import (
    StreamDigestError,
    StreamDigestLengthError,
    StreamDigestLimitError,
    digest_stream_sha256,
)


@pytest.mark.parametrize(
    ("payload", "maximum_bytes"),
    [
        (b"", 0),
        (b"ets", 3),
        (b"x" * 64, 64),
        (b"y" * 8192, 8192),
    ],
)
def test_digest_stream_accepts_empty_small_and_exact_bound(
    payload: bytes,
    maximum_bytes: int,
) -> None:
    result = digest_stream_sha256(BytesIO(payload), maximum_bytes=maximum_bytes)

    assert result.algorithm == "sha256"
    assert result.value == hashlib.sha256(payload).hexdigest()
    assert result.byte_count == len(payload)
    assert result.declared_length is None
    assert result.source_stability == "not_evaluated"
    assert result.commitment_state == "not_committed"
    assert result.raw_object_retained is False


def test_digest_stream_rejects_one_byte_over_bound() -> None:
    with pytest.raises(StreamDigestLimitError, match="configured object limit"):
        digest_stream_sha256(BytesIO(b"x" * 8193), maximum_bytes=8192)


@pytest.mark.parametrize("chunk_size", [1, 7, 63, 64, 65, 1024, 4096])
def test_digest_is_independent_of_read_segmentation(chunk_size: int) -> None:
    payload = (b"lantern-evidence-" * 700) + b"tail"

    result = digest_stream_sha256(
        BytesIO(payload),
        maximum_bytes=len(payload),
        chunk_size=chunk_size,
    )

    assert result.value == hashlib.sha256(payload).hexdigest()
    assert result.byte_count == len(payload)


class GeneratedReader:
    def __init__(self, total_bytes: int) -> None:
        self.remaining = total_bytes
        self.maximum_requested = 0

    def read(self, size: int = -1) -> bytes:
        assert size >= 0
        self.maximum_requested = max(self.maximum_requested, size)
        if self.remaining == 0:
            return b""
        produced = min(size, self.remaining)
        self.remaining -= produced
        return b"z" * produced


def test_large_generated_stream_uses_bounded_read_requests() -> None:
    total_bytes = 5 * 1024 * 1024
    chunk_size = 4096
    reader = GeneratedReader(total_bytes)

    result = digest_stream_sha256(
        reader,
        maximum_bytes=total_bytes,
        chunk_size=chunk_size,
        declared_length=total_bytes,
    )

    assert result.byte_count == total_bytes
    assert result.value == hashlib.sha256(b"z" * total_bytes).hexdigest()
    assert reader.maximum_requested <= chunk_size


def test_declared_length_exact_match_is_recorded() -> None:
    payload = b"declared-length"

    result = digest_stream_sha256(
        BytesIO(payload),
        maximum_bytes=1024,
        declared_length=len(payload),
    )

    assert result.declared_length == len(payload)
    assert result.byte_count == len(payload)


def test_declared_length_classifies_premature_eof() -> None:
    with pytest.raises(StreamDigestLengthError, match=r"expected 10 bytes, observed 5"):
        digest_stream_sha256(
            BytesIO(b"short"),
            maximum_bytes=100,
            declared_length=10,
        )


def test_declared_length_classifies_extra_bytes() -> None:
    with pytest.raises(StreamDigestLengthError, match=r"expected 4 bytes, observed more"):
        digest_stream_sha256(
            BytesIO(b"extra"),
            maximum_bytes=100,
            declared_length=4,
        )


def test_declared_length_over_bound_fails_before_reading() -> None:
    reader = GeneratedReader(10)

    with pytest.raises(StreamDigestLimitError, match="declared length"):
        digest_stream_sha256(reader, maximum_bytes=9, declared_length=10)

    assert reader.maximum_requested == 0


def test_result_and_errors_do_not_disclose_raw_marker() -> None:
    marker = b"RAW-SECRET-MARKER"
    result = digest_stream_sha256(BytesIO(marker), maximum_bytes=len(marker))
    assert marker.decode() not in repr(result)

    with pytest.raises(StreamDigestLimitError) as exc_info:
        digest_stream_sha256(BytesIO(marker), maximum_bytes=4)
    assert marker.decode() not in str(exc_info.value)


@pytest.mark.parametrize(
    ("maximum_bytes", "chunk_size", "declared_length", "message"),
    [
        (-1, 1, None, "maximum_bytes"),
        (1, 0, None, "chunk_size"),
        (1, 1, -1, "declared_length"),
    ],
)
def test_digest_stream_rejects_invalid_configuration(
    maximum_bytes: int,
    chunk_size: int,
    declared_length: int | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        digest_stream_sha256(
            BytesIO(b""),
            maximum_bytes=maximum_bytes,
            chunk_size=chunk_size,
            declared_length=declared_length,
        )


class InvalidReader:
    def read(self, size: int = -1) -> bytes:  # type: ignore[return-value]
        return "not-bytes"  # type: ignore[return-value]


def test_digest_stream_rejects_non_bytes_reader() -> None:
    with pytest.raises(TypeError, match="must return bytes"):
        digest_stream_sha256(InvalidReader(), maximum_bytes=10)


class OversizedReader:
    def read(self, size: int = -1) -> bytes:
        return b"x" * (size + 1)


def test_digest_stream_rejects_reader_that_exceeds_requested_size() -> None:
    with pytest.raises(StreamDigestError, match="more bytes than requested"):
        digest_stream_sha256(OversizedReader(), maximum_bytes=10, chunk_size=4)
