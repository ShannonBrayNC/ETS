from ets.core import InMemoryAppendOnlyLog
from ets.experiments.dataset import generate_synthetic_events
from ets.experiments.fork_simulation import run_fork_simulation
from ets.experiments.omission_detection import detect_omissions


def test_generate_synthetic_events_uses_no_real_pii() -> None:
    events = generate_synthetic_events(2)

    assert [event.event_id for event in events] == ["evt_lab_0000", "evt_lab_0001"]
    assert "@" not in str(events[0].metadata)


def test_fork_simulation_detects_fork() -> None:
    result = run_fork_simulation(3)

    assert result.fork_detected is True
    assert result.left_root != result.right_root


def test_omission_detection_reports_missing_expected_event() -> None:
    log = InMemoryAppendOnlyLog()
    events = generate_synthetic_events(3)
    log.append(events[0])
    log.append(events[2])

    findings = detect_omissions([event.event_id for event in events], log.list_entries())

    assert [finding.event_id for finding in findings] == ["evt_lab_0001"]
