import pytest

from ets.experiments.liveness import (
    LivenessSchedule,
    simulate_bounded_liveness,
    validate_liveness_schedule,
)


def test_validate_liveness_schedule_accepts_bounded_schedule() -> None:
    validate_liveness_schedule(
        LivenessSchedule(
            partition_until_step=2,
            adversarial_pressure_until_step=3,
            max_steps=5,
        )
    )


def test_validate_liveness_schedule_rejects_invalid_schedule() -> None:
    with pytest.raises(ValueError):
        validate_liveness_schedule(
            LivenessSchedule(
                partition_until_step=-1,
                adversarial_pressure_until_step=0,
                max_steps=5,
            )
        )
    with pytest.raises(ValueError):
        validate_liveness_schedule(
            LivenessSchedule(
                partition_until_step=0,
                adversarial_pressure_until_step=0,
                max_steps=0,
            )
        )


def test_simulate_bounded_liveness_reports_eventual_convergence() -> None:
    result = simulate_bounded_liveness(
        LivenessSchedule(
            partition_until_step=2,
            adversarial_pressure_until_step=3,
            max_steps=5,
        )
    )

    assert result.replay_completed is True
    assert result.partition_healed is True
    assert result.witness_propagated is True
    assert result.stale_state_recovered is True
    assert result.convergence_step == 3
    assert result.bounded_progress is True
    assert "weak fairness" in result.assumptions[2]


def test_simulate_bounded_liveness_reports_unhealed_partition() -> None:
    result = simulate_bounded_liveness(
        LivenessSchedule(
            partition_until_step=10,
            adversarial_pressure_until_step=1,
            max_steps=5,
        )
    )

    assert result.partition_healed is False
    assert result.bounded_progress is False
    assert result.convergence_step is None
