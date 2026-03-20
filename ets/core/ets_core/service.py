import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .canonical import canonical_json_bytes
from .hashing import hash_payload, hash_leaf
from .merkle import merkle_root, inclusion_proof, verify_inclusion
from .storage import EventStore


class TransparencyLogService:
    def __init__(self, db_path: str):
        self.store = EventStore(db_path)

    @staticmethod
    def utc_now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def append_event(self, payload: Any, event_type: str, metadata: dict | None = None, event_id: str | None = None) -> dict:
        event_id = event_id or str(uuid.uuid4())
        timestamp_utc = self.utc_now_iso()
        payload_hash = hash_payload(payload)
        leaf_hash = hash_leaf(
            event_id=event_id,
            timestamp_utc=timestamp_utc,
            payload_hash=payload_hash,
            event_type=event_type,
            metadata=metadata or {}
        )

        self.store.insert_event(
            event_id=event_id,
            timestamp_utc=timestamp_utc,
            event_type=event_type,
            payload_json=canonical_json_bytes(payload).decode("utf-8"),
            payload_hash=payload_hash,
            leaf_hash=leaf_hash,
            metadata_json=canonical_json_bytes(metadata or {}).decode("utf-8")
        )

        return {
            "event_id": event_id,
            "timestamp_utc": timestamp_utc,
            "type": event_type,
            "payload_hash": payload_hash,
            "leaf_hash": leaf_hash
        }

    def get_event(self, event_id: str) -> dict | None:
        row = self.store.get_event_by_event_id(event_id)
        if row is None:
            return None

        return {
            "id": row["id"],
            "event_id": row["event_id"],
            "timestamp_utc": row["timestamp_utc"],
            "type": row["type"],
            "payload_json": json.loads(row["payload_json"]),
            "payload_hash": row["payload_hash"],
            "leaf_hash": row["leaf_hash"],
            "metadata_json": json.loads(row["metadata_json"])
        }

    def tree_head(self) -> dict:
        rows = self.store.list_events()
        leaves = [row["leaf_hash"] for row in rows]
        root = merkle_root(leaves)
        return {
            "tree_size": len(leaves),
            "root_hash": root
        }

    def proof_for_event(self, event_id: str) -> dict | None:
        rows = self.store.list_events()
        leaves = [row["leaf_hash"] for row in rows]

        target_index = None
        target_row = None

        for idx, row in enumerate(rows):
            if row["event_id"] == event_id:
                target_index = idx
                target_row = row
                break

        if target_index is None or target_row is None:
            return None

        root = merkle_root(leaves)
        proof = inclusion_proof(leaves, target_index)

        return {
            "event_id": event_id,
            "leaf_hash": target_row["leaf_hash"],
            "tree_size": len(leaves),
            "root_hash": root,
            "proof": proof
        }

    def verify_payload_against_event(self, event_id: str, payload: Any) -> dict | None:
        event = self.get_event(event_id)
        if event is None:
            return None

        candidate_hash = hash_payload(payload)
        matches = candidate_hash == event["payload_hash"]

        proof_bundle = self.proof_for_event(event_id)
        included = False
        if proof_bundle:
            included = verify_inclusion(
                leaf_hash=proof_bundle["leaf_hash"],
                proof=proof_bundle["proof"],
                expected_root=proof_bundle["root_hash"]
            )

        return {
            "event_id": event_id,
            "payload_hash_matches": matches,
            "included_in_tree": included,
            "expected_payload_hash": event["payload_hash"],
            "candidate_payload_hash": candidate_hash
        }
