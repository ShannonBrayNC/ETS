from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ets.core import InMemoryAppendOnlyLog, generate_inclusion_proof  # noqa: E402
from ets.core.models import EvidenceEvent  # noqa: E402
from ets.core.proofs import verify_inclusion_proof  # noqa: E402


def make_demo_event(index: int) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=f"evt_merkle_{index:03d}",
        tenant_id="tenant_demo",
        workspace_id="workspace_demo",
        evidence_id=f"evidence_merkle_{index:03d}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash=f"{index + 1:064x}"[-64:],
        content_hash_alg="sha256",
        metadata={"demo": "merkle", "ordinal": index, "contains_real_pii": False},
        created_at_utc=datetime(2026, 5, 26, 13, index, tzinfo=UTC),
    )


def run_demo() -> dict[str, object]:
    log = InMemoryAppendOnlyLog()
    for index in range(4):
        log.append(make_demo_event(index))

    proof = generate_inclusion_proof(
        log.list_entries(),
        2,
        generated_at_utc=datetime(2026, 5, 26, 14, 0, tzinfo=UTC),
    )
    valid_result = verify_inclusion_proof(proof)
    tampered = proof.model_copy(update={"root_hash": "0" * 64})
    tampered_result = verify_inclusion_proof(tampered)

    return {
        "demo": "merkle-proof",
        "event_id": log.get_by_index(2).event.event_id,
        "proof": proof.model_dump(mode="json"),
        "valid_proof": valid_result.model_dump(mode="json"),
        "tampered_proof": tampered_result.model_dump(mode="json"),
    }


def main() -> int:
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
