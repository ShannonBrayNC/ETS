import pytest

from ets.experiments.async_network import (
    NetworkConfig,
    simulate_async_broadcast,
    validate_network_config,
)


def test_validate_network_config_accepts_bounded_profile() -> None:
    validate_network_config(
        NetworkConfig(
            seed=7,
            min_delay_ms=1,
            max_delay_ms=10,
            packet_loss_probability=0.1,
            partial_synchrony_bound_ms=20,
        )
    )


def test_validate_network_config_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError):
        validate_network_config(
            NetworkConfig(
                seed=7,
                min_delay_ms=5,
                max_delay_ms=4,
                packet_loss_probability=0.0,
                partial_synchrony_bound_ms=10,
            )
        )


def test_simulate_async_broadcast_is_deterministic_for_seed() -> None:
    config = NetworkConfig(
        seed=7,
        min_delay_ms=1,
        max_delay_ms=10,
        packet_loss_probability=0.0,
        partial_synchrony_bound_ms=10,
    )

    first = simulate_async_broadcast("log-a", ["v1", "v2", "v3"], {"root": "a"}, config)
    second = simulate_async_broadcast("log-a", ["v1", "v2", "v3"], {"root": "a"}, config)

    assert first == second
    assert first.delivered_count == 3
    assert first.lost_count == 0
    assert first.converged_within_bound is True
    assert sorted(first.delivery_order) == ["v1", "v2", "v3"]


def test_simulate_async_broadcast_models_packet_loss() -> None:
    config = NetworkConfig(
        seed=7,
        min_delay_ms=1,
        max_delay_ms=10,
        packet_loss_probability=1.0,
        partial_synchrony_bound_ms=10,
    )

    result = simulate_async_broadcast("log-a", ["v1", "v2"], {"root": "a"}, config)

    assert result.delivered_count == 0
    assert result.lost_count == 2
    assert result.converged_within_bound is False
    assert result.max_observed_delay_ms is None
    assert result.delivery_order == []


def test_simulate_async_broadcast_reports_partial_synchrony_violation() -> None:
    config = NetworkConfig(
        seed=7,
        min_delay_ms=50,
        max_delay_ms=50,
        packet_loss_probability=0.0,
        partial_synchrony_bound_ms=49,
    )

    result = simulate_async_broadcast("log-a", ["v1"], {"root": "a"}, config)

    assert result.delivered_count == 1
    assert result.max_observed_delay_ms == 50
    assert result.converged_within_bound is False


def test_simulate_async_broadcast_can_preserve_transport_order() -> None:
    config = NetworkConfig(
        seed=7,
        min_delay_ms=1,
        max_delay_ms=10,
        packet_loss_probability=0.0,
        partial_synchrony_bound_ms=10,
        allow_reordering=False,
    )

    result = simulate_async_broadcast("log-a", ["v1", "v2", "v3"], {"root": "a"}, config)

    assert result.delivery_order == ["v1", "v2", "v3"]
