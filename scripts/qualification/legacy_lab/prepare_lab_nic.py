#!/usr/bin/env python3
"""Prepare one T430 NIC as an isolated legacy-device lab path.

Default mode is plan-only. Apply mode requires a second surviving default-route
interface and NetworkManager, preserves the original connection name in a local
record, creates a dedicated static lab profile, and verifies that the selected
NIC no longer carries a default route.
"""

from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def run(args: list[str], *, check: bool = True) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise SystemExit(
            f"ERROR: command failed ({result.returncode}): {' '.join(args)}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result.stdout.strip()


def default_route_interfaces() -> list[str]:
    tokens = run(["ip", "route", "show", "default"]).split()
    return [tokens[i + 1] for i, token in enumerate(tokens[:-1]) if token == "dev"]


def current_connection(interface: str) -> str:
    value = run(["nmcli", "-g", "GENERAL.CONNECTION", "device", "show", interface])
    if not value or value == "--":
        raise SystemExit(f"ERROR: no active NetworkManager connection on {interface}")
    return value


def interface_exists(interface: str) -> bool:
    result = subprocess.run(
        ["ip", "link", "show", "dev", interface],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def ensure_record_dir(record_dir: Path) -> None:
    """Create the local evidence directory without weakening ownership."""

    if record_dir.exists():
        return

    user = pwd.getpwuid(os.getuid()).pw_name
    group = grp.getgrgid(os.getgid()).gr_name
    run(
        [
            "sudo",
            "-n",
            "install",
            "-d",
            "-m",
            "0700",
            "-o",
            user,
            "-g",
            group,
            str(record_dir),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", required=True)
    parser.add_argument("--address", default="192.168.77.2/24")
    parser.add_argument("--connection-name")
    parser.add_argument(
        "--record-root",
        type=Path,
        default=Path("/srv/ets-lab/evidence/network-baseline"),
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    for command in ("ip", "nmcli"):
        if shutil.which(command) is None:
            raise SystemExit(f"ERROR: required command missing: {command}")

    if not interface_exists(args.interface):
        raise SystemExit(f"ERROR: interface does not exist: {args.interface}")

    defaults = default_route_interfaces()
    original = current_connection(args.interface)
    alternate_defaults = [name for name in defaults if name != args.interface]
    connection_name = args.connection_name or f"ets-lab-{args.interface}"

    plan = {
        "schema": "ets.t430.lab-nic-plan.v1",
        "interface": args.interface,
        "current_connection": original,
        "default_route_interfaces": defaults,
        "alternate_default_route_interfaces": alternate_defaults,
        "new_connection": connection_name,
        "lab_address": args.address,
        "ipv4_gateway": None,
        "ipv4_never_default": True,
        "ipv6_method": "disabled",
        "apply_requested": args.apply,
        "safety_gate": bool(alternate_defaults),
        "claim_boundary": "lab_network_preparation_only_not_hardware_qualification",
    }
    print(json.dumps(plan, indent=2))

    if not args.apply:
        print()
        print("PLAN ONLY: no network configuration was changed.")
        return 0

    if not alternate_defaults:
        raise SystemExit(
            f"ERROR: refusing to repurpose {args.interface}; "
            "no other interface currently provides a default route."
        )

    if subprocess.run(["sudo", "-n", "true"], check=False).returncode != 0:
        raise SystemExit("ERROR: sudo credentials are not active. Run sudo -v and retry.")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    record_dir = args.record_root.expanduser().resolve()
    ensure_record_dir(record_dir)

    original_profile = run(["nmcli", "connection", "show", original], check=False)

    record = record_dir / f"{args.interface}-{timestamp}.json"
    record_payload = {
        "plan": plan,
        "original_connection_profile": original_profile,
    }
    record.write_text(json.dumps(record_payload, indent=2) + "\n", encoding="utf-8")

    existing = run(["nmcli", "-t", "-f", "NAME", "connection", "show"]).splitlines()
    if connection_name in existing:
        run(
            [
                "sudo",
                "nmcli",
                "connection",
                "modify",
                connection_name,
                "connection.interface-name",
                args.interface,
                "ipv4.method",
                "manual",
                "ipv4.addresses",
                args.address,
                "ipv4.gateway",
                "",
                "ipv4.dns",
                "",
                "ipv4.never-default",
                "yes",
                "ipv6.method",
                "disabled",
            ]
        )
    else:
        run(
            [
                "sudo",
                "nmcli",
                "connection",
                "add",
                "type",
                "ethernet",
                "ifname",
                args.interface,
                "con-name",
                connection_name,
                "ipv4.method",
                "manual",
                "ipv4.addresses",
                args.address,
                "ipv4.never-default",
                "yes",
                "ipv6.method",
                "disabled",
            ]
        )

    run(["sudo", "nmcli", "connection", "up", connection_name])

    remaining_defaults = default_route_interfaces()
    if args.interface in remaining_defaults:
        raise SystemExit(
            f"ERROR: {args.interface} still carries a default route after lab-profile activation."
        )

    print()
    print("LAB_NIC_READY=true")
    print(f"interface={args.interface}")
    print(f"lab_address={args.address}")
    print(f"connection={connection_name}")
    print(f"original_connection={original}")
    print(f"baseline_record={record}")
    print()
    print("Rollback:")
    print(f"  sudo nmcli connection up {json.dumps(original)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
