import hashlib
from typing import Any

from .canonical import canonical_json_bytes


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_payload(payload: Any) -> str:
    return sha256_hex(canonical_json_bytes(payload))


def hash_leaf(
    event_id: str,
    timestamp_utc: str,
    payload_hash: str,
    event_type: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    envelope = {
        "event_id": event_id,
        "timestamp_utc": timestamp_utc,
        "type": event_type,
        "payload_hash": payload_hash,
        "metadata": metadata or {},
    }
    return sha256_hex(canonical_json_bytes(envelope))
