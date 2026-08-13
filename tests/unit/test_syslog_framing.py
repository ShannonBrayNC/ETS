from __future__ import annotations

import pytest

from ets.capture import OctetCountingFramer, SyslogFramingError


def _frame(message: bytes) -> bytes:
    return str(len(message)).encode("ascii") + b" " + message


def test_framer_accepts_fragmented_prefix_and_payload() -> None:
    framer = OctetCountingFramer()
    message = b"<34>1 - host app 123 ID47 - payload"
    encoded = _frame(message)

    assert framer.feed(encoded[:1]) == ()
    assert framer.feed(encoded[1:4]) == ()
    assert framer.feed(encoded[4:-3]) == ()
    assert framer.feed(encoded[-3:]) == (message,)
    assert framer.buffered_bytes == 0
    framer.finish()


def test_framer_returns_multiple_frames_and_retains_partial_next_frame() -> None:
    framer = OctetCountingFramer()
    first = b"<13>1 - a app p m - one"
    second = b"<13>1 - b app p m - two"
    third = b"<13>1 - c app p m - three"
    third_frame = _frame(third)

    combined = _frame(first) + _frame(second) + third_frame[:-2]
    assert framer.feed(combined) == (first, second)
    assert framer.buffered_bytes > 0
    assert framer.feed(third_frame[-2:]) == (third,)
    framer.finish()


@pytest.mark.parametrize(
    "encoded",
    [
        b" ",
        b"x ",
        b"0 ",
        b"01 x",
    ],
)
def test_framer_rejects_invalid_length_prefixes(encoded: bytes) -> None:
    framer = OctetCountingFramer()
    with pytest.raises(SyslogFramingError):
        framer.feed(encoded)


def test_framer_rejects_prefix_longer_than_configured_bound() -> None:
    framer = OctetCountingFramer(maximum_prefix_bytes=3)

    assert framer.feed(b"123") == ()
    with pytest.raises(SyslogFramingError, match="prefix exceeds"):
        framer.feed(b"4")


def test_framer_rejects_oversize_before_buffering_payload() -> None:
    framer = OctetCountingFramer(maximum_message_bytes=8192)

    with pytest.raises(SyslogFramingError, match="message limit"):
        framer.feed(b"8193 " + (b"x" * 8193))

    assert framer.buffered_bytes == 0


@pytest.mark.parametrize("size", [8191, 8192])
def test_framer_accepts_qualified_message_boundaries(size: int) -> None:
    framer = OctetCountingFramer(maximum_message_bytes=8192)
    message = b"x" * size

    assert framer.feed(_frame(message)) == (message,)
    assert framer.buffered_bytes == 0
    framer.finish()


def test_framer_rejects_message_one_byte_over_qualified_boundary() -> None:
    framer = OctetCountingFramer(maximum_message_bytes=8192)

    with pytest.raises(SyslogFramingError, match="message limit"):
        framer.feed(b"8193 ")

    assert framer.buffered_bytes == 0


def test_framer_retained_bytes_are_bounded_for_incomplete_message() -> None:
    framer = OctetCountingFramer(
        maximum_message_bytes=8,
        maximum_prefix_bytes=2,
        maximum_buffer_bytes=10,
    )

    assert framer.feed(b"8 " + (b"x" * 7)) == ()
    assert framer.buffered_bytes == 7
    assert framer.feed(b"x") == (b"xxxxxxxx",)
    assert framer.buffered_bytes == 0


def test_framer_finish_rejects_incomplete_prefix() -> None:
    framer = OctetCountingFramer()
    assert framer.feed(b"12") == ()

    with pytest.raises(SyslogFramingError, match="incomplete frame"):
        framer.finish()


def test_framer_finish_rejects_incomplete_payload() -> None:
    framer = OctetCountingFramer()
    assert framer.feed(b"3 ab") == ()

    with pytest.raises(SyslogFramingError, match="incomplete frame"):
        framer.finish()


def test_framer_finish_accepts_clean_shutdown() -> None:
    framer = OctetCountingFramer()
    assert framer.feed(b"3 abc") == (b"abc",)
    framer.finish()
