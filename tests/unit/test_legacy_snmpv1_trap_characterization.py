from __future__ import annotations

from scripts.qualification.legacy_lab import capture_snmpv1_trap


def _length(length: int) -> bytes:
    if length < 128:
        return bytes([length])
    raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _length(len(value)) + value


def _integer(value: int) -> bytes:
    width = max(1, (value.bit_length() + 7) // 8)
    raw = value.to_bytes(width, "big")
    if raw[0] & 0x80:
        raw = b"\x00" + raw
    return _tlv(0x02, raw)


def _oid(value: str) -> bytes:
    arcs = [int(part) for part in value.split(".")]
    encoded = bytearray([40 * arcs[0] + arcs[1]])
    for arc in arcs[2:]:
        chunks = [arc & 0x7F]
        arc >>= 7
        while arc:
            chunks.append(0x80 | (arc & 0x7F))
            arc >>= 7
        encoded.extend(reversed(chunks))
    return _tlv(0x06, bytes(encoded))


def _synthetic_trap() -> bytes:
    text = b"out.TCP.from 192.0.2.10:55516 to 198.51.100.10:80"
    varbind = _tlv(
        0x30,
        _oid("1.3.6.1.4.1.3955.1.1.0") + _tlv(0x04, text),
    )
    trap_pdu = _tlv(
        0xA4,
        _oid("1.3.6.1.4.1.3955.1.1")
        + _tlv(0x40, bytes([192, 0, 2, 1]))
        + _integer(6)
        + _integer(1)
        + _tlv(0x43, b"\x00\x01\x00")
        + _tlv(0x30, varbind),
    )
    return _tlv(
        0x30,
        _integer(0)
        + _tlv(0x04, b"synthetic-community")
        + trap_pdu,
    )


def test_snmpv1_trap_parser_preserves_identity_boundary() -> None:
    parsed = capture_snmpv1_trap.parse_snmpv1_trap(_synthetic_trap())

    assert parsed["classification"] == "snmpv1_trap_candidate"
    assert parsed["snmp_version"] == 1
    assert parsed["community_observation"] == "synthetic-community"
    assert parsed["enterprise_oid_observation"] == "1.3.6.1.4.1.3955.1.1"
    assert parsed["agent_address_observation"] == "192.0.2.1"
    assert parsed["generic_trap_observation"] == 6
    assert parsed["specific_trap_observation"] == 1
    assert parsed["authenticated_source_identity_claim"] is False
    assert parsed["semantic_truth_claim"] is False
    assert parsed["community_security_boundary"].endswith(
        "not_authenticated_identity"
    )

    varbind = parsed["varbinds"][0]
    assert varbind["oid"] == "1.3.6.1.4.1.3955.1.1.0"
    assert "out.TCP.from 192.0.2.10" in varbind["value_observation"]["utf8_observation"]


def test_one_byte_mutation_changes_exact_datagram_digest() -> None:
    payload = _synthetic_trap()
    mutated = bytearray(payload)
    mutated[-1] ^= 0x01

    original = capture_snmpv1_trap.hashlib.sha256(payload).hexdigest()
    changed = capture_snmpv1_trap.hashlib.sha256(bytes(mutated)).hexdigest()

    assert original != changed


def test_non_snmpv1_payload_stays_unclassified() -> None:
    parsed = capture_snmpv1_trap.characterize(b"not-an-snmp-trap")

    assert parsed["classification"] == "not_snmpv1_trap"
    assert parsed["authenticated_source_identity_claim"] is False
    assert parsed["semantic_truth_claim"] is False
