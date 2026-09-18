#!/usr/bin/env python3
"""Capture exact UDP syslog datagrams for bounded legacy-device characterization.

This is a lab characterization helper, not a qualification verifier. It hashes
the exact received UDP payload before protocol classification and never upgrades
transport/message fields into authenticated source identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RFC5424_PREFIX = re.compile(
    rb"^<(?P<pri>\d{1,3})>1 "
    rb"(?P<timestamp>\S+) "
    rb"(?P<hostname>\S+) "
    rb"(?P<app_name>\S+) "
    rb"(?P<procid>\S+) "
    rb"(?P<msgid>\S+) "
)
RFC3164_PREFIX = re.compile(
    rb"^<(?P<pri>\d{1,3})>"
    rb"(?P<month>[A-Z][a-z]{2})\s+"
    rb"(?P<day>\d{1,2})\s+"
    rb"(?P<time>\d{2}:\d{2}:\d{2})\s+"
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _bounded_ascii(value: bytes, limit: int = 256) -> str:
    return value[:limit].decode("ascii", errors="replace")


def classify(payload: bytes) -> tuple[str, dict[str, Any]]:
    """Classify after the caller has already committed the payload digest."""

    match_5424 = RFC5424_PREFIX.match(payload)
    if match_5424:
        groups = match_5424.groupdict()
        return (
            "rfc5424_version_1_candidate",
            {
                "pri": int(groups["pri"]),
                "version": 1,
                "timestamp_observation": _bounded_ascii(groups["timestamp"]),
                "hostname_observation": _bounded_ascii(groups["hostname"]),
                "app_name_observation": _bounded_ascii(groups["app_name"]),
                "procid_observation": _bounded_ascii(groups["procid"]),
                "msgid_observation": _bounded_ascii(groups["msgid"]),
                "identity_boundary": "message_fields_are_observations_not_authenticated_identity",
            },
        )

    match_3164 = RFC3164_PREFIX.match(payload)
    if match_3164:
        groups = match_3164.groupdict()
        return (
            "rfc3164_like_candidate",
            {
                "pri": int(groups["pri"]),
                "timestamp_prefix_observation": " ".join(
                    (
                        _bounded_ascii(groups["month"]),
                        _bounded_ascii(groups["day"]),
                        _bounded_ascii(groups["time"]),
                    )
                ),
                "identity_boundary": "legacy_message_fields_are_observations_not_authenticated_identity",
            },
        )

    return (
        "vendor_specific_or_unclassified",
        {
            "identity_boundary": "transport_and_message_fields_are_observations_not_authenticated_identity"
        },
    )


def capture(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    session_started = _utc_now()
    records: list[dict[str, Any]] = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if args.interface:
        # Linux-specific and intentionally explicit. Binding failure is safer than
        # silently receiving from a different interface.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, args.interface.encode() + b"\0")
    sock.bind((args.bind_ip, args.port))
    sock.settimeout(min(1.0, args.seconds))

    deadline = time.monotonic() + args.seconds
    try:
        while time.monotonic() < deadline and len(records) < args.max_datagrams:
            try:
                payload, peer = sock.recvfrom(args.max_bytes)
            except TimeoutError:
                continue

            received_at = _utc_now()

            # Commitment boundary: hash exact bytes before parsing/classification.
            digest = hashlib.sha256(payload).hexdigest()
            ordinal = len(records) + 1
            raw_name = f"datagram-{ordinal:04d}.bin"
            raw_path = output_dir / raw_name
            raw_path.write_bytes(payload)

            classification, observations = classify(payload)
            record = {
                "ordinal": ordinal,
                "received_at_utc": received_at,
                "source_ip_observation": peer[0],
                "source_port_observation": peer[1],
                "destination_ip_observation": args.bind_ip,
                "destination_port_observation": args.port,
                "byte_size": len(payload),
                "sha256": digest,
                "raw_datagram_file": raw_name,
                "classification": classification,
                "observations": observations,
                "authenticated_source_identity_claim": False,
            }
            (output_dir / f"datagram-{ordinal:04d}.json").write_text(
                json.dumps(record, indent=2) + "\n",
                encoding="utf-8",
            )
            records.append(record)
    finally:
        sock.close()

    counts: dict[str, int] = {}
    for record in records:
        key = str(record["classification"])
        counts[key] = counts.get(key, 0) + 1

    if counts.get("rfc5424_version_1_candidate", 0) > 0:
        disposition = "rfc5424_profile_candidate"
    elif records:
        disposition = "bounded_adapter_or_fault_infrastructure_candidate"
    else:
        disposition = "no_remote_syslog_observed"

    summary = {
        "schema": "ets.legacy-router.characterization.v1",
        "session_started_utc": session_started,
        "session_completed_utc": _utc_now(),
        "bind_ip": args.bind_ip,
        "interface": args.interface,
        "port": args.port,
        "duration_seconds": args.seconds,
        "max_datagrams": args.max_datagrams,
        "datagrams_received": len(records),
        "classification_counts": counts,
        "characterization_disposition": disposition,
        "authenticated_source_identity_claim": False,
        "qualification_claim": False,
        "claim_boundary": (
            "legacy_router_characterization_only_not_authenticated_source_identity_"
            "not_complete_observation_not_hardware_qualification"
        ),
    }
    (output_dir / "session-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-ip", required=True)
    parser.add_argument("--interface")
    parser.add_argument("--port", type=int, default=514)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--max-datagrams", type=int, default=100)
    parser.add_argument("--max-bytes", type=int, default=65535)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.seconds <= 0 or args.seconds > 3600:
        parser.error("--seconds must be > 0 and <= 3600")
    if args.max_datagrams < 1 or args.max_datagrams > 10000:
        parser.error("--max-datagrams must be between 1 and 10000")
    if args.max_bytes < 1 or args.max_bytes > 65535:
        parser.error("--max-bytes must be between 1 and 65535")

    summary = capture(args)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
