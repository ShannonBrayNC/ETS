import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ets.election import (
    ChainContinuityError,
    DuplicatePacketError,
    ElectionEvidencePacket,
    ElectionLedgerEntry,
    InMemoryElectionLedger,
    PacketNotFoundError,
    export_election_audit_log,
    hash_election_packet,
    make_compensating_packet,
    verify_election_chain,
)
from ets.election.demo import build_sample_ledger, load_sample_packets, run_tamper_demo

ROOT = Path(__file__).resolve().parents[2]


def sample_packets() -> list[ElectionEvidencePacket]:
    path = ROOT / "ets/demos/election-security/sample-packets.json"
    return [
        ElectionEvidencePacket.model_validate_json(json.dumps(item))
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]


def test_append_only_ledger_appends_packets_in_order() -> None:
    ledger = InMemoryElectionLedger()
    packets = sample_packets()

    first = ledger.append(packets[0])
    second = ledger.append(packets[1])

    assert first.sequence == 0
    assert second.sequence == 1
    assert ledger.tip_hash == hash_election_packet(packets[1])
    assert ledger.list_entries() == [first, second]


def test_append_only_ledger_rejects_duplicate_event_id() -> None:
    ledger = InMemoryElectionLedger()
    packet = sample_packets()[0]
    ledger.append(packet)

    with pytest.raises(DuplicatePacketError):
        ledger.append(packet)


def test_append_only_ledger_rejects_broken_previous_hash() -> None:
    ledger = InMemoryElectionLedger()
    packet = sample_packets()[1]

    with pytest.raises(ChainContinuityError):
        ledger.append(packet)


def test_get_by_event_id_returns_entry_and_missing_is_deterministic() -> None:
    ledger = build_sample_ledger(sample_packets())

    assert ledger.get_by_event_id("elx_evt_0002").sequence == 1
    with pytest.raises(PacketNotFoundError):
        ledger.get_by_event_id("missing")


def test_replay_valid_chain_succeeds() -> None:
    ledger = build_sample_ledger(sample_packets())

    result = verify_election_chain(ledger.list_entries())

    assert result.valid is True
    assert result.entry_count == 3
    assert result.tip_hash == ledger.tip_hash
    assert result.issues == []


def test_replay_detects_tampered_packet_payload() -> None:
    ledger = build_sample_ledger(sample_packets())
    entries = ledger.list_entries()
    tampered_packet = entries[1].packet.model_copy(update={"payload_hash": "f" * 64}, deep=True)
    tampered_entries = [
        entries[0],
        ElectionLedgerEntry(
            sequence=entries[1].sequence,
            packet=tampered_packet,
            event_hash=entries[1].event_hash,
        ),
        entries[2],
    ]

    result = verify_election_chain(tampered_entries)

    assert result.valid is False
    assert [issue.code for issue in result.issues] == [
        "ETS_ELECTION_EVENT_HASH_MISMATCH",
        "ETS_ELECTION_PREVIOUS_HASH_MISMATCH",
    ]


def test_replay_detects_sequence_gap() -> None:
    ledger = build_sample_ledger(sample_packets())
    entries = ledger.list_entries()
    shifted = ElectionLedgerEntry(
        sequence=3,
        packet=entries[1].packet,
        event_hash=entries[1].event_hash,
    )

    result = verify_election_chain([entries[0], shifted])

    assert result.valid is False
    assert "ETS_ELECTION_SEQUENCE_GAP" in [issue.code for issue in result.issues]


def test_replay_detects_duplicate_event_id() -> None:
    ledger = build_sample_ledger(sample_packets())
    entries = ledger.list_entries()
    duplicate = ElectionLedgerEntry(
        sequence=1,
        packet=entries[0].packet,
        event_hash=entries[0].event_hash,
    )

    result = verify_election_chain([entries[0], duplicate])

    assert result.valid is False
    assert "ETS_ELECTION_DUPLICATE_EVENT" in [issue.code for issue in result.issues]


def test_export_election_audit_log_excludes_signature_and_raw_artifacts() -> None:
    ledger = build_sample_ledger(sample_packets())

    audit_log = export_election_audit_log(ledger.list_entries())

    assert audit_log[0]["event_id"] == "elx_evt_0001"
    assert "signature" not in audit_log[0]
    assert "metadata" not in audit_log[0]
    assert audit_log[0]["payload_hash"] == "1" * 64


def test_make_compensating_packet_preserves_original_and_links_tip() -> None:
    ledger = build_sample_ledger(sample_packets())
    original = ledger.get_by_event_id("elx_evt_0002").packet

    compensation = make_compensating_packet(
        original,
        event_id="elx_evt_0004",
        timestamp_utc=datetime(2026, 5, 4, 10, 0, tzinfo=UTC),
        previous_event_hash=ledger.tip_hash or "",
        reason="replace sealed artifact reference after clerical review",
    )
    entry = ledger.append(compensation)

    assert entry.sequence == 3
    assert original.event_id == "elx_evt_0002"
    assert compensation.metadata["compensates_event_id"] == original.event_id
    assert verify_election_chain(ledger.list_entries()).valid is True


def test_load_sample_packets_uses_default_fixture_path() -> None:
    packets = load_sample_packets()

    assert [packet.event_id for packet in packets] == [
        "elx_evt_0001",
        "elx_evt_0002",
        "elx_evt_0003",
    ]


def test_run_tamper_demo_reports_valid_and_tampered_outcomes() -> None:
    result = run_tamper_demo()

    assert result["valid_chain"] is True
    assert result["tampered_chain"] is False
    assert result["tamper_issue_codes"] == [
        "ETS_ELECTION_EVENT_HASH_MISMATCH",
        "ETS_ELECTION_PREVIOUS_HASH_MISMATCH",
    ]
    assert len(result["audit_log"]) == 3
