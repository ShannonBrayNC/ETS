from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ets.core import (  # noqa: E402
    GENESIS_BLOCK_HASH,
    InMemoryAppendOnlyLog,
    build_block,
    export_block,
    verify_chain,
)  # noqa: E402
from ets.core.models import EvidenceEvent  # noqa: E402


def make_demo_event(event_id: str, content_hash: str) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_demo",
        workspace_id="workspace_demo",
        evidence_id=f"evidence_{event_id}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash=content_hash,
        content_hash_alg="sha256",
        metadata={"demo": "hash-chain", "contains_real_pii": False},
        created_at_utc=datetime(2026, 5, 26, 12, 0, tzinfo=UTC),
) 


def run_demo() -> dict[str, object]:
    log = InMemoryAppendOnlyLog()
    first = log.append(make_demo_event("evt_demo_001", "a" * 64))
    second = log.append(make_demo_event("evt_demo_002", "b" * 64))
    created_at = datetime(2026, 5, 26, 12, 30, tzinfo=UTC)

    first_block = build_block(0, GENESIS_BLOCK_HASH, [first], created_at)
    second_block = build_block(1, first_block.block_hash, [second], created_at)
    valid_result = verify_chain([first_block, second_block])

    tampered_second_block = build_block(1, "1" * 64, [second], created_at)
    tampered_result = verify_chain([first_block, tampered_second_block])

    return {
        "demo": "hash-chain",
        "valid_chain": valid_result.__dict__,
        "tampered_chain": tampered_result.__dict__,
        "blocks": [export_block(first_block), export_block(second_block)],
    }


def main() -> int:
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
