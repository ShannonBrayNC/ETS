from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.ranger.agent365_r0_hardware_config import (
    R0BenchGPIOConfigV1,
    hardware_config_sha256,
    load_r0_bench_hardware_config,
)


def test_canonical_hardware_config_loads_with_expected_gpio_map() -> None:
    path = Path("config/ranger/r0-bench-pi-drv8833-dual-vl53l0x.v1.json")
    config = load_r0_bench_hardware_config(path)

    assert config.gpio.i2c_sda_bcm == 2
    assert config.gpio.i2c_scl_bcm == 3
    assert config.gpio.left_in1_bcm == 12
    assert config.gpio.left_in2_bcm == 16
    assert config.gpio.right_in1_bcm == 13
    assert config.gpio.right_in2_bcm == 19
    assert config.gpio.estop_bcm == 17
    assert config.gpio.front_xshut_bcm == 22
    assert config.gpio.rear_xshut_bcm == 27
    assert config.calibrated_max_speed_mps == pytest.approx(0.15)
    assert config.max_duty_cycle == pytest.approx(0.55)
    assert len(hardware_config_sha256(path)) == 64


def test_gpio_config_rejects_duplicate_assignments() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        R0BenchGPIOConfigV1(
            left_in1_bcm=12,
            left_in2_bcm=12,
            right_in1_bcm=13,
            right_in2_bcm=19,
            estop_bcm=17,
            front_xshut_bcm=22,
            rear_xshut_bcm=27,
        )


def test_gpio_config_rejects_i2c_collision() -> None:
    with pytest.raises(ValidationError, match="must not collide with BCM2/3 I2C"):
        R0BenchGPIOConfigV1(
            left_in1_bcm=2,
            left_in2_bcm=16,
            right_in1_bcm=13,
            right_in2_bcm=19,
            estop_bcm=17,
            front_xshut_bcm=22,
            rear_xshut_bcm=27,
        )
