"""CLI entry point for omission detection."""

from __future__ import annotations

import json

from ets.core import InMemoryAppendOnlyLog
from ets.experiments.dataset import generate_synthetic_events
from ets.experiments.omission_detection import detect_omissions


def main() -> int:
    log = InMemoryAppendOnlyLog()
    events = generate_synthetic_events(3)
    log.append(events[0])
    log.append(events[2])
    findings = detect_omissions([event.event_id for event in events], log.list_entries())
    print(json.dumps([finding.__dict__ for finding in findings], sort_keys=True))
    return 0 if findings else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
