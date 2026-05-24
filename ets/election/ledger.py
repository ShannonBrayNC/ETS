"""Append-only election evidence ledger for the RC demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ets.election.models import ElectionEvidencePacket, hash_election_packet


class ElectionLedgerError(ValueError):
    """Base error for election ledger validation failures."""


class DuplicatePacketError(ElectionLedgerError):
    """Raised when a packet event ID has already been appended."""


class ChainContinuityError(ElectionLedgerError):
    """Raised when a packet does not reference the current ledger tip."""


class PacketNotFoundError(ElectionLedgerError):
    """Raised when a packet cannot be found by event ID."""


@dataclass(frozen=True)
class ElectionLedgerEntry:
    """Immutable ledger entry containing a packet and its canonical hash."""

    sequence: int
    packet: ElectionEvidencePacket
    event_hash: str


@dataclass(frozen=True)
class ChainVerificationIssue:
    """A deterministic chain verification issue."""

    sequence: int
    event_id: str
    code: str
    message: str


@dataclass(frozen=True)
class ChainVerificationResult:
    """Result of replaying an election evidence ledger."""

    valid: bool
    entry_count: int
    tip_hash: str | None
    issues: list[ChainVerificationIssue]


class ElectionPacketStore(Protocol):
    """WORM-compatible packet store contract."""

    def append(self, packet: ElectionEvidencePacket) -> ElectionLedgerEntry: ...

    def get_by_event_id(self, event_id: str) -> ElectionLedgerEntry: ...

    def list_entries(self) -> list[ElectionLedgerEntry]: ...


class InMemoryElectionLedger:
    """Append-only in-memory election packet ledger.

    The store is intentionally small and auditable for RC demos. It rejects
    duplicate event IDs and does not expose update or delete operations.
    """

    def __init__(self) -> None:
        self._entries: list[ElectionLedgerEntry] = []
        self._by_event_id: dict[str, ElectionLedgerEntry] = {}

    def append(self, packet: ElectionEvidencePacket) -> ElectionLedgerEntry:
        """Append a packet if it links to the current ledger tip."""

        if packet.event_id in self._by_event_id:
            raise DuplicatePacketError(f"duplicate election event_id: {packet.event_id}")

        expected_previous = self.tip_hash
        if packet.previous_event_hash != expected_previous:
            raise ChainContinuityError(
                "previous_event_hash does not match current election ledger tip"
            )

        entry = ElectionLedgerEntry(
            sequence=len(self._entries),
            packet=packet,
            event_hash=hash_election_packet(packet),
        )
        self._entries.append(entry)
        self._by_event_id[packet.event_id] = entry
        return entry

    @property
    def tip_hash(self) -> str | None:
        """Return the current ledger tip hash."""

        if not self._entries:
            return None
        return self._entries[-1].event_hash

    def get_by_event_id(self, event_id: str) -> ElectionLedgerEntry:
        """Return a ledger entry by event ID."""

        try:
            return self._by_event_id[event_id]
        except KeyError as exc:
            raise PacketNotFoundError(f"election event_id not found: {event_id}") from exc

    def list_entries(self) -> list[ElectionLedgerEntry]:
        """Return entries in append order."""

        return list(self._entries)


def verify_election_chain(entries: list[ElectionLedgerEntry]) -> ChainVerificationResult:
    """Replay ledger entries and validate hash-chain continuity."""

    issues: list[ChainVerificationIssue] = []
    previous_hash: str | None = None
    seen_event_ids: set[str] = set()
    tip_hash: str | None = None

    for expected_sequence, entry in enumerate(entries):
        recomputed_hash = hash_election_packet(entry.packet)
        if entry.sequence != expected_sequence:
            issues.append(
                ChainVerificationIssue(
                    sequence=entry.sequence,
                    event_id=entry.packet.event_id,
                    code="ETS_ELECTION_SEQUENCE_GAP",
                    message="ledger entry sequence does not match append order",
                )
            )
        if entry.packet.event_id in seen_event_ids:
            issues.append(
                ChainVerificationIssue(
                    sequence=entry.sequence,
                    event_id=entry.packet.event_id,
                    code="ETS_ELECTION_DUPLICATE_EVENT",
                    message="duplicate election event_id in replay",
                )
            )
        if entry.event_hash != recomputed_hash:
            issues.append(
                ChainVerificationIssue(
                    sequence=entry.sequence,
                    event_id=entry.packet.event_id,
                    code="ETS_ELECTION_EVENT_HASH_MISMATCH",
                    message="stored event hash does not match canonical packet hash",
                )
            )
        if entry.packet.previous_event_hash != previous_hash:
            issues.append(
                ChainVerificationIssue(
                    sequence=entry.sequence,
                    event_id=entry.packet.event_id,
                    code="ETS_ELECTION_PREVIOUS_HASH_MISMATCH",
                    message="packet previous_event_hash does not match replay tip",
                )
            )
        seen_event_ids.add(entry.packet.event_id)
        previous_hash = recomputed_hash
        tip_hash = recomputed_hash

    return ChainVerificationResult(
        valid=not issues,
        entry_count=len(entries),
        tip_hash=tip_hash,
        issues=issues,
    )


def export_election_audit_log(entries: list[ElectionLedgerEntry]) -> list[dict[str, Any]]:
    """Export an audit-safe ledger summary without raw sealed artifacts."""

    return [
        {
            "sequence": entry.sequence,
            "event_id": entry.packet.event_id,
            "election_id": entry.packet.election_id,
            "jurisdiction": entry.packet.jurisdiction,
            "event_type": entry.packet.event_type,
            "timestamp_utc": entry.packet.model_dump(mode="json")["timestamp_utc"],
            "privacy_class": entry.packet.privacy_class,
            "payload_hash": entry.packet.payload_hash,
            "previous_event_hash": entry.packet.previous_event_hash,
            "event_hash": entry.event_hash,
        }
        for entry in entries
    ]


def make_compensating_packet(
    original: ElectionEvidencePacket,
    *,
    event_id: str,
    timestamp_utc: Any,
    previous_event_hash: str,
    reason: str,
) -> ElectionEvidencePacket:
    """Create a compensating event without mutating the original packet."""

    payload = original.model_dump(mode="json")
    payload.update(
        {
            "event_id": event_id,
            "timestamp_utc": timestamp_utc,
            "previous_event_hash": previous_event_hash,
            "metadata": {
                **original.metadata,
                "compensates_event_id": original.event_id,
                "compensation_reason": reason,
            },
        }
    )
    return ElectionEvidencePacket.model_validate(payload)
