#!/usr/bin/env python3
"""Explicitly armed wheels-off-ground qualification for the physical R0 bench."""

from __future__ import annotations

import argparse
from pathlib import Path

from ets.ranger.agent365_r0_bench_hardware import (
    GpioZeroDrv8833Backend,
    GpioZeroNormallyClosedEstop,
    create_dual_vl53l0x_backends,
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
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--left-in1", type=int, required=True)
    parser.add_argument("--left-in2", type=int, required=True)
    parser.add_argument("--right-in1", type=int, required=True)
    parser.add_argument("--right-in2", type=int, required=True)
    parser.add_argument("--estop-pin", type=int, required=True)
    parser.add_argument("--front-xshut", type=int, required=True)
    parser.add_argument("--rear-xshut", type=int, required=True)
    parser.add_argument("--duty-cycle", type=float, default=0.20)
    parser.add_argument("--pulse-seconds", type=float, default=0.40)
    parser.add_argument("--max-rear-translation-m", type=float, default=0.03)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.execute_wheels_off_ground:
        raise SystemExit(
            "Refusing motor initialization without --execute-wheels-off-ground"
        )

    config = R0WheelsOffGroundConfigV1(
        duty_cycle=args.duty_cycle,
        pulse_seconds=args.pulse_seconds,
        max_rear_translation_m=args.max_rear_translation_m,
    )

    motor: GpioZeroDrv8833Backend | None = None
    estop: GpioZeroNormallyClosedEstop | None = None
    try:
        motor = GpioZeroDrv8833Backend(
            left_in1_pin=args.left_in1,
            left_in2_pin=args.left_in2,
            right_in1_pin=args.right_in1,
            right_in2_pin=args.right_in2,
        )
        estop = GpioZeroNormallyClosedEstop(args.estop_pin)
        front, rear = create_dual_vl53l0x_backends(
            front_xshut_pin=args.front_xshut,
            rear_xshut_pin=args.rear_xshut,
        )
        result = run_wheels_off_ground_pulse(
            motor=motor,
            front_sensor=front,
            rear_sensor=rear,
            estop=estop,
            config=config,
        )
        payload = result.model_dump_json(indent=2) + "\n"
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
