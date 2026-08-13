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
        self._prefix = bytearray()
        self._buffer = bytearray()
        self._expected_message_bytes: int | None = None

    @property
    def buffered_bytes(self) -> int:
        """Return the currently retained incomplete frame bytes."""

        return len(self._prefix) + len(self._buffer)

    def feed(self, data: bytes) -> tuple[bytes, ...]:
        """Feed stream bytes and return every complete syslog message produced."""

        if not data:
            return ()

        frames: list[bytes] = []
        offset = 0
        while offset < len(data):
            if self._expected_message_bytes is None:
                byte = data[offset]
                offset += 1
                if byte == ord(" "):
                    self._expected_message_bytes = self._finish_prefix()
                    continue
                if byte < ord("0") or byte > ord("9"):
                    raise SyslogFramingError("syslog frame length prefix must be decimal")
                if len(self._prefix) >= self._maximum_prefix_bytes:
                    raise SyslogFramingError(
                        "syslog frame length prefix exceeds configured limit"
                    )
                self._prefix.append(byte)
                continue

            expected = self._expected_message_bytes
            if expected is None:
                continue
            remaining_message_bytes = expected - len(self._buffer)
            if remaining_message_bytes <= 0:
                raise SyslogFramingError("invalid syslog framing state")

            take = min(remaining_message_bytes, len(data) - offset)
            if self.buffered_bytes + take > self._maximum_buffer_bytes:
                raise SyslogFramingError("syslog framing buffer exceeds configured limit")
            self._buffer.extend(data[offset : offset + take])
            offset += take

            if len(self._buffer) == expected:
                frames.append(bytes(self._buffer))
                self._buffer.clear()
                self._expected_message_bytes = None

        return tuple(frames)

    def finish(self) -> None:
        """Validate that stream shutdown did not leave an incomplete frame."""

        if self._prefix or self._buffer or self._expected_message_bytes is not None:
            raise SyslogFramingError("syslog stream ended with an incomplete frame")

    def _finish_prefix(self) -> int:
        if not self._prefix:
            raise SyslogFramingError("syslog frame length prefix is missing")
        if self._prefix[0:1] == b"0":
            raise SyslogFramingError("syslog frame length must be a non-zero decimal value")

        expected = int(self._prefix)
        self._prefix.clear()
        if expected > self._maximum_message_bytes:
            raise SyslogFramingError("syslog frame exceeds configured message limit")
        return expected
