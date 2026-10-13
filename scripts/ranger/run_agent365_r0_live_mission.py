#!/usr/bin/env python3
"""Operator-gated launcher for one fully live Agent 365 -> physical R0 mission."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from ets.demos.agent365_r0_correlation import Agent365R0CorrelationBundleV1
from ets.demos.agent365_r0_live_mission import (
    RangerR0HardwareRunAttestationV1,
    run_agent365_r0_live_mission,
)
from ets.demos.agent365_r0_live_runner import authorize_live_hardware_launch
from ets.demos.agent365_r0_profile_qualification import Agent365ProfileQualificationResultV1
from ets.demos.agent365_r0_sharepoint_live import SharePointMissionLiveObservationV1
from ets.ranger.agent365_r0_bench_hardware import (
    Drv8833R0Actuator,
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
        description="Execute exactly one operator-confirmed live Agent 365 -> R0 bench mission."
    )
    parser.add_argument("--qualification-json", type=Path, required=True)
    parser.add_argument("--sharepoint-json", type=Path, required=True)
    parser.add_argument("--correlation-json", type=Path, required=True)
    parser.add_argument("--hardware-config", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--confirm-mission-id", required=True)
    parser.add_argument("--execute-live-mission", action="store_true")
    parser.add_argument("--operator-subject", required=True)
    parser.add_argument("--run-id", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    qualification = Agent365ProfileQualificationResultV1.model_validate_json(
        args.qualification_json.read_text(encoding="utf-8")
    )
    sharepoint = SharePointMissionLiveObservationV1.model_validate_json(
        args.sharepoint_json.read_text(encoding="utf-8")
    )
    correlation = Agent365R0CorrelationBundleV1.model_validate_json(
        args.correlation_json.read_text(encoding="utf-8")
    )
    hardware = load_r0_bench_hardware_config(args.hardware_config)
    gpio = hardware.gpio

    mission_id = authorize_live_hardware_launch(
        qualification=qualification,
        sharepoint_observation=sharepoint,
        correlation_bundle=correlation,
        confirmed_mission_id=args.confirm_mission_id,
        execute_live_mission=args.execute_live_mission,
    )

    calibration = R0BenchCalibrationV1(
        calibrated_max_speed_mps=hardware.calibrated_max_speed_mps,
        max_duty_cycle=hardware.max_duty_cycle,
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
        actuator = Drv8833R0Actuator(motor, calibration)
        sensors = DualRangeR0PhysicalSensors(
            front_sensor=front,
            rear_sensor=rear,
            estop=estop,
            calibration=calibration,
        )

        if sensors.hardware_estop_asserted():
            raise RuntimeError(
                "normally-closed hardware E-stop is asserted/open; live mission denied"
            )

        attestation = RangerR0HardwareRunAttestationV1(
            run_id=args.run_id,
            mission_id=mission_id,
            actuator_id=actuator.actuator_id,
            result_observer_id=sensors.observer_id,
            operator_subject=args.operator_subject,
            attested_at=datetime.now(UTC),
        )
        result = run_agent365_r0_live_mission(
            args.workdir,
            qualification=qualification,
            sharepoint_observation=sharepoint,
            correlation_bundle=correlation,
            actuator=actuator,
            sensors=sensors,
            hardware_attestation=attestation,
        )
        print(
            json.dumps(
                {
                    "mission_id": result.report.mission_id,
                    "report_sha256": result.report_sha256,
                    "hardware_config_sha256": hardware_config_sha256(
                        args.hardware_config
                    ),
                    "physical_result_supported": result.report.physical_result_supported,
                    "physical_store_reopened": result.report.physical_store_reopened,
                    "agent365_correlation_store_reopened": (
                        result.report.agent365_correlation_store_reopened
                    ),
                    "claim_boundary": result.report.claim_boundary,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
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
