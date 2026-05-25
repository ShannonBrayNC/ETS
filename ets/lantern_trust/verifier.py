from __future__ import annotations

import hashlib

from ets.lantern_trust.contracts import LanternTrustReceipt
from ets.lantern_trust.notary import hash_event


def verify_receipt(receipt: LanternTrustReceipt) -> bool:
    recalculated_hash = hash_event(receipt.governance_event)

    if recalculated_hash != receipt.canonical_hash:
        return False

    payload = (
        f"{receipt.canonical_hash}:{receipt.previous_hash}:{receipt.verifier}"
    )

    expected_receipt_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return expected_receipt_hash == receipt.receipt_hash
