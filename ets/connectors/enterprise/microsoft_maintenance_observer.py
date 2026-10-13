"""Synthetic retained SharePoint maintenance-item comparison for DemoDriver DD-020.

No network acquisition, authorization, target mutation or live-source claim is provided.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

from ets.connectors.enterprise.microsoft_sharepoint_state import snapshot_sharepoint_metadata_record

_MAX_BYTES = 16 * 1024
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = ("CaseId", "TicketId", "ApprovalStatus", "DraftSha256", "OutboundCommunicationAllowed")


@dataclass(frozen=True)
class MaintenanceExpectation:
    """Verifier-owned expected state; source/producer claims cannot overwrite it."""

    item_id: str
    case_id: str
    ticket_id: str
    draft_sha256: str

    def __post_init__(self) -> None:
        for value in (self.item_id, self.case_id, self.ticket_id):
            if not isinstance(value, str) or not 1 <= len(value) <= 256:
                raise ValueError("maintenance identity must contain 1-256 characters")
            if any(ord(char) < 32 for char in value):
                raise ValueError("maintenance identity contains control data")
        if not isinstance(self.draft_sha256, str) or not _HEX.fullmatch(self.draft_sha256):
            raise ValueError("draft digest must be lowercase SHA-256")


@dataclass(frozen=True)
class MaintenanceObservation:
    """Minimized comparison receipt; does not retain source field values."""

    source_sha256: str
    expectation_sha256: str
    outcome: Literal["observed", "unresolved", "contradictory"]
    assertions: tuple[tuple[str, bool], ...]
    metadata_sha256: str | None
    producer_reported_success: bool | None
    mode: Literal["simulated-source"] = "simulated-source"
    qualified: Literal[False] = False


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate source key")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise ValueError("non-finite source number")


def observe_synthetic_maintenance_item(
    payload: bytes,
    *,
    expected: MaintenanceExpectation,
    producer_reported_success: bool | None = None,
) -> MaintenanceObservation:
    """Compare already-retained synthetic Graph bytes; producer success is context only.

    Caller retains exact source bytes under its fixture policy before invoking this function.
    The raw digest binds this receipt to those bytes. The existing ETS snapshot primitive
    supplies the bounded metadata commitment; no operational state is advanced.
    """
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= _MAX_BYTES:
        raise ValueError("maintenance source exceeds byte bound")
    if not isinstance(expected, MaintenanceExpectation):
        raise ValueError("verifier-owned maintenance expectation is required")
    if producer_reported_success is not None and type(producer_reported_success) is not bool:
        raise ValueError("producer success must be boolean or unavailable")
    expected_fields = {
        "CaseId": expected.case_id,
        "TicketId": expected.ticket_id,
        "ApprovalStatus": "approved",
        "DraftSha256": expected.draft_sha256,
        "OutboundCommunicationAllowed": False,
    }
    expected_bytes = json.dumps(
        {"id": expected.item_id, "fields": expected_fields}, sort_keys=True, separators=(",", ":")
    ).encode()
    source_hash = hashlib.sha256(payload).hexdigest()
    expectation_hash = hashlib.sha256(expected_bytes).hexdigest()
    assertions: list[tuple[str, bool]] = []
    outcome: Literal["observed", "unresolved", "contradictory"] = "unresolved"
    metadata_hash = None
    try:
        decoded = json.loads(payload.decode("utf-8"), object_pairs_hook=_object,
                             parse_constant=_constant)
        if not isinstance(decoded, dict) or not isinstance(decoded.get("fields"), dict):
            raise ValueError("source item or fields missing")
        fields = decoded["fields"]
        complete = isinstance(decoded.get("id"), str) and 1 <= len(decoded["id"]) <= 256
        for name in _FIELDS:
            value = fields.get(name)
            valid = (type(value) is bool if name == "OutboundCommunicationAllowed"
                     else isinstance(value, str) and 1 <= len(value) <= 256)
            if name == "DraftSha256":
                valid = isinstance(value, str) and _HEX.fullmatch(value) is not None
            complete = complete and valid
            assertions.append((name + "_present_valid", valid))
        assertions.append(("item_identity", decoded.get("id") == expected.item_id))
        assertions.append(("not_deleted", "deleted" not in decoded))
        for name, value in expected_fields.items():
            assertions.append((name + "_matches", type(fields.get(name)) is type(value)
                               and fields.get(name) == value))
        if complete:
            # Only bounded, interpreted fields enter operational metadata hashing.
            snapshot = snapshot_sharepoint_metadata_record({
                "object_id": decoded["id"], "scope": "list", "deleted": "deleted" in decoded,
                "metadata": {name: fields[name] for name in _FIELDS},
            })
            metadata_hash = snapshot.metadata_sha256
            outcome = "observed" if all(ok for _, ok in assertions) else "contradictory"
    except (ValueError, UnicodeError, RecursionError):
        assertions.append(("source_shape", False))
    return MaintenanceObservation(
        source_sha256=source_hash, expectation_sha256=expectation_hash,
        outcome=outcome, assertions=tuple(assertions), metadata_sha256=metadata_hash,
        producer_reported_success=producer_reported_success,
    )
