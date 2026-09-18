#!/usr/bin/env python3
"""Operator CLI for the retained Agent 365 -> physical R0 qualification campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ets.demos.agent365_r0_qualification_campaign import (
    R0QualificationPhase,
    R0QualificationPhaseState,
)
from ets.demos.agent365_r0_qualification_recorder import (
    append_phase,
    campaign_status,
    initialize_campaign,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the retained R0 qualification campaign.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--root", type=Path, required=True)
    init.add_argument("--campaign-id", required=True)
    init.add_argument("--code-sha", required=True)

    record = subparsers.add_parser("record-phase")
    record.add_argument("--root", type=Path, required=True)
    record.add_argument("--phase", choices=[phase.value for phase in R0QualificationPhase], required=True)
    record.add_argument(
        "--state",
        choices=[state.value for state in R0QualificationPhaseState if state is not R0QualificationPhaseState.NOT_RUN],
        required=True,
    )
    record.add_argument("--artifact", type=Path, action="append", default=[])
    record.add_argument("--note", action="append", default=[])
    record.add_argument("--mission-id", action="append", default=[])
    record.add_argument(
        "--operator-observation",
        choices=["both_wheels_forward"],
        default=None,
    )

    status = subparsers.add_parser("status")
    status.add_argument("--root", type=Path, required=True)

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "init":
        initialize_campaign(
            args.root,
            campaign_id=args.campaign_id,
            code_sha=args.code_sha,
        )
    elif args.command == "record-phase":
        append_phase(
            args.root,
            phase=R0QualificationPhase(args.phase),
            state=R0QualificationPhaseState(args.state),
            artifact_paths=tuple(args.artifact),
            notes=tuple(args.note),
            mission_ids=tuple(args.mission_id),
            operator_observation=args.operator_observation,
        )

    print(json.dumps(campaign_status(args.root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
