#!/usr/bin/env python3
"""Exact-byte SNMPv1 Trap capture for bounded legacy-device characterization.

The datagram SHA-256 is committed before BER/SNMP parsing. Parsed SNMP fields,
transport metadata, community strings, and varbind text remain observations;
none of them establish authenticated device identity or semantic truth.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import socket
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TLV:
    tag: int
    value: bytes
    next_offset: int


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def read_tlv(data: bytes, offset: int = 0) -> TLV:
    if offset >= len(data):
        raise ValueError("missing BER tag")
    tag = data[offset]
    offset += 1
    if offset >= len(data):
        raise ValueError("missing BER length")

    first = data[offset]
    offset += 1
    if first & 0x80:
        count = first & 0x7F
        if count == 0:
            raise ValueError("indefinite BER length is not supported")
        if count > 4 or offset + count > len(data):
            raise ValueError("invalid BER long-form length")
        length = int.from_bytes(data[offset : offset + count], "big")
        offset += count
    else:
        length = first

    end = offset + length
    if end > len(data):
        raise ValueError("BER value exceeds datagram")
    return TLV(tag=tag, value=data[offset:end], next_offset=end)


def decode_integer(value: bytes) -> int:
    if not value:
        raise ValueError("empty BER integer")
    return int.from_bytes(value, "big", signed=bool(value[0] & 0x80))


def decode_oid(value: bytes) -> str:
    if not value:
        raise ValueError("empty BER OID")
    first = value[0]
    first_arc = min(first // 40, 2)
    second_arc = first - (first_arc * 40)
    arcs = [first_arc, second_arc]
    current = 0
    in_component = False
    for byte in value[1:]:
        in_component = True
        current = (current << 7) | (byte & 0x7F)
        if not byte & 0x80:
            arcs.append(current)
            current = 0
            in_component = False
    if in_component:
        raise ValueError("unterminated BER OID component")
    return ".".join(str(part) for part in arcs)


def decode_value(tag: int, value: bytes) -> dict[str, Any]:
    if tag == 0x02:
        return {"type": "integer", "value": decode_integer(value)}
    if tag == 0x04:
        return {
            "type": "octet_string",
            "utf8_observation": value.decode("utf-8", errors="replace"),
            "hex": value.hex(),
        }
    if tag == 0x05:
        return {"type": "null", "value": None}
    if tag == 0x06:
        return {"type": "object_identifier", "value": decode_oid(value)}
    if tag == 0x40 and len(value) == 4:
        return {"type": "ip_address", "value": str(ipaddress.IPv4Address(value))}
    if tag in {0x41, 0x42, 0x43, 0x46}:
        names = {
            0x41: "counter32",
            0x42: "gauge32",
            0x43: "timeticks",
            0x46: "counter64",
        }
        return {"type": names[tag], "value": int.from_bytes(value, "big")}
    return {"type": f"ber_tag_0x{tag:02x}", "hex": value.hex()}


def parse_varbinds(data: bytes) -> list[dict[str, Any]]:
    outer = read_tlv(data)
    if outer.tag != 0x30 or outer.next_offset != len(data):
        raise ValueError("SNMP varbind list is not a bounded SEQUENCE")

    varbinds: list[dict[str, Any]] = []
    offset = 0
    while offset < len(outer.value):
        varbind = read_tlv(outer.value, offset)
        if varbind.tag != 0x30:
            raise ValueError("SNMP varbind is not a SEQUENCE")
        offset = varbind.next_offset

        name = read_tlv(varbind.value, 0)
        if name.tag != 0x06:
            raise ValueError("SNMP varbind name is not an OID")
        value = read_tlv(varbind.value, name.next_offset)
        if value.next_offset != len(varbind.value):
            raise ValueError("unexpected trailing bytes in SNMP varbind")
        varbinds.append(
            {
                "oid": decode_oid(name.value),
                "value_observation": decode_value(value.tag, value.value),
            }
        )
    return varbinds


def parse_snmpv1_trap(payload: bytes) -> dict[str, Any]:
    message = read_tlv(payload)
    if message.tag != 0x30 or message.next_offset != len(payload):
        raise ValueError("SNMP message is not one bounded SEQUENCE")

    offset = 0
    version = read_tlv(message.value, offset)
    offset = version.next_offset
    community = read_tlv(message.value, offset)
    offset = community.next_offset
    pdu = read_tlv(message.value, offset)

    if version.tag != 0x02 or decode_integer(version.value) != 0:
        raise ValueError("message is not SNMPv1")
    if community.tag != 0x04:
        raise ValueError("SNMP community is not an OCTET STRING")
    if pdu.tag != 0xA4:
        raise ValueError("message is not an SNMPv1 Trap-PDU")
    if pdu.next_offset != len(message.value):
        raise ValueError("unexpected trailing bytes after SNMP Trap-PDU")

    pdu_offset = 0
    enterprise = read_tlv(pdu.value, pdu_offset)
    pdu_offset = enterprise.next_offset
    agent = read_tlv(pdu.value, pdu_offset)
    pdu_offset = agent.next_offset
    generic = read_tlv(pdu.value, pdu_offset)
    pdu_offset = generic.next_offset
    specific = read_tlv(pdu.value, pdu_offset)
    pdu_offset = specific.next_offset
    timestamp = read_tlv(pdu.value, pdu_offset)
    pdu_offset = timestamp.next_offset
    varbinds = read_tlv(pdu.value, pdu_offset)

    if enterprise.tag != 0x06:
        raise ValueError("trap enterprise is not an OID")
    if agent.tag != 0x40 or len(agent.value) != 4:
        raise ValueError("trap agent address is not IPv4")
    if generic.tag != 0x02 or specific.tag != 0x02:
        raise ValueError("trap generic/specific values are not INTEGERs")
    if timestamp.tag != 0x43:
        raise ValueError("trap timestamp is not TimeTicks")
    if varbinds.tag != 0x30 or varbinds.next_offset != len(pdu.value):
        raise ValueError("trap varbinds are not a bounded SEQUENCE")

    return {
        "classification": "snmpv1_trap_candidate",
        "snmp_version": 1,
        "community_observation": community.value.decode("latin-1", errors="replace"),
        "community_security_boundary": (
            "legacy_cleartext_community_metadata_not_authenticated_identity"
        ),
        "enterprise_oid_observation": decode_oid(enterprise.value),
        "agent_address_observation": str(ipaddress.IPv4Address(agent.value)),
        "generic_trap_observation": decode_integer(generic.value),
        "specific_trap_observation": decode_integer(specific.value),
        "timeticks_observation": int.from_bytes(timestamp.value, "big"),
        "varbinds": _parse_varbind_sequence_value(varbinds.value),
        "authenticated_source_identity_claim": False,
        "semantic_truth_claim": False,
    }


def _parse_varbind_sequence_value(value: bytes) -> list[dict[str, Any]]:
    varbinds: list[dict[str, Any]] = []
    offset = 0
    while offset < len(value):
        varbind = read_tlv(value, offset)
        if varbind.tag != 0x30:
            raise ValueError("SNMP varbind is not a SEQUENCE")
        offset = varbind.next_offset
        name = read_tlv(varbind.value, 0)
        body = read_tlv(varbind.value, name.next_offset)
        if name.tag != 0x06 or body.next_offset != len(varbind.value):
            raise ValueError("invalid SNMP varbind")
        varbinds.append(
            {
                "oid": decode_oid(name.value),
                "value_observation": decode_value(body.tag, body.value),
            }
        )
    return varbinds


def characterize(payload: bytes) -> dict[str, Any]:
    try:
        return parse_snmpv1_trap(payload)
    except ValueError as exc:
        return {
            "classification": "not_snmpv1_trap",
            "parse_error": str(exc),
            "authenticated_source_identity_claim": False,
            "semantic_truth_claim": False,
        }


def capture(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if args.interface:
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_BINDTODEVICE,
            args.interface.encode() + b"\0",
        )
    sock.bind((args.bind_ip, args.port))
    sock.settimeout(min(1.0, args.seconds))

    started = utc_now()
    records: list[dict[str, Any]] = []
    deadline = time.monotonic() + args.seconds
    try:
        while time.monotonic() < deadline and len(records) < args.max_datagrams:
            try:
                payload, peer = sock.recvfrom(65535)
            except TimeoutError:
                continue

            # Evidence commitment occurs before any BER/SNMP interpretation.
            digest = hashlib.sha256(payload).hexdigest()
            ordinal = len(records) + 1
            raw_name = f"datagram-{ordinal:04d}.bin"
            (output_dir / raw_name).write_bytes(payload)

            parsed = characterize(payload)
            record = {
                "ordinal": ordinal,
                "received_at_utc": utc_now(),
                "source_ip_observation": peer[0],
                "source_port_observation": peer[1],
                "destination_ip_observation": args.bind_ip,
                "destination_port_observation": args.port,
                "byte_size": len(payload),
                "sha256": digest,
                "raw_datagram_file": raw_name,
                "parsed_observations": parsed,
                "authenticated_source_identity_claim": False,
            }
            (output_dir / f"datagram-{ordinal:04d}.json").write_text(
                json.dumps(record, indent=2) + "\n",
                encoding="utf-8",
            )
            records.append(record)
    finally:
        sock.close()

    snmpv1_count = sum(
        1
        for record in records
        if record["parsed_observations"]["classification"] == "snmpv1_trap_candidate"
    )
    summary = {
        "schema": "ets.legacy.snmpv1-trap-characterization.v1",
        "session_started_utc": started,
        "session_completed_utc": utc_now(),
        "bind_ip": args.bind_ip,
        "interface": args.interface,
        "port": args.port,
        "datagrams_received": len(records),
        "snmpv1_traps_observed": snmpv1_count,
        "qualification_claim": False,
        "authenticated_source_identity_claim": False,
        "claim_boundary": (
            "snmpv1_trap_characterization_only_not_authenticated_identity_"
            "not_complete_observation_not_semantic_truth_not_hardware_qualification"
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
    parser.add_argument("--port", type=int, default=162)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--max-datagrams", type=int, default=100)
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

    summary = capture(args)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
