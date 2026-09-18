#!/usr/bin/env python3
"""Explicitly armed wheels-off-ground qualification for the physical R0 bench."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ets.ranger.agent365_r0_bench_hardware import (
    GpioZeroDrv8833Backend,
    GpioZeroNormallyClosedEstop,
    create_dual_vl53l0x_backends,
)
from ets.ranger.agent365_r0_hardware_config import (
    hardware_config_sha256,
    load_r0_bench_hardware_config,
)
from ets.ranger.agent365_r0_wheels_off_ground import (
    R0WheelsOffGroundConfigV1,
    run_wheels_off_ground_pulse,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one bounded motor pulse with the R0 chassis physically supported. "
            "This gate never infers wheel direction or chassis translation from the motor command."
        )
    )
    parser.add_argument("--execute-wheels-off-ground", action="store_true")
    parser.add_argument("--hardware-config", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.execute_wheels_off_ground:
        raise SystemExit(
            "Refusing motor initialization without --execute-wheels-off-ground"
        )

    hardware = load_r0_bench_hardware_config(args.hardware_config)
    gpio = hardware.gpio
    config = R0WheelsOffGroundConfigV1(
        duty_cycle=hardware.wheels_off_ground_duty_cycle,
        pulse_seconds=hardware.wheels_off_ground_pulse_seconds,
        max_rear_translation_m=hardware.wheels_off_ground_max_rear_translation_m,
    )

    motor: GpioZeroDrv8833Backend | None = None
    estop: GpioZeroNormallyClosedEstop | None = None
    try:
        motor = GpioZeroDrv8833Backend(
            left_in1_pin=gpio.left_in1_bcm,
            left_in2_pin=gpio.left_in2_bcm,
            right_in1_pin=gpio.right_in1_bcm,
            right_in2_pin=gpio.right_in2_bcm,
        )
        estop = GpioZeroNormallyClosedEstop(gpio.estop_bcm)
        front, rear = create_dual_vl53l0x_backends(
            front_xshut_pin=gpio.front_xshut_bcm,
            rear_xshut_pin=gpio.rear_xshut_bcm,
            front_address=hardware.front_vl53l0x_address,
            rear_address=hardware.rear_vl53l0x_address,
        )
        result = run_wheels_off_ground_pulse(
            motor=motor,
            front_sensor=front,
            rear_sensor=rear,
            estop=estop,
            config=config,
        )
        payload_obj = result.model_dump(mode="json")
        payload_obj["hardware_config_sha256"] = hardware_config_sha256(
            args.hardware_config
        )
        payload_obj["gpio"] = gpio.model_dump(mode="json")
        payload = json.dumps(
            payload_obj,
            indent=2,
            sort_keys=True,
        ) + "\n"
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload, encoding="utf-8")
        print(payload, end="")
        return 0 if result.automated_checks_passed else 2
    finally:
        if motor is not None:
            try:
                motor.stop()
            finally:
                motor.close()
        if estop is not None:
            estop.close()


if __name__ == "__main__":
    raise SystemExit(main())
