import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.election import (
    ELECTION_EVENT_TYPES,
    PRIVACY_CLASSES,
    ElectionEvidencePacket,
    PacketSignature,
    hash_election_packet,
)

ROOT = Path(__file__).resolve().parents[2]


def make_packet(**overrides) -> ElectionEvidencePacket:
    data = {
        "event_id": "elx_evt_001",
        "election_id": "mock-election-2026",
        "jurisdiction": "Fictional County",
        "event_type": "election_config_registered",
        "actor_id": "actor_demo",
        "device_id": "device_demo",
        "timestamp_utc": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "payload_hash": "a" * 64,
        "previous_event_hash": None,
        "signature": PacketSignature(
            algorithm="simulated-ed25519",
            key_id="mock-key",
            value="simulated-signature",
        ),
        "privacy_class": "public",
        "artifact_ref": "sealed://mock-election/config.json",
        "metadata": {"b": 2, "a": 1},
    }
    data.update(overrides)
    return ElectionEvidencePacket(**data)


def test_packet_accepts_required_event_types() -> None:
    for event_type in ELECTION_EVENT_TYPES:
        packet = make_packet(event_type=event_type)
        assert packet.event_type == event_type


def test_packet_accepts_required_privacy_classes() -> None:
    for privacy_class in PRIVACY_CLASSES:
        packet = make_packet(privacy_class=privacy_class)
        assert packet.privacy_class == privacy_class


def test_packet_rejects_invalid_event_type() -> None:
    with pytest.raises(ValidationError):
        make_packet(event_type="vote_cast")


def test_packet_rejects_invalid_privacy_class() -> None:
    with pytest.raises(ValidationError):
        make_packet(privacy_class="secret")


def test_packet_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        make_packet(timestamp_utc=datetime(2026, 5, 1, 12, 0))


def test_packet_rejects_non_hex_payload_hash() -> None:
    with pytest.raises(ValidationError):
        make_packet(payload_hash="z" * 64)


def test_packet_hash_is_deterministic_for_metadata_key_order() -> None:
    left = make_packet(metadata={"b": 2, "a": 1})
    right = make_packet(metadata={"a": 1, "b": 2})

    assert hash_election_packet(left) == hash_election_packet(right)


def test_packet_hash_excludes_signature_envelope() -> None:
    left = make_packet(
        signature=PacketSignature(algorithm="simulated-ed25519", key_id="key-1", value="left")
    )
    right = make_packet(
        signature=PacketSignature(algorithm="simulated-ed25519", key_id="key-2", value="right")
    )

    assert hash_election_packet(left) == hash_election_packet(right)


def test_sample_packets_parse_and_chain() -> None:
    path = ROOT / "ets/demos/election-security/sample-packets.json"
    packets = [
        ElectionEvidencePacket.model_validate_json(json.dumps(item))
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]

    assert [packet.event_id for packet in packets] == [
        "elx_evt_0001",
        "elx_evt_0002",
        "elx_evt_0003",
    ]
    assert packets[0].previous_event_hash is None
    assert packets[1].previous_event_hash == hash_election_packet(packets[0])
    assert packets[2].previous_event_hash == hash_election_packet(packets[1])


def test_schema_file_matches_model_contract() -> None:
    schema_path = ROOT / "docs/spec/election-evidence-packet.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["title"] == "ElectionEvidencePacket"
    assert set(ELECTION_EVENT_TYPES).issubset(set(schema["properties"]["event_type"]["enum"]))
    assert set(PRIVACY_CLASSES).issubset(set(schema["properties"]["privacy_class"]["enum"]))
