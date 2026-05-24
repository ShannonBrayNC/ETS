"""Omission detection helpers for expected event IDs."""

from __future__ import annotations

from dataclasses import dataclass

from ets.core.log import LogEntry


@dataclass(frozen=True)
class OmissionFinding:
    event_id: str
    reason: str


def detect_omissions(
    expected_event_ids: list[str],
    entries: list[LogEntry],
) -> list[OmissionFinding]:
    observed = {entry.event.event_id for entry in entries}
    return [
        OmissionFinding(event_id=event_id, reason="expected event missing from log")
        for event_id in expected_event_ids
        if event_id not in observed
    ]
