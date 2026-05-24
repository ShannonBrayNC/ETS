"""Executable helpers for the election ledger tamper demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ets.election.ledger import (
    ElectionLedgerEntry,
    InMemoryElectionLedger,
    export_election_audit_log,
    verify_election_chain,
)
from ets.election.models import ElectionEvidencePacket


def load_sample_packets(
    path: Path = Path("ets/demos/election-security/sample-packets.json"),
) -> list[ElectionEvidencePacket]:
    """Load fictional election evidence packets from JSON."""

    return [
        ElectionEvidencePacket.model_validate_json(json.dumps(item))
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]


def build_sample_ledger(
    packets: list[ElectionEvidencePacket] | None = None,
) -> InMemoryElectionLedger:
    """Build an append-only ledger from sample packets."""

    ledger = InMemoryElectionLedger()
    for packet in packets or load_sample_packets():
        ledger.append(packet)
    return ledger


def run_tamper_demo() -> dict[str, Any]:
    """Run a deterministic tamper demo and return audit-safe results."""

    ledger = build_sample_ledger()
    valid_result = verify_election_chain(ledger.list_entries())

    entries = ledger.list_entries()
    tampered_packet = entries[1].packet.model_copy(
        update={"payload_hash": "f" * 64},
        deep=True,
    )
    tampered_entries = [
        entries[0],
        ElectionLedgerEntry(
            sequence=entries[1].sequence,
            packet=tampered_packet,
            event_hash=entries[1].event_hash,
        ),
        entries[2],
    ]
    tampered_result = verify_election_chain(tampered_entries)

    return {
        "valid_chain": valid_result.valid,
        "tampered_chain": tampered_result.valid,
        "tamper_issue_codes": [issue.code for issue in tampered_result.issues],
        "audit_log": export_election_audit_log(entries),
    }


def main() -> int:
    """Print the tamper demo result as deterministic JSON."""

    print(json.dumps(run_tamper_demo(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
