"""Bounded liveness and fairness experiments for ETS federation research."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LivenessSchedule:
    partition_until_step: int
    adversarial_pressure_until_step: int
    max_steps: int


@dataclass(frozen=True)
class LivenessResult:
    replay_completed: bool
    partition_healed: bool
    witness_propagated: bool
    stale_state_recovered: bool
    convergence_step: int | None
    bounded_progress: bool
    assumptions: list[str]


def validate_liveness_schedule(schedule: LivenessSchedule) -> None:
    if schedule.partition_until_step < 0:
        raise ValueError("partition_until_step must be non-negative")
    if schedule.adversarial_pressure_until_step < 0:
        raise ValueError("adversarial_pressure_until_step must be non-negative")
    if schedule.max_steps < 1:
        raise ValueError("max_steps must be at least 1")


def simulate_bounded_liveness(schedule: LivenessSchedule) -> LivenessResult:
    """Simulate eventual progress after partition and adversarial pressure end.

    This is a bounded executable hypothesis, not a proof of Internet-scale
    liveness or Byzantine convergence.
    """

    validate_liveness_schedule(schedule)
    replay_completed = False
    witness_propagated = False
    stale_state_recovered = False
    convergence_step: int | None = None

    for step in range(schedule.max_steps + 1):
        partition_active = step < schedule.partition_until_step
        adversarial_pressure_active = step < schedule.adversarial_pressure_until_step
        if partition_active or adversarial_pressure_active:
            continue

        replay_completed = True
        witness_propagated = True
        stale_state_recovered = True
        convergence_step = step
        break

    partition_healed = schedule.partition_until_step <= schedule.max_steps
    bounded_progress = convergence_step is not None
    return LivenessResult(
        replay_completed=replay_completed,
        partition_healed=partition_healed,
        witness_propagated=witness_propagated,
        stale_state_recovered=stale_state_recovered,
        convergence_step=convergence_step,
        bounded_progress=bounded_progress,
        assumptions=[
            "eventual partition healing",
            "bounded adversarial pressure",
            "weak fairness for enabled propagation and recovery actions",
        ],
    )
