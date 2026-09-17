#!/usr/bin/env python3
"""Render one pending P0 R0 mission and its Microsoft Graph listItem body."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from pydantic import JsonValue

from ets.demos.agent365_r0_mission import (
    MISSION_CONTRACT_ID,
    MISSION_SCENARIO_ID,
    SHAREPOINT_MISSION_LIST_NAME,
    create_pending_mission,
    sharepoint_create_item_body,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the one canonical mission_id for a pending Agent 365 + R0 demo mission "
            "and render the SharePoint listItem create body."
        )
    )
    parser.add_argument("--policy-version", required=True)
    parser.add_argument(
        "--command-parameters",
        required=True,
        help="Non-empty JSON object containing the bounded movement parameters.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        decoded = json.loads(args.command_parameters)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--command-parameters is not valid JSON: {exc}") from exc
    if not isinstance(decoded, dict) or not decoded:
        raise SystemExit("--command-parameters must be a non-empty JSON object")

    parameters: dict[str, JsonValue] = decoded
    mission = create_pending_mission(
        policy_version=args.policy_version,
        command_parameters=parameters,
    )
    output = {
        "contract_id": MISSION_CONTRACT_ID,
        "scenario_id": MISSION_SCENARIO_ID,
        "sharepoint_list": SHAREPOINT_MISSION_LIST_NAME,
        "mission_id": mission.mission_id,
        "authorization_material_sha256": mission.authorization_material_sha256(),
        "graph_create_body": sharepoint_create_item_body(mission),
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
