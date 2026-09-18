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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate R0 bench GPIO, normally-closed E-stop, and dual VL53L0X sensors "
            "without authorizing motion."
        )
    )
    parser.add_argument("--left-in1", type=int, required=True)
    parser.add_argument("--left-in2", type=int, required=True)
    parser.add_argument("--right-in1", type=int, required=True)
    parser.add_argument("--right-in2", type=int, required=True)
    parser.add_argument("--estop-pin", type=int, required=True)
    parser.add_argument("--front-xshut", type=int, required=True)
    parser.add_argument("--rear-xshut", type=int, required=True)
    parser.add_argument("--calibrated-max-speed-mps", type=float, default=0.15)
    parser.add_argument("--max-duty-cycle", type=float, default=0.55)
    parser.add_argument("--output-json", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    calibration = R0BenchCalibrationV1(
        calibrated_max_speed_mps=args.calibrated_max_speed_mps,
        max_duty_cycle=args.max_duty_cycle,
    )

    motor = GpioZeroDrv8833Backend(
        left_in1_pin=args.left_in1,
        left_in2_pin=args.left_in2,
        right_in1_pin=args.right_in1,
        right_in2_pin=args.right_in2,
    )
    estop = GpioZeroNormallyClosedEstop(args.estop_pin)
    try:
        motor.stop()
        front, rear = create_dual_vl53l0x_backends(
            front_xshut_pin=args.front_xshut,
            rear_xshut_pin=args.rear_xshut,
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
                "profile": "r0-bench-pi-drv8833-dual-vl53l0x.v1",
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
        ) + "\\n"
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
