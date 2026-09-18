#!/usr/bin/env python3
"""No-motion hardware preflight for the Agent 365 -> Ranger R0 bench profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import sleep

from ets.ranger.agent365_r0_bench_hardware import (
    DualRangeR0PhysicalSensors,
    GpioZeroDrv8833Backend,
    GpioZeroNormallyClosedEstop,
    R0BenchCalibrationV1,
    create_dual_vl53l0x_backends,
)
from ets.ranger.agent365_r0_hardware_config import (
    hardware_config_sha256,
    load_r0_bench_hardware_config,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate R0 bench GPIO, normally-closed E-stop, and dual VL53L0X sensors "
            "without authorizing motion."
        )
    )
    parser.add_argument("--hardware-config", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    hardware = load_r0_bench_hardware_config(args.hardware_config)
    gpio = hardware.gpio
    calibration = R0BenchCalibrationV1(
        calibrated_max_speed_mps=hardware.calibrated_max_speed_mps,
        max_duty_cycle=hardware.max_duty_cycle,
    )

    motor = GpioZeroDrv8833Backend(
        left_in1_pin=gpio.left_in1_bcm,
        left_in2_pin=gpio.left_in2_bcm,
        right_in1_pin=gpio.right_in1_bcm,
        right_in2_pin=gpio.right_in2_bcm,
    )
    estop = GpioZeroNormallyClosedEstop(gpio.estop_bcm)
    try:
        motor.stop()
        front, rear = create_dual_vl53l0x_backends(
            front_xshut_pin=gpio.front_xshut_bcm,
            rear_xshut_pin=gpio.rear_xshut_bcm,
            front_address=hardware.front_vl53l0x_address,
            rear_address=hardware.rear_vl53l0x_address,
        )
        sensors = DualRangeR0PhysicalSensors(
            front_sensor=front,
            rear_sensor=rear,
            estop=estop,
            calibration=calibration,
        )

        if sensors.hardware_estop_asserted():
            print(
                "FAIL: normally-closed E-stop circuit is open/asserted; motion remains disabled.",
                file=sys.stderr,
            )
            return 2

        samples: list[dict[str, float]] = []
        for _ in range(3):
            samples.append(
                {
                    "front_distance_m": front.read_distance_m(),
                    "rear_distance_m": rear.read_distance_m(),
                }
            )
            sleep(0.10)

        payload = json.dumps(
            {
                "profile": hardware.profile,
                "hardware_config_sha256": hardware_config_sha256(args.hardware_config),
                "gpio": gpio.model_dump(mode="json"),
                "motion_authorized": False,
                "estop_circuit_closed": True,
                "actuator_outputs_forced_stopped": True,
                "calibration": calibration.model_dump(mode="json"),
                "range_samples": samples,
                "claim_boundary": (
                    "preflight_only_no_motor_motion_or_physical_mission_claim"
                ),
            },
            indent=2,
            sort_keys=True,
        ) + "\n"
        if args.output_json is not None:
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            args.output_json.write_text(payload, encoding="utf-8")
        print(payload, end="")
        return 0
    finally:
        motor.stop()
        motor.close()
        estop.close()


if __name__ == "__main__":
    raise SystemExit(main())
