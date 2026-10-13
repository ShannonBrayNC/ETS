#!/usr/bin/env python3
"""T430 legacy router characterization harness.

Inventory mode is read-only. Capture mode refuses an interface carrying an
active default route, binds only to the selected interface's IPv4 address, and
retains exact UDP datagram bytes before protocol classification.

This tool characterizes existing Linksys/D-Link hardware. It does not qualify a
device and does not turn IP/MAC/syslog fields into authenticated identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from capture_udp_syslog import capture


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def run_command(args: list[str]) -> str:
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout
    if completed.stderr:
        output += completed.stderr
    return output


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def default_route_interfaces() -> set[str]:
    output = run_command(["ip", "route", "show", "default"])
    interfaces: set[str] = set()
    tokens = output.split()
    for index, token in enumerate(tokens[:-1]):
        if token == "dev":
            interfaces.add(tokens[index + 1])
    return interfaces


def interface_ipv4(interface: str) -> str | None:
    output = run_command(["ip", "-4", "-o", "addr", "show", "dev", interface, "scope", "global"])
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 4:
            return fields[3].split("/", 1)[0]
    return None


def interface_exists(interface: str) -> bool:
    result = subprocess.run(
        ["ip", "link", "show", "dev", interface],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def port_in_use(port: int) -> bool:
    if not command_exists("ss"):
        return False
    output = run_command(["ss", "-lun"])
    needle = f":{port}"
    return any(needle in line for line in output.splitlines()[1:])


def write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def inventory() -> int:
    print("=== T430 LEGACY-LAB NETWORK INVENTORY ===")
    print(f"utc={utc_now()}")

    sections = [
        ("interfaces", ["ip", "-br", "link"]),
        ("addresses", ["ip", "-br", "address"]),
        ("default routes", ["ip", "route", "show", "default"]),
        ("route table", ["ip", "route", "show", "table", "main"]),
        ("neighbor observations", ["ip", "neigh", "show"]),
    ]
    for title, command in sections:
        print()
        print(f"--- {title} ---")
        print(run_command(command).rstrip())

    if command_exists("ss"):
        print()
        print("--- UDP listener observations ---")
        listeners = run_command(["ss", "-lunp"])
        selected = [
            line
            for line in listeners.splitlines()
            if ":514 " in line or ":5514 " in line
        ]
        print("\n".join(selected) if selected else "no UDP 514/5514 listener observed")

    print()
    print("No network configuration was changed.")
    return 0


def collect_context(
    output_dir: Path,
    *,
    interface: str,
    bind_ip: str,
    args: argparse.Namespace,
) -> None:
    metadata = {
        "schema": "ets.legacy-router.host-context.v1",
        "captured_at_utc": utc_now(),
        "device_label": args.device_label,
        "manufacturer": args.manufacturer,
        "model": args.model,
        "hardware_revision": args.hardware_revision,
        "firmware": args.firmware,
        "interface": interface,
        "bind_ip": bind_ip,
        "port": args.port,
        "qualification_claim": False,
        "authenticated_source_identity_claim": False,
    }
    write_text(output_dir / "session-metadata.json", json.dumps(metadata, indent=2) + "\n")

    commands = {
        "interface-link.txt": ["ip", "-details", "link", "show", "dev", interface],
        "interface-ipv4.txt": ["ip", "-4", "addr", "show", "dev", interface],
        "interface-routes.txt": ["ip", "route", "show", "dev", interface],
        "interface-neighbors-before.txt": ["ip", "neigh", "show", "dev", interface],
        "default-routes.txt": ["ip", "route", "show", "default"],
    }
    if command_exists("ethtool"):
        commands["ethtool.txt"] = ["ethtool", interface]
        commands["ethtool-driver.txt"] = ["ethtool", "-i", interface]
    if command_exists("timedatectl"):
        commands["time-source.txt"] = ["timedatectl", "show"]

    for filename, command in commands.items():
        write_text(output_dir / filename, run_command(command))

    device_path = Path("/sys/class/net") / interface / "device"
    try:
        resolved = str(device_path.resolve(strict=True))
    except FileNotFoundError:
        resolved = "unavailable"
    write_text(output_dir / "interface-device-path.txt", resolved + "\n")


def write_checksums(output_dir: Path) -> None:
    rows: list[str] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS", "SHA256SUMS.verify.txt"}:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.relative_to(output_dir)}")
    write_text(output_dir / "SHA256SUMS", "\n".join(rows) + "\n")
    write_text(
        output_dir / "SHA256SUMS.verify.txt",
        "PASS: all retained characterization artifacts were hashed after capture.\n",
    )


def characterize(args: argparse.Namespace) -> int:
    if not interface_exists(args.interface):
        raise SystemExit(f"ERROR: interface does not exist: {args.interface}")

    default_interfaces = default_route_interfaces()
    if args.interface in default_interfaces:
        raise SystemExit(
            f"ERROR: refusing capture on {args.interface}; it carries an active default route. "
            "Move the router to a dedicated lab NIC/path before capture."
        )

    bind_ip = args.bind_ip or interface_ipv4(args.interface)
    if not bind_ip:
        raise SystemExit(
            f"ERROR: no global IPv4 address found on {args.interface}; "
            "configure the isolated lab path or pass --bind-ip."
        )

    if port_in_use(args.port):
        raise SystemExit(
            f"ERROR: UDP port {args.port} already appears to be in use; "
            "refusing to steal an existing listener."
        )

    if args.port < 1024 and os.geteuid() != 0:
        raise SystemExit(
            f"ERROR: UDP port {args.port} is privileged. "
            "Use a configurable high lab port such as 5514, or run this capture with sudo."
        )

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_label = "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in args.device_label
    ).strip("_") or "device"
    output_dir = args.output_root.expanduser().resolve() / f"{safe_label}-{run_id}"
    output_dir.mkdir(parents=True, exist_ok=False)

    collect_context(output_dir, interface=args.interface, bind_ip=bind_ip, args=args)

    print("Starting bounded UDP characterization capture.")
    print(f"  device:    {args.device_label}")
    print(f"  interface: {args.interface}")
    print(f"  bind:      {bind_ip}:{args.port}")
    print(f"  duration:  {args.seconds}s")
    print(f"  output:    {output_dir}")
    print()
    print("Generate only a synthetic/non-sensitive router event during the capture window.")

    capture_args = SimpleNamespace(
        bind_ip=bind_ip,
        interface=args.interface if os.geteuid() == 0 else None,
        port=args.port,
        seconds=args.seconds,
        max_datagrams=args.max_datagrams,
        max_bytes=65535,
        output_dir=output_dir / "datagrams",
    )
    summary = capture(capture_args)

    write_text(
        output_dir / "interface-neighbors-after.txt",
        run_command(["ip", "neigh", "show", "dev", args.interface]),
    )

    disposition = summary["characterization_disposition"]
    next_gate = {
        "rfc5424_profile_candidate": (
            "Bind exact device/firmware/configuration and proceed to "
            "LEGACY-NET-SYSLOG-RT0 preflight."
        ),
        "bounded_adapter_or_fault_infrastructure_candidate": (
            "Do not claim RFC 5424 conformance. Retain exact bytes and define a "
            "bounded adapter extension if useful."
        ),
        "no_remote_syslog_observed": (
            "Use the device as network-fault infrastructure unless another "
            "supported log-export path is discovered."
        ),
    }[disposition]

    result: dict[str, Any] = {
        "schema": "ets.legacy-router.characterization-result.v1",
        "device_label": args.device_label,
        "interface": args.interface,
        "bind_ip": bind_ip,
        "port": args.port,
        "characterization_disposition": disposition,
        "datagrams_received": summary["datagrams_received"],
        "classification_counts": summary["classification_counts"],
        "next_gate": next_gate,
        "qualification_claim": False,
        "authenticated_source_identity_claim": False,
        "claim_boundary": (
            "characterization_only_not_hardware_qualification_"
            "not_authenticated_source_identity"
        ),
    }
    write_text(output_dir / "characterization-result.json", json.dumps(result, indent=2) + "\n")
    write_checksums(output_dir)

    print()
    print(json.dumps(result, indent=2))
    print()
    print(f"Characterization retained locally: {output_dir}")
    print("Do not publish serial/MAC/SSID or other unnecessary identifiers without redaction.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("inventory", help="read-only T430 network inventory")

    capture_parser = subparsers.add_parser(
        "capture",
        help="bounded exact-byte UDP syslog characterization",
    )
    capture_parser.add_argument("--interface", required=True)
    capture_parser.add_argument("--device-label", required=True)
    capture_parser.add_argument("--manufacturer", default="")
    capture_parser.add_argument("--model", default="")
    capture_parser.add_argument("--hardware-revision", default="")
    capture_parser.add_argument("--firmware", default="")
    capture_parser.add_argument("--bind-ip")
    capture_parser.add_argument("--port", type=int, default=5514)
    capture_parser.add_argument("--seconds", type=float, default=60.0)
    capture_parser.add_argument("--max-datagrams", type=int, default=100)
    capture_parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/srv/ets-lab/evidence/legacy-router-characterization"),
    )
    return parser


def main() -> int:
    if not command_exists("ip"):
        raise SystemExit("ERROR: iproute2 'ip' command is required")

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "inventory":
        return inventory()

    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.seconds <= 0 or args.seconds > 3600:
        parser.error("--seconds must be > 0 and <= 3600")
    if args.max_datagrams < 1 or args.max_datagrams > 10000:
        parser.error("--max-datagrams must be between 1 and 10000")

    return characterize(args)


if __name__ == "__main__":
    raise SystemExit(main())
