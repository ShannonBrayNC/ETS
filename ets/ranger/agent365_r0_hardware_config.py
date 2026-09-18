"""Canonical retained hardware configuration for the physical Agent 365 -> R0 bench."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HARDWARE_PROFILE = "r0-bench-pi-drv8833-dual-vl53l0x.v1"


class StrictHardwareConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class R0BenchGPIOConfigV1(StrictHardwareConfigModel):
    schema_version: Literal["ets.demo.agent365-r0.gpio-config.v1"] = (
        "ets.demo.agent365-r0.gpio-config.v1"
    )
    i2c_sda_bcm: Literal[2] = 2
    i2c_scl_bcm: Literal[3] = 3
    left_in1_bcm: int = Field(ge=0, le=27)
    left_in2_bcm: int = Field(ge=0, le=27)
    right_in1_bcm: int = Field(ge=0, le=27)
    right_in2_bcm: int = Field(ge=0, le=27)
    estop_bcm: int = Field(ge=0, le=27)
    front_xshut_bcm: int = Field(ge=0, le=27)
    rear_xshut_bcm: int = Field(ge=0, le=27)

    @model_validator(mode="after")
    def validate_gpio_assignments(self) -> R0BenchGPIOConfigV1:
        assigned = (
            self.left_in1_bcm,
            self.left_in2_bcm,
            self.right_in1_bcm,
            self.right_in2_bcm,
            self.estop_bcm,
            self.front_xshut_bcm,
            self.rear_xshut_bcm,
        )
        if len(set(assigned)) != len(assigned):
            raise ValueError("R0 bench GPIO assignments must be unique")
        if self.i2c_sda_bcm in assigned or self.i2c_scl_bcm in assigned:
            raise ValueError("R0 bench GPIO assignments must not collide with BCM2/3 I2C")
        return self


class R0BenchHardwareConfigV1(StrictHardwareConfigModel):
    schema_version: Literal["ets.demo.agent365-r0.hardware-config.v1"] = (
        "ets.demo.agent365-r0.hardware-config.v1"
    )
    profile: Literal["r0-bench-pi-drv8833-dual-vl53l0x.v1"] = HARDWARE_PROFILE
    gpio: R0BenchGPIOConfigV1
    calibrated_max_speed_mps: float = Field(gt=0.0, le=0.25)
    max_duty_cycle: float = Field(gt=0.0, le=1.0)
    wheels_off_ground_duty_cycle: float = Field(gt=0.0, le=0.35)
    wheels_off_ground_pulse_seconds: float = Field(gt=0.0, le=1.0)
    wheels_off_ground_max_rear_translation_m: float = Field(gt=0.0, le=0.05)
    front_vl53l0x_address: Literal[48] = 48
    rear_vl53l0x_address: Literal[49] = 49
    estop_wiring: Literal["normally_closed_to_ground_internal_pullup"] = (
        "normally_closed_to_ground_internal_pullup"
    )
    power_boundary: Literal["separate_pi_and_motor_supplies_common_ground"] = (
        "separate_pi_and_motor_supplies_common_ground"
    )


def load_r0_bench_hardware_config(path: str | Path) -> R0BenchHardwareConfigV1:
    return R0BenchHardwareConfigV1.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def hardware_config_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


__all__ = [
    "HARDWARE_PROFILE",
    "R0BenchGPIOConfigV1",
    "R0BenchHardwareConfigV1",
    "hardware_config_sha256",
    "load_r0_bench_hardware_config",
]
