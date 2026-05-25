from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from ets.lantern_trust.contracts import LanternGovernanceEvent, LanternTrustReceipt


def canonicalize_event(event: LanternGovernanceEvent) -> str:
    return json.dumps(event.model_dump(), sort_keys=True, separators=(",", ":"))


def hash_event(event: LanternGovernanceEvent) -> str:
    canonical = canonicalize_event(event)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def issue_receipt(
    event: LanternGovernanceEvent,
    verifier: str,
    previous_hash: str = "genesis",
) -> LanternTrustReceipt:
    canonical_hash = hash_event(event)

    payload = f"{canonical_hash}:{previous_hash}:{verifier}"

    receipt_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return LanternTrustReceipt(
        receipt_id=str(uuid4()),
        governance_event=event,
        canonical_hash=canonical_hash,
        previous_hash=previous_hash,
        receipt_hash=receipt_hash,
        verifier=verifier,
        verified_utc=datetime.now(UTC).isoformat(),
    )
