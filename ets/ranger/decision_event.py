"""Deterministic integrity helpers for ETS Ranger Decision Event v0.1.

The Ranger event digest and signature cover the canonical event body excluding
``event_digest`` and ``signature``.  This preserves a non-recursive integrity
boundary and reuses the ETS Core ``ets.canonical.json.v1`` serialization rules.

These helpers prove byte-level integrity and signer possession only.  They do
not prove semantic truth, sensor correctness, identity truth, or policy
sufficiency.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from ets.core.canonical_json import canonicalize

_DECISION_EVENT_SCHEMA_VERSION = "ranger.decision-event.v0.1"
_SIGNING_ALGORITHM = "ed25519"


class RangerDecisionIntegrityError(ValueError):
    """Raised when a Ranger Decision Event cannot be hashed, signed, or verified."""


def decision_event_preimage(event: Mapping[str, Any]) -> dict[str, Any]:
    """Return the immutable Ranger Decision Event hash/signature preimage.

    ``event_digest`` and ``signature`` are envelope fields and are excluded.
    Every other field participates, including epistemic state, source evidence,
    participating/excluded claims, policy, selected action, and chain linkage.
    """

    payload = deepcopy(dict(event))
    if payload.get("schema_version") != _DECISION_EVENT_SCHEMA_VERSION:
        raise RangerDecisionIntegrityError(
            f"schema_version must be {_DECISION_EVENT_SCHEMA_VERSION}"
        )
    payload.pop("event_digest", None)
    payload.pop("signature", None)
    return payload


def decision_event_canonical_bytes(event: Mapping[str, Any]) -> bytes:
    """Return canonical ETS Core bytes for the Ranger decision-event preimage."""

    return canonicalize(decision_event_preimage(event))


def decision_event_digest(event: Mapping[str, Any]) -> str:
    """Return ``sha256:<lowercase-hex>`` over canonical decision-event bytes."""

    digest = hashlib.sha256(decision_event_canonical_bytes(event)).hexdigest()
    return f"sha256:{digest}"


def sign_decision_event(
    event: Mapping[str, Any],
    *,
    private_key_hex: str,
    key_id: str,
) -> dict[str, Any]:
    """Return a copy of ``event`` with deterministic digest and Ed25519 signature.

    The exact signing input is ``decision_event_canonical_bytes(event)``.  The
    signature therefore covers the same semantic body as ``event_digest``.
    """

    if not key_id:
        raise RangerDecisionIntegrityError("key_id must not be empty")
    try:
        private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    except ValueError as exc:
        raise RangerDecisionIntegrityError(
            "private_key_hex must encode a 32-byte Ed25519 private key"
        ) from exc

    canonical = decision_event_canonical_bytes(event)
    signed = deepcopy(dict(event))
    signed["event_digest"] = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    signed["signature"] = {
        "algorithm": _SIGNING_ALGORITHM,
        "key_id": key_id,
        "value": private_key.sign(canonical).hex(),
    }
    return signed


def verify_decision_event(
    event: Mapping[str, Any],
    *,
    public_key_hex: str,
) -> bool:
    """Verify Ranger event digest and Ed25519 signature against canonical bytes."""

    expected_digest = event.get("event_digest")
    signature = event.get("signature")
    if not isinstance(expected_digest, str) or not isinstance(signature, Mapping):
        return False
    if signature.get("algorithm") != _SIGNING_ALGORITHM:
        return False
    signature_value = signature.get("value")
    if not isinstance(signature_value, str):
        return False

    canonical = decision_event_canonical_bytes(event)
    actual_digest = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    if expected_digest != actual_digest:
        return False

    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        signature_bytes = bytes.fromhex(signature_value)
        public_key.verify(signature_bytes, canonical)
    except (ValueError, InvalidSignature):
        return False
    return True


__all__ = [
    "RangerDecisionIntegrityError",
    "decision_event_preimage",
    "decision_event_canonical_bytes",
    "decision_event_digest",
    "sign_decision_event",
    "verify_decision_event",
]
