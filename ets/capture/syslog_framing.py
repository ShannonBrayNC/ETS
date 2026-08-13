"""Bounded RFC 5425 octet-counting stream framing primitives."""

from __future__ import annotations


class SyslogFramingError(ValueError):
    """Raised when an RFC 5425 octet-counted stream frame is invalid."""


class OctetCountingFramer:
    """Incrementally frame RFC 5425 syslog messages with explicit bounds."""

    def __init__(
        self,
        *,
        maximum_message_bytes: int = 8192,
        maximum_prefix_bytes: int = 10,
        maximum_buffer_bytes: int | None = None,
    ) -> None:
        if maximum_message_bytes < 1:
            raise ValueError("maximum_message_bytes must be positive")
        if maximum_prefix_bytes < 1:
            raise ValueError("maximum_prefix_bytes must be positive")
        resolved_buffer_bytes = (
            maximum_message_bytes + maximum_prefix_bytes + 1
            if maximum_buffer_bytes is None
            else maximum_buffer_bytes
        )
        if resolved_buffer_bytes < maximum_message_bytes + 2:
            raise ValueError(
                "maximum_buffer_bytes must accommodate a message and framing prefix"
            )

        self._maximum_message_bytes = maximum_message_bytes
        self._maximum_prefix_bytes = maximum_prefix_bytes
        self._maximum_buffer_bytes = resolved_buffer_bytes
        self._buffer = bytearray()
        self._expected_message_bytes: int | None = None

    @property
    def buffered_bytes(self) -> int:
        """Return the currently retained incomplete frame bytes."""

        return len(self._buffer)

    def feed(self, data: bytes) -> tuple[bytes, ...]:
        """Feed stream bytes and return every complete syslog message produced."""

        if not data:
            return ()

        frames: list[bytes] = []
        offset = 0
        while offset < len(data):
            remaining_capacity = self._maximum_buffer_bytes - len(self._buffer)
            if remaining_capacity <= 0:
                raise SyslogFramingError("syslog framing buffer exceeds configured limit")

            take = min(remaining_capacity, len(data) - offset)
            self._buffer.extend(data[offset : offset + take])
            offset += take
            frames.extend(self._drain_complete_frames())

            if len(self._buffer) >= self._maximum_buffer_bytes and offset < len(data):
                raise SyslogFramingError("syslog framing buffer exceeds configured limit")

        return tuple(frames)

    def finish(self) -> None:
        """Validate that stream shutdown did not leave an incomplete frame."""

        if self._buffer or self._expected_message_bytes is not None:
            raise SyslogFramingError("syslog stream ended with an incomplete frame")

    def _drain_complete_frames(self) -> list[bytes]:
        frames: list[bytes] = []
        while True:
            if self._expected_message_bytes is None:
                expected = self._parse_prefix_if_complete()
                if expected is None:
                    break
                self._expected_message_bytes = expected

            expected_bytes = self._expected_message_bytes
            if expected_bytes is None or len(self._buffer) < expected_bytes:
                break

            frames.append(bytes(self._buffer[:expected_bytes]))
            del self._buffer[:expected_bytes]
            self._expected_message_bytes = None

        return frames

    def _parse_prefix_if_complete(self) -> int | None:
        separator = self._buffer.find(b" ")
        if separator < 0:
            if len(self._buffer) > self._maximum_prefix_bytes:
                raise SyslogFramingError("syslog frame length prefix exceeds configured limit")
            if any(byte < ord("0") or byte > ord("9") for byte in self._buffer):
                raise SyslogFramingError("syslog frame length prefix must be decimal")
            return None

        if separator == 0:
            raise SyslogFramingError("syslog frame length prefix is missing")
        if separator > self._maximum_prefix_bytes:
            raise SyslogFramingError("syslog frame length prefix exceeds configured limit")

        prefix = bytes(self._buffer[:separator])
        if any(byte < ord("0") or byte > ord("9") for byte in prefix):
            raise SyslogFramingError("syslog frame length prefix must be decimal")
        if prefix[0:1] == b"0":
            raise SyslogFramingError("syslog frame length must be a non-zero decimal value")

        expected = int(prefix)
        if expected > self._maximum_message_bytes:
            raise SyslogFramingError("syslog frame exceeds configured message limit")

        del self._buffer[: separator + 1]
        return expected
