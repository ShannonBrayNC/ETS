"""Product-neutral bounded streaming digest helpers for captured objects."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


class BinaryStream(Protocol):
    """Minimum byte-stream behavior required by the digest primitive."""

    def read(self, size: int = -1) -> bytes:
        """Read at most ``size`` bytes from the stream."""


class StreamDigestError(ValueError):
    """Base error for streamed digest validation failures."""


class StreamDigestLimitError(StreamDigestError):
    """Raised when a stream exceeds the configured object-size bound."""


class StreamDigestLengthError(StreamDigestError):
    """Raised when observed bytes do not match a declared object length."""


@dataclass(frozen=True, slots=True)
class StreamDigestResult:
    """Digest result without source-stability or ETS-commitment claims."""

    algorithm: str
    value: str
    byte_count: int
    declared_length: int | None
    source_stability: str = "not_evaluated"
    commitment_state: str = "not_committed"
    raw_object_retained: bool = False


def digest_stream_sha256(
    stream: BinaryStream,
    *,
    maximum_bytes: int,
    chunk_size: int = 64 * 1024,
    declared_length: int | None = None,
) -> StreamDigestResult:
    """Incrementally hash one bounded byte stream with SHA-256.

    The primitive deliberately makes no claim that the source object remained
    stable before, during, or after the read, and it does not commit evidence.
    """

    if maximum_bytes < 0:
        raise ValueError("maximum_bytes must be non-negative")
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if declared_length is not None:
        if declared_length < 0:
            raise ValueError("declared_length must be non-negative")
        if declared_length > maximum_bytes:
            raise StreamDigestLimitError("declared length exceeds configured object limit")

    hasher = hashlib.sha256()
    observed = 0

    while True:
        remaining_limit = maximum_bytes - observed
        read_size = min(chunk_size, remaining_limit + 1)
        if declared_length is not None:
            remaining_declared = declared_length - observed
            read_size = min(read_size, max(1, remaining_declared + 1))

        chunk = stream.read(read_size)
        if not isinstance(chunk, bytes):
            raise TypeError("stream.read() must return bytes")
        if len(chunk) > read_size:
            raise StreamDigestError("stream returned more bytes than requested")
        if not chunk:
            if declared_length is not None and observed != declared_length:
                raise StreamDigestLengthError(
                    f"declared length mismatch: expected {declared_length} bytes, observed {observed}"
                )
            return StreamDigestResult(
                algorithm="sha256",
                value=hasher.hexdigest(),
                byte_count=observed,
                declared_length=declared_length,
            )

        next_observed = observed + len(chunk)
        if next_observed > maximum_bytes:
            raise StreamDigestLimitError("stream exceeds configured object limit")
        if declared_length is not None and next_observed > declared_length:
            raise StreamDigestLengthError(
                f"declared length mismatch: expected {declared_length} bytes, observed more"
            )

        hasher.update(chunk)
        observed = next_observed
